"""Shape griffe Classes into render-ready data: name references, wire kinds,
module-level aliases. Version-snapshot planning lives in `versioning.py`."""

import click
import griffe

from .parse import (
    class_since,
    is_int_enum,
    name_kwarg,
    parse_member_value,
    str_kwarg,
)
from .types import PRIMITIVE_TYPES, VARINT_PRIMITIVES, resolve_type


def has_named_ref(ann, names: set[str]) -> bool:
    """True if `ann` (a griffe annotation expression) references any name in `names`."""
    if ann is None:
        return False
    if isinstance(ann, griffe.ExprName):
        return ann.name in names
    if isinstance(ann, griffe.ExprBinOp):
        return has_named_ref(ann.left, names) or has_named_ref(ann.right, names)
    if isinstance(ann, griffe.ExprSubscript):
        s = ann.slice
        if isinstance(s, griffe.ExprTuple):
            return any(has_named_ref(el, names) for el in s.elements)
        return has_named_ref(s, names)
    return False


def referenced_names(ann) -> set[str]:
    """Every identifier `ann` (a griffe annotation expression) mentions."""
    if ann is None:
        return set()
    if isinstance(ann, griffe.ExprName):
        return {ann.name}
    if isinstance(ann, griffe.ExprBinOp):
        return referenced_names(ann.left) | referenced_names(ann.right)
    if isinstance(ann, griffe.ExprSubscript):
        out = referenced_names(ann.left)
        s = ann.slice
        if isinstance(s, griffe.ExprTuple):
            for el in s.elements:
                out |= referenced_names(el)
        else:
            out |= referenced_names(s)
        return out
    return set()


def class_has_field_since(cls) -> bool:
    """True if any of the class's fields carries `field(since=N)`."""
    from .parse import since_kwarg

    for _, attr in cls.attributes.items():
        if attr.value is not None and since_kwarg(attr.value, "field") is not None:
            return True
    return False


def nested_enums(cls) -> dict[str, griffe.Class]:
    """IntEnum classes declared inside `cls`, keyed by name.

    A nested enum models a per-packet enum (EndstoneMC's `Packet::Enum`). It
    emits as an `enum class` member of the packet struct, not as a module-scope
    type -- so it has no version parameter of its own and its visibility is the
    owning packet's.
    """
    return {
        c.name: c
        for c in cls.classes.values()
        if not c.is_alias and is_int_enum(c)
    }


