"""BDS's cereal JSON reader and writer, over the bound packets and the compiler's schema model."""

import enum
import importlib
import keyword
import math
import re
import struct
import uuid
from copy import copy
from functools import cache, reduce
from operator import or_
from pathlib import Path
from types import SimpleNamespace

from bedrock_protocol import nbt
from bedrock_protocol_compiler.builder import build
from bedrock_protocol_compiler.descriptor import (
    AliasRef,
    Array,
    Bitset,
    BuiltinRef,
    EnumName,
    EnumRef,
    List,
    Literal,
    Map,
    MemberRef,
    Primitive,
    Struct,
    StructRef,
    Variant,
)
from bedrock_protocol_compiler.descriptor import Optional as OptionalType
from bedrock_protocol_compiler.schema import Schema

MODEL = Schema(build(Path(__file__).parents[1] / "protocol"))


def qualified_name(family):
    return family.name if family.owner is None else f"{qualified_name(family.owner)}.{family.name}"


FAMILIES = {qualified_name(family): family for family in MODEL.order if isinstance(family, Struct)}


class SchemaRWType(enum.IntFlag):
    NONE = 0
    OBJECT = 1
    ARRAY = 2
    OTHER = 4


class ErrorCode(enum.IntEnum):
    UNRECOGNIZED_FIELD = 4
    ERROR = 8
    MISSING_REQUIRED_FIELD = 128
    INVALID_ENUM_VALUE = 4096


class SerializationTraits(enum.IntFlag):
    NONE = 0
    COMPRESSION = 1
    ENUM_AS_VALUE = 4


class LoadError(ValueError):
    """The entries a strict load logged."""


class SerializerContext:
    """The log of one load or save, which counts the codes of its error mask as errors."""

    STRICT_ERROR_CODES = 0xFFFC

    def __init__(self):
        self.entries = []

    def log(self, code, message):
        self.entries.append((code, message))

    def get_log_checkpoint(self):
        return len(self.entries)

    def clear_generations(self, start, end):
        del self.entries[start:end]

    def has_error(self, checkpoint=0):
        return any(code & self.STRICT_ERROR_CODES for code, _ in self.entries[checkpoint:])


FLOAT_LIMIT = struct.unpack(">d", bytes.fromhex("47EFFFFFD586B834"))[0]
NON_FINITE = {"NaN": math.nan, "Infinity": math.inf, "-Infinity": -math.inf}


class CaseForm:
    """The case spelling of what BDS prints outside JSON, which is one place to change."""

    @classmethod
    def number_out(cls, value):
        if isinstance(value, float) and not math.isfinite(value):
            return "NaN" if math.isnan(value) else "Infinity" if value > 0 else "-Infinity"
        return value

    @classmethod
    def number_in(cls, value):
        return NON_FINITE.get(value, value) if isinstance(value, str) else value

    @staticmethod
    def text(raw):
        return raw.decode("latin-1")

    @staticmethod
    def raw(text):
        try:
            return text.encode("latin-1")
        except UnicodeEncodeError:
            return None

    @classmethod
    def stream(cls, tokens):
        tokens = [
            {key: cls.number_out(each) for key, each in token.items()} if isinstance(token, dict) else token
            for token in tokens
        ]
        return tokens[0] if len(tokens) == 1 else tokens

    @staticmethod
    def tokens(node):
        return node if isinstance(node, list) else [node]


class SchemaReader:
    def expected_type(self):
        raise NotImplementedError

    def as_bool(self):
        raise NotImplementedError

    def as_string(self):
        raise NotImplementedError

    def as_raw_bytes(self):
        raise NotImplementedError

    def members(self):
        raise NotImplementedError

    def length(self, hint):
        raise NotImplementedError

    def push_member(self, name):
        raise NotImplementedError

    def push_next_member(self):
        raise NotImplementedError

    def push_element(self, index):
        raise NotImplementedError

    def pop(self):
        raise NotImplementedError

    def additional_data_as_bool(self):
        raise NotImplementedError

    def additional_data_as_uint32(self):
        raise NotImplementedError


