"""Field-type C++ spelling + shared file-level context.

`FileContext` is the cross-cutting state every per-construct generator
reads (known names, builtins, the resolver for snapshot lookups, etc.).
Builds once in `FileGenerator.__init__`, passed by reference.

`cpp_type()` walks a `FieldType` tree and returns the C++ spelling for
the field; it's called from the struct field declarations, from
serializer body emission, and from `type` alias rendering.
"""

from __future__ import annotations

from dataclasses import dataclass

from ...descriptor import (
    BitsetType,
    CondType,
    EnumType,
    FieldType,
    MappingType,
    OptionalType,
    Predicate,
    PrimitiveType,
    RepeatedType,
    ResolvedFile,
    StructType,
    TupleType,
    VariantType,
)
from .names import PRIMITIVE_TYPES, camel, snapshot_namespace


@dataclass(frozen=True)
class FileContext:
    """Cross-cutting state shared across the per-construct generators."""

    resolved: ResolvedFile
    known: frozenset[str]
    builtins: frozenset[str]
    string_coded_enums: frozenset[str]


def cpp_type(
    t: FieldType | None,
    ctx: FileContext,
    nested: frozenset[str],
    snapshot: int | None = None,
) -> str | None:
    """C++ spelling for a field-type node, or None if unresolvable.

    When `snapshot` is set, versioned struct / enum references are
    snapshot-qualified (e.g. `v354::FurnaceRecipe`). Inside a namespace
    that already contains the right view (the struct's own body), pass
    `snapshot=None` and let unqualified lookup do the work.
    """
    if t is None:
        return None
    if isinstance(t, PrimitiveType):
        if t.alias is not None:
            return t.alias
        return PRIMITIVE_TYPES.get(t.name)
    if isinstance(t, (StructType, EnumType)):
        name = t.name
        # A dotted ref `Parent.Child` is a nested struct: the spelling is
        # `Parent::Child` and the snapshot rules apply to the outer parent.
        root = name.split(".", 1)[0]
        cpp_spell = name.replace(".", "::")
        if root in nested:
            return cpp_spell
        if root in ctx.builtins:
            return cpp_spell
        if name not in ctx.known:
            return None
        if snapshot is not None and ctx.resolved.is_versioned(root):
            view = ctx.resolved.present_at(root, snapshot)
            if view is not None:
                return f"{snapshot_namespace(view.concrete)}::{cpp_spell}"
        return cpp_spell
    if isinstance(t, OptionalType):
        inner = cpp_type(t.inner, ctx, nested, snapshot)
        return None if inner is None else f"std::optional<{inner}>"
    if isinstance(t, RepeatedType):
        inner = cpp_type(t.inner, ctx, nested, snapshot)
        if inner is None:
            return None
        if t.count is None:
            return f"std::vector<{inner}>"
        return f"std::array<{inner}, {t.count}>"
    if isinstance(t, MappingType):
        key = cpp_type(t.key, ctx, nested, snapshot)
        value = cpp_type(t.value, ctx, nested, snapshot)
        if key is None or value is None:
            return None
        return f"std::map<{key}, {value}>"
    if isinstance(t, TupleType):
        parts: list[str] = []
        for m in t.members:
            spelled = cpp_type(m, ctx, nested, snapshot)
            if spelled is None:
                return None
            parts.append(spelled)
        if len(parts) == 2:
            return f"std::pair<{parts[0]}, {parts[1]}>"
        return f"std::tuple<{', '.join(parts)}>"
    if isinstance(t, VariantType):
        parts: list[str] = []
        for case in t.cases:
            if case is None:
                parts.append("std::monostate")
                continue
            case_type = cpp_type(case, ctx, nested, snapshot)
            if case_type is None:
                return None
            parts.append(case_type)
        return f"std::variant<{', '.join(parts)}>"
    if isinstance(t, BitsetType):
        return f"std::bitset<{t.size}>"
    if isinstance(t, CondType):
        return cpp_type(t.inner, ctx, nested, snapshot)
    return None


def qualified_at(
    name: str,
    ctx: FileContext,
    owner_qualified: str,
    nested_enums: frozenset[str],
    snapshot: int | None,
) -> str:
    """Qualified spelling of `name` from inside a serializer at `snapshot`."""
    if name in nested_enums:
        return f"{owner_qualified}::{name}"
    root = name.split(".", 1)[0]
    cpp_spell = name.replace(".", "::")
    if ctx.resolved.is_versioned(root):
        assert snapshot is not None
        view = ctx.resolved.present_at(root, snapshot)
        assert view is not None
        return f"{snapshot_namespace(view.concrete)}::{cpp_spell}"
    return cpp_spell


def render_predicate(
    pred: Predicate,
    base: str,
    ctx: FileContext,
    owner_qualified: str,
    nested_enums: frozenset[str],
    snapshot: int | None,
    enum_fields: frozenset[str] = frozenset(),
) -> str:
    """Render a `Predicate` AST node into a C++ boolean expression.

    `enum_fields` names the owner struct's scalar enum-typed fields. Inside a
    bitwise operator (`&`, `|`, `^`), an enum operand -- an `Enum.MEMBER` or a
    reference to one of those fields -- is cast to its underlying integer with
    `static_cast<std::underlying_type_t<decltype(x)>>`, since a scoped enum has
    no built-in bitwise operators. Everywhere else the enum value is left as-is.
    """

    def cast_underlying(expr: str) -> str:
        return f"static_cast<std::underlying_type_t<decltype({expr})>>({expr})"

    def go(node: Predicate, in_bitwise: bool) -> str:
        if node.kind == "field":
            ref = f"{base}.{node.text}"
            return cast_underlying(ref) if in_bitwise and node.text in enum_fields else ref
        if node.kind == "int":
            return node.text
        if node.kind == "enum":
            enum, member = node.text.rsplit(".", 1)
            q = qualified_at(enum, ctx, owner_qualified, nested_enums, snapshot)
            ref = f"{q}::{camel(member)}"
            return cast_underlying(ref) if in_bitwise else ref
        if node.kind == "not":
            return f"!({go(node.operands[0], False)})"
        if node.kind == "bittest":
            bit = f"static_cast<std::size_t>({go(node.operands[0], False)})"
            return f"{base}.{node.text}.test({bit})"
        if node.kind in ("&", "|", "^"):
            return "(" + f" {node.kind} ".join(go(o, True) for o in node.operands) + ")"
        op = {"and": "&&", "or": "||"}.get(node.kind, node.kind)
        if node.kind in ("*", "+", "-"):
            return f"({go(node.operands[0], False)} {op} {go(node.operands[1], False)})"
        return f" {op} ".join(f"({go(o, False)})" for o in node.operands)

    return go(pred, False)
