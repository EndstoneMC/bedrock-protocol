"""Jinja filter implementations: shape griffe Classes into render-ready dicts."""

import click
import griffe

from .parse import (
    class_packet_id,
    name_kwarg,
    parse_member_value,
    since_kwarg,
)
from .types import PRIMITIVE_TYPES, WIRE_METHODS, resolve_type


def _has_named_ref(ann, names: set[str]) -> bool:
    """True if `ann` (a griffe annotation expression) references any name in `names`."""
    if ann is None:
        return False
    if isinstance(ann, griffe.ExprName):
        return ann.name in names
    if isinstance(ann, griffe.ExprBinOp):
        return _has_named_ref(ann.left, names) or _has_named_ref(ann.right, names)
    if isinstance(ann, griffe.ExprSubscript):
        s = ann.slice
        if isinstance(s, griffe.ExprTuple):
            return any(_has_named_ref(el, names) for el in s.elements)
        return _has_named_ref(s, names)
    return False


def _class_has_field_since(cls) -> bool:
    for _, attr in cls.attributes.items():
        if attr.value is not None and since_kwarg(attr.value, "field") is not None:
            return True
    return False


def compute_templated_classes(classes, enum_names: set[str]) -> set[str]:
    """Return the names of non-enum classes that should be emitted as
    `template <int ProtocolVersion> struct Foo_;` rather than plain structs.

    A class is templated iff (a) any of its fields carries `field(since=N)` or
    (b) any of its field annotations transitively reaches a templated entity
    (every enum, plus other templated structs). Fixed-point iteration over
    the dependency graph until stable.
    """
    templated: set[str] = set()
    for c in classes:
        from .parse import is_int_enum
        if is_int_enum(c):
            continue
        if _class_has_field_since(c):
            templated.add(c.name)

    while True:
        seed = enum_names | templated
        changed = False
        for c in classes:
            from .parse import is_int_enum
            if is_int_enum(c) or c.name in templated:
                continue
            for _, attr in c.attributes.items():
                if _has_named_ref(attr.annotation, seed):
                    templated.add(c.name)
                    changed = True
                    break
        if not changed:
            break

    return templated


def type_alias_wires(mod) -> dict[str, dict]:
    """Map module-level alias name to its wire methods, when the alias target
    is a primitive with a known wire encoding.

    Covers both `X = primitive` (plain assignment) and PEP 695
    `type X = primitive` (which griffe surfaces in `mod.type_aliases`).
    Aliases whose target is not a primitive in WIRE_METHODS are skipped.
    """
    out: dict[str, dict] = {}
    for name, attr in mod.attributes.items():
        if name == "package" or attr.value is None:
            continue
        if isinstance(attr.value, griffe.ExprName) and attr.value.name in WIRE_METHODS:
            out[name] = WIRE_METHODS[attr.value.name]
    for name, ta in mod.type_aliases.items():
        if ta.value is None:
            continue
        if isinstance(ta.value, griffe.ExprName) and ta.value.name in WIRE_METHODS:
            out[name] = WIRE_METHODS[ta.value.name]
    return out


def _serialize_kind_for_type(
    ann,
    class_names: set[str],
    enum_names: set[str],
    templated_classes: set[str],
    alias_wires: dict[str, dict],
) -> dict | None:
    """Return `{kind, ...}` info for a direct (non-optional) type annotation."""
    if isinstance(ann, griffe.ExprName):
        name = ann.name
        if name in enum_names:
            return {"kind": "enum", "type_name": name}
        if name in class_names:
            return {
                "kind": "struct",
                "type_name": name,
                "templated": name in templated_classes,
            }
        if name == "str":
            return {"kind": "string"}
        if name in alias_wires:
            w = alias_wires[name]
            return {
                "kind": "primitive",
                "type_name": name,
                "wire_write": w["write"],
                "wire_read": w["read"],
                "underlying": w["underlying"],
            }
        if name in WIRE_METHODS:
            w = WIRE_METHODS[name]
            return {
                "kind": "primitive",
                "type_name": None,
                "wire_write": w["write"],
                "wire_read": w["read"],
                "underlying": w["underlying"],
            }
    return None