class RapidJSONSchemaReader(SchemaReader):
    """A reader over a parsed value, strict about numbers and exact about keys."""

    def __init__(self, value):
        self.stack = [[value, None]]

    @property
    def node(self):
        return self.stack[-1][0]

    def expected_type(self):
        match self.node:
            case dict():
                return SchemaRWType.OBJECT
            case list():
                return SchemaRWType.ARRAY
        return SchemaRWType.OTHER

    def as_null(self):
        return True if self.node is None else None

    def as_bool(self):
        return self.node if type(self.node) is bool else None

    def integer(self, low, high):
        return self.node if type(self.node) is int and low <= self.node < high else None

    def as_int8(self):
        return self.integer(-(1 << 7), 1 << 7)

    def as_uint8(self):
        return self.integer(0, 1 << 8)

    def as_int16(self):
        return self.integer(-(1 << 15), 1 << 15)

    def as_uint16(self):
        return self.integer(0, 1 << 16)

    def as_int32(self):
        return self.integer(-(1 << 31), 1 << 31)

    def as_uint32(self):
        return self.integer(0, 1 << 32)

    def as_int64(self):
        return self.integer(-(1 << 63), 1 << 63)

    def as_uint64(self):
        return self.integer(0, 1 << 64)

    def as_double(self):
        node = CaseForm.number_in(self.node)
        return float(node) if type(node) in (int, float) else None

    def as_float(self):
        value = self.as_double()
        return value if value is None or not math.isfinite(value) or abs(value) <= FLOAT_LIMIT else None

    def as_string(self):
        return self.node if isinstance(self.node, str) else None

    def as_raw_bytes(self):
        return CaseForm.raw(self.node) if isinstance(self.node, str) else None

    def as_tokens(self):
        return CaseForm.tokens(self.node)

    def members(self):
        return len(self.node)

    def length(self, hint):
        return len(self.node)

    def push_member(self, name):
        if not isinstance(self.node, dict) or name not in self.node:
            return False
        self.stack.append([self.node[name], None])
        return True

    def push_next_member(self):
        frame = self.stack[-1]
        frame[1] = frame[1] or iter(frame[0])
        key = next(frame[1], None)
        if key is None:
            frame[1] = None
        else:
            self.stack.append([frame[0][key], None])
        return key

    def push_element(self, index):
        self.stack.append([self.node[index], None])

    def pop(self):
        self.stack.pop()

    def additional_data_as_bool(self):
        return None

    def additional_data_as_uint32(self):
        return None


class SchemaWriter:
    def write(self, value):
        raise NotImplementedError

    def write_additional_data(self, data):
        raise NotImplementedError

    def push_member(self, name):
        raise NotImplementedError

    def pop_member(self):
        raise NotImplementedError

    def open_object(self):
        raise NotImplementedError

    def open_array(self, dynamic, size):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError


class RapidJSONSchemaWriter(SchemaWriter):
    """A writer that builds the value, giving a member a key only once a value follows."""

    def __init__(self):
        self.result = None
        self.stack = []
        self.pending = None
        self.additional = []

    def place(self, value):
        if not self.stack:
            self.result = value
        elif isinstance(self.stack[-1], dict):
            self.stack[-1][self.pending] = value
        else:
            self.stack[-1].append(value)

    def write(self, value):
        if isinstance(value, bytes):
            value = CaseForm.text(value)
        self.place(CaseForm.number_out(value))

    def write_tokens(self, tokens):
        self.place(CaseForm.stream(tokens))

    def write_additional_data(self, data):
        self.additional.append(data)

    def push_member(self, name):
        self.pending = name

    def pop_member(self):
        self.pending = None

    def open(self, container):
        self.place(container)
        self.stack.append(container)

    def open_object(self):
        self.open({})
        return SchemaRWType.OBJECT

    def open_array(self, dynamic, size):
        self.open([])
        return SchemaRWType.ARRAY

    def close(self):
        self.stack.pop()


class BasicSchema:
    bound_type = None

    def load(self, reader, context, traits=SerializationTraits.NONE):
        checkpoint = context.get_log_checkpoint()
        value = self.do_load(reader, context, traits)
        if not context.has_error(checkpoint):
            context.clear_generations(checkpoint, context.get_log_checkpoint())
        return value

    def save(self, value, writer, context, traits=SerializationTraits.NONE):
        self.do_save(value, writer, context, traits)

    def do_load(self, reader, context, traits):
        raise NotImplementedError

    def do_save(self, value, writer, context, traits):
        raise NotImplementedError


class BoolSchema(BasicSchema):
    bound_type = bool

    def do_load(self, reader, context, traits):
        value = reader.as_bool()
        if value is None:
            context.log(ErrorCode.ERROR, "invalid numeric value")
        return bool(value)

    def do_save(self, value, writer, context, traits):
        writer.write(bool(value))


