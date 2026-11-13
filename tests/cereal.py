"""BDS's cereal JSON reader and writer, over the bound packets and the compiler's schema model."""

import importlib
import keyword
import math
import re
import struct
import uuid
from functools import cache, reduce
from pathlib import Path

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


class LoadError(ValueError):
    """What BDS logs as an error while loading."""


class BasicSchema:
    def do_load(self, value):
        raise NotImplementedError

    def do_save(self, value):
        raise NotImplementedError

    def holds(self, _value):
        return False


class BoolSchema(BasicSchema):
    def do_load(self, value):
        if type(value) is not bool:
            raise LoadError(f"{value!r}: expected a bool")
        return value

    def do_save(self, value):
        return bool(value)

    def holds(self, value):
        return type(value) is bool


class IntegerSchema(BasicSchema):
    """An integer member, printed in the range of its wire type as BDS's member holds it."""

    def __init__(self, declared, wire=None):
        self.declared = self.bounds(declared)
        self.wire = self.bounds(wire or declared)

    @staticmethod
    def bounds(name):
        bits = int(re.search(r"\d+", name)[0])
        return range(1 << bits) if name.startswith("u") else range(-(1 << (bits - 1)), 1 << (bits - 1))

    @staticmethod
    def fit(value, bounds):
        return (value - bounds.start) % (bounds.stop - bounds.start) + bounds.start

    def do_load(self, value):
        if type(value) is not int or value not in self.wire:
            raise LoadError(f"{value!r}: expected an integer in {self.wire}")
        return self.fit(value, self.declared)

    def do_save(self, value):
        return self.fit(value, self.wire)

    def holds(self, value):
        return type(value) is int


NON_FINITE = {"NaN": float("nan"), "Infinity": float("inf"), "-Infinity": float("-inf")}


class FloatSchema(BasicSchema):
    def __init__(self, bits):
        self.bits = bits

    def do_load(self, value):
        if isinstance(value, str) and value in NON_FINITE:
            return NON_FINITE[value]
        if type(value) not in (int, float):
            raise LoadError(f"{value!r}: expected a number")
        if self.bits == 32:
            try:
                struct.pack("f", value)
            except OverflowError as error:
                raise LoadError(f"{value!r}: out of range for a float") from error
        return float(value)

    def do_save(self, value):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        if self.bits == 64:
            return value
        shortest = (float(f"{value:.{digits}g}") for digits in range(1, 10))
        return next(each for each in shortest if struct.pack("f", each) == struct.pack("f", value))

    def holds(self, value):
        return type(value) is float


class StringSchema(BasicSchema):
    def do_load(self, value):
        if type(value) is not str:
            raise LoadError(f"{value!r}: expected a string")
        return value

    def do_save(self, value):
        return value

    def holds(self, value):
        return type(value) is str


class BytesSchema(BasicSchema):
    def do_load(self, value):
        try:
            return bytes.fromhex(value)
        except (TypeError, ValueError) as error:
            raise LoadError(f"{value!r}: expected hex text") from error

    def do_save(self, value):
        return value.hex()


class AliasSchema(BasicSchema):
    def __init__(self, integer):
        self.integer = integer

    def do_load(self, value):
        return self.integer.do_load(value)

    def do_save(self, value):
        return self.integer.do_save(value)

    def holds(self, value):
        return self.integer.holds(value)


class UUIDSchema(BasicSchema):
    def do_load(self, value):
        try:
            return uuid.UUID(value)
        except (AttributeError, TypeError, ValueError) as error:
            raise LoadError(f"{value!r}: expected a UUID") from error

    def do_save(self, value):
        return str(value)


class DynamicValueSchema(BasicSchema):
    def do_load(self, value):
        return value

    def do_save(self, value):
        return value


class NullSchema(BasicSchema):
    def do_load(self, value):
        if value is not None:
            raise LoadError(f"{value!r}: expected null")

    def do_save(self, _value):
        return None

    def holds(self, value):
        return value is None


class LiteralSchema(BasicSchema):
    """A const selector, which BDS prints with its constant and checks on load."""

    def __init__(self, constant):
        self.constant = constant

    def do_load(self, value):
        if type(value) is not type(self.constant) or value != self.constant:
            raise LoadError(f"{value!r}: wrong const value, expected {self.constant!r}")

    def do_save(self, _value):
        return self.constant


class EnumNameSchema(BasicSchema):
    def __init__(self, shape):
        self.numbers = {member.wire_name: shape.numbers[member.name] for member in shape.members}
        self.wire_names = {member.name: member.wire_name for member in shape.members}

    def do_load(self, value):
        if not isinstance(value, str) or value.lower() not in self.numbers:
            raise LoadError(f"{value!r}: not an enumerator name")
        return self.numbers[value.lower()]

    def do_save(self, value):
        return self.wire_names[value.name]


