"""The golden cases, and Bedrock's cereal JSON reader and writer over the bound packets and the schema model."""

import enum
import importlib
import json
import keyword
import math
import re
import struct
import types
import uuid
from functools import reduce
from json.decoder import WHITESPACE
from operator import methodcaller, or_
from pathlib import Path
from typing import ClassVar, override

import nbtlib
import pytest

import bedrock_protocol
from bedrock_protocol import nbt
from bedrock_protocol_compiler.builder import build
from bedrock_protocol_compiler.descriptor import (
    AliasRef,
    Array,
    Bitset,
    BuiltinRef,
    Color,
    EnumName,
    EnumRef,
    Int,
    List,
    Literal,
    Map,
    MemberRef,
    Primitive,
    Struct,
    StructRef,
    TypeChoice,
    Variant,
)
from bedrock_protocol_compiler.descriptor import Optional as OptionalType
from bedrock_protocol_compiler.schema import Schema, outermost


class SchemaRWType(enum.IntFlag):
    OBJECT = 1
    ARRAY = 2
    OTHER = 4


class ResultCode(enum.IntEnum):
    UNRECOGNIZED_FIELD = 4
    ERROR = 8
    MISSING_REQUIRED_FIELD = 128
    INVALID_DYNAMIC_VALUE = 256
    INVALID_ENUM_VALUE = 4096


class SerializationTraits(enum.IntFlag):
    NONE = 0
    COMPRESSION = 1
    ENUM_AS_VALUE = 4


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
MISSING = object()


class TokenList(list):
    """Values that a writer gathered into one member slot, which is how Bedrock prints a token stream."""


class SchemaReader:
    def expected_type(self):
        raise NotImplementedError

    def as_null(self):
        raise NotImplementedError

    def as_bool(self):
        raise NotImplementedError

    def as_int8(self):
        raise NotImplementedError

    def as_uint8(self):
        raise NotImplementedError

    def as_int16(self):
        raise NotImplementedError

    def as_uint16(self):
        raise NotImplementedError

    def as_int32(self):
        raise NotImplementedError

    def as_uint32(self):
        raise NotImplementedError

    def as_int64(self):
        raise NotImplementedError

    def as_uint64(self):
        raise NotImplementedError

    def as_float(self):
        raise NotImplementedError

    def as_double(self):
        raise NotImplementedError

    def as_string(self):
        raise NotImplementedError

    def as_raw_bytes(self):
        raise NotImplementedError

    def additional_data_as_bool(self):
        raise NotImplementedError

    def additional_data_as_uint32(self):
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


class StrictJSONSchemaReader(SchemaReader):
    """A reader over a parsed value: exact keys, strict numbers, and scalars read in turn from a token list."""

    def __init__(self, value):
        self.stack = [[value, 0]]

    @property
    def node(self):
        return self.stack[-1][0]

    def scalar(self):
        frame = self.stack[-1]
        if not isinstance(frame[0], TokenList):
            return frame[0]
        frame[1] += 1
        return frame[0][frame[1] - 1] if frame[1] <= len(frame[0]) else MISSING

    def integer(self, low, high):
        value = self.scalar()
        return value if type(value) is int and low <= value < high else None

    @override
    def expected_type(self):
        match self.node:
            case dict():
                return SchemaRWType.OBJECT
            case list():
                return SchemaRWType.ARRAY
        return SchemaRWType.OTHER

    @override
    def as_null(self):
        return True if self.scalar() is None else None

    @override
    def as_bool(self):
        value = self.scalar()
        return value if type(value) is bool else None

    @override
    def as_int8(self):
        return self.integer(-(1 << 7), 1 << 7)

    @override
    def as_uint8(self):
        return self.integer(0, 1 << 8)

    @override
    def as_int16(self):
        return self.integer(-(1 << 15), 1 << 15)

    @override
    def as_uint16(self):
        return self.integer(0, 1 << 16)

    @override
    def as_int32(self):
        return self.integer(-(1 << 31), 1 << 31)

    @override
    def as_uint32(self):
        return self.integer(0, 1 << 32)

    @override
    def as_int64(self):
        return self.integer(-(1 << 63), 1 << 63)

    @override
    def as_uint64(self):
        return self.integer(0, 1 << 64)

    @override
    def as_double(self):
        value = self.scalar()
        return float(value) if type(value) in (int, float) else None

    @override
    def as_float(self):
        value = self.as_double()
        return value if value is None or abs(value) <= FLOAT_LIMIT else None

    @override
    def as_string(self):
        value = self.scalar()
        return value if isinstance(value, str) else None

    @override
    def as_raw_bytes(self):
        value = self.as_string()
        return None if value is None else value.encode("utf-8", "surrogateescape")

    @override
    def additional_data_as_bool(self):
        return None

    @override
    def additional_data_as_uint32(self):
        return None

    @override
    def members(self):
        return len(self.node)

    @override
    def length(self, hint):
        return len(self.node)

    @override
    def push_member(self, name):
        node = self.node
        if isinstance(node, TokenList):
            node = self.scalar()
        if not isinstance(node, dict) or name not in node:
            return False
        self.stack.append([node[name], 0])
        return True

    @override
    def push_next_member(self):
        frame = self.stack[-1]
        keys = list(frame[0])
        key = keys[frame[1] % len(keys)]
        frame[1] += 1
        self.stack.append([frame[0][key], 0])
        return key

    @override
    def push_element(self, index):
        self.stack.append([self.node[index], 0])

    @override
    def pop(self):
        self.stack.pop()


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


class JSONSchemaWriter(SchemaWriter):
    """A writer that builds the value, with a key only once a value follows and later values gathered into its slot."""

    def __init__(self):
        self.result = None
        self.written = False
        self.stack = []
        self.pending = None

    def place(self, value):
        if not self.stack:
            if not self.written:
                self.result = value
            elif isinstance(self.result, TokenList):
                self.result.append(value)
            else:
                self.result = TokenList([self.result, value])
            self.written = True
            return
        self.written = True
        container, last = self.stack[-1]
        if isinstance(container, list):
            container.append(value)
        elif self.pending is not None:
            container[self.pending] = value
            self.stack[-1][1] = self.pending
            self.pending = None
        elif isinstance(container[last], TokenList):
            container[last].append(value)
        else:
            container[last] = TokenList([container[last], value])

    @override
    def write(self, value):
        if isinstance(value, float) and not math.isfinite(value):
            return False
        self.place(value.decode("utf-8", "surrogateescape") if isinstance(value, bytes) else value)
        return True

    @override
    def write_additional_data(self, data):
        return True

    @override
    def push_member(self, name):
        self.pending = name

    @override
    def pop_member(self):
        self.pending = None

    def open(self, container):
        self.place(container)
        self.stack.append([container, None])

    @override
    def open_object(self):
        self.open({})
        return SchemaRWType.OBJECT

    @override
    def open_array(self, dynamic, size):
        self.open([])
        return SchemaRWType.ARRAY

    @override
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

    @override
    def do_load(self, reader, context, traits):
        value = reader.as_bool()
        if value is None:
            context.log(ResultCode.ERROR, "invalid numeric value")
        return bool(value)

    @override
    def do_save(self, value, writer, context, traits):
        writer.write(bool(value))