def _field_serialize_kind(
    attr,
    class_names: set[str],
    enum_names: set[str],
    templated_classes: set[str],
    alias_wires: dict[str, dict],
) -> dict | None:
    """Return `{kind, ...}` info for a field's annotation+value.

    Supported kinds: `enum`, `struct`, `string`, `primitive`, `optional`
    (`X | None`, bool-flag wire with 1=present), and `optional_variant`
    (`X | None` with `field(type=Union)`, varint-discriminator wire with
    0=present and 1=absent for compat with gophertunnel's HideX pattern).
    """
    ann = attr.annotation
    if (
        isinstance(ann, griffe.ExprBinOp)
        and ann.operator == "|"
        and (ann.right == "None" or ann.left == "None")
    ):
        other = ann.left if ann.right == "None" else ann.right
        inner = _serialize_kind_for_type(
            other, class_names, enum_names, templated_classes, alias_wires
        )
        if inner is None:
            return None
        marker = name_kwarg(attr.value, "field", "type") if attr.value else None
        if marker == "Union":
            return {"kind": "optional_variant", "inner": inner}
        return {"kind": "optional", "inner": inner}
    return _serialize_kind_for_type(
        ann, class_names, enum_names, templated_classes, alias_wires
    )


def class_fields(
    cls,
    class_names: set[str],
    enum_names: set[str],
    templated_classes: set[str] = frozenset(),
    alias_wires: dict[str, dict] | None = None,
) -> dict | None:
    """Resolve a struct's constants and instance fields, with version gating.

    Returns `None` if any type is unmappable. Otherwise:
      - `constants`: list of (name, ctype, value); currently just the packet
        `id` when the class is decorated with `@packet(id=N)`.
      - `specializations`: list of (since_min, since_max_excl, visible_fields)
        ranges. Always has at least one entry — a class with no version-gated
        fields collapses to a single `(None, None, all_fields)` specialization,
        which the template emits as an unconstrained class-template body.
    """
    if alias_wires is None:
        alias_wires = {}
    type_aliases = set(alias_wires)
    constants: list[tuple[str, str, str]] = []
    pid = class_packet_id(cls)
    if pid is not None:
        constants.append(("id", "int", str(pid)))
    raw_fields: list[dict] = []
    for name, attr in cls.attributes.items():
        if attr.annotation is None:
            return None
        ctype = resolve_type(
            attr.annotation, class_names, enum_names, templated_classes, type_aliases
        )
        if ctype is None:
            return None
        kind_info = _field_serialize_kind(
            attr, class_names, enum_names, templated_classes, alias_wires
        ) or {"kind": "unknown"}
        since = since_kwarg(attr.value, "field") if attr.value is not None else None
        raw_fields.append(
            {"name": name, "ctype": ctype, "since": since, **kind_info}
        )

    is_templated = cls.name in templated_classes
    sinces = sorted({f["since"] for f in raw_fields if f["since"] is not None})
    if not sinces:
        return {
            "constants": constants,
            "specializations": [(None, None, list(raw_fields))],
            "templated": is_templated,
        }

    specializations: list[tuple[int | None, int | None, list[dict]]] = []
    specializations.append(
        (None, sinces[0], [f for f in raw_fields if f["since"] is None])
    )
    for i, lo in enumerate(sinces):
        hi = sinces[i + 1] if i + 1 < len(sinces) else None
        visible = [f for f in raw_fields if f["since"] is None or f["since"] <= lo]
        specializations.append((lo, hi, visible))
    return {
        "constants": constants,
        "specializations": specializations,
        "templated": is_templated,
    }


