"""CLI entry point: read protocol definitions and emit C++ headers."""

from pathlib import Path

import click
import griffe
import inflection
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .filters import (
    class_fields,
    compute_templated_classes,
    enum_members,
    enum_ranges,
    enum_serializers,
    module_aliases,
    type_alias_wires,
)
from .parse import class_since, is_int_enum


@click.command()
@click.version_option(version="0.1.0", prog_name="bpc")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output.")
@click.option(
    "--out",
    "out_dir",
    type=click.Path(file_okay=False, path_type=Path),
    help="Output directory for per-input .hpp files (compile mode).",
)
@click.option(
    "--umbrella",
    "umbrella_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Generate an umbrella header at PATH listing #includes for each "
    "input (skips per-input compilation).",
)
@click.option(
    "--latest",
    "latest_version",
    type=int,
    default=974,
    show_default=True,
    help="Protocol version exposed as the default template argument and "
    "via the `latest::` sub-namespace.",
)
@click.argument(
    "inputs",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def main(
    verbose: bool,
    out_dir: Path | None,
    umbrella_path: Path | None,
    latest_version: int,
    inputs: tuple[Path, ...],
):
    if umbrella_path is not None:
        umbrella_path.parent.mkdir(parents=True, exist_ok=True)
        names = sorted(f"{inp.stem}.hpp" for inp in inputs)
        body = "#pragma once\n\n" + "".join(f'#include "{n}"\n' for n in names)
        umbrella_path.write_text(body)
        if verbose:
            click.echo(f"wrote {umbrella_path}")
        return

    if out_dir is None:
        raise click.UsageError("--out is required when not using --umbrella")

    env = Environment(
        loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )
    env.filters["camelize"] = lambda s: inflection.camelize(s.lower())
    env.filters["enum_members"] = enum_members
    env.filters["enum_ranges"] = enum_ranges
    env.filters["class_since"] = class_since
    template = env.get_template("header.hpp.jinja")
    out_dir.mkdir(parents=True, exist_ok=True)
    for inp in inputs:
        mod = griffe.load(
            inp.stem, search_paths=[str(inp.parent)], allow_inspection=False
        )
        classes = [c for c in mod.classes.values() if not c.is_alias]
        class_names = {c.name for c in classes}
        enum_names = {c.name for c in classes if is_int_enum(c)}
        templated_classes = compute_templated_classes(classes, enum_names)
        alias_wires = type_alias_wires(mod)
        type_aliases = module_aliases(mod, class_names, enum_names)
        serializers = enum_serializers(mod, enum_names)
        has_struct_serializer = any(
            not is_int_enum(c)
            and class_fields(c, class_names, enum_names, templated_classes, alias_wires) is not None
            for c in classes
        )
        has_serializers = bool(serializers) or has_struct_serializer
        if not classes and not type_aliases:
            if verbose:
                click.echo(f"skip {inp} (nothing to emit)")
            continue
        env.filters["class_fields"] = (
            lambda cls, _cn=class_names, _en=enum_names, _tc=templated_classes, _aw=alias_wires:
            class_fields(cls, _cn, _en, _tc, _aw)
        )
        attr = mod.members.get("package")
        package = str(attr.value).strip("'\"") if attr and attr.value else None
        target = out_dir / f"{inp.stem}.hpp"
        target.write_text(
            template.render(
                mod=mod,
                package=package,
                type_aliases=type_aliases,
                has_classes=bool(classes),
                serializers=serializers,
                has_serializers=has_serializers,
                latest_version=latest_version,
            )
        )
        if verbose:
            click.echo(f"wrote {target}")


if __name__ == "__main__":
    main()  # type: ignore[call-arg]