class IntegerSchema(BasicSchema):
    """An integer member, printed in the range of its encoded type as Bedrock's member holds it."""

    bound_type = int
    READS: ClassVar = {
        "int8": methodcaller("as_int8"),
        "uint8": methodcaller("as_uint8"),
        "int16": methodcaller("as_int16"),
        "uint16": methodcaller("as_uint16"),
        "int32": methodcaller("as_int32"),
        "uint32": methodcaller("as_uint32"),
        "int64": methodcaller("as_int64"),
        "uint64": methodcaller("as_uint64"),
    }

    def __init__(self, declared, encoded=None):
        self.declared = self.bounds(declared)
        self.encoded = self.bounds(encoded or declared)
        self.read = self.READS[(encoded or declared).replace("varint", "int")]

    @staticmethod
    def bounds(name):
        bits = int(re.search(r"\d+", name)[0])
        return range(1 << bits) if name.startswith("u") else range(-(1 << (bits - 1)), 1 << (bits - 1))

    @staticmethod
    def fit(value, bounds):
        return (value - bounds.start) % (bounds.stop - bounds.start) + bounds.start

    @override
    def do_load(self, reader, context, traits):
        value = self.read(reader)
        if value is None:
            context.log(ResultCode.ERROR, "invalid numeric value")
            value = 0
        return self.fit(value, self.declared)

    @override
    def do_save(self, value, writer, context, traits):
        writer.write(self.fit(int(value), self.encoded))


class FloatSchema(BasicSchema):
    bound_type = float

    def __init__(self, width):
        self.read = methodcaller("as_float" if width == 32 else "as_double")

    @override
    def do_load(self, reader, context, traits):
        value = self.read(reader)
        if value is None:
            context.log(ResultCode.ERROR, "invalid numeric value")
            value = 0.0
        return value

    @override
    def do_save(self, value, writer, context, traits):
        if not writer.write(float(value)):
            context.log(ResultCode.ERROR, "unexpected writer error while saving numeric value")


class StringSchema(BasicSchema):
    bound_type = str

    @override
    def do_load(self, reader, context, traits):
        value = reader.as_string()
        if value is None:
            context.log(ResultCode.ERROR, "invalid string")
        return value or ""

    @override
    def do_save(self, value, writer, context, traits):
        writer.write(value)


class BlobSchema(BasicSchema):
    """Bedrock's std::vector<uint8_t> or std::vector<int8_t>, read and written as raw bytes."""

    def __init__(self, listed, signed=False):
        self.bound_type = list if listed else bytes
        self.listed = listed
        self.signed = signed

    @override
    def do_load(self, reader, context, traits):
        value = reader.as_raw_bytes()
        if value is None:
            context.log(ResultCode.ERROR, "invalid blob: failed to parse input as binary data")
            value = b""
        if self.signed:
            return list(struct.unpack(f"{len(value)}b", value))
        return list(value) if self.listed else value

    @override
    def do_save(self, value, writer, context, traits):
        writer.write(struct.pack(f"{len(value)}b", *value) if self.signed else bytes(value))


class UUIDSchema(BasicSchema):
    bound_type = uuid.UUID

    @override
    def do_load(self, reader, context, traits):
        try:
            return uuid.UUID(reader.as_string())
        except (TypeError, ValueError):
            context.log(ResultCode.ERROR, "invalid string")
            return uuid.UUID(int=0)

    @override
    def do_save(self, value, writer, context, traits):
        writer.write(str(value))


class NullTypeSchema(BasicSchema):
    bound_type = type(None)

    @override
    def do_load(self, reader, context, traits):
        if not reader.as_null():
            context.log(ResultCode.ERROR, 'Expected "null"')

    @override
    def do_save(self, value, writer, context, traits):
        writer.write(None)


class EnumSchema(BasicSchema):
    """An enum printed by its registered name, or by its number when the member asks for it."""

    def __init__(self, shape, underlying, numbering=None, naming=None):
        self.underlying = underlying
        self.numbering = numbering
        self.naming = naming
        self.live_numbers = {shape.numbers[member.name] for member in shape.members}
        self.names = {member.encoded_name: shape.numbers[member.name] for member in shape.members}

    @override
    def do_load(self, reader, context, traits):
        if traits & SerializationTraits.ENUM_AS_VALUE:
            number = self.underlying.load(reader, context)
            if number in self.numbering.lossy:
                context.log(ResultCode.INVALID_ENUM_VALUE, f"{number}: invalid enum value")
            return self.numbering.decoded.get(number, number)
        name = reader.as_string()
        if name is None:
            context.log(ResultCode.ERROR, "invalid string")
        elif name.lower() not in self.naming.read:
            context.log(ResultCode.INVALID_ENUM_VALUE, f"{name!r}: invalid enum value")
        return self.naming.read.get((name or "").lower(), 0)

    @override
    def do_save(self, value, writer, context, traits):
        library = int(value)
        if traits & SerializationTraits.ENUM_AS_VALUE:
            number = self.numbering.encoded.get(library, library)
            if library in self.numbering.absent or (number not in self.live_numbers and isinstance(value, enum.Enum)):
                context.log(ResultCode.INVALID_ENUM_VALUE, f"{library}: not bound")
            else:
                self.underlying.save(number, writer, context)
        elif library not in self.naming.written:
            context.log(ResultCode.INVALID_ENUM_VALUE, f"{library}: not bound")
        else:
            writer.write(self.naming.written[library])


class OptionalSchema(BasicSchema):
    def __init__(self, element):
        self.element = element

    @override
    def do_load(self, reader, context, traits):
        if reader.additional_data_as_bool() is False:
            return None
        return self.element.load(reader, context, traits)

    @override
    def do_save(self, value, writer, context, traits):
        writer.write_additional_data(value is not None)
        if value is not None:
            self.element.save(value, writer, context, traits)


class VectorSchema(BasicSchema):
    bound_type = list

    def __init__(self, element):
        self.element = element

    @override
    def do_load(self, reader, context, traits):
        if not reader.expected_type() & SchemaRWType.ARRAY:
            context.log(ResultCode.ERROR, "expected an array")
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

    @override
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

    @override
    def do_load(self, reader, context, traits):
        if reader.expected_type() & SchemaRWType.ARRAY and reader.length(self.size) != self.size:
            context.log(
                ResultCode.ERROR, f"wrong number of elements in fixed size container, expected exactly {self.size}"
            )
            return []
        return super().do_load(reader, context, traits)

    @override
    def do_save(self, value, writer, context, traits):
        writer.open_array(False, self.size)
        for each in value:
            if context.has_error():
                break
            self.element.save(each, writer, context, traits)
        writer.close()