def type_alias_wires(mod) -> dict[str, dict]:
    """Map module-level alias name to its wire info, when the alias target is
    a primitive with a known wire encoding.

    Covers both `X = primitive` and PEP 695 `type X = primitive`. The returned
    info is `{"underlying": <c++ type>, "varint": <bool>}` — enough for the
    codegen to emit `stream.writeVarInt<U>(...)` or `stream.write<U>(...)`.
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
    alias_wires: dict[str, dict],
    nested_enum_names: set[str] = frozenset(),
) -> dict | None:
    """Return `{kind, ...}` info for a direct (non-optional) type annotation."""
    if isinstance(ann, griffe.ExprName):
        name = ann.name
        if name in nested_enum_names:
            return {"kind": "enum", "type_name": name, "nested": True}
        if name in enum_names:
            return {"kind": "enum", "type_name": name, "nested": False}
        if name in class_names:
            return {"kind": "struct", "type_name": name}
        if name == "str":
            return {"kind": "string"}
        # Built-in primitives win over alias_wires: the codegen knows their
        # wire encoding directly via PRIMITIVE_TYPES + VARINT_PRIMITIVES,
        # without consulting whatever `type varint32 = int` happens to alias
        # to in common.py. `big_endian` defaults to False here -- it is a
        # per-field choice (`field(endian="big")`) applied by the caller.
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


def _reject_string_coded_nested(enum_info: dict, field_name: str) -> None:
    """A string-coded enum is encoded via a `Serializer<Enum>` specialization.
    A nested enum is a member of its owning packet and cannot be a
    specialization pattern on its own, so it must use an integer wire."""
    if enum_info.get("nested") and enum_info["wire"]["string"]:
        raise click.ClickException(
            f"{field_name}: a nested enum cannot be string-coded "
            f"(field(type=str)) -- use an integer wire primitive, or lift "
            f"the enum to module scope"
        )


def field_serialize_kind(
    attr,
    class_names: set[str],
    enum_names: set[str],
    alias_wires: dict[str, dict],
    nested_enum_names: set[str] = frozenset(),
) -> dict | None:
    """Return `{kind, ...}` info for a field's annotation+value.

    Supported kinds: `enum`, `struct`, `string`, `primitive`, `optional`
    (`X | None`, bool-flag wire with 1=present), and `optional_variant`
    (`X | None` with `field(type=Union)`, varint-discriminator wire with
    0=present and 1=absent for compat with gophertunnel's HideX pattern).

    An `enum` kind (direct, or as an `optional` inner) carries a `wire` spec
    resolved from `field(type=...)` -- see `_enum_wire`. A `field(endian=...)`
    marker flips the `big_endian` flag on a fixed-width primitive field, or on
    a fixed-width integer-coded enum field's `wire` spec.
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
            other, class_names, enum_names, alias_wires, nested_enum_names
        )
        if inner is None:
            return None
        if type_kw == "Union":
            info = {"kind": "optional_variant", "inner": inner}
        else:
            info = {"kind": "optional", "inner": inner}
    else:
        info = _serialize_kind_for_type(
            ann, class_names, enum_names, alias_wires, nested_enum_names
        )
        if info is None:
            return None

    if info["kind"] == "enum":
        info["wire"] = _enum_wire(type_kw, attr.name)
        _reject_string_coded_nested(info, attr.name)
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
        _reject_string_coded_nested(info["inner"], attr.name)

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


def module_aliases(
    mod, class_names: set[str], enum_names: set[str]
) -> list[tuple[str, str]]:
    """Return module-level type aliases as (name, ctype) pairs, suitable for
    emission as `enum Name : ctype {};` strong typedefs in the header.

    Picks up both plain `Name = <type>` assignments (skipping `package`) and
    PEP 695 `type Name = <type>` statements. Aliases whose NAME is itself a
    built-in primitive are skipped -- those names are wired into the codegen's
    PRIMITIVE_TYPES table directly.
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
    `None`). `until` is the protocol version at which it was removed (or
    `None`). The entry is visible for any V in `[since, until)`.
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


def string_coded_enums(mod, enum_names: set[str]) -> set[str]:
    """Names of module-scope enums that some struct field encodes as a string
    via `field(type=str)`.

    Such an enum needs a `Serializer<Enum>` specialization that reads and
    writes the enumerator name lowercased with underscores stripped
    (`THROW_ITEM` -> `throwitem`). Integer-coded enum uses get no `Serializer`
    -- the codegen inlines a cast at the field site.
    """
    out: set[str] = set()
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
            if name_kwarg(attr.value, "field", "type") == "str":
                out.add(ann.name)
    return out


def reject_versioned_nested_enums(cls, nested: dict) -> None:
    """A nested enum's member set must be version-invariant: its visibility is
    the owning packet's, and per-member `since`/`until` would have to compose
    with the packet's own version split. Version such an enum at module scope
    instead."""
    for ename, ecls in nested.items():
        if class_since(ecls) is not None:
            raise click.ClickException(
                f"{cls.name}.{ename}: a nested enum cannot carry @enum(since=); "
                f"declare it at module scope to version it"
            )
        for mname, _, since, until in enum_members(ecls)["entries"]:
            if since is not None or until is not None:
                raise click.ClickException(
                    f"{cls.name}.{ename}.{mname}: a nested enum cannot have "
                    f"version-gated members; declare it at module scope to "
                    f"version it"
                )