class IntegerSchema(BasicSchema):
    """An integer member, printed in the range of its wire type as BDS's member holds it."""

    bound_type = int

    def __init__(self, declared, wire=None):
        self.declared = self.bounds(declared)
        self.wire = self.bounds(wire or declared)
        self.reader_method = "as_" + (wire or declared).replace("varint", "int")

    @staticmethod
    def bounds(name):
        bits = int(re.search(r"\d+", name)[0])
        return range(1 << bits) if name.startswith("u") else range(-(1 << (bits - 1)), 1 << (bits - 1))

    @staticmethod
    def fit(value, bounds):
        return (value - bounds.start) % (bounds.stop - bounds.start) + bounds.start

    def do_load(self, reader, context, traits):
        value = getattr(reader, self.reader_method)()
        if value is None:
            context.log(ErrorCode.ERROR, "invalid numeric value")
            value = 0
        return self.fit(value, self.declared)

    def do_save(self, value, writer, context, traits):
        writer.write(self.fit(int(value), self.wire))


class FloatSchema(BasicSchema):
    bound_type = float

    def __init__(self, width):
        self.reader_method = "as_float" if width == 32 else "as_double"

    def do_load(self, reader, context, traits):
        value = getattr(reader, self.reader_method)()
        if value is None:
            context.log(ErrorCode.ERROR, "invalid numeric value")
            value = 0.0
        return value

    def do_save(self, value, writer, context, traits):
        writer.write(float(value))


class StringSchema(BasicSchema):
    bound_type = str

    def do_load(self, reader, context, traits):
        value = reader.as_string()
        if value is None:
            context.log(ErrorCode.ERROR, "invalid string")
        return value or ""

    def do_save(self, value, writer, context, traits):
        writer.write(value)


class BlobSchema(BasicSchema):
    """BDS's std::vector<uint8_t>, bound as bytes or as a list of integers."""

    def __init__(self, listed):
        self.bound_type = list if listed else bytes
        self.listed = listed

    def do_load(self, reader, context, traits):
        value = reader.as_raw_bytes()
        if value is None:
            context.log(ErrorCode.ERROR, "invalid string")
            value = b""
        return list(value) if self.listed else value

    def do_save(self, value, writer, context, traits):
        writer.write(bytes(value))


class UUIDSchema(BasicSchema):
    bound_type = uuid.UUID

    def do_load(self, reader, context, traits):
        text = reader.as_string()
        try:
            return uuid.UUID(text)
        except (AttributeError, TypeError, ValueError):
            context.log(ErrorCode.ERROR, "invalid string")
            return uuid.UUID(int=0)

    def do_save(self, value, writer, context, traits):
        writer.write(str(value))


class DynamicValueSchema(BasicSchema):
    def do_load(self, reader, context, traits):
        for read in (reader.as_string, reader.as_bool, reader.as_int64, reader.as_double):
            value = read()
            if value is not None:
                return value
        if reader.expected_type() & SchemaRWType.ARRAY:
            return [self.element(reader, context, index) for index in range(reader.length(-1))]
        if reader.expected_type() & SchemaRWType.OBJECT:
            values = {}
            while (key := reader.push_next_member()) is not None:
                values[key] = self.load(reader, context)
                reader.pop()
            return values
        if not reader.as_null():
            context.log(ErrorCode.ERROR, "invalid dynamic value")
        return None

    def element(self, reader, context, index):
        reader.push_element(index)
        value = self.load(reader, context)
        reader.pop()
        return value

    def do_save(self, value, writer, context, traits):
        writer.write(value)


class NullTypeSchema(BasicSchema):
    bound_type = type(None)

    def do_load(self, reader, context, traits):
        if not reader.as_null():
            context.log(ErrorCode.ERROR, "expected null")

    def do_save(self, value, writer, context, traits):
        writer.write(None)


class EnumSchema(BasicSchema):
    """An enum printed by its registered name, or by its number when the member asks for it."""

    def __init__(self, shape, underlying):
        self.underlying = underlying
        self.wire_names = {}
        self.numbers = {}
        for member in shape.members:
            number = shape.numbers[member.name]
            self.wire_names.setdefault(number, member.wire_name)
            self.numbers.setdefault(member.wire_name, number)

    def do_load(self, reader, context, traits):
        if traits & SerializationTraits.ENUM_AS_VALUE:
            number = self.underlying.load(reader, context)
            if number not in self.wire_names:
                context.log(ErrorCode.INVALID_ENUM_VALUE, f"{number}: invalid enum value")
            return number
        name = reader.as_string()
        if name is None:
            context.log(ErrorCode.ERROR, "invalid string")
        elif name.lower() not in self.numbers:
            context.log(ErrorCode.INVALID_ENUM_VALUE, f"{name!r}: invalid enum value")
        return self.numbers.get((name or "").lower(), 0)

    def do_save(self, value, writer, context, traits):
        number = int(value)
        if number not in self.wire_names:
            context.log(ErrorCode.INVALID_ENUM_VALUE, f"{number}: not bound")
        elif traits & SerializationTraits.ENUM_AS_VALUE:
            self.underlying.save(number, writer, context)
        else:
            writer.write(self.wire_names[number])