class MapSchema(BasicSchema):
    """An object for a std::string key and key and value objects in an array for any other, both read."""

    bound_type = dict

    def __init__(self, key, value):
        self.key = key
        self.value = value

    @override
    def do_load(self, reader, context, traits):
        values = {}
        expected = reader.expected_type()
        checkpoint = context.get_log_checkpoint()
        if expected & SchemaRWType.OBJECT:
            for _ in range(reader.members()):
                if context.has_error(checkpoint):
                    break
                key = reader.push_next_member()
                if self.key.bound_type is not str:
                    context.log(ResultCode.ERROR, "invalid key type: map keys must be strings or string-convertible")
                else:
                    values[key] = self.value.load(reader, context, traits)
                reader.pop()
        elif expected & SchemaRWType.ARRAY:
            for index in range(reader.length(-1)):
                if context.has_error(checkpoint):
                    break
                reader.push_element(index)
                if not reader.expected_type() & SchemaRWType.OBJECT or reader.members() != 2:
                    context.log(ResultCode.ERROR, "expected a key/value object")
                elif not reader.push_member("key"):
                    context.log(ResultCode.ERROR, "invalid or missing 'key' member in key/value pair object")
                else:
                    key = self.key.load(reader, context, traits)
                    reader.pop()
                    if reader.push_member("value"):
                        values[key] = self.value.load(reader, context, traits)
                        reader.pop()
                    else:
                        context.log(ResultCode.ERROR, "invalid or missing 'value' member in key/value pair object")
                reader.pop()
        else:
            context.log(ResultCode.ERROR, "expected an object" if self.key.bound_type is str else "expected an array")
        return values

    @override
    def do_save(self, value, writer, context, traits):
        if self.key.bound_type is str:
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

    @override
    def do_load(self, reader, context, traits):
        traits |= SerializationTraits.COMPRESSION
        index = reader.additional_data_as_uint32()
        if index is not None:
            return self.arms[index].load(reader, context, traits)
        start = context.get_log_checkpoint()
        for arm in self.arms:
            attempt = context.get_log_checkpoint()
            value = arm.load(reader, context, traits)
            if not context.has_error(attempt):
                break
        context.clear_generations(start, attempt)
        return value

    @override
    def do_save(self, value, writer, context, traits):
        traits |= SerializationTraits.COMPRESSION
        index = next(index for index, arm in enumerate(self.arms) if type(value) is arm.bound_type)
        writer.write_additional_data(index)
        self.arms[index].save(value, writer, context, traits)


class DynamicValueSchema(BasicSchema):
    def __init__(self):
        self.boolean = BoolSchema()
        self.integer = IntegerSchema("int64")
        self.float = FloatSchema(64)
        self.string = StringSchema()
        self.array = VectorSchema(self)
        self.object = MapSchema(self.string, self)

    @override
    def do_load(self, reader, context, traits):
        index = reader.additional_data_as_uint32()
        expected = reader.expected_type()
        if index is None and expected & SchemaRWType.OBJECT:
            return self.object.load(reader, context, traits)
        if index is None and expected & SchemaRWType.ARRAY:
            return self.array.load(reader, context, traits)
        for read in (reader.as_string, reader.as_bool, reader.as_int64, reader.as_double):
            value = read()
            if value is not None:
                return value
        if not reader.as_null():
            context.log(ResultCode.INVALID_DYNAMIC_VALUE, "Invalid data: impossible to load into a DynamicValue")
        return None

    @override
    def do_save(self, value, writer, context, traits):
        kinds = (type(None), bool, int, float, str, list, dict)
        if type(value) not in kinds:
            context.log(ResultCode.INVALID_DYNAMIC_VALUE, "Invalid data: impossible to save from a DynamicValue")
            return
        writer.write_additional_data(kinds.index(type(value)))
        schemas = {
            bool: self.boolean,
            int: self.integer,
            float: self.float,
            str: self.string,
            list: self.array,
            dict: self.object,
        }
        if value is None:
            writer.write(None)
        else:
            schemas[type(value)].save(value, writer, context, traits)


