"""Map a single serialize() statement to a DSL field record.

This is the lossy/heuristic core: every write call CloudburstMC makes has to be
translated into a Python DSL field declaration. We handle the common patterns
inline and emit `# CLOUDBURST_IMPORT_TODO` markers for everything else so the
reviewer sees exactly which statement needs hand work.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from javalang.tree import (
    Cast,
    LambdaExpression,
    MemberReference,
    MethodInvocation,
    StatementExpression,
    TernaryExpression,
)


@dataclass
class DraftField:
    """One DSL field line that the emitter will render."""

    name: str  # snake_case; reviewer renames against bedrock-headers
    dsl_type: str  # e.g. "varint32", "str", "BlockPos"
    extras: dict[str, str]  # since=, until=, type=, endian=, when=...
    todo: str | None  # populated when we couldn't fully translate
    cond_chain: list[str]  # the if-wrap context, for grouping


# Direct call -> (dsl_type, extras). The extras dict can override field
# kwargs (e.g. `endian="big"` for big-endian fixed-width).
_DIRECT_WRITES: dict[str, tuple[str, dict[str, str]]] = {
    "VarInts.writeInt": ("varint32", {}),
    "VarInts.writeUnsignedInt": ("uvarint32", {}),
    "VarInts.writeLong": ("varint64", {}),
    "VarInts.writeUnsignedLong": ("uvarint64", {}),
    "buffer.writeByte": ("uint8", {}),
    "buffer.writeBoolean": ("bool", {}),
    "buffer.writeShortLE": ("int16", {}),
    "buffer.writeShort": ("int16", {"endian": '"big"'}),
    "buffer.writeIntLE": ("int32", {}),
    "buffer.writeInt": ("int32", {"endian": '"big"'}),
    "buffer.writeLongLE": ("int64", {}),
    "buffer.writeLong": ("int64", {"endian": '"big"'}),
    "buffer.writeFloatLE": ("float32", {}),
    "buffer.writeDoubleLE": ("double", {}),
    "helper.writeString": ("str", {}),
    "helper.writeUuid": ("uuid.UUID", {}),
    "helper.writeBlockPosition": ("BlockPos", {}),
    "helper.writeNetworkBlockPosition": ("NetworkBlockPos", {}),
    "helper.writeVector3f": ("Vec3", {}),
    "helper.writeVector3i": ("Vec3", {}),
    "helper.writeVector2f": ("Vec2", {}),
    "helper.writeVector2i": ("Vec2", {}),
    "helper.writeByteAngle": ("uint8", {}),
    "helper.writeByteRotation": ("uint8", {}),
    "helper.writeTag": ("CompoundTag", {}),
    "helper.writeItem": ("ItemStack", {}),
    "helper.writeNetworkItemStackDescriptor": ("ItemStack", {}),
    "helper.writeCommandOrigin": ("CommandOriginData", {}),
    "buffer.writeBytes": ("bytes", {"prefix": "None"}),
    "helper.writeByteArray": ("bytes", {}),
}


def translate_op(versioned_op, java_field_types: dict[str, str] | None = None) -> DraftField:
    """Turn one VersionedFieldOp into a DraftField record.

    `java_field_types` maps snake_case field names to the Java type declared on
    the packet class. When provided and the Java type is an enum/struct (not a
    primitive), the DraftField's Python type uses the Java name and the wire
    type drops into `field(type=...)`. This mirrors the hand-written DSL form
    (e.g. `reason: DisconnectFailReason = field(type=varint32, since=622)`).
    """
    from .version_chain import VersionedFieldOp

    assert isinstance(versioned_op, VersionedFieldOp)
    raw = versioned_op.raw
    cond_chain = _split_cond_chain(versioned_op.signature)

    expr = None
    if isinstance(raw, StatementExpression) and isinstance(raw.expression, MethodInvocation):
        expr = raw.expression

    if expr is None:
        return DraftField(
            name="_unknown",
            dsl_type="bytes",
            extras={},
            todo=f"CLOUDBURST_IMPORT_TODO: non-call statement: {type(raw).__name__}",
            cond_chain=cond_chain,
        )

    write_key = f"{expr.qualifier or ''}.{expr.member}"
    field_name = _infer_field_name(expr) or write_key.split(".")[-1]

    extras: dict[str, str] = {}
    if versioned_op.since is not None:
        extras["since"] = str(versioned_op.since)
    if versioned_op.until is not None:
        extras["until"] = str(versioned_op.until)

    java_type = (java_field_types or {}).get(field_name)
    python_type = _java_type_to_python(java_type)

    if write_key in _DIRECT_WRITES:
        wire_type, type_extras = _DIRECT_WRITES[write_key]
        extras.update(type_extras)
        dsl_type = _resolve_dsl_type(python_type, wire_type, extras)
        return DraftField(
            name=field_name,
            dsl_type=dsl_type,
            extras=extras,
            todo=None,
            cond_chain=cond_chain,
        )

    if write_key == "helper.writeArray":
        inner = _infer_array_inner_type(expr)
        return DraftField(
            name=field_name,
            dsl_type=python_type or (f"list[{inner}]" if inner else "list"),
            extras=extras,
            todo=None if inner or python_type else "CLOUDBURST_IMPORT_TODO: list element type unclear",
            cond_chain=cond_chain,
        )

    if write_key in {"helper.writeOptional", "helper.writeOptionalNull"}:
        inner = _infer_array_inner_type(expr) or python_type
        return DraftField(
            name=field_name,
            dsl_type=f"{inner or 'bytes'} | None",
            extras=extras,
            todo=None if inner else "CLOUDBURST_IMPORT_TODO: optional inner type unclear",
            cond_chain=cond_chain,
        )

    return DraftField(
        name=field_name,
        dsl_type="bytes",
        extras=extras,
        todo=f"CLOUDBURST_IMPORT_TODO: unknown write `{write_key}` - translate by hand",
        cond_chain=cond_chain,
    )


# ----- Java type -> Python type -----

# Java types that translate 1:1 to a DSL type the project already exposes.
# When the packet class declares one of these, drop the wire-type wrap
# (`field(type=...)`) because the Python type already pins the on-wire shape.
_JAVA_TO_PYTHON: dict[str, str] = {
    "String": "str",
    "CharSequence": "str",
    "UUID": "uuid.UUID",
    "Vector3f": "Vec3",
    "Vector3i": "Vec3",
    "Vector2f": "Vec2",
    "Vector2i": "Vec2",
    "BlockPosition": "BlockPos",
    "NetworkBlockPosition": "NetworkBlockPos",
    "NbtMap": "CompoundTag",
    "NbtTag": "CompoundTag",
    "ItemData": "ItemStack",
}

# Java primitives — we let the wire-type stand as the Python type for these.
_JAVA_PRIMITIVES: set[str] = {
    "boolean",
    "byte",
    "short",
    "int",
    "long",
    "float",
    "double",
    "char",
}

# DSL struct types where the wire type IS the type itself (no `type=` wrap).
_SELF_DESCRIBING_STRUCTS: set[str] = {
    "BlockPos",
    "NetworkBlockPos",
    "Vec3",
    "Vec3",
    "Vec2",
    "Vec2",
    "ItemStack",
    "CompoundTag",
    "CommandOriginData",
}


def _java_type_to_python(java_type: str | None) -> str | None:
    """Resolve a Java field type to a Python DSL type, or None if uninformative.

    Returns None for Java primitives (let the wire type stand) and for
    parameterized container types like `List<X>` (handled by the array path).
    """
    if not java_type:
        return None
    if java_type in _JAVA_PRIMITIVES:
        return None
    if java_type in _JAVA_TO_PYTHON:
        return _JAVA_TO_PYTHON[java_type]
    if "<" in java_type:
        # Any generic container in the Java field (List<X>, NbtList<NbtMap>,
        # ...) leaves the wire type to drive the Python type. The element type
        # is recovered by the array/optional path when applicable.
        return None
    if java_type[:1].isupper():
        return java_type
    return None


def _resolve_dsl_type(python_type: str | None, wire_type: str, extras: dict[str, str]) -> str:
    """Decide whether to wrap the wire type into field(type=...) or not.

    - python_type=None -> the wire type stands as the Python type.
    - python_type matches a DSL struct that already pins its wire shape ->
      keep python_type, drop the wrap.
    - python_type maps directly to the wire type (e.g. str -> "str" wire) ->
      keep python_type, drop the wrap.
    - Otherwise (typical enum case) -> python_type + field(type=wire_type, ...).
    """
    if python_type is None:
        return wire_type
    if python_type == wire_type:
        return python_type
    if python_type in _SELF_DESCRIBING_STRUCTS:
        return python_type
    if python_type == "str" and wire_type == "str":
        return python_type
    extras["type"] = wire_type
    return python_type


# ----- helpers -----

_CAMEL_RE = re.compile(r"(?<!^)(?=[A-Z])")


def to_snake(name: str) -> str:
    return _CAMEL_RE.sub("_", name).lower()


_to_snake = to_snake  # back-compat re-export for callers


def _strip_accessor(getter: str) -> str:
    if getter.startswith("get") and len(getter) > 3 and getter[3].isupper():
        return getter[3:]
    if getter.startswith("is") and len(getter) > 2 and getter[2].isupper():
        return getter[2:]
    return getter


def _infer_field_name(expr: MethodInvocation) -> str | None:
    """Find the first packet.getXxx target inside the call's argument list."""
    for arg in expr.arguments or []:
        getter = _walk_for_getter(arg)
        if getter:
            return _to_snake(_strip_accessor(getter))
    return None