class OptionalSchema(BasicSchema):
    def __init__(self, element):
        self.element = element

    def do_load(self, reader, context, traits):
        return self.element.load(reader, context, traits)

    def do_save(self, value, writer, context, traits):
        writer.write_additional_data(value is not None)
        if value is not None:
            self.element.save(value, writer, context, traits)


class VectorSchema(BasicSchema):
    bound_type = list

    def __init__(self, element):
        self.element = element

    def do_load(self, reader, context, traits):
        if not reader.expected_type() & SchemaRWType.ARRAY:
            context.log(ErrorCode.ERROR, "expected an array")
            return []
        values = []
        checkpoint = context.get_log_checkpoint()
        for index in range(reader.length(-1)):
            if context.has_error(checkpoint):
                break
            reader.push_element(index)
            values.append(self.element.load(reader, context, traits))
            reader.pop()
        return values

    def do_save(self, value, writer, context, traits):
        writer.open_array(True, len(value))
        for each in value:
            if context.has_error():
                break
            self.element.save(each, writer, context, traits)
        writer.close()


class ArraySchema(VectorSchema):
    def __init__(self, element, size):
        super().__init__(element)
        self.size = size

    def do_load(self, reader, context, traits):
        if reader.expected_type() & SchemaRWType.ARRAY and reader.length(self.size) != self.size:
            context.log(ErrorCode.ERROR, f"expected exactly {self.size} elements")
            return []
        return super().do_load(reader, context, traits)


class MapSchema(BasicSchema):
    """An object for a std::string key and key and value objects in an array for any other."""

    bound_type = dict

    def __init__(self, key, value, keyed_by_string):
        self.key = key
        self.value = value
        self.keyed_by_string = keyed_by_string

    def do_load(self, reader, context, traits):
        values = {}
        if self.keyed_by_string:
            if not reader.expected_type() & SchemaRWType.OBJECT:
                context.log(ErrorCode.ERROR, "expected an object")
                return values
            while (key := reader.push_next_member()) is not None:
                values[key] = self.value.load(reader, context, traits)
                reader.pop()
            return values
        if not reader.expected_type() & SchemaRWType.ARRAY:
            context.log(ErrorCode.ERROR, "expected an array")
            return values
        for index in range(reader.length(-1)):
            reader.push_element(index)
            if reader.members() != 2 or not reader.push_member("key"):
                context.log(ErrorCode.ERROR, "expected a key/value object")
                reader.pop()
                break
            key = self.key.load(reader, context, traits)
            reader.pop()
            if not reader.push_member("value"):
                context.log(ErrorCode.ERROR, "invalid or missing 'value' member")
                reader.pop()
                break
            values[key] = self.value.load(reader, context, traits)
            reader.pop()
            reader.pop()
        return values

    def do_save(self, value, writer, context, traits):
        if self.keyed_by_string:
            writer.open_object()
            for key, each in value.items():
                writer.push_member(key)
                self.value.save(each, writer, context, traits)
                writer.pop_member()
            writer.close()
            return
        writer.open_array(True, len(value))
        for key, each in value.items():
            writer.open_object()
            writer.push_member("key")
            self.key.save(key, writer, context, traits)
            writer.pop_member()
            writer.push_member("value")
            self.value.save(each, writer, context, traits)
            writer.pop_member()
            writer.close()
        writer.close()


class VariantSchema(BasicSchema):
    """The plain path: the index goes out as additional data and the active arm is printed bare."""

    def __init__(self, arms):
        self.arms = arms

    def do_load(self, reader, context, traits):
        start = context.get_log_checkpoint()
        for arm in self.arms:
            attempt = context.get_log_checkpoint()
            value = arm.load(reader, context, traits)
            if not context.has_error(attempt):
                break
        context.clear_generations(start, attempt)
        return value

    def do_save(self, value, writer, context, traits):
        index = next(index for index, arm in enumerate(self.arms) if type(value) is arm.bound_type)
        writer.write_additional_data(index)
        self.arms[index].save(value, writer, context, traits)


