"""CLI entry point: read protocol definitions and emit C++ headers."""

from pathlib import Path

import click
import griffe
import inflection
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .filters import class_fields, enum_codecs, enum_members, module_aliases
from .parse import class_since, is_int_enum


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
        classes = [c for c in mod.classes.values() if not c.is_alias]
        class_names = {c.name for c in classes}
        enum_names = {c.name for c in classes if is_int_enum(c)}
        type_aliases = module_aliases(mod, class_names, enum_names)
        codecs = enum_codecs(mod, enum_names)
        if not classes and not type_aliases:
            if verbose:
                click.echo(f"skip {inp} (nothing to emit)")
            continue
        env.filters["class_fields"] = lambda cls, _cn=class_names, _en=enum_names: (
            class_fields(cls, _cn, _en)
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
                codecs=codecs,
            )
        )
        if verbose:
            click.echo(f"wrote {target}")


if __name__ == "__main__":
    main()  # type: ignore[call-arg]