def enum_serializers(mod, enum_names: set[str]) -> list[tuple[str, dict]]:
    """Return (enum_name, wire_methods) for enums with a field-level `type=`.

    Walks struct fields, finds those whose annotation is one of the module's
    enum classes, and pulls the `type=` primitive name out of `field(...)`.
    Enum-typed fields are required to specify `type=` — missing or unknown
    primitives raise a ClickException so the bpc command exits cleanly.
    Last write wins on conflicting types for the same enum.
    """
    out: dict[str, dict] = {}
    for cls in mod.classes.values():
        if cls.is_alias:
            continue
        for fname, attr in cls.attributes.items():
            if "instance-attribute" not in attr.labels:
                continue
            if not isinstance(attr.annotation, griffe.ExprName):
                continue
            type_name = attr.annotation.name
            if type_name not in enum_names:
                continue
            wire = name_kwarg(attr.value, "field", "type")
            if wire is None:
                raise click.ClickException(
                    f"{cls.name}.{fname}: enum-typed field requires "
                    f"field(type=<primitive>) — e.g. type=uvarint32"
                )
            if wire not in WIRE_METHODS:
                raise click.ClickException(
                    f"{cls.name}.{fname}: unknown wire primitive {wire!r}; "
                    f"valid: {sorted(WIRE_METHODS)}"
                )
            out[type_name] = WIRE_METHODS[wire]
    return list(out.items())


def module_aliases(
    mod, class_names: set[str], enum_names: set[str]
) -> list[tuple[str, str]]:
    """Return module-level type aliases as (name, ctype) pairs.

    Picks up both plain `Name = <type>` assignments (skipping `package`,
    which is namespace metadata) and PEP 695 `type Name = <type>` statements,
    which griffe surfaces in `mod.type_aliases`.
    """
    aliases: list[tuple[str, str]] = []
    for name, attr in mod.attributes.items():
        if name == "package" or attr.value is None:
            continue
        ctype = resolve_type(attr.value, class_names, enum_names)
        if ctype is not None:
            aliases.append((name, ctype))
    for name, ta in mod.type_aliases.items():
        if ta.value is None:
            continue
        ctype = resolve_type(ta.value, class_names, enum_names)
        if ctype is not None:
            aliases.append((name, ctype))
    return aliases


def enum_members(cls) -> dict:
    """Return the enum's entries as `{"entries": [(name, value, since, until)]}`.

    `since` is the protocol version at which the entry was introduced (or
    `None` if it has always been there). `until` is the protocol version at
    which the entry was removed (or `None` if it is still present). The
    entry is visible for any V in `[since, until)`.
    """
    entries: list[tuple[str, int, int | None, int | None]] = []
    for name, attr in cls.attributes.items():
        if attr.value is None:
            continue
        parsed = parse_member_value(attr.value)
        if parsed is None:
            continue
        ivalue, since, until = parsed
        entries.append((name, ivalue, since, until))
    return {"entries": entries}


def enum_ranges(cls) -> list[tuple[int | None, int | None, list[tuple[str, int]]]]:
    """Return `[(lo, hi, visible_entries), ...]` ranges where the visible set
    is constant. `lo` is inclusive (or `None` for "no lower bound"); `hi` is
    exclusive (or `None` for "no upper bound").

    Change-points are the union of `@enum(since=N)`, every member's `since`,
    and every member's `until`. A single range with `(None, None)` is
    returned when the enum is wholly unversioned.
    """
    from .parse import class_since

    entries = enum_members(cls)["entries"]
    cs = class_since(cls)

    points: set[int] = set()
    if cs is not None:
        points.add(cs)
    for _, _, since, until in entries:
        if since is not None:
            points.add(since)
        if until is not None:
            points.add(until)

    if not points:
        return [(None, None, [(n, v) for n, v, _, _ in entries])]

    sorted_points = sorted(points)
    ranges: list[tuple[int | None, int | None, list[tuple[str, int]]]] = []

    # Pre-first-point range exists only when there is no class-level since
    # (the enum is valid at versions below the first member-level change).
    if cs is None:
        first = sorted_points[0]
        visible = [
            (n, v) for n, v, s, u in entries
            if s is None and (u is None or first <= u)
        ]
        if visible:
            # Representative V = first - 1; any V in [0, first).
            rep = first - 1
            visible = [
                (n, v) for n, v, s, u in entries
                if (s is None or s <= rep) and (u is None or rep < u)
            ]
            ranges.append((None, first, visible))

    for i, lo in enumerate(sorted_points):
        hi = sorted_points[i + 1] if i + 1 < len(sorted_points) else None
        visible = [
            (n, v) for n, v, s, u in entries
            if (s is None or s <= lo) and (u is None or lo < u)
        ]
        ranges.append((lo, hi, visible))

    return ranges