class BitsetSchema(BasicSchema):
    """A bitset on the Compression path: a little-endian varint, each group written as a uint8."""

    bound_type = int

    def __init__(self, width):
        self.groups = -(-width // 7)

    def do_load(self, reader, context, traits):
        value = 0
        for index, token in enumerate(reader.as_tokens()):
            if type(token) is not int or not 0 <= token < 256 or index >= self.groups:
                context.log(ErrorCode.ERROR, "failed to read bitset byte")
                break
            value |= (token & 0x7F) << (7 * index)
        return value

    def do_save(self, value, writer, context, traits):
        groups = [(value >> shift) & 0x7F for shift in range(0, max(value.bit_length(), 1), 7)]
        writer.write_tokens([group | 0x80 for group in groups[:-1]] + groups[-1:])


NBT_IDS = {
    nbt.ByteTag: 1,
    nbt.ShortTag: 2,
    nbt.IntTag: 3,
    nbt.Int64Tag: 4,
    nbt.FloatTag: 5,
    nbt.DoubleTag: 6,
    nbt.ByteArrayTag: 7,
    nbt.StringTag: 8,
    nbt.ListTag: 9,
    nbt.CompoundTag: 10,
    nbt.IntArrayTag: 11,
}
NBT_CLASSES = {number: cls for cls, number in NBT_IDS.items()}


class CompoundTagSchema(BasicSchema):
    """A compound as BDS's token stream: an optional header, entries of type id, name and payload, then 0."""

    bound_type = nbt.CompoundTag

    def __init__(self, header):
        self.header = header

    def entries(self, compound, tokens):
        for name, tag in compound.items():
            tokens += [NBT_IDS[type(tag)], name]
            self.payload(tag, tokens)
        tokens.append(0)

    def payload(self, tag, tokens):
        match tag:
            case nbt.CompoundTag():
                self.entries(tag, tokens)
            case nbt.ListTag():
                tokens += [int(tag.type), len(tag)]
                for index in range(len(tag)):
                    self.payload(tag[index], tokens)
            case nbt.ByteArrayTag() | nbt.IntArrayTag():
                tokens += [len(tag.value), *tag.value]
            case _:
                tokens.append({"data": tag.value})

    def read_entries(self, tokens):
        compound = nbt.CompoundTag()
        while (number := next(tokens)) != 0:
            name = next(tokens)
            compound[name] = self.read_payload(number, tokens)
        return compound

    def read_payload(self, number, tokens):
        cls = NBT_CLASSES[number]
        if cls is nbt.CompoundTag:
            return self.read_entries(tokens)
        if cls is nbt.ListTag:
            element, count = next(tokens), next(tokens)
            return nbt.ListTag([self.read_payload(element, tokens) for _ in range(count)], element)
        if number in (7, 11):
            return cls([next(tokens) for _ in range(next(tokens))])
        data = next(tokens)["data"]
        return cls(CaseForm.number_in(data) if number in (5, 6) else data)

    def do_load(self, reader, context, traits):
        try:
            tokens = iter(reader.as_tokens())
            if self.header:
                next(tokens), next(tokens)
            return self.read_entries(tokens)
        except (StopIteration, KeyError, TypeError, ValueError, OverflowError):
            context.log(ErrorCode.ERROR, "invalid tag stream")
            return nbt.CompoundTag()

    def do_save(self, value, writer, context, traits):
        tokens = [NBT_IDS[nbt.CompoundTag], ""] if self.header else []
        self.entries(value, tokens)
        writer.write_tokens(tokens)


class MemberDescriptor:
    """A struct member, reached from the owner through the bound attributes of its path."""

    def __init__(self, name, schema, path, traits=SerializationTraits.NONE, is_required=True, marker=False):
        self.name = name
        self.schema = schema
        self.path = path
        self.traits = traits
        self.is_required = is_required
        self.marker = marker
        self.is_const_selector = False
        self.constant = None

    def get(self, owner):
        return reduce(getattr, self.path, owner)

    def set(self, owner, value):
        setattr(reduce(getattr, self.path[:-1], owner), self.path[-1], value)

    def under(self, attribute):
        member = copy(self)
        member.path = (attribute, *self.path)
        return member

    def save(self, owner, writer, context):
        writer.push_member(self.name)
        if self.marker:
            writer.write_additional_data(True)
        value = self.constant if self.is_const_selector else self.get(owner)
        self.schema.save(value, writer, context, self.traits)
        writer.pop_member()

    def load(self, reader, context, owner):
        if not reader.push_member(self.name):
            if self.is_required:
                context.log(ErrorCode.MISSING_REQUIRED_FIELD, f"{self.name}: missing required field")
            return False
        checkpoint = context.get_log_checkpoint()
        value = self.schema.load(reader, context, self.traits)
        reader.pop()
        if context.has_error(checkpoint):
            return True
        if self.is_const_selector:
            if value != self.constant:
                context.log(ErrorCode.ERROR, f"wrong const value for member {self.name!r}")
        else:
            self.set(owner, value)
        return True


class GroupMember(MemberDescriptor):
    """A member that BDS nests and the DSL keeps flat, read from and written into the owner itself."""

    def set(self, owner, value):
        for attribute, each in vars(value).items():
            setattr(owner, attribute, each)


class CompositeSchema(BasicSchema):
    """A struct prints one key per member in registration order and loads schema-driven."""

    def __init__(self, cls, members):
        self.cls = cls
        self.members = members
        self.bound_type = cls

    def create(self):
        return self.cls()

    def view(self, value):
        return value

    def finish(self, owner):
        return owner

    def do_load(self, reader, context, traits):
        owner = self.create()
        if not reader.expected_type() & SchemaRWType.OBJECT:
            context.log(ErrorCode.ERROR, "expected an object")
            return self.finish(owner)
        checkpoint = context.get_log_checkpoint()
        found = 0
        for member in self.members:
            found += member.load(reader, context, owner)
            if context.has_error(checkpoint):
                return self.finish(owner)
        names = {member.name for member in self.members}
        if reader.members() > found:
            while (key := reader.push_next_member()) is not None:
                reader.pop()
                if key not in names:
                    context.log(ErrorCode.UNRECOGNIZED_FIELD, f"{key}: found in the input, but not in the schema")
        return self.finish(owner)

    def do_save(self, value, writer, context, traits):
        owner = self.view(value)
        writer.open_object()
        for member in self.members:
            if context.has_error():
                break
            member.save(owner, writer, context)
        writer.close()


class WrapperSchema(CompositeSchema):
    """BDS's one-member struct around a value that the DSL holds bare."""

    def __init__(self, key, inner):
        super().__init__(int, [MemberDescriptor(key, inner, ("value",))])

    def create(self):
        return SimpleNamespace(value=0)

    def view(self, value):
        return SimpleNamespace(value=value)

    def finish(self, owner):
        return owner.value


class UUIDHalvesSchema(CompositeSchema):
    """mce::UUID as BDS reflects it: the big-endian halves of the 128-bit value."""

    def __init__(self):
        half = IntegerSchema("uint64")
        members = [
            MemberDescriptor("most_significant_bits", half, ("most",)),
            MemberDescriptor("least_significant_bits", half, ("least",)),
        ]
        super().__init__(uuid.UUID, members)

    def create(self):
        return SimpleNamespace(most=0, least=0)

    def view(self, value):
        return SimpleNamespace(most=value.int >> 64, least=value.int & (1 << 64) - 1)

    def finish(self, owner):
        return uuid.UUID(int=owner.most << 64 | owner.least)


class MemberOnlySchema(CompositeSchema):
    """A one-member struct that BDS prints as its member."""

    def do_load(self, reader, context, traits):
        owner = self.create()
        [member] = self.members
        checkpoint = context.get_log_checkpoint()
        value = member.schema.load(reader, context, member.traits)
        if not context.has_error(checkpoint):
            member.set(owner, value)
        return self.finish(owner)

    def do_save(self, value, writer, context, traits):
        [member] = self.members
        member.schema.save(member.get(self.view(value)), writer, context, member.traits)


class ArrayOfMembersSchema(CompositeSchema):
    """A struct that BDS prints as an array of its members."""

    def do_load(self, reader, context, traits):
        owner = self.create()
        if not reader.expected_type() & SchemaRWType.ARRAY or reader.length(len(self.members)) != len(self.members):
            context.log(ErrorCode.ERROR, f"expected exactly {len(self.members)} elements")
            return self.finish(owner)
        for index, member in enumerate(self.members):
            checkpoint = context.get_log_checkpoint()
            reader.push_element(index)
            value = member.schema.load(reader, context, member.traits)
            reader.pop()
            if not context.has_error(checkpoint):
                member.set(owner, value)
        return self.finish(owner)

    def do_save(self, value, writer, context, traits):
        owner = self.view(value)
        writer.open_array(False, len(self.members))
        for member in self.members:
            member.schema.save(member.get(owner), writer, context, member.traits)
        writer.close()


class DslShape(enum.Enum):
    FLATTEN = enum.auto()
    GROUP = enum.auto()
    PAIRS = enum.auto()
    PLAIN_INTEGER = enum.auto()
    BARE = enum.auto()
    MEMBER_ONLY = enum.auto()
    ARRAY_OF_MEMBERS = enum.auto()


SHAPES = {
    ("ServerboundDiagnosticsPacket", "telemetry"): (DslShape.FLATTEN, None),
    ("ServerboundDiagnosticsPacket", "entity_system_diagnostics"): (DslShape.FLATTEN, None),
    ("DeathInfoPacket", "death_cause_attack_name"): (DslShape.GROUP, "death_cause_message"),
    ("DeathInfoPacket", "death_cause_message_list"): (DslShape.GROUP, "death_cause_message"),
    ("CameraAimAssistCategoryPriorities", "entities"): (DslShape.PAIRS, None),
    ("CameraAimAssistCategoryPriorities", "blocks"): (DslShape.PAIRS, None),
    ("CameraAimAssistPresetDefinition", "item_settings"): (DslShape.PAIRS, None),
    ("VoxelShapesPacket", "name_map"): (DslShape.PAIRS, None),
    ("SpawnSettings", "dimension"): (DslShape.BARE, None),
    ("InventorySource", "container_id"): (DslShape.PLAIN_INTEGER, None),
    ("InventoryContentPacket", "inventory_id"): (DslShape.PLAIN_INTEGER, None),
    ("InventorySlotPacket", "inventory_id"): (DslShape.PLAIN_INTEGER, None),
    ("ContainerClosePacket", "container_id"): (DslShape.PLAIN_INTEGER, None),
    ("PlayerHotbarPacket", "container_id"): (DslShape.PLAIN_INTEGER, None),
    ("ContainerSetDataPacket", "container_id"): (DslShape.PLAIN_INTEGER, None),
    ("ContainerOpenPacket", "container_id"): (DslShape.PLAIN_INTEGER, None),
    ("UpdateTradePacket", "container_id"): (DslShape.PLAIN_INTEGER, None),
    ("UpdateEquipPacket", "container_id"): (DslShape.PLAIN_INTEGER, None),
    ("MobEquipmentPacket", "container_id"): (DslShape.PLAIN_INTEGER, None),
    ("DimensionDefinitionGroup", None): (DslShape.MEMBER_ONLY, None),
    ("EffectDuration", None): (DslShape.MEMBER_ONLY, None),
    ("MoveActorAbsoluteData.Header", None): (DslShape.MEMBER_ONLY, None),
    ("Color255RGBA", None): (DslShape.ARRAY_OF_MEMBERS, None),
}

WRAPPER_KEYS = {
    "ActorUniqueID": "actor_unique_id",
    "ActorRuntimeID": "actor_runtime_id",
    "PlayerInputTick": "input_tick",
    "DimensionType": "value",
    "Color": "color",
}
MARKER = re.compile(r"_true(_\d+)?")
COMPOSITES = {DslShape.MEMBER_ONLY: MemberOnlySchema, DslShape.ARRAY_OF_MEMBERS: ArrayOfMembersSchema}


class ReflectionCtx:
    """The schemas of one protocol, built from the model on first use."""

    def __init__(self, protocol):
        self.protocol = protocol
        self.module = importlib.import_module(f"bedrock_protocol.v{protocol}")
        self.composites = {}

    def shape(self, family):
        return MODEL.live[family, self.protocol]

    def composite(self, family):
        if family not in self.composites:
            name = qualified_name(family)
            kind, _ = SHAPES.get((name, None), (None, None))
            cls = reduce(getattr, name.split("."), self.module)
            self.composites[family] = schema = COMPOSITES.get(kind, CompositeSchema)(cls, [])
            schema.members = self.members(family)
        return self.composites[family]

    def members(self, family):
        name = qualified_name(family)
        members, groups, marker = [], {}, False
        for field in self.shape(family).fields:
            if MARKER.fullmatch(field.name):
                marker = True
                continue
            kind, argument = SHAPES.get((name, field.name), (None, None))
            attribute = f"{field.name}_" if keyword.iskeyword(field.name) else field.name
            if kind is DslShape.FLATTEN:
                members += [each.under(attribute) for each in self.members(field.type.struct)]
                continue
            member = self.member(field, kind, attribute, marker)
            marker = False
            if kind is DslShape.GROUP:
                groups.setdefault(argument, []).append(member)
                members += [] if len(groups[argument]) > 1 else [argument]
            else:
                members.append(member)
        return [
            GroupMember(each, CompositeSchema(SimpleNamespace, groups[each]), (), SerializationTraits.NONE)
            if isinstance(each, str)
            else each
            for each in members
        ]

    def member(self, field, kind, attribute, marker):
        node = field.type
        optional = isinstance(node, OptionalType)
        node = node.element if optional else node
        match node:
            case Literal(value=MemberRef(enum=enum, name=name)):
                constant, node = self.shape(enum).numbers[name], EnumRef(enum)
            case Literal(value=constant):
                node = Primitive("str" if isinstance(constant, str) else "bool")
        if kind is DslShape.PLAIN_INTEGER:
            node = Primitive(self.shape(node.enum).underlying.name, node.wire)
        if kind is DslShape.BARE:
            node = AliasRef(node.alias, node.alias.primitive.name)
        schema = self.schema(node)
        if kind is DslShape.PAIRS:
            schema.keyed_by_string = False
        schema = OptionalSchema(schema) if optional else schema
        member = MemberDescriptor(field.name, schema, (attribute,), self.traits(node), not optional, marker)
        if isinstance(field.type, Literal):
            member.is_const_selector, member.constant = True, constant
        return member

    def traits(self, node):
        match node:
            case EnumRef():
                return SerializationTraits.ENUM_AS_VALUE
            case Bitset():
                return SerializationTraits.COMPRESSION
            case OptionalType(element=element) | List(element=element) | Array(element=element):
                return self.traits(element)
            case Map(key=key, value=value):
                return self.traits(key) | self.traits(value)
            case Variant(cases=arms):
                return reduce(or_, (self.traits(arm) for arm in arms if arm), SerializationTraits.NONE)
        return SerializationTraits.NONE

    def schema(self, node):
        match node:
            case Primitive(name="bool"):
                return BoolSchema()
            case Primitive(name="str"):
                return StringSchema()
            case Primitive(name="bytes"):
                return BlobSchema(False)
            case Primitive(name="float"):
                return FloatSchema(32)
            case Primitive(name="double"):
                return FloatSchema(64)
            case Primitive(name=name, wire=wire):
                return IntegerSchema(name, wire)
            case AliasRef(alias=alias, wire=wire):
                integer = IntegerSchema(alias.primitive.name, wire)
                key = WRAPPER_KEYS.get(alias.name)
                return integer if wire or key is None else WrapperSchema(key, integer)
            case BuiltinRef(builtin=builtin, wire="str") if builtin.name == "UUID":
                return UUIDSchema()
            case BuiltinRef(builtin=builtin) if builtin.name == "UUID":
                return UUIDHalvesSchema()
            case BuiltinRef(builtin=builtin) if builtin.name in ("CompoundTag", "CompoundTagData"):
                return CompoundTagSchema(builtin.name == "CompoundTag")
            case BuiltinRef(builtin=builtin) if builtin.name == "DynamicValue":
                return DynamicValueSchema()
            case EnumRef(enum=enum):
                return EnumSchema(self.shape(enum), self.schema(self.shape(enum).underlying))
            case EnumName(enum=enum):
                return EnumSchema(self.shape(enum), None)
            case StructRef(struct=family):
                return self.composite(family)
            case List(element=Primitive(name="uint8", wire=None)):
                return BlobSchema(True)
            case List(element=element):
                return VectorSchema(self.schema(element))
            case Array(element=element, size=size):
                return ArraySchema(self.schema(element), size)
            case Map(key=key, value=value):
                return MapSchema(self.schema(key), self.schema(value), key == Primitive("str"))
            case Variant(cases=arms):
                return VariantSchema([NullTypeSchema() if arm is None else self.schema(arm) for arm in arms])
            case Bitset(width=MemberRef(enum=enum, name=name)):
                return BitsetSchema(self.shape(enum).numbers[name])
        raise LookupError(f"{node!r}: has no schema")


REFLECTIONS = {protocol: ReflectionCtx(protocol) for protocol in MODEL.versions}


@cache
def schema_of(cls):
    return REFLECTIONS[int(cls.__module__.rpartition(".v")[2])].composite(FAMILIES[cls.__qualname__])


def save(value):
    """The JSON BDS writes for a bound struct."""
    writer = RapidJSONSchemaWriter()
    schema_of(type(value)).save(value, writer, SerializerContext())
    return writer.result


def load(cls, value):
    """The bound struct BDS reads from JSON, raising the entries a strict load logged."""
    context = SerializerContext()
    loaded = schema_of(cls).load(RapidJSONSchemaReader(value), context)
    if context.entries:
        raise LoadError(context.entries)
    return loaded


def additional_data(value):
    """The variant indexes and optional flags that saving a bound struct passes along."""
    writer = RapidJSONSchemaWriter()
    schema_of(type(value)).save(value, writer, SerializerContext())
    return writer.additional


def loses_arms(cls, value, data):
    """Whether loading the JSON value gives another variant arm than the bytes decode to."""
    try:
        return additional_data(load(cls, value)) != additional_data(cls.from_bytes(data))
    except LoadError:
        return False