class BitsetSchema(BasicSchema):
    def __init__(self, width):
        self.width = width

    def do_load(self, value):
        if type(value) is not int or value not in range(1 << self.width):
            raise LoadError(f"{value!r}: expected a {self.width}-bit integer")
        return value

    def do_save(self, value):
        return value


class VectorSchema(BasicSchema):
    def __init__(self, element):
        self.element = element

    def do_load(self, value):
        if not isinstance(value, list):
            raise LoadError(f"{value!r}: expected an array")
        return [self.element.do_load(each) for each in value]

    def do_save(self, value):
        return [self.element.do_save(each) for each in value]


class ArraySchema(VectorSchema):
    def __init__(self, element, size):
        super().__init__(element)
        self.size = size

    def do_load(self, value):
        if isinstance(value, list) and len(value) != self.size:
            raise LoadError(f"{value!r}: expected exactly {self.size} elements")
        return super().do_load(value)


class MapSchema(BasicSchema):
    """An object for a std::string key and an array of key and value objects for any other."""

    def __init__(self, key, value, keyed_by_string):
        self.key = key
        self.value = value
        self.keyed_by_string = keyed_by_string

    def do_load(self, value):
        if self.keyed_by_string:
            if not isinstance(value, dict):
                raise LoadError(f"{value!r}: expected an object")
            return {self.key.do_load(key): self.value.do_load(each) for key, each in value.items()}
        if not isinstance(value, list) or any(
            not isinstance(each, dict) or each.keys() != {"key", "value"} for each in value
        ):
            raise LoadError(f"{value!r}: expected an array of key and value objects")
        return {self.key.do_load(each["key"]): self.value.do_load(each["value"]) for each in value}

    def do_save(self, value):
        if self.keyed_by_string:
            return {self.key.do_save(key): self.value.do_save(each) for key, each in value.items()}
        return [{"key": self.key.do_save(key), "value": self.value.do_save(each)} for key, each in value.items()]


class VariantSchema(BasicSchema):
    """A variant prints its active arm bare and loads the first arm that loads cleanly."""

    def __init__(self, arms):
        self.arms = arms

    def do_load(self, value):
        for arm in self.arms:
            try:
                return arm.do_load(value)
            except LoadError:
                continue
        raise LoadError(f"{value!r}: no arm loads it")

    def do_save(self, value):
        for arm in self.arms:
            if arm.holds(value):
                return arm.do_save(value)
        raise LoadError(f"{value!r}: no arm holds it")


class TagSchema(BasicSchema):
    def __init__(self, context):
        self.compound = CompoundTagSchema(self)
        self.tags = VectorSchema(self)
        integers = {name: context.schema(Primitive(name)) for name in ("int8", "int16", "int32", "int64")}
        self.payloads = {
            nbt.ByteTag: integers["int8"],
            nbt.ShortTag: integers["int16"],
            nbt.IntTag: integers["int32"],
            nbt.Int64Tag: integers["int64"],
            nbt.FloatTag: context.schema(Primitive("float")),
            nbt.DoubleTag: context.schema(Primitive("double")),
            nbt.StringTag: context.schema(Primitive("str")),
            nbt.ByteArrayTag: VectorSchema(integers["int8"]),
            nbt.IntArrayTag: VectorSchema(integers["int32"]),
        }
        self.kinds = {cls.__name__: cls for cls in self.payloads}

    def do_load(self, value):
        if value is None:
            return None
        if not isinstance(value, dict) or len(value) != 1:
            raise LoadError(f"{value!r}: expected a one-key object")
        [(kind, payload)] = value.items()
        if kind == "CompoundTag":
            return self.compound.do_load(payload)
        if kind == "ListTag":
            if not isinstance(payload, dict) or payload.keys() != {"type", "tags"}:
                raise LoadError(f"{payload!r}: expected a type and tags")
            return nbt.ListTag(self.tags.do_load(payload["tags"]), payload["type"])
        if kind not in self.kinds:
            raise LoadError(f"{kind!r}: not a tag kind")
        cls = self.kinds[kind]
        return cls(self.payloads[cls].do_load(payload))

    def do_save(self, value):
        if value is None:
            return None
        if isinstance(value, nbt.CompoundTag):
            return {"CompoundTag": self.compound.do_save(value)}
        if isinstance(value, nbt.ListTag):
            return {"ListTag": {"type": int(value.type), "tags": self.tags.do_save(value)}}
        return {type(value).__name__: self.payloads[type(value)].do_save(value.value)}


class CompoundTagSchema(BasicSchema):
    def __init__(self, tag):
        self.tag = tag

    def do_load(self, value):
        if not isinstance(value, dict):
            raise LoadError(f"{value!r}: expected an object")
        compound = nbt.CompoundTag()
        for key, each in value.items():
            compound[key] = self.tag.do_load(each)
        return compound

    def do_save(self, value):
        return {key: self.tag.do_save(each) for key, each in value.items()}