class BitsetSchema(BasicSchema):
    """A bitset on the Compression path: a little-endian varint, each group written as a uint8."""

    bound_type = int

    def __init__(self, width):
        self.bits = -(-width // 7) * 7
        self.uint8 = IntegerSchema("uint8")

    @override
    def do_load(self, reader, context, traits):
        value, shift = 0, 0
        while True:
            checkpoint = context.get_log_checkpoint()
            group = self.uint8.load(reader, context)
            if context.has_error(checkpoint):
                context.log(ResultCode.ERROR, "failed to read bitset byte")
                return value
            value |= (group & 0x7F) << shift
            shift += 7
            if not group & 0x80:
                return value
            if shift >= self.bits:
                context.log(ResultCode.ERROR, "bitset read overflow")
                return value

    @override
    def do_save(self, value, writer, context, traits):
        while True:
            group, value = value & 0x7F, value >> 7
            self.uint8.save(group | (0x80 if value else 0), writer, context)
            if not value:
                return


class CompoundTagSchema(BasicSchema):
    """A compound as Bedrock writes it: an optional header, then type, name and payload per entry, then 0."""

    bound_type = nbt.CompoundTag
    CLASSES: ClassVar = {
        1: nbt.ByteTag,
        2: nbt.ShortTag,
        3: nbt.IntTag,
        4: nbt.Int64Tag,
        5: nbt.FloatTag,
        6: nbt.DoubleTag,
        7: nbt.ByteArrayTag,
        8: nbt.StringTag,
        9: nbt.ListTag,
        10: nbt.CompoundTag,
        11: nbt.IntArrayTag,
    }
    IDS: ClassVar = {cls: number for number, cls in CLASSES.items()}

    def __init__(self, header):
        self.header = header
        self.uint8 = IntegerSchema("uint8")
        self.int16 = IntegerSchema("int16")
        self.int32 = IntegerSchema("int32")
        self.int64 = IntegerSchema("int64")
        self.float32 = FloatSchema(32)
        self.float64 = FloatSchema(64)
        self.string = StringSchema()
        self.primitives = {
            1: self.uint8,
            2: self.int16,
            3: self.int32,
            4: self.int64,
            5: self.float32,
            6: self.float64,
            8: self.string,
        }

    def save_entries(self, compound, writer, context):
        for name, tag in compound.items():
            self.uint8.save(self.IDS[type(tag)], writer, context)
            self.string.save(name, writer, context)
            self.save_payload(tag, writer, context)
        self.uint8.save(0, writer, context)

    def save_payload(self, tag, writer, context):
        number = self.IDS[type(tag)]
        if number == 10:
            self.save_entries(tag, writer, context)
        elif number == 9:
            self.uint8.save(int(tag.type), writer, context)
            self.int32.save(len(tag), writer, context)
            for index in range(len(tag)):
                if self.IDS[type(tag[index])] != int(tag.type):
                    context.log(ResultCode.ERROR, "Unexpected type")
                else:
                    self.save_payload(tag[index], writer, context)
        elif number in (7, 11):
            self.int32.save(len(tag.value), writer, context)
            for each in tag.value:
                (self.uint8 if number == 7 else self.int32).save(each, writer, context)
        else:
            writer.open_object()
            writer.push_member("data")
            self.primitives[number].save(tag.value, writer, context)
            writer.pop_member()
            writer.close()

    def load_entries(self, reader, context):
        compound = nbt.CompoundTag()
        checkpoint = context.get_log_checkpoint()
        while not context.has_error(checkpoint) and (number := self.uint8.load(reader, context)) != 0:
            name = self.string.load(reader, context)
            compound[name] = self.load_payload(number, reader, context)
        return compound

    def load_payload(self, number, reader, context):
        if number not in self.CLASSES:
            context.log(ResultCode.ERROR, f"{number}: unknown tag type")
            return nbt.ByteTag()
        if number == 10:
            return self.load_entries(reader, context)
        if number == 9:
            checkpoint = context.get_log_checkpoint()
            element, count = self.uint8.load(reader, context), self.int32.load(reader, context)
            tags = [self.load_payload(element, reader, context) for _ in range(count)]
            return nbt.ListTag() if context.has_error(checkpoint) else nbt.ListTag(tags, element)
        if number in (7, 11):
            count = self.int32.load(reader, context)
            values = [(self.uint8 if number == 7 else self.int32).load(reader, context) for _ in range(count)]
            return self.CLASSES[number](values)
        if not reader.push_member("data"):
            context.log(ResultCode.MISSING_REQUIRED_FIELD, "data: missing required field")
            return self.CLASSES[number]()
        value = self.primitives[number].load(reader, context)
        reader.pop()
        return self.CLASSES[number](value)

    @override
    def do_load(self, reader, context, traits):
        if self.header:
            self.uint8.load(reader, context)
            self.string.load(reader, context)
        return self.load_entries(reader, context)

    @override
    def do_save(self, value, writer, context, traits):
        if self.header:
            self.uint8.save(10, writer, context)
            self.string.save("", writer, context)
        self.save_entries(value, writer, context)


class MemberDescriptor:
    """A struct member, reached through its bound attribute on the owner and written once per copy."""

    def __init__(self, name, schema, attribute, traits, is_required, copies):
        self.name = name
        self.schema = schema
        self.attribute = attribute
        self.traits = traits
        self.is_required = is_required
        self.copies = copies
        self.is_const_selector = False
        self.constant = None

    def get(self, owner):
        return getattr(owner, self.attribute)

    def set(self, owner, value):
        setattr(owner, self.attribute, value)

    def save(self, owner, writer, context):
        value = self.constant if self.is_const_selector else self.get(owner)
        for _ in range(self.copies):
            writer.push_member(self.name)
            self.schema.save(value, writer, context, self.traits)
            writer.pop_member()

    def load(self, reader, context, owner):
        for _ in range(self.copies):
            if not reader.push_member(self.name):
                if self.is_required:
                    context.log(ResultCode.MISSING_REQUIRED_FIELD, f"{self.name}: missing required field")
                return False
            checkpoint = context.get_log_checkpoint()
            value = self.schema.load(reader, context, self.traits)
            reader.pop()
            if context.has_error(checkpoint):
                return True
            if self.is_const_selector:
                if value != self.constant:
                    context.log(ResultCode.ERROR, f"wrong const value for member {self.name!r}")
            else:
                self.set(owner, value)
        return True


class GenericCompositeSchema(BasicSchema):
    """A struct prints one key per member in registration order and loads schema-driven."""

    def __init__(self, cls, members):
        self.cls = cls
        self.members = members
        self.declared = []
        self.bound_type = cls

    @override
    def do_load(self, reader, context, traits):
        owner = self.cls()
        if not reader.expected_type() & SchemaRWType.OBJECT:
            context.log(ResultCode.ERROR, "expected an object")
            return owner
        checkpoint = context.get_log_checkpoint()
        found = 0
        for member in self.members:
            if member.load(reader, context, owner):
                found += 1
            if context.has_error(checkpoint):
                return owner
        names = {member.name for member in self.members}
        if reader.members() > found:
            for _ in range(reader.members()):
                key = reader.push_next_member()
                reader.pop()
                if key not in names:
                    context.log(ResultCode.UNRECOGNIZED_FIELD, f"{key}: found in the input, but not in the schema")
        return owner

    @override
    def do_save(self, value, writer, context, traits):
        writer.open_object()
        for member in self.members:
            if context.has_error():
                break
            member.save(value, writer, context)
        writer.close()


NON_FINITE = {"NaN": math.nan, "Infinity": math.inf, "-Infinity": -math.inf}
ESCAPED_UUID = re.compile(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}")
ESCAPED_BYTES = re.compile(r"(\\x[0-9a-f]{2})*")
ESCAPED_COLOR = re.compile(r"#[0-9a-f]{8}")
ESCAPED_BITS = re.compile(r"0b[01]+")


class FlatObject(list):
    """The values of an object Bedrock printed with keys that are not strings, in order."""


class BedrockDecoder(json.JSONDecoder):
    """Bedrock's printed JSON, where an object's key slots may hold any value."""

    def __init__(self):
        super().__init__(strict=False)
        self.parse_object = self.object
        self.scan_once = json.scanner.py_make_scanner(self)

    def object(self, text_and_end, _strict, scan_once, *_):
        text, end = text_and_end
        values = []
        end = WHITESPACE.match(text, end).end()
        while text[end : end + 1] != "}":
            value, end = scan_once(text, end)
            values.append(value)
            end = WHITESPACE.match(text, end).end()
            end = WHITESPACE.match(text, end + text.startswith((":", ","), end)).end()
        rebuilt = []
        tokens = iter(values)
        for value in tokens:
            header = bool(rebuilt) and type(rebuilt[-1]) is int and rebuilt[-1] == 10 and value == ""
            if header:
                rebuilt.pop()
            else:
                rebuilt.append(value)
            if header or (type(value) is str and value == "__[[CTD]]__"):
                try:
                    rebuilt.append(CaseForm.nbt_tag(10, tokens))
                except (StopIteration, KeyError, TypeError, ValueError) as error:
                    raise json.JSONDecodeError(f"malformed NBT tokens ({error!r})", text, end) from error
        values = rebuilt
        keys = values[::2]
        plain = len(values) % 2 == 0 and all(type(key) is str for key in keys) and len(set(keys)) == len(keys)
        return (dict(zip(keys, values[1::2], strict=True)) if plain else FlatObject(values)), end + 1


BEDROCK_DECODER = BedrockDecoder()


class CaseForm:
    """Where a golden's JSON departs from Bedrock's: each mapping is deterministic and goes both ways."""

    PLAIN_ENUMS: ClassVar = {"ContainerID", "ContainerType", "NetherWorldType"}

    @classmethod
    def matches(cls, case, bedrock, schema, declared, node):
        """Whether Bedrock's JSON holds a case's value, keys aside, a primitive standing for a one-child object."""
        match schema:
            case OptionalSchema():
                return cls.matches(case, bedrock, schema.element, declared, node)
            case DynamicValueSchema() if isinstance(case, dict):
                return cls.matches(case, bedrock, schema.object, declared, node)
            # "#04010203" vs {"Color": 67174915}
            case ColorCase() if isinstance(case, str):
                return cls.matches(schema.to_bedrock(case), bedrock, schema, declared, node)
            case DynamicValueSchema() if isinstance(case, list):
                return cls.matches(case, bedrock, schema.array, declared, node)
            case VariantCase() if not (isinstance(case, dict) and "__class__" in case):
                return any(
                    cls.matches(case, bedrock, arm, declared, each)
                    for arm, each in zip(schema.inner.arms, cls.arms(schema, node), strict=True)
                )

        # {"__class__": "Pause"} vs {}
        if isinstance(case, dict) and "__class__" in case:
            index = next(i for i, arm in enumerate(schema.inner.arms) if arm.bound_type.__name__ == case["__class__"])
            bare = {key: value for key, value in case.items() if key != "__class__"}
            return cls.matches(bare, bedrock, schema.inner.arms[index], declared, cls.arms(schema, node)[index])

        # {"value": "0b100000001"} vs {"Actor Flag Bitset Data": 129, 2}
        if isinstance(case, dict) and isinstance(bedrock, FlatObject) and isinstance(schema, GenericCompositeSchema):
            index = 0
            for _, value, slot in cls.slots(case, schema):
                index += 1
                if isinstance(value, str) and ESCAPED_BITS.fullmatch(value):
                    groups = cls.varint_groups(int(value, 2))
                    if bedrock[index : index + len(groups)] != groups:
                        return False
                    index += len(groups)
                else:
                    if index >= len(bedrock) or not cls.matches(value, bedrock[index], slot, declared, None):
                        return False
                    index += 1
            return index == len(bedrock)

        # {"entity_id": 1} vs {"Entity ID": 1}
        if (
            isinstance(case, dict)
            and isinstance(bedrock, dict)
            and isinstance(schema, GenericCompositeSchema | MapSchema)
        ):
            slots = cls.slots(case, schema)
            fields = cls.fields(declared, node)
            named = {field.get("name"): field["type"] for field in fields}
            value_node = node.get("value") if isinstance(node, dict) else None
            if len(slots) == len(bedrock) and all(
                cls.matches(value, each, slot, declared, named.get(key, value_node))
                for (_, value, slot), (key, each) in zip(slots, bedrock.items(), strict=True)
            ):
                return True
            if not isinstance(schema, GenericCompositeSchema) or not fields:
                return False

            # {"attach_to_entity_id": -5, "actor_locator": 2} vs {"Entity Actor ID": -5}
            reached = {0}
            for member in schema.declared:
                value = case.get(member.name, MISSING if member in schema.members else member.constant)
                for _ in range(member.copies):
                    aligned = set()
                    for index in reached - {len(fields)}:
                        field = fields[index]
                        name = field.get("name")
                        if name in bedrock:
                            fits = value is not MISSING and cls.matches(
                                value, bedrock[name], member.schema, declared, field["type"]
                            )
                        elif name is not None:
                            fits = value is MISSING and field.get("optional", False)
                        else:
                            fits = member not in schema.members and field.get("value", MISSING) == member.constant
                        if fits:
                            aligned.add(index + 1)
                    reached |= aligned
            return len(fields) in reached and bedrock.keys() <= named.keys()

        # [1, 2] vs [1, 2]
        if isinstance(case, list) and isinstance(bedrock, list) and isinstance(schema, VectorSchema | MapSchema):
            element = schema if isinstance(schema, MapSchema) else schema.element
            element_node = node["type"] if isinstance(node, dict) and "repeat" in node else node
            return len(case) == len(bedrock) and all(
                cls.matches(a, b, element, declared, element_node) for a, b in zip(case, bedrock, strict=True)
            )

        # {"minecraft:anvil": 2} vs [{"key": "minecraft:anvil", "value": {"Value": 2}}]
        if (
            isinstance(case, dict)
            and isinstance(bedrock, list)
            and isinstance(schema, MapSchema)
            and all(isinstance(pair, dict) and pair.keys() == {"key", "value"} for pair in bedrock)
        ):
            pairs = {pair["key"]: pair["value"] for pair in bedrock}
            value_node = node.get("value") if isinstance(node, dict) else None
            return case.keys() == pairs.keys() and all(
                cls.matches(value, pairs[key], schema.value, declared, value_node) for key, value in case.items()
            )

        # "#0a141eff" vs [10, 20, 30, 255]
        if isinstance(case, str) and isinstance(bedrock, list) and ESCAPED_COLOR.fullmatch(case):
            return [int(case[index : index + 2], 16) for index in range(1, 9, 2)] == bedrock

        # "00000000-0000-0001-0000-000000000002" vs {"Most Significant Bits": 1, "Least Significant Bits": 2}
        if isinstance(case, str) and isinstance(bedrock, dict) and len(bedrock) == 2 and ESCAPED_UUID.fullmatch(case):
            most, least = bedrock.values()
            return uuid.UUID(case).int == most << 64 | least

        # "\x2a\xaa" vs "*\udcaa"
        if isinstance(case, str) and isinstance(bedrock, str) and ESCAPED_BYTES.fullmatch(case):
            return bytes.fromhex(case.replace("\\x", "")) == bedrock.encode("utf-8", "surrogateescape")

        # [7, -3] vs "\u0007\udcfd"
        if isinstance(case, list) and isinstance(bedrock, str) and isinstance(schema, SignedBlobCase):
            return schema.to_bedrock(case) == bedrock

        # 0.1 vs 0.10000000149011612
        if type(case) is float and type(bedrock) is float:
            return case == bedrock or cls.widened_float32(case) == bedrock

        # "0b11111" vs 31
        if isinstance(case, str) and type(bedrock) is int and ESCAPED_BITS.fullmatch(case):
            return cls.varint_groups(int(case, 2)) == [bedrock]

        # "{id:\"Chest\"}" vs 10, "", 8, "id", {"data": "Chest"}, 0
        if isinstance(case, str) and isinstance(bedrock, nbtlib.Compound):
            tag = nbtlib.parse_nbt(case)
            return nbtlib.serialize_tag(tag, compact=True) == nbtlib.serialize_tag(bedrock, compact=True)

        # 7 vs {"Actor Runtime ID": 7}
        if isinstance(bedrock, dict) and not isinstance(case, dict | list):
            return len(bedrock) == 1 and cls.matches(case, next(iter(bedrock.values())), schema, declared, None)

        # 27 vs "out_back"
        if type(case) is int and isinstance(bedrock, str) and isinstance(schema, EnumSchema):
            return schema.names.get(bedrock.lower()) == case

        return case == bedrock

    @classmethod
    def locate(cls, case, bedrock, schema, declared, node, path=""):
        """The deepest path where `matches` fails with the case's and Bedrock's values there, or None when it holds."""
        if cls.matches(case, bedrock, schema, declared, node):
            return None
        match schema:
            case OptionalSchema():
                return cls.locate(case, bedrock, schema.element, declared, node, path)
            case DynamicValueSchema() if isinstance(case, dict | list):
                inner = schema.object if isinstance(case, dict) else schema.array
                return cls.locate(case, bedrock, inner, declared, node, path)
            case VariantCase() if not (isinstance(case, dict) and "__class__" in case):
                return path, case, bedrock
        if isinstance(case, dict) and "__class__" in case:
            index = next(i for i, arm in enumerate(schema.inner.arms) if arm.bound_type.__name__ == case["__class__"])
            bare = {key: value for key, value in case.items() if key != "__class__"}
            return cls.locate(bare, bedrock, schema.inner.arms[index], declared, cls.arms(schema, node)[index], path)
        if isinstance(case, dict) and isinstance(bedrock, dict):
            slots = cls.slots(case, schema)
            if len(slots) == len(bedrock):
                named = {field.get("name"): field["type"] for field in cls.fields(declared, node)}
                value_node = node.get("value") if isinstance(node, dict) else None
                for (name, value, slot), (key, each) in zip(slots, bedrock.items(), strict=True):
                    child = named.get(key, value_node)
                    if found := cls.locate(value, each, slot, declared, child, f"{path}.{name}" if path else name):
                        return found
        if isinstance(case, list) and isinstance(bedrock, list) and len(case) == len(bedrock):
            element = schema if isinstance(schema, MapSchema) else schema.element
            element_node = node["type"] if isinstance(node, dict) and "repeat" in node else node
            for index, (a, b) in enumerate(zip(case, bedrock, strict=True)):
                if found := cls.locate(a, b, element, declared, element_node, f"{path}[{index}]"):
                    return found
        return path, case, bedrock

    @staticmethod
    def fields(declared, node):
        return declared[node]["fields"] if isinstance(node, str) and node in declared else []

    @staticmethod
    def arms(schema, node):
        cases = node.get("cases", []) if isinstance(node, dict) else []
        return cases if len(cases) == len(schema.inner.arms) else [None] * len(schema.inner.arms)

    @staticmethod
    def slots(case, schema):
        """Each value of a case object with its name and schema, once per slot Bedrock prints it in."""
        if not isinstance(schema, MapSchema):
            members = {member.name: member for member in schema.members}
            return [
                (key, value, members[key].schema) for key, value in case.items() for _ in range(members[key].copies)
            ]
        if schema.key.bound_type is str:
            return [(key, value, schema.value) for key, value in case.items()]
        return [("key", case["key"], schema.key), ("value", case["value"], schema.value)]

    @staticmethod
    def parse_bedrock(text):
        """Read Bedrock's printed text, valid JSON or not, keeping an object whose tokens leak as its flat values."""
        return BEDROCK_DECODER.decode(text)

    @staticmethod
    def escaped_bytes(raw):
        return "".join(f"\\x{byte:02x}" for byte in raw)

    @staticmethod
    def shortest_float32(value):
        packed = struct.pack("f", value)
        return next(
            each
            for each in (float(f"{value:.{digits}g}") for digits in range(1, 10))
            if struct.pack("f", each) == packed
        )

    @staticmethod
    def widened_float32(value):
        return struct.unpack("f", struct.pack("f", value))[0]

    @staticmethod
    def varint_groups(value):
        groups = [(value >> shift) & 0x7F for shift in range(0, max(value.bit_length(), 1), 7)]
        return [group | 0x80 for group in groups[:-1]] + groups[-1:]

    @staticmethod
    def tokens(stream):
        return iter(stream if isinstance(stream, list) else [stream])

    @staticmethod
    def stream(tokens):
        return tokens[0] if len(tokens) == 1 else TokenList(tokens)

    @classmethod
    def nbt_tag(cls, number, tokens):
        """The tag of type `number` that Bedrock's token stream holds next, a compound without its header."""
        kind = nbtlib.Base.get_tag(number)
        match number:
            case 9:
                element, count = next(tokens), next(tokens)
                return kind[nbtlib.Base.get_tag(element)](cls.nbt_tag(element, tokens) for _ in range(count))
            case 10:
                compound = kind()
                while (entry := next(tokens)) != 0:
                    name = next(tokens)
                    compound[name] = cls.nbt_tag(entry, tokens)
                return compound
            case 7 | 11:
                values = [next(tokens) for _ in range(next(tokens))]
                if not all(issubclass(kind.wrapper, type(value)) for value in values):
                    raise TypeError(f"{values!r}: not tokens for {kind.__name__}")
                wrap = kind.wrapper.from_unsigned if number == 7 else kind.wrapper
                return kind([wrap(value) for value in values])
        value = next(tokens)["data"]
        if not issubclass(kind, type(value)):
            raise TypeError(f"{value!r}: not a token for {kind.__name__}")
        if number == 5:
            return kind(cls.shortest_float32(value))
        return kind.from_unsigned(value) if number == 1 else kind(value)

    @classmethod
    def nbt_tokens(cls, tag, tokens):
        match tag.tag_id:
            case 9:
                tokens += [tag.subtype.tag_id, len(tag)]
                for each in tag:
                    cls.nbt_tokens(each, tokens)
            case 10:
                for name, each in tag.items():
                    tokens += [each.tag_id, name]
                    cls.nbt_tokens(each, tokens)
                tokens.append(0)
            case 7:
                tokens += [len(tag), *tag.tobytes()]
            case 11:
                tokens += [len(tag), *tag.tolist()]
            case 1:
                tokens.append({"data": tag.as_unsigned})
            case 5:
                tokens.append({"data": cls.widened_float32(tag)})
            case _:
                tokens.append({"data": tag.unpack()})


class CaseSchema(BasicSchema):
    """A schema whose JSON the case spells in another form than Bedrock."""

    def __init__(self, inner):
        self.inner = inner
        self.bound_type = inner.bound_type

    def to_case(self, bedrock):
        raise NotImplementedError

    def to_bedrock(self, case):
        raise NotImplementedError

    @override
    def do_save(self, value, writer, context, traits):
        scratch = JSONSchemaWriter()
        self.inner.save(value, scratch, context, traits)
        if scratch.written:
            writer.place(self.to_case(scratch.result))

    @override
    def do_load(self, reader, context, traits):
        return self.inner.load(StrictJSONSchemaReader(self.to_bedrock(reader.node)), context, traits)


class FloatCase(CaseSchema):
    """A float32 as its shortest spelling and a non-finite float by its name."""

    def __init__(self, inner, width):
        super().__init__(inner)
        self.width = width

    @override
    def to_case(self, bedrock):
        return CaseForm.shortest_float32(bedrock) if self.width == 32 else bedrock

    @override
    def to_bedrock(self, case):
        return CaseForm.widened_float32(case) if self.width == 32 and type(case) in (int, float) else case

    @override
    def do_save(self, value, writer, context, traits):
        if math.isfinite(value):
            super().do_save(value, writer, context, traits)
        else:
            writer.place("NaN" if math.isnan(value) else "Infinity" if value > 0 else "-Infinity")

    @override
    def do_load(self, reader, context, traits):
        if isinstance(reader.node, str) and reader.node in NON_FINITE:
            return NON_FINITE[reader.node]
        return super().do_load(reader, context, traits)


class StringCase(CaseSchema):
    """A std::string as its text, or as escaped bytes when it is not valid UTF-8."""

    @override
    def to_case(self, bedrock):
        raw = bedrock.encode("utf-8", "surrogateescape")
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            return CaseForm.escaped_bytes(raw)
        return bedrock

    @override
    def to_bedrock(self, case):
        if isinstance(case, str) and ESCAPED_BYTES.fullmatch(case):
            return bytes.fromhex(case.replace("\\x", "")).decode("utf-8", "surrogateescape")
        return case


class BlobCase(StringCase):
    """A byte blob as escaped bytes."""

    @override
    def to_case(self, bedrock):
        return CaseForm.escaped_bytes(bedrock.encode("utf-8", "surrogateescape"))


class SignedBlobCase(StringCase):
    """A byte blob of int8 values as a list of ints."""

    @override
    def to_case(self, bedrock):
        raw = bedrock.encode("utf-8", "surrogateescape")
        return list(struct.unpack(f"{len(raw)}b", raw))

    @override
    def to_bedrock(self, case):
        if isinstance(case, list):
            return struct.pack(f"{len(case)}b", *case).decode("utf-8", "surrogateescape")
        return case


class BitsetCase(CaseSchema):
    """A compressed bitset as a binary string."""

    @override
    def to_case(self, bedrock):
        return bin(sum((token & 0x7F) << (7 * index) for index, token in enumerate(CaseForm.tokens(bedrock))))

    @override
    def to_bedrock(self, case):
        if isinstance(case, str) and ESCAPED_BITS.fullmatch(case):
            return CaseForm.stream(CaseForm.varint_groups(int(case, 2)))
        return case


class CompoundTagCase(CaseSchema):
    """A compound as its compact SNBT string."""

    @override
    def to_case(self, bedrock):
        tokens = CaseForm.tokens(bedrock)
        if self.inner.header:
            next(tokens)
            next(tokens)
        return nbtlib.serialize_tag(CaseForm.nbt_tag(10, tokens), compact=True)

    @override
    def to_bedrock(self, case):
        if not isinstance(case, str):
            return case
        tokens = [10, ""] if self.inner.header else []
        CaseForm.nbt_tokens(nbtlib.parse_nbt(case), tokens)
        return CaseForm.stream(tokens)


class VariantCase(CaseSchema):
    """A union whose object arm starts with `__class__`, its DSL class name, and loads as that arm alone."""

    @override
    def do_save(self, value, writer, context, traits):
        scratch = JSONSchemaWriter()
        self.inner.save(value, scratch, context, traits)
        if scratch.written:
            bare = scratch.result
            writer.place({"__class__": type(value).__name__, **bare} if isinstance(bare, dict) else bare)

    @override
    def do_load(self, reader, context, traits):
        case = reader.node
        if not isinstance(case, dict):
            return self.inner.load(reader, context, traits)
        name = case.get("__class__")
        arm = next((arm for arm in self.inner.arms if arm.bound_type.__name__ == name), None)
        if arm is None:
            context.log(ResultCode.ERROR, f"__class__: {name!r} names no arm of the union")
            return None
        bare = {key: value for key, value in case.items() if key != "__class__"}
        return arm.load(StrictJSONSchemaReader(bare), context, traits | SerializationTraits.COMPRESSION)


class HexColorSchema(GenericCompositeSchema):
    """A Color255RGBA as the string #rrggbbaa."""

    @override
    def do_load(self, reader, context, traits):
        owner = self.cls()
        text = reader.as_string()
        if text is None or not ESCAPED_COLOR.fullmatch(text):
            context.log(ResultCode.ERROR, "expected #rrggbbaa")
            return owner
        for index, member in enumerate(self.members):
            member.set(owner, int(text[1 + 2 * index : 3 + 2 * index], 16))
        return owner

    @override
    def do_save(self, value, writer, context, traits):
        writer.write("#" + "".join(f"{member.get(value):02x}" for member in self.members))


class ColorCase(BasicSchema):
    """A packed mce::Color as the string #aarrggbb of the int mce::Color::toARGB packs its channels into."""

    def __init__(self, channels):
        self.channels = channels
        self.bound_type = channels.bound_type
        self.order = (channels.members[-1], *channels.members[:-1])

    @staticmethod
    def to_bedrock(case):
        packed = int(case[1:], 16)
        return packed - (1 << 32) if packed >> 31 else packed

    @override
    def do_load(self, reader, context, traits):
        owner = self.channels.cls()
        text = reader.as_string()
        if text is None or not ESCAPED_COLOR.fullmatch(text):
            context.log(ResultCode.ERROR, "expected #aarrggbb")
            return owner
        for index, member in enumerate(self.order):
            member.set(owner, int(text[1 + 2 * index : 3 + 2 * index], 16) / 255)
        return owner

    @override
    def do_save(self, value, writer, context, traits):
        channels = (CaseForm.widened_float32(member.get(value)) for member in self.order)
        writer.write("#" + "".join(f"{int(CaseForm.widened_float32(channel * 255)):02x}" for channel in channels))


MODEL = Schema(build(Path(__file__).parents[1] / "protocol"))


def qualified_name(family):
    return family.name if family.owner is None else f"{qualified_name(family.owner)}.{family.name}"


FAMILIES = {qualified_name(family): family for family in MODEL.order if isinstance(family, Struct)}


MARKER_EXCEPTIONS = {"_deprecated"}


class ReflectionCtx:
    """The schemas of one protocol, built from the model on first use."""

    def __init__(self, protocol):
        self.protocol = protocol
        self.module = importlib.import_module(f"bedrock_protocol.v{protocol}")
        self.composites = {}
        self.live_structs = {key for key in MODEL.live if isinstance(key[0], Struct)}

    def shape(self, family):
        return MODEL.live[family, self.protocol]

    def bound(self, family):
        model = MODEL.model_at(outermost(family), self.protocol)
        scope = MODEL.scope(model)
        home = bedrock_protocol if scope is None else importlib.import_module(f"bedrock_protocol.v{scope}")
        return reduce(getattr, qualified_name(family).split(".")[1:], getattr(home, MODEL.name(model)))

    def served(self):
        result = {}
        for family in MODEL.order:
            if isinstance(family, Struct) and (family, self.protocol) in self.live_structs:
                result[self.bound(family)] = {
                    bedrock_protocol._core.SerializationMode[mode.name]: encoding.since
                    for encoding in MODEL.encodings(MODEL.model_at(family, self.protocol))
                    for mode, runs in encoding.served.items()
                    if any(run.contains(self.protocol) for run in runs)
                }
        return result

    def composite(self, family):
        if family not in self.composites:
            name = qualified_name(family)
            cls = self.bound(family)
            composite = HexColorSchema if name == "Color255RGBA" else GenericCompositeSchema
            self.composites[family] = schema = composite(cls, [])
            for field in self.shape(family).fields:
                attribute = f"{field.name}_" if keyword.iskeyword(field.name) else field.name
                node = field.type
                while isinstance(node, TypeChoice):
                    node = node.when_true
                optional = isinstance(node, OptionalType)
                node = node.element if optional else node
                match node:
                    case Literal(value=MemberRef(enum=enum, name=selector)):
                        number = self.shape(enum).numbers[selector]
                        constant, node = (
                            MODEL.numbering_at(enum, self.protocol).decoded.get(number, number),
                            EnumRef(enum),
                        )
                    case Literal(value=constant):
                        node = Primitive("str" if isinstance(constant, str) else "bool")
                element = self.schema(node)
                member = MemberDescriptor(
                    field.name,
                    OptionalSchema(element) if optional else element,
                    attribute,
                    self.traits(node),
                    not optional,
                    field.duplicate.value if isinstance(field.duplicate, Int) else 1,
                )
                if isinstance(field.type, Literal):
                    member.is_const_selector, member.constant = True, constant
                schema.declared.append(member)
                if not field.name.startswith("_") or field.name in MARKER_EXCEPTIONS:
                    schema.members.append(member)
        return self.composites[family]

    def traits(self, node):
        match node:
            case EnumRef(enum=enum):
                return (
                    SerializationTraits.NONE if enum.name in CaseForm.PLAIN_ENUMS else SerializationTraits.ENUM_AS_VALUE
                )
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
                return StringCase(StringSchema())
            case Primitive(name="bytes"):
                return BlobCase(BlobSchema(False))
            case Primitive(name="float"):
                return FloatCase(FloatSchema(32), 32)
            case Primitive(name="double"):
                return FloatCase(FloatSchema(64), 64)
            case Primitive(name=name, encoded=encoded):
                return IntegerSchema(name, encoded)
            case AliasRef(alias=alias, encoded=encoded):
                return IntegerSchema(alias.primitive.name, encoded)
            case BuiltinRef(builtin=builtin) if builtin.name == "UUID":
                return UUIDSchema()
            case BuiltinRef(builtin=builtin) if builtin.name in ("CompoundTag", "CompoundTagData"):
                return CompoundTagCase(CompoundTagSchema(builtin.name == "CompoundTag"))
            case BuiltinRef(builtin=builtin) if builtin.name == "DynamicValue":
                return DynamicValueSchema()
            case EnumRef(enum=enum, encoded=encoded) if enum.name in CaseForm.PLAIN_ENUMS:
                numbering = MODEL.numbering_at(enum, self.protocol)
                if numbering.encoded or numbering.decoded:
                    raise LoadError(f"{enum.name}: numbers a value apart from it at {self.protocol}")
                return self.schema(Primitive(self.shape(enum).underlying.name, encoded))
            case EnumRef(enum=enum):
                return EnumSchema(
                    self.shape(enum),
                    self.schema(self.shape(enum).underlying),
                    numbering=MODEL.numbering_at(enum, self.protocol),
                )
            case EnumName(enum=enum):
                return EnumSchema(self.shape(enum), None, naming=MODEL.naming_at(enum, self.protocol))
            case StructRef(struct=family):
                return self.composite(family)
            case Color(struct=family):
                return ColorCase(self.composite(family))
            case List(element=Primitive(name="uint8", encoded=None)):
                return BlobCase(BlobSchema(True))
            case List(element=Primitive(name="int8", encoded=None)):
                return SignedBlobCase(BlobSchema(True, signed=True))
            case List(element=element):
                return VectorSchema(self.schema(element))
            case Array(element=element, size=size):
                return ArraySchema(self.schema(element), size)
            case Map(key=key, value=value):
                return MapSchema(self.schema(key), self.schema(value))
            case Variant(cases=arms):
                return VariantCase(
                    VariantSchema([NullTypeSchema() if arm is None else self.schema(arm) for arm in arms])
                )
            case Bitset(width=MemberRef(enum=enum, name=name)):
                return BitsetCase(BitsetSchema(self.shape(enum).numbers[name]))
        raise LookupError(f"{node!r}: has no schema")


REFLECTIONS = {context.module: context for context in map(ReflectionCtx, MODEL.versions)}


def schema_of(module, cls):
    return REFLECTIONS[module].composite(FAMILIES[cls.__qualname__])


class LoadError(ValueError):
    """The entries a strict load logged."""


def save(module, value):
    """The case JSON for a bound struct."""
    writer = JSONSchemaWriter()
    context = SerializerContext()
    schema_of(module, type(value)).save(value, writer, context)
    if context.has_error():
        raise LoadError(context.entries)
    return writer.result


def load(module, cls, value):
    """The bound struct for case JSON, loaded strictly."""
    context = SerializerContext()
    loaded = schema_of(module, cls).load(StrictJSONSchemaReader(value), context)
    if context.has_error():
        raise LoadError(context.entries)
    return loaded


GOLDENS = Path(__file__).parent / "goldens"
CASES = {path: json.loads(path.read_text()) for path in sorted(GOLDENS.glob("*/*.json"))}


@pytest.fixture(name="save")
def fixture_save():
    return save


@pytest.fixture(name="load")
def fixture_load():
    return load


@pytest.fixture(name="served")
def fixture_served():
    return lambda module: REFLECTIONS[module].served()


def pytest_make_parametrize_id(val):
    if isinstance(val, types.ModuleType):
        return val.__name__.rpartition(".")[2]
    return None


def pytest_generate_tests(metafunc):
    if "protocol" in metafunc.fixturenames:
        names = [f"v{version}" for version in bedrock_protocol._core.modes]
        versions = [importlib.import_module(f"bedrock_protocol.{name}") for name in names]
        metafunc.parametrize("protocol", versions, ids=names)

    if "cls" in metafunc.fixturenames and ("case" in metafunc.fixturenames or "round_trip" in metafunc.fixturenames):
        rows = [
            (
                module := importlib.import_module(f"bedrock_protocol.{path.parent.name}"),
                module.packets[int(path.stem[:3])],
                case,
                f"{path.parent.name}/{path.stem}/{case['id']}",
            )
            for path, cases in CASES.items()
            for case in cases
        ]
        argnames = "module, cls, round_trip" if "round_trip" in metafunc.fixturenames else "module, cls, case"
        metafunc.parametrize(argnames, [pytest.param(module, cls, case, id=name) for module, cls, case, name in rows])

    if "case_file" in metafunc.fixturenames:
        metafunc.parametrize("case_file", list(CASES), ids=[f"{path.parent.name}/{path.stem}" for path in CASES])
