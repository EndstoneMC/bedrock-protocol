"""Jinja filter implementations: shape griffe Classes into render-ready dicts."""

import click
import griffe

from .parse import (
    name_kwarg,
    parse_member_value,
    since_kwarg,
)
from .types import PRIMITIVE_TYPES, WIRE_METHODS, resolve_type


def _serialize_kind_for_type(
    ann, class_names: set[str], enum_names: set[str]
) -> dict | None:
    """Return `{kind, ...}` info for a direct (non-optional) type annotation."""
    if isinstance(ann, griffe.ExprName):
        name = ann.name
        if name in enum_names:
            return {"kind": "enum", "type_name": name}
        if name in class_names:
            return {"kind": "struct", "type_name": name}
        if name == "str":
            return {"kind": "string"}
    return None


def _field_serialize_kind(
    attr, class_names: set[str], enum_names: set[str]
) -> dict | None:
    """Return `{kind, ...}` info for a field's annotation+value.

    Supported kinds today: `enum`, `struct`, `string`, `optional_variant`
    (`X | None` with `field(type=UnionType)`).
    """
    ann = attr.annotation
    if (
        isinstance(ann, griffe.ExprBinOp)
        and ann.operator == "|"
        and (ann.right == "None" or ann.left == "None")
    ):
        other = ann.left if ann.right == "None" else ann.right
        inner = _serialize_kind_for_type(other, class_names, enum_names)
        if inner is None:
            return None
        marker = name_kwarg(attr.value, "field", "type") if attr.value else None
        if marker != "UnionType":
            return None
        return {"kind": "optional_variant", "inner": inner}
    return _serialize_kind_for_type(ann, class_names, enum_names)


def class_fields(cls, class_names: set[str], enum_names: set[str]) -> dict | None:
    """Resolve a struct's constants and instance fields, with version gating.

    Returns `None` if any type is unmappable — the template falls back to an
    empty shell. Otherwise returns a dict with:
      - `constants`: list of (name, ctype, value) for ClassVar attributes.
      - `specializations`: list of (since_min, since_max_excl, visible_fields)
        ranges, each carrying the fields present at that ProtocolVersion. Empty
        if no field is version-gated.
      - `fields`: list of field dicts when there are no gates (single shell).

    Each field dict carries `name`, `ctype`, plus kind-specific info (see
    `_field_serialize_kind`) so the template can emit both the struct shell
    and the Serializer specialization.
    """
    constants: list[tuple[str, str, str]] = []
    raw_fields: list[dict] = []
    for name, attr in cls.attributes.items():
        if attr.annotation is None:
            return None
        if "instance-attribute" not in attr.labels:
            if not (
                isinstance(attr.annotation, griffe.ExprName)
                and attr.annotation.name in PRIMITIVE_TYPES
            ):
                return None
            constants.append(
                (name, PRIMITIVE_TYPES[attr.annotation.name], str(attr.value))
            )
            continue
        ctype = resolve_type(attr.annotation, class_names, enum_names)
        if ctype is None:
            return None
        kind_info = _field_serialize_kind(attr, class_names, enum_names) or {
            "kind": "unknown"
        }
        since = since_kwarg(attr.value, "field") if attr.value is not None else None
        raw_fields.append(
            {"name": name, "ctype": ctype, "since": since, **kind_info}
        )

    sinces = sorted({f["since"] for f in raw_fields if f["since"] is not None})
    if not sinces:
        return {
            "constants": constants,
            "specializations": [],
            "fields": list(raw_fields),
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
        "fields": [],
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
    """Bucket an enum class's attributes into always-present vs version-gated."""
    always: list[tuple[str, int]] = []
    gates: dict[int, list[tuple[str, int]]] = {}
    for name, attr in cls.attributes.items():
        if attr.value is None:
            continue
        parsed = parse_member_value(attr.value)
        if parsed is None:
            continue
        ivalue, since = parsed
        if since is None:
            always.append((name, ivalue))
        else:
            gates.setdefault(since, []).append((name, ivalue))
    return {"always": always, "gates": sorted(gates.items())}
