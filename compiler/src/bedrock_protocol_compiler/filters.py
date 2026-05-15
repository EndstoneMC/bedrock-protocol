"""Jinja filter implementations: shape griffe Classes into render-ready dicts."""

import click
import griffe

from .parse import (
    class_packet_id,
    name_kwarg,
    parse_member_value,
    since_kwarg,
    str_kwarg,
)
from .types import PRIMITIVE_TYPES, VARINT_PRIMITIVES, resolve_type


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
    """Map module-level alias name to its wire info, when the alias target is
    a primitive with a known wire encoding.

    Covers both `X = primitive` and PEP 695 `type X = primitive`. The returned
    info is `{"underlying": <c++ type>, "varint": <bool>}` — enough for the
    codegen to emit `stream.write<U, true>(...)` or `stream.write<U>(...)`.
    """
    out: dict[str, dict] = {}

    def _info(prim_name: str) -> dict:
        return {
            "underlying": PRIMITIVE_TYPES[prim_name],
            "varint": prim_name in VARINT_PRIMITIVES,
        }

    for name, attr in mod.attributes.items():
        if name == "package" or attr.value is None or name in PRIMITIVE_TYPES:
            continue
        if (
            isinstance(attr.value, griffe.ExprName)
            and attr.value.name in PRIMITIVE_TYPES
        ):
            out[name] = _info(attr.value.name)
    for name, ta in mod.type_aliases.items():
        if ta.value is None or name in PRIMITIVE_TYPES:
            continue
        if isinstance(ta.value, griffe.ExprName) and ta.value.name in PRIMITIVE_TYPES:
            out[name] = _info(ta.value.name)
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
            return {"kind": "enum", "type_name": name, "templated": True}
        if name in class_names:
            return {
                "kind": "struct",
                "type_name": name,
                "templated": name in templated_classes,
            }
        if name == "str":
            return {"kind": "string"}
        # Built-in primitives win over alias_wires: the codegen knows their
        # wire encoding directly via PRIMITIVE_TYPES + VARINT_PRIMITIVES,
        # without consulting whatever `type varint32 = int` happens to alias
        # to in common.py. `big_endian` defaults to False here -- it is a
        # per-field choice (`field(endian="big")`) applied by the caller,
        # not a property of the type.
        if name in PRIMITIVE_TYPES:
            return {
                "kind": "primitive",
                "type_name": None,
                "underlying": PRIMITIVE_TYPES[name],
                "varint": name in VARINT_PRIMITIVES,
                "big_endian": False,
            }
        if name in alias_wires:
            w = alias_wires[name]
            return {
                "kind": "primitive",
                "type_name": name,
                "underlying": w["underlying"],
                "varint": w["varint"],
                "big_endian": False,
            }
    return None