def _walk_for_getter(arg) -> str | None:
    if isinstance(arg, MethodInvocation):
        if (arg.qualifier or "").startswith("packet"):
            return arg.member
        for inner in arg.arguments or []:
            g = _walk_for_getter(inner)
            if g:
                return g
    elif isinstance(arg, Cast):
        return _walk_for_getter(arg.expression)
    elif isinstance(arg, TernaryExpression):
        # `packet.isXxx() ? 1 : 0` -> recurse into the condition.
        for sub in (arg.condition, arg.if_true, arg.if_false):
            g = _walk_for_getter(sub)
            if g:
                return g
    elif isinstance(arg, MemberReference) and (arg.qualifier or "").startswith("packet"):
        return arg.member
    return None


# Map helper.writeXxx -> DSL element type, for the array/optional inner.
_HELPER_TO_ELEMENT_TYPE: dict[str, str] = {
    "writeString": "str",
    "writeUuid": "uuid.UUID",
    "writeVarInt": "varint32",
    "writeVarLong": "varint64",
    "writeBlockPosition": "BlockPos",
    "writeNetworkBlockPosition": "NetworkBlockPos",
    "writeVector3f": "Vec3",
    "writeVector3i": "Vec3",
    "writeVector2f": "Vec2",
    "writeItem": "ItemStack",
    "writeNetworkItemStackDescriptor": "ItemStack",
    "writeTag": "CompoundTag",
    "writeByteArray": "bytes",
}


def _infer_array_inner_type(call: MethodInvocation) -> str | None:
    """For `helper.writeArray(buf, list, (b, v) -> helper.writeXxx(b, v))`,
    pull out the inner write call name and map it to a DSL element type.

    Falls back to None when the lambda body isn't a single method call we know.
    """
    for arg in call.arguments or []:
        if not isinstance(arg, LambdaExpression):
            continue
        body = arg.body
        # body can be an expression (single-statement lambda) or a list of stmts
        if isinstance(body, list):
            stmts = body
        else:
            stmts = [body]
        for stmt in stmts:
            target = stmt.expression if isinstance(stmt, StatementExpression) else stmt
            if isinstance(target, MethodInvocation):
                inner = _HELPER_TO_ELEMENT_TYPE.get(target.member)
                if inner:
                    return inner
                return None
    return None


def _split_cond_chain(signature: str) -> list[str]:
    """Pull the if/for conditions out of a leaf signature (`cond|cond|leaf`)."""
    parts = signature.split("|")
    return parts[:-1] if len(parts) > 1 else []
