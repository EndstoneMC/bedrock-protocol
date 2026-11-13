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
from operator import methodcaller, or_
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar, override

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


class KeyKind(enum.Enum):
    STD_STRING = enum.auto()
    HASHED_STRING = enum.auto()
    OTHER = enum.auto()


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
MISSING = object()


class TokenList(list):
    """Values that a writer gathered into one member slot, which is how BDS prints a token stream."""


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


class StrictRapidJSONSchemaReader(SchemaReader):
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
        frame = self.stack[-1]
        node = frame[0]
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


class RapidJSONSchemaWriter(SchemaWriter):
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


NON_FINITE = {"NaN": math.nan, "Infinity": math.inf, "-Infinity": -math.inf}
ESCAPED_BYTES = re.compile(r"(\\x[0-9a-f]{2})*")
TAG_KINDS = {
    1: "ByteTag",
    2: "ShortTag",
    3: "IntTag",
    4: "Int64Tag",
    5: "FloatTag",
    6: "DoubleTag",
    7: "ByteArrayTag",
    8: "StringTag",
    9: "ListTag",
    10: "CompoundTag",
    11: "IntArrayTag",
}
TAG_IDS = {kind: number for number, kind in TAG_KINDS.items()}


class DslShape(enum.Enum):
    FLATTEN = enum.auto()
    GROUP = enum.auto()
    PAIRS = enum.auto()
    BARE = enum.auto()
    MEMBER_ONLY = enum.auto()
    ARRAY_OF_MEMBERS = enum.auto()


