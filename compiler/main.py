#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "click",
#   "griffe",
#   "inflection",
#   "jinja2",
# ]
# ///

from pathlib import Path

import click
import griffe
import inflection
from jinja2 import Environment, FileSystemLoader, StrictUndefined


_PRIMITIVE_TYPES = {
    "str": "std::string",
    "int": "int",
    "bool": "bool",
}


def _as_int(x) -> int | None:
    """Coerce a griffe literal (a raw `str` from source) to int, or None."""
    if isinstance(x, str):
        try:
            return int(x)
        except ValueError:
            return None
    return None


def _is_call(expr, name: str) -> bool:
    return (
        isinstance(expr, griffe.ExprCall)
        and isinstance(expr.function, griffe.ExprName)
        and expr.function.name == name
    )


def _keyword(call: griffe.ExprCall, name: str):
    """Return the value of the first `name=` kwarg in a call, or None."""
    for arg in call.arguments:
        if isinstance(arg, griffe.ExprKeyword) and arg.name == name:
            return arg.value
    return None


def _is_int_enum(cls) -> bool:
    return any(
        isinstance(b, griffe.ExprName) and b.name == "IntEnum" for b in cls.bases
    )


def _parse_member_value(value) -> tuple[int, int | None] | None:
    """Parse `0` or `value(N, since=V)`. Returns (int_value, since_or_None)."""
    direct = _as_int(value)
    if direct is not None:
        return direct, None
    if not _is_call(value, "value") or not value.arguments:
        return None
    ivalue = _as_int(value.arguments[0])
    if ivalue is None:
        return None
    return ivalue, _as_int(_keyword(value, "since"))


def _parse_field_default(value) -> tuple[bool, int | None]:
    """Parse `field(since=N)`. Returns (is_field_call, since_or_None)."""
    if not _is_call(value, "field"):
        return False, None
    return True, _as_int(_keyword(value, "since"))


def class_since(cls) -> int | None:
    """Read `@enum(since=N)` from a class's decorators. Returns N or None."""
    for dec in cls.decorators:
        if _is_call(dec.value, "enum"):
            since = _as_int(_keyword(dec.value, "since"))
            if since is not None:
                return since
    return None


def _resolve_type(ann, class_names: set[str], enum_names: set[str]) -> str | None:
    """Map a griffe annotation Expr to a C++ type. None if unmappable.

    Routes user-defined classes through their `ProtocolVersion` template, uses
    the inner `::Value` enum type for IntEnum classes, and maps explicit
    `Union[A, B, None]` to `std::variant<A, B, std::monostate>`.
    """
    if (
        isinstance(ann, griffe.ExprSubscript)
        and isinstance(ann.left, griffe.ExprName)
        and ann.left.name == "Union"
    ):
        elements = (
            ann.slice.elements
            if isinstance(ann.slice, griffe.ExprTuple)
            else [ann.slice]
        )
        parts: list[str] = []
        for member in elements:
            if isinstance(member, str) and member == "None":
                parts.append("std::monostate")
                continue
            resolved = _resolve_type(member, class_names, enum_names)
            if resolved is None:
                return None
            parts.append(resolved)
        return f"std::variant<{', '.join(parts)}>"
    if isinstance(ann, griffe.ExprName):
        name = ann.name
        if name in enum_names:
            return f"{name}<ProtocolVersion>::Value"
        if name in class_names:
            return f"{name}<ProtocolVersion>"
        if name in _PRIMITIVE_TYPES:
            return _PRIMITIVE_TYPES[name]
    return None


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
                and attr.annotation.name in _PRIMITIVE_TYPES
            ):
                return None
            ctype = _PRIMITIVE_TYPES[attr.annotation.name]
            constants.append((name, ctype, str(attr.value)))
            continue
        ctype = _resolve_type(attr.annotation, class_names, enum_names)
        if ctype is None:
            return None
        since: int | None = None
        if attr.value is not None:
            ok, parsed = _parse_field_default(attr.value)
            if ok:
                since = parsed
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


def enum_members(cls) -> dict:
    """Bucket an enum class's attributes into always-present vs version-gated."""
    always: list[tuple[str, int]] = []
    gates: dict[int, list[tuple[str, int]]] = {}
    for name, attr in cls.attributes.items():
        if attr.value is None:
            continue
        parsed = _parse_member_value(attr.value)
        if parsed is None:
            continue
        ivalue, since = parsed
        if since is None:
            always.append((name, ivalue))
        else:
            gates.setdefault(since, []).append((name, ivalue))
    return {"always": always, "gates": sorted(gates.items())}


@click.command()
@click.version_option(version="0.1.0", prog_name="bpc")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output.")
@click.option(
    "--out",
    "out_dir",
    required=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Output directory for generated .hpp files.",
)
@click.argument(
    "inputs",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def main(verbose: bool, out_dir: Path, inputs: tuple[Path, ...]):
    env = Environment(
        loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )
    env.filters["camelize"] = lambda s: inflection.camelize(s.lower())
    env.filters["enum_members"] = enum_members
    env.filters["class_since"] = class_since
    template = env.get_template("header.hpp.jinja")
    out_dir.mkdir(parents=True, exist_ok=True)
    for inp in inputs:
        mod = griffe.load(
            inp.stem, search_paths=[str(inp.parent)], allow_inspection=False
        )
        if not any(not c.is_alias for c in mod.classes.values()):
            if verbose:
                click.echo(f"skip {inp} (no classes)")
            continue
        classes = [c for c in mod.classes.values() if not c.is_alias]
        class_names = {c.name for c in classes}
        enum_names = {c.name for c in classes if _is_int_enum(c)}
        env.filters["class_fields"] = lambda cls, _cn=class_names, _en=enum_names: (
            class_fields(cls, _cn, _en)
        )
        attr = mod.members.get("package")
        package = str(attr.value).strip("'\"") if attr and attr.value else None
        target = out_dir / f"{inp.stem}.hpp"
        target.write_text(template.render(mod=mod, package=package))
        if verbose:
            click.echo(f"wrote {target}")


if __name__ == "__main__":
    main()  # type: ignore[call-arg]
