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
) -> str:
    """Render a `Predicate` AST node into a C++ boolean expression."""
    if pred.kind == "field":
        return f"{base}.{pred.text}"
    if pred.kind == "int":
        return pred.text
    if pred.kind == "enum":
        enum, member = pred.text.rsplit(".", 1)
        q = qualified_at(enum, ctx, owner_qualified, nested_enums, snapshot)
        return f"{q}::{camel(member)}"
    if pred.kind == "not":
        return f"!({render_predicate(pred.operands[0], base, ctx, owner_qualified, nested_enums, snapshot)})"
    if pred.kind == "bittest":
        arg = render_predicate(
            pred.operands[0], base, ctx, owner_qualified, nested_enums, snapshot,
        )
        bit = f"static_cast<std::size_t>({arg})"
        return f"{base}.{pred.text}.test({bit})"
    op = {"and": "&&", "or": "||"}.get(pred.kind, pred.kind)
    if pred.kind in ("*", "+", "-"):
        lhs = render_predicate(pred.operands[0], base, ctx, owner_qualified, nested_enums, snapshot)
        rhs = render_predicate(pred.operands[1], base, ctx, owner_qualified, nested_enums, snapshot)
        return f"({lhs} {op} {rhs})"
    return f" {op} ".join(
        f"({render_predicate(o, base, ctx, owner_qualified, nested_enums, snapshot)})"
        for o in pred.operands
    )