class CaseForm:
    """Where a golden's JSON departs from BDS's: each mapping is deterministic and goes both ways."""

    SHAPES: ClassVar = {
        ("ServerboundDiagnosticsPacket", "telemetry"): (DslShape.FLATTEN, None),
        ("ServerboundDiagnosticsPacket", "entity_system_diagnostics"): (DslShape.FLATTEN, None),
        ("DeathInfoPacket", "death_cause_attack_name"): (DslShape.GROUP, "death_cause_message"),
        ("DeathInfoPacket", "death_cause_message_list"): (DslShape.GROUP, "death_cause_message"),
        ("CameraAimAssistCategoryPriorities", "entities"): (DslShape.PAIRS, KeyKind.OTHER),
        ("CameraAimAssistCategoryPriorities", "blocks"): (DslShape.PAIRS, KeyKind.OTHER),
        ("CameraAimAssistPresetDefinition", "item_settings"): (DslShape.PAIRS, KeyKind.OTHER),
        ("VoxelShapesPacket", "name_map"): (DslShape.PAIRS, KeyKind.HASHED_STRING),
        ("SpawnSettings", "dimension"): (DslShape.BARE, None),
        ("DimensionDefinitionGroup", None): (DslShape.MEMBER_ONLY, None),
        ("EffectDuration", None): (DslShape.MEMBER_ONLY, None),
        ("MoveActorAbsoluteData.Header", None): (DslShape.MEMBER_ONLY, None),
        ("Color255RGBA", None): (DslShape.ARRAY_OF_MEMBERS, None),
    }
    WRAPPER_KEYS: ClassVar = {
        "ActorUniqueID": "actor_unique_id",
        "ActorRuntimeID": "actor_runtime_id",
        "PlayerInputTick": "input_tick",
        "DimensionType": "value",
        "Color": "color",
    }
    PLAIN_ENUMS: ClassVar = {"ContainerID", "ContainerType", "NetherWorldType"}

    @staticmethod
    def escaped_bytes(raw):
        return "".join(f"\\x{byte:02x}" for byte in raw)

    @staticmethod
    def raw_string(text):
        pairs = re.findall(r"\\x(..)", text)
        return bytes.fromhex("".join(pairs)).decode("utf-8", "surrogateescape")

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
    def non_finite_name(value):
        return "NaN" if math.isnan(value) else "Infinity" if value > 0 else "-Infinity"

    @staticmethod
    def varint_groups(value):
        groups = [(value >> shift) & 0x7F for shift in range(0, max(value.bit_length(), 1), 7)]
        return [group | 0x80 for group in groups[:-1]] + groups[-1:]

    @staticmethod
    def tokens(stream):
        return iter(stream if isinstance(stream, list) else [stream])

    @classmethod
    def stream(cls, tokens):
        return tokens[0] if len(tokens) == 1 else TokenList(tokens)

    @classmethod
    def nbt_payload(cls, number, tokens):
        kind = TAG_KINDS[number]
        match kind:
            case "CompoundTag":
                return {kind: cls.nbt_entries(tokens)}
            case "ListTag":
                element, count = next(tokens), next(tokens)
                return {kind: {"type": element, "tags": [cls.nbt_payload(element, tokens) for _ in range(count)]}}
            case "ByteArrayTag" | "IntArrayTag":
                return {kind: [next(tokens) for _ in range(next(tokens))]}
            case "FloatTag":
                return {kind: cls.shortest_float32(next(tokens)["data"])}
        return {kind: next(tokens)["data"]}

    @classmethod
    def nbt_entries(cls, tokens):
        entries = {}
        while (number := next(tokens)) != 0:
            name = next(tokens)
            entries[name] = cls.nbt_payload(number, tokens)
        return entries

    @classmethod
    def nbt_tokens(cls, tag, tokens):
        [(kind, payload)] = tag.items()
        match kind:
            case "CompoundTag":
                cls.nbt_entry_tokens(payload, tokens)
            case "ListTag":
                tokens += [payload["type"], len(payload["tags"])]
                for each in payload["tags"]:
                    cls.nbt_tokens(each, tokens)
            case "ByteArrayTag" | "IntArrayTag":
                tokens += [len(payload), *payload]
            case "FloatTag":
                tokens.append({"data": cls.widened_float32(payload)})
            case _:
                tokens.append({"data": payload})

    @classmethod
    def nbt_entry_tokens(cls, entries, tokens):
        for name, tag in entries.items():
            [(kind, _)] = tag.items()
            tokens += [TAG_IDS[kind], name]
            cls.nbt_tokens(tag, tokens)
        tokens.append(0)


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
    """An integer member, printed in the range of its wire type as BDS's member holds it."""

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

    def __init__(self, declared, wire=None):
        self.declared = self.bounds(declared)
        self.wire = self.bounds(wire or declared)
        self.read = self.READS[(wire or declared).replace("varint", "int")]

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
        writer.write(self.fit(int(value), self.wire))


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
    """BDS's std::vector<uint8_t>, read and written as raw bytes."""

    def __init__(self, listed):
        self.bound_type = list if listed else bytes
        self.listed = listed

    @override
    def do_load(self, reader, context, traits):
        value = reader.as_raw_bytes()
        if value is None:
            context.log(ResultCode.ERROR, "invalid blob: failed to parse input as binary data")
            value = b""
        return list(value) if self.listed else value

    @override
    def do_save(self, value, writer, context, traits):
        writer.write(bytes(value))


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

    def __init__(self, shape, underlying):
        self.underlying = underlying
        self.wire_names = {}
        self.numbers = {}
        for member in shape.members:
            number = shape.numbers[member.name]
            self.wire_names.setdefault(number, member.wire_name)
            self.numbers.setdefault(member.wire_name, number)

    @override
    def do_load(self, reader, context, traits):
        if traits & SerializationTraits.ENUM_AS_VALUE:
            number = self.underlying.load(reader, context)
            if number not in self.wire_names:
                context.log(ResultCode.INVALID_ENUM_VALUE, f"{number}: invalid enum value")
            return number
        name = reader.as_string()
        if name is None:
            context.log(ResultCode.ERROR, "invalid string")
        elif name.lower() not in self.numbers:
            context.log(ResultCode.INVALID_ENUM_VALUE, f"{name!r}: invalid enum value")
        return self.numbers.get((name or "").lower(), 0)

    @override
    def do_save(self, value, writer, context, traits):
        number = int(value)
        if number not in self.wire_names:
            context.log(ResultCode.INVALID_ENUM_VALUE, f"{number}: not bound")
        elif traits & SerializationTraits.ENUM_AS_VALUE:
            self.underlying.save(number, writer, context)
        else:
            writer.write(self.wire_names[number])


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

    def __init__(self, key, value, key_kind):
        self.key = key
        self.value = value
        self.key_kind = key_kind

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
                if self.key_kind is KeyKind.OTHER:
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
            context.log(
                ResultCode.ERROR, "expected an array" if self.key_kind is KeyKind.OTHER else "expected an object"
            )
        return values

    @override
    def do_save(self, value, writer, context, traits):
        if self.key_kind is KeyKind.STD_STRING:
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
        self.array = VectorSchema(self)
        self.object = MapSchema(StringSchema(), self, KeyKind.STD_STRING)
        self.integer = IntegerSchema("int64")
        self.float = FloatSchema(64)
        self.string = StringSchema()
        self.boolean = BoolSchema()

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
    """A compound as BDS writes it: an optional header, then type, name and payload per entry, then 0."""

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
        self.count = IntegerSchema("int32")
        self.string = StringSchema()
        self.int32 = IntegerSchema("int32")
        self.primitives = {
            1: IntegerSchema("int8"),
            2: IntegerSchema("int16"),
            3: self.int32,
            4: IntegerSchema("int64"),
            5: FloatSchema(32),
            6: FloatSchema(64),
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
            self.count.save(len(tag), writer, context)
            for index in range(len(tag)):
                if self.IDS[type(tag[index])] != int(tag.type):
                    context.log(ResultCode.ERROR, "Unexpected type")
                else:
                    self.save_payload(tag[index], writer, context)
        elif number in (7, 11):
            self.count.save(len(tag.value), writer, context)
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
            element, count = self.uint8.load(reader, context), self.count.load(reader, context)
            tags = [self.load_payload(element, reader, context) for _ in range(count)]
            return nbt.ListTag() if context.has_error(checkpoint) else nbt.ListTag(tags, element)
        if number in (7, 11):
            count = self.count.load(reader, context)
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


class CaseSchema(BasicSchema):
    """A schema whose JSON the case spells in another form than BDS."""

    def __init__(self, inner):
        self.inner = inner
        self.bound_type = inner.bound_type

    def to_case(self, bds):
        raise NotImplementedError

    def to_bds(self, case):
        raise NotImplementedError

    @override
    def do_save(self, value, writer, context, traits):
        scratch = RapidJSONSchemaWriter()
        self.inner.save(value, scratch, context, traits)
        if scratch.written:
            writer.place(self.to_case(scratch.result))

    @override
    def do_load(self, reader, context, traits):
        return self.inner.load(StrictRapidJSONSchemaReader(self.to_bds(reader.node)), context, traits)


class FloatCase(CaseSchema):
    """A float32 as its shortest spelling and a non-finite float by its name."""

    def __init__(self, inner, width):
        super().__init__(inner)
        self.width = width

    @override
    def to_case(self, bds):
        return CaseForm.shortest_float32(bds) if self.width == 32 else bds

    @override
    def to_bds(self, case):
        return CaseForm.widened_float32(case) if self.width == 32 and type(case) in (int, float) else case

    @override
    def do_save(self, value, writer, context, traits):
        if math.isfinite(value):
            super().do_save(value, writer, context, traits)
        else:
            writer.place(CaseForm.non_finite_name(value))

    @override
    def do_load(self, reader, context, traits):
        if isinstance(reader.node, str) and reader.node in NON_FINITE:
            return NON_FINITE[reader.node]
        return super().do_load(reader, context, traits)


class StringCase(CaseSchema):
    """A std::string as its text, or as escaped bytes when it is not valid UTF-8."""

    @override
    def to_case(self, bds):
        raw = bds.encode("utf-8", "surrogateescape")
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            return CaseForm.escaped_bytes(raw)
        return bds

    @override
    def to_bds(self, case):
        return CaseForm.raw_string(case) if isinstance(case, str) and ESCAPED_BYTES.fullmatch(case) else case


class BlobCase(StringCase):
    """A byte blob as escaped bytes."""

    @override
    def to_case(self, bds):
        return CaseForm.escaped_bytes(bds.encode("utf-8", "surrogateescape"))


class BitsetCase(CaseSchema):
    """A compressed bitset as a plain integer."""

    @override
    def to_case(self, bds):
        return sum((token & 0x7F) << (7 * index) for index, token in enumerate(CaseForm.tokens(bds)))

    @override
    def to_bds(self, case):
        return CaseForm.stream(CaseForm.varint_groups(case)) if type(case) is int and case >= 0 else case


class CompoundTagCase(CaseSchema):
    """A compound as the typed tags of its entries."""

    def __init__(self, inner):
        super().__init__(inner)
        self.header = inner.header

    @override
    def to_case(self, bds):
        tokens = CaseForm.tokens(bds)
        if self.header:
            next(tokens), next(tokens)
        return CaseForm.nbt_entries(tokens)

    @override
    def to_bds(self, case):
        tokens = [10, ""] if self.header else []
        CaseForm.nbt_entry_tokens(case, tokens)
        return CaseForm.stream(tokens)


class MemberDescriptor:
    """A struct member, reached from the owner through the bound attributes of its path."""

    def __init__(self, name, schema, path, traits=SerializationTraits.NONE, is_required=True):
        self.name = name
        self.schema = schema
        self.path = path
        self.traits = traits
        self.is_required = is_required
        self.is_const_selector = False
        self.constant = None

    def get(self, owner):
        return reduce(getattr, self.path, owner)

    def set(self, owner, value):
        setattr(reduce(getattr, self.path[:-1], owner), self.path[-1], value)

    def save(self, owner, writer, context):
        writer.push_member(self.name)
        value = self.constant if self.is_const_selector else self.get(owner)
        self.schema.save(value, writer, context, self.traits)
        writer.pop_member()

    def load(self, reader, context, owner):
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


class GroupMember(MemberDescriptor):
    """A member that BDS nests and the DSL keeps flat, read from and written into the owner itself."""

    @override
    def set(self, owner, value):
        for attribute, each in vars(value).items():
            setattr(owner, attribute, each)


class GenericCompositeSchema(BasicSchema):
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

    @override
    def do_load(self, reader, context, traits):
        owner = self.create()
        if not reader.expected_type() & SchemaRWType.OBJECT:
            context.log(ResultCode.ERROR, "expected an object")
            return self.finish(owner)
        checkpoint = context.get_log_checkpoint()
        found = 0
        for member in self.members:
            found += member.load(reader, context, owner)
            if context.has_error(checkpoint):
                return self.finish(owner)
        names = {member.name for member in self.members}
        if reader.members() > found:
            for _ in range(reader.members()):
                key = reader.push_next_member()
                reader.pop()
                if key not in names:
                    context.log(ResultCode.UNRECOGNIZED_FIELD, f"{key}: found in the input, but not in the schema")
        return self.finish(owner)

    @override
    def do_save(self, value, writer, context, traits):
        owner = self.view(value)
        writer.open_object()
        for member in self.members:
            if context.has_error():
                break
            member.save(owner, writer, context)
        writer.close()


class WrapperSchema(GenericCompositeSchema):
    """BDS's one-member struct around a value that the DSL holds bare."""

    def __init__(self, key, inner):
        super().__init__(int, [MemberDescriptor(key, inner, ("value",))])

    @override
    def create(self):
        return SimpleNamespace(value=0)

    @override
    def view(self, value):
        return SimpleNamespace(value=value)

    @override
    def finish(self, owner):
        return owner.value


class UUIDHalvesSchema(GenericCompositeSchema):
    """mce::UUID as BDS reflects it: the big-endian halves of the 128-bit value."""

    def __init__(self):
        half = IntegerSchema("uint64")
        members = [
            MemberDescriptor("most_significant_bits", half, ("most",)),
            MemberDescriptor("least_significant_bits", half, ("least",)),
        ]
        super().__init__(uuid.UUID, members)

    @override
    def create(self):
        return SimpleNamespace(most=0, least=0)

    @override
    def view(self, value):
        return SimpleNamespace(most=value.int >> 64, least=value.int & (1 << 64) - 1)

    @override
    def finish(self, owner):
        return uuid.UUID(int=owner.most << 64 | owner.least)


class MemberOnlySchema(GenericCompositeSchema):
    """A one-member struct that BDS prints as its member."""

    @override
    def do_load(self, reader, context, traits):
        owner = self.create()
        [member] = self.members
        checkpoint = context.get_log_checkpoint()
        value = member.schema.load(reader, context, member.traits)
        if not context.has_error(checkpoint):
            member.set(owner, value)
        return self.finish(owner)

    @override
    def do_save(self, value, writer, context, traits):
        [member] = self.members
        member.schema.save(member.get(self.view(value)), writer, context, member.traits)


class ArrayOfMembersSchema(GenericCompositeSchema):
    """A struct that BDS prints as an array of its members."""

    @override
    def do_load(self, reader, context, traits):
        owner = self.create()
        if not reader.expected_type() & SchemaRWType.ARRAY or reader.length(len(self.members)) != len(self.members):
            context.log(ResultCode.ERROR, f"expected exactly {len(self.members)} elements")
            return self.finish(owner)
        for index, member in enumerate(self.members):
            checkpoint = context.get_log_checkpoint()
            reader.push_element(index)
            value = member.schema.load(reader, context, member.traits)
            reader.pop()
            if not context.has_error(checkpoint):
                member.set(owner, value)
        return self.finish(owner)

    @override
    def do_save(self, value, writer, context, traits):
        owner = self.view(value)
        writer.open_array(False, len(self.members))
        for member in self.members:
            member.schema.save(member.get(owner), writer, context, member.traits)
        writer.close()


MARKER_EXCEPTIONS = {"_deprecated"}
COMPOSITES = {DslShape.MEMBER_ONLY: MemberOnlySchema, DslShape.ARRAY_OF_MEMBERS: ArrayOfMembersSchema}


class ReflectionCtx:
    """The schemas of one protocol, built from the model on first use."""

    def __init__(self, protocol, mapped):
        self.protocol = protocol
        self.mapped = mapped
        self.module = importlib.import_module(f"bedrock_protocol.v{protocol}")
        self.composites = {}

    def shape(self, family):
        return MODEL.live[family, self.protocol]

    def case(self, schema, case_class, *arguments):
        return case_class(schema, *arguments) if self.mapped else schema

    def composite(self, family):
        if family not in self.composites:
            name = qualified_name(family)
            kind, _ = CaseForm.SHAPES.get((name, None), (None, None))
            cls = reduce(getattr, name.split("."), self.module)
            self.composites[family] = schema = COMPOSITES.get(kind, GenericCompositeSchema)(cls, [])
            schema.members = self.members(family)
        return self.composites[family]

    def members(self, family):
        name = qualified_name(family)
        members, groups = [], {}
        for field in self.shape(family).fields:
            if field.name.startswith("_") and field.name not in MARKER_EXCEPTIONS:
                continue
            kind, argument = CaseForm.SHAPES.get((name, field.name), (None, None))
            attribute = f"{field.name}_" if keyword.iskeyword(field.name) else field.name
            if kind is DslShape.FLATTEN:
                for each in self.members(field.type.struct):
                    flattened = copy(each)
                    flattened.path = (attribute, *each.path)
                    members.append(flattened)
                continue
            member = self.member(field, kind, argument, attribute)
            if kind is not DslShape.GROUP:
                members.append(member)
                continue
            if argument not in groups:
                groups[argument] = GroupMember(argument, GenericCompositeSchema(SimpleNamespace, []), ())
                members.append(groups[argument])
            groups[argument].schema.members.append(member)
        return members

    def member(self, field, kind, argument, attribute):
        node = field.type
        optional = isinstance(node, OptionalType)
        node = node.element if optional else node
        match node:
            case Literal(value=MemberRef(enum=enum, name=name)):
                constant, node = self.shape(enum).numbers[name], EnumRef(enum)
            case Literal(value=constant):
                node = Primitive("str" if isinstance(constant, str) else "bool")
        if kind is DslShape.BARE:
            node = AliasRef(node.alias, node.alias.primitive.name)
        schema = self.schema(node, argument if kind is DslShape.PAIRS else None)
        schema = OptionalSchema(schema) if optional else schema
        member = MemberDescriptor(field.name, schema, (attribute,), self.traits(node), not optional)
        if isinstance(field.type, Literal):
            member.is_const_selector, member.constant = True, constant
        return member

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

    def schema(self, node, key_kind=None):
        match node:
            case Primitive(name="bool"):
                return BoolSchema()
            case Primitive(name="str"):
                return self.case(StringSchema(), StringCase)
            case Primitive(name="bytes"):
                return self.case(BlobSchema(False), BlobCase)
            case Primitive(name="float"):
                return self.case(FloatSchema(32), FloatCase, 32)
            case Primitive(name="double"):
                return self.case(FloatSchema(64), FloatCase, 64)
            case Primitive(name=name, wire=wire):
                return IntegerSchema(name, wire)
            case AliasRef(alias=alias, wire=wire):
                integer = IntegerSchema(alias.primitive.name, wire)
                key = CaseForm.WRAPPER_KEYS.get(alias.name)
                return integer if wire or key is None else WrapperSchema(key, integer)
            case BuiltinRef(builtin=builtin, wire="str") if builtin.name == "UUID":
                return UUIDSchema()
            case BuiltinRef(builtin=builtin) if builtin.name == "UUID":
                return UUIDHalvesSchema()
            case BuiltinRef(builtin=builtin) if builtin.name in ("CompoundTag", "CompoundTagData"):
                return self.case(CompoundTagSchema(builtin.name == "CompoundTag"), CompoundTagCase)
            case BuiltinRef(builtin=builtin) if builtin.name == "DynamicValue":
                return DynamicValueSchema()
            case EnumRef(enum=enum, wire=wire) if enum.name in CaseForm.PLAIN_ENUMS:
                return self.schema(Primitive(self.shape(enum).underlying.name, wire))
            case EnumRef(enum=enum):
                return EnumSchema(self.shape(enum), self.schema(self.shape(enum).underlying))
            case EnumName(enum=enum):
                return EnumSchema(self.shape(enum), None)
            case StructRef(struct=family):
                return self.composite(family)
            case List(element=Primitive(name="uint8", wire=None)):
                return self.case(BlobSchema(True), BlobCase)
            case List(element=element):
                return VectorSchema(self.schema(element))
            case Array(element=element, size=size):
                return ArraySchema(self.schema(element), size)
            case Map(key=key, value=value):
                kind = key_kind or (KeyKind.STD_STRING if key == Primitive("str") else KeyKind.OTHER)
                return MapSchema(self.schema(key), self.schema(value), kind)
            case Variant(cases=arms):
                return VariantSchema([NullTypeSchema() if arm is None else self.schema(arm) for arm in arms])
            case Bitset(width=MemberRef(enum=enum, name=name)):
                return self.case(BitsetSchema(self.shape(enum).numbers[name]), BitsetCase)
        raise LookupError(f"{node!r}: has no schema")


REFLECTIONS = {
    (protocol, mapped): ReflectionCtx(protocol, mapped) for protocol in MODEL.versions for mapped in (False, True)
}


@cache
def schema_of(cls, mapped):
    return REFLECTIONS[int(cls.__module__.rpartition(".v")[2]), mapped].composite(FAMILIES[cls.__qualname__])


def save(value, bds=False):
    """The case JSON for a bound struct, or BDS's own JSON with `bds`."""
    writer = RapidJSONSchemaWriter()
    schema_of(type(value), not bds).save(value, writer, SerializerContext())
    return writer.result


def load(cls, value, bds=False):
    """The bound struct for case JSON, or for BDS's own JSON with `bds`, loaded strictly."""
    context = SerializerContext()
    loaded = schema_of(cls, not bds).load(StrictRapidJSONSchemaReader(value), context)
    if context.has_error():
        raise LoadError(context.entries)
    return loaded