class Member:
    """A struct member, saved under its schema name and read back from the bound attribute."""

    def __init__(self, name, schema, optional):
        self.name = name
        self.attribute = f"{name}_" if keyword.iskeyword(name) else name
        self.schema = schema
        self.optional = optional

    def get(self, owner):
        return getattr(owner, self.attribute)

    def set(self, owner, value):
        setattr(owner, self.attribute, value)

    def do_save(self, owner, saved):
        value = self.get(owner)
        if value is not None or not self.optional:
            saved[self.name] = self.schema.do_save(value)

    def do_load(self, saved, owner):
        if self.name in saved:
            self.set(owner, self.schema.do_load(saved[self.name]))
        elif not self.optional:
            raise LoadError(f"{self.name}: is missing")


class ConstSelector(Member):
    """A member BDS binds to a constant, which no attribute holds."""

    def get(self, _owner):
        return None

    def set(self, _owner, _value):
        pass


class CompositeSchema(BasicSchema):
    """A struct prints one key per member in registration order and loads strictly."""

    def __init__(self, context, family):
        self.qualified_name = qualified_name(family)
        self.cls = reduce(getattr, self.qualified_name.split("."), context.module)
        self.members = []
        context.composites[family] = self
        for field in context.shape(family).fields:
            if field.name.startswith("_"):
                continue
            optional = isinstance(field.type, OptionalType)
            schema = context.schema(field.type.element if optional else field.type)
            kind = ConstSelector if isinstance(field.type, Literal) else Member
            self.members.append(kind(field.name, schema, optional))

    def do_load(self, value):
        if not isinstance(value, dict):
            raise LoadError(f"{value!r}: expected an object")
        unknown = value.keys() - {member.name for member in self.members}
        if unknown:
            raise LoadError(f"{sorted(unknown)}: not members of {self.qualified_name}")
        owner = self.cls()
        for member in self.members:
            member.do_load(value, owner)
        return owner

    def do_save(self, value):
        saved = {}
        for member in self.members:
            member.do_save(value, saved)
        return saved

    def holds(self, value):
        return type(value).__qualname__ == self.qualified_name


class SerializerContext:
    """The schemas of one protocol, built from the model on first use."""

    def __init__(self, protocol):
        self.protocol = protocol
        self.module = importlib.import_module(f"bedrock_protocol.v{protocol}")
        self.composites = {}

    def shape(self, family):
        return MODEL.live[family, self.protocol]

    def composite(self, family):
        return self.composites.get(family) or CompositeSchema(self, family)

    def schema(self, node):
        match node:
            case Primitive(name="bool"):
                return BoolSchema()
            case Primitive(name="str"):
                return StringSchema()
            case Primitive(name="bytes"):
                return BytesSchema()
            case Primitive(name="float"):
                return FloatSchema(32)
            case Primitive(name="double"):
                return FloatSchema(64)
            case Primitive(name=name, wire=wire):
                return IntegerSchema(name, wire)
            case AliasRef(alias=alias, wire=wire):
                return AliasSchema(IntegerSchema(alias.primitive.name, wire))
            case BuiltinRef(builtin=builtin) if builtin.name == "UUID":
                return UUIDSchema()
            case BuiltinRef(builtin=builtin) if builtin.name in ("CompoundTag", "CompoundTagData"):
                return TagSchema(self).compound
            case BuiltinRef(builtin=builtin) if builtin.name == "DynamicValue":
                return DynamicValueSchema()
            case EnumRef(enum=enum):
                return self.schema(self.shape(enum).underlying)
            case EnumName(enum=enum):
                return EnumNameSchema(self.shape(enum))
            case StructRef(struct=family):
                return self.composite(family)
            case List(element=element):
                return VectorSchema(self.schema(element))
            case Array(element=element, size=size):
                return ArraySchema(self.schema(element), size)
            case Map(key=key, value=value):
                return MapSchema(self.schema(key), self.schema(value), key == Primitive("str"))
            case Variant(cases=arms):
                return VariantSchema([NullSchema() if arm is None else self.schema(arm) for arm in arms])
            case Literal(value=MemberRef(enum=enum, name=name)):
                return LiteralSchema(self.shape(enum).numbers[name])
            case Literal(value=constant):
                return LiteralSchema(constant)
            case Bitset(width=MemberRef(enum=enum, name=name)):
                return BitsetSchema(self.shape(enum).numbers[name])
        raise LoadError(f"{node!r}: has no schema")


CONTEXTS = {protocol: SerializerContext(protocol) for protocol in MODEL.versions}


@cache
def schema_of(cls):
    return CONTEXTS[int(cls.__module__.rpartition(".v")[2])].composite(FAMILIES[cls.__qualname__])


def save(value):
    """The JSON BDS writes for a bound struct."""
    return schema_of(type(value)).do_save(value)


def load(cls, value):
    """The bound struct BDS reads from JSON."""
    return schema_of(cls).do_load(value)
