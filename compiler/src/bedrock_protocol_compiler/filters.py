"""Jinja filter implementations: shape griffe Classes into render-ready dicts."""

import griffe

from .parse import (
    name_kwarg,
    parse_member_value,
    since_kwarg,
)
from .types import PRIMITIVE_TYPES, WIRE_METHODS, resolve_type


def class_fields(cls, class_names: set[str], enum_names: set[str]) -> dict | None:
    """Resolve a struct's constants and instance fields, with version gating.

    Returns `None` if any type is unmappable — the template falls back to an
    empty shell. Otherwise returns a dict with:
      - `constants`: list of (name, ctype, value) for ClassVar attributes.
      - `specializations`: list of (since_min, since_max_excl, visible_fields)
        ranges, each carrying the fields present at that ProtocolVersion. Empty
        if no field is version-gated.
      - `fields`: list of (name, ctype) when there are no gates (single shell).
    """
    constants: list[tuple[str, str, str]] = []
    raw_fields: list[tuple[str, str, int | None]] = []
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
        since = since_kwarg(attr.value, "field") if attr.value is not None else None
        raw_fields.append((name, ctype, since))

    sinces = sorted({s for _, _, s in raw_fields if s is not None})
    if not sinces:
        return {
            "constants": constants,
            "specializations": [],
            "fields": [(n, t) for n, t, _ in raw_fields],
        }

    specializations: list[tuple[int | None, int | None, list[tuple[str, str]]]] = []
    specializations.append(
        (None, sinces[0], [(n, t) for n, t, s in raw_fields if s is None])
    )
    for i, lo in enumerate(sinces):
        hi = sinces[i + 1] if i + 1 < len(sinces) else None
        visible = [(n, t) for n, t, s in raw_fields if s is None or s <= lo]
        specializations.append((lo, hi, visible))
    return {
        "constants": constants,
        "specializations": specializations,
        "fields": [],
    }


def enum_serializers(mod, enum_names: set[str]) -> list[tuple[str, dict]]:
    """Return (enum_name, wire_methods) for enums with a field-level `wire=`.

    Walks struct fields, finds those whose annotation is one of the module's
    enum classes and whose `field(...)` call carries a `wire=` marker, then
    looks up the wire-method table. Last write wins on conflicting wires for
    the same enum.
    """
    out: dict[str, dict] = {}
    for cls in mod.classes.values():
        if cls.is_alias:
            continue
        for _, attr in cls.attributes.items():
            if "instance-attribute" not in attr.labels:
                continue
            if not isinstance(attr.annotation, griffe.ExprName):
                continue
            type_name = attr.annotation.name
            if type_name not in enum_names:
                continue
            wire = name_kwarg(attr.value, "field", "wire")
            if wire is None or wire not in WIRE_METHODS:
                continue
            out[type_name] = WIRE_METHODS[wire]
    return list(out.items())


def module_aliases(
    mod, class_names: set[str], enum_names: set[str]
) -> list[tuple[str, str]]:
    """Return module-level `Name = <type>` aliases as (name, ctype) pairs.

    The `package` string attribute is skipped (it's namespace metadata, not a
    type). Anything else whose RHS resolves to a known type is emitted.
    """
    aliases: list[tuple[str, str]] = []
    for name, attr in mod.attributes.items():
        if name == "package" or attr.value is None:
            continue
        ctype = resolve_type(attr.value, class_names, enum_names)
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
