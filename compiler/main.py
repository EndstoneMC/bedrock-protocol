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

import ast
from pathlib import Path

import click
import griffe
import inflection
from jinja2 import Environment, FileSystemLoader, StrictUndefined


def _parse_member_value(raw: str) -> tuple[int, int | None] | None:
    """Parse `0` or `value(N, since=V)`. Returns (int_value, since_or_None)."""
    try:
        node = ast.parse(raw, mode="eval").body
    except (SyntaxError, ValueError):
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value, None
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "value"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, int)
    ):
        since: int | None = None
        for kw in node.keywords:
            if (
                kw.arg == "since"
                and isinstance(kw.value, ast.Constant)
                and isinstance(kw.value.value, int)
            ):
                since = kw.value.value
        return node.args[0].value, since
    return None


_PRIMITIVE_TYPES = {
    "str": "std::string",
    "int": "int",
    "bool": "bool",
}


def _resolve_type(py_type: str, class_names: set[str]) -> str | None:
    """Map a Python type expression to a C++ type. None if unmappable.

    Handles `X | None` → `std::optional<X>` and routes user-defined classes
    through their `ProtocolVersion` template.
    """
    py_type = py_type.strip()
    optional = py_type.endswith("| None")
    if optional:
        py_type = py_type[: -len("| None")].strip()
    if py_type in class_names:
        ctype = f"{py_type}<ProtocolVersion>"
    elif py_type in _PRIMITIVE_TYPES:
        ctype = _PRIMITIVE_TYPES[py_type]
    else:
        return None
    if optional:
        ctype = f"std::optional<{ctype}>"
    return ctype


def _parse_field_default(raw: str) -> tuple[bool, int | None]:
    """Parse a field's default. Returns (is_field_call, since_or_None)."""
    try:
        node = ast.parse(raw, mode="eval").body
    except (SyntaxError, ValueError):
        return False, None
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "field"
    ):
        return False, None
    for kw in node.keywords:
        if (
            kw.arg == "since"
            and isinstance(kw.value, ast.Constant)
            and isinstance(kw.value.value, int)
        ):
            return True, kw.value.value
    return True, None


def class_since(cls) -> int | None:
    """Read `@enum(since=N)` from a class's decorators. Returns N or None."""
    for dec in cls.decorators:
        try:
            node = ast.parse(str(dec.value), mode="eval").body
        except (SyntaxError, ValueError):
            continue
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "enum"
        ):
            continue
        for kw in node.keywords:
            if (
                kw.arg == "since"
                and isinstance(kw.value, ast.Constant)
                and isinstance(kw.value.value, int)
            ):
                return kw.value.value
    return None


def class_fields(cls, class_names: set[str]) -> dict | None:
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
        ann = str(attr.annotation).strip()
        if "instance-attribute" not in attr.labels:
            ctype = _PRIMITIVE_TYPES.get(ann)
            if ctype is None:
                return None
            constants.append((name, ctype, str(attr.value)))
            continue
        ctype = _resolve_type(ann, class_names)
        if ctype is None:
            return None
        since: int | None = None
        if attr.value is not None:
            ok, parsed = _parse_field_default(str(attr.value))
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
        parsed = _parse_member_value(str(attr.value))
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
        mod = griffe.load(inp.stem, search_paths=[str(inp.parent)])
        if not any(not c.is_alias for c in mod.classes.values()):
            if verbose:
                click.echo(f"skip {inp} (no classes)")
            continue
        class_names = {c.name for c in mod.classes.values() if not c.is_alias}
        env.filters["class_fields"] = lambda cls, _n=class_names: class_fields(cls, _n)
        attr = mod.members.get("package")
        package = str(attr.value).strip("'\"") if attr and attr.value else None
        target = out_dir / f"{inp.stem}.hpp"
        target.write_text(template.render(mod=mod, package=package))
        if verbose:
            click.echo(f"wrote {target}")


if __name__ == "__main__":
    main()  # type: ignore[call-arg]