def _enum_wire(type_kw: str | None, field_name: str) -> dict:
    """Resolve an enum field's `field(type=...)` to a wire spec.

    `type=str` yields `{"string": True}`, a name-coded enum (the codegen
    reads/writes the enumerator name). Any other primitive yields
    `{"string": False, "underlying": <c++ type>, "varint": <bool>,
    "big_endian": <bool>}`, an integer-coded enum. `big_endian` defaults
    False and is flipped by a `field(endian="big")` on the field. A missing
    or non-primitive `type=` is a hard error.

    The wire encoding belongs to the field, not the enum, so the same enum
    can be string-coded in one field and integer-coded in another.
    """
    if type_kw is None:
        raise click.ClickException(
            f"{field_name}: enum-typed field requires field(type=<primitive>) "
            f"-- e.g. type=uvarint32 or type=str"
        )
    if type_kw == "str":
        return {"string": True}
    if type_kw not in PRIMITIVE_TYPES:
        raise click.ClickException(
            f"{field_name}: unknown wire primitive {type_kw!r}; "
            f"valid: {sorted(PRIMITIVE_TYPES)}"
        )
    return {
        "string": False,
        "underlying": PRIMITIVE_TYPES[type_kw],
        "varint": type_kw in VARINT_PRIMITIVES,
        "big_endian": False,
    }


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

    An `enum` kind (direct, or as an `optional` inner) carries a `wire` spec
    resolved from `field(type=...)` -- see `_enum_wire`.

    A `field(endian="big")` marker flips the `big_endian` flag on a
    fixed-width primitive field, or on a fixed-width integer-coded enum
    field's `wire` spec, so the codegen emits
    `stream.write<T, std::endian::big>(...)`.
    """
    ann = attr.annotation
    endian = (
        str_kwarg(attr.value, "field", "endian") if attr.value is not None else None
    )
    if endian is not None and endian not in ("big", "little"):
        raise click.ClickException(
            f'{attr.name}: field(endian=...) must be "big" or "little", got {endian!r}'
        )
    type_kw = name_kwarg(attr.value, "field", "type") if attr.value is not None else None

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
        if type_kw == "Union":
            info = {"kind": "optional_variant", "inner": inner}
        else:
            info = {"kind": "optional", "inner": inner}
    else:
        info = _serialize_kind_for_type(
            ann, class_names, enum_names, templated_classes, alias_wires
        )
        if info is None:
            return None

    if info["kind"] == "enum":
        info["wire"] = _enum_wire(type_kw, attr.name)
    elif (
        info["kind"] in ("optional", "optional_variant")
        and info["inner"]["kind"] == "enum"
    ):
        if info["kind"] == "optional_variant":
            raise click.ClickException(
                f"{attr.name}: an optional enum field needs field(type=) for the "
                f"enum wire primitive and so cannot also use type=Union"
            )
        info["inner"]["wire"] = _enum_wire(type_kw, attr.name)

    if endian is not None:
        if info["kind"] == "primitive":
            info = {**info, "big_endian": endian == "big"}
        elif (
            info["kind"] == "enum"
            and not info["wire"]["string"]
            and not info["wire"]["varint"]
        ):
            info["wire"] = {**info["wire"], "big_endian": endian == "big"}
        else:
            raise click.ClickException(
                f"{attr.name}: field(endian=...) only applies to fixed-width "
                f"primitive or fixed-width integer-coded enum fields"
            )
    return info


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
        `Id` when the class is decorated with `@packet(id=N)`.
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
        constants.append(("Id", "int", str(pid)))
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
        raw_fields.append({"name": name, "ctype": ctype, "since": since, **kind_info})

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
    """Return (enum_name, codec) for every enum a struct field encodes as a
    string via `field(type=str)`.

    These enums need a `Serializer<Enum_<V>>` specialization that reads and
    writes the enumerator name lowercased with underscores stripped
    (`THROW_ITEM` -> `throwitem`). `codec` is `{"members": [(name, wire), ...]}`.

    Integer-coded enum uses get no `Serializer` -- the codegen inlines a cast
    around `stream.read`/`write` at the field site (see `_enum_wire`), so the
    same enum may be string-coded in one field and integer-coded in another.
    """
    enum_classes = {c.name: c for c in mod.classes.values() if not c.is_alias}
    out: dict[str, dict] = {}
    for cls in mod.classes.values():
        if cls.is_alias:
            continue
        for attr in cls.attributes.values():
            if "instance-attribute" not in attr.labels or attr.value is None:
                continue
            ann = attr.annotation
            if (
                isinstance(ann, griffe.ExprBinOp)
                and ann.operator == "|"
                and (ann.right == "None" or ann.left == "None")
            ):
                ann = ann.left if ann.right == "None" else ann.right
            if not isinstance(ann, griffe.ExprName) or ann.name not in enum_names:
                continue
            if name_kwarg(attr.value, "field", "type") != "str":
                continue
            entries = enum_members(enum_classes[ann.name])["entries"]
            out[ann.name] = {
                "members": [
                    (n, n.lower().replace("_", "")) for n, _, _, _ in entries
                ]
            }
    return list(out.items())


def module_aliases(
    mod, class_names: set[str], enum_names: set[str]
) -> list[tuple[str, str]]:
    """Return module-level type aliases as (name, ctype) pairs, suitable for
    emission as `enum Name : ctype {};` strong typedefs in the header.

    Picks up both plain `Name = <type>` assignments (skipping `package`, which
    is namespace metadata) and PEP 695 `type Name = <type>` statements (griffe
    surfaces these in `mod.type_aliases`). Aliases whose NAME is itself a
    built-in primitive (`varint32`, `uint8`, `double`, ...) are skipped, since
    those names are wired into the codegen's `PRIMITIVE_TYPES` table directly
    and there is no need to emit a C++ alias for them.
    """
    aliases: list[tuple[str, str]] = []
    for name, attr in mod.attributes.items():
        if name == "package" or attr.value is None or name in PRIMITIVE_TYPES:
            continue
        ctype = resolve_type(attr.value, class_names, enum_names)
        if ctype is not None:
            aliases.append((name, ctype))
    for name, ta in mod.type_aliases.items():
        if ta.value is None or name in PRIMITIVE_TYPES:
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
            (n, v) for n, v, s, u in entries if s is None and (u is None or first <= u)
        ]
        if visible:
            # Representative V = first - 1; any V in [0, first).
            rep = first - 1
            visible = [
                (n, v)
                for n, v, s, u in entries
                if (s is None or s <= rep) and (u is None or rep < u)
            ]
            ranges.append((None, first, visible))

    for i, lo in enumerate(sorted_points):
        hi = sorted_points[i + 1] if i + 1 < len(sorted_points) else None
        visible = [
            (n, v)
            for n, v, s, u in entries
            if (s is None or s <= lo) and (u is None or lo < u)
        ]
        ranges.append((lo, hi, visible))

    return ranges
