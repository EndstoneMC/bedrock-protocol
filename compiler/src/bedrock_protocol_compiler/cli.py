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
    required=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Output directory for per-input .hpp files.",
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
    out_dir: Path,
    latest_version: int,
    inputs: tuple[Path, ...],
):

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

    # Pre-load every input so each file's `from X.Y import ...` can be resolved
    # against the others. Keyed by the dotted module path that import statements
    # would use (e.g. "protocol.common").
    mods: dict[str, tuple] = {}
    for inp in inputs:
        mod = griffe.load(
            inp.stem, search_paths=[str(inp.parent)], allow_inspection=False
        )
        module_name = f"{inp.parent.name}.{inp.stem}" if inp.parent.name else inp.stem
        mods[module_name] = (mod, inp)
    known_modules = set(mods)

    for module_name, (mod, inp) in mods.items():
        deps = sorted(_module_dependencies(mod, known_modules, module_name))
        own_classes = [c for c in mod.classes.values() if not c.is_alias]
        extra_classes: list = []
        extra_alias_wires: dict[str, dict] = {}
        for dep in deps:
            dep_mod = mods[dep][0]
            extra_classes.extend(c for c in dep_mod.classes.values() if not c.is_alias)
            extra_alias_wires.update(type_alias_wires(dep_mod))
        resolvable = own_classes + extra_classes
        class_names = {c.name for c in resolvable}
        enum_names = {c.name for c in resolvable if is_int_enum(c)}
        templated_classes = compute_templated_classes(resolvable, enum_names)
        alias_wires = {**extra_alias_wires, **type_alias_wires(mod)}
        type_aliases = module_aliases(mod, class_names, enum_names)
        serializers = enum_serializers(mod, enum_names)
        has_struct_serializer = any(
            not is_int_enum(c)
            and class_fields(c, class_names, enum_names, templated_classes, alias_wires) is not None
            for c in own_classes
        )
        has_serializers = bool(serializers) or has_struct_serializer
        if not own_classes and not type_aliases:
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
        dep_includes = [d.replace(".", "/") + ".hpp" for d in deps]
        target.write_text(
            template.render(
                mod=mod,
                package=package,
                type_aliases=type_aliases,
                has_classes=bool(own_classes),
                serializers=serializers,
                has_serializers=has_serializers,
                latest_version=latest_version,
                dep_includes=dep_includes,
            )
        )
        if verbose:
            click.echo(f"wrote {target}")


def _module_dependencies(mod, known_modules: set[str], self_module: str) -> set[str]:
    """Return the set of `known_modules` that `mod` imports from.

    Walks `mod.members` for griffe Alias entries (one per `from X.Y import Name`
    binding) and extracts the source module from each alias's target path.
    Modules outside `known_modules` (typing, enum, protocol._dsl, etc.) are
    ignored.
    """
    deps: set[str] = set()
    for _, member in mod.members.items():
        target = getattr(member, "target_path", None)
        if target is None:
            continue
        target_str = str(target)
        if "." not in target_str:
            continue
        candidate = target_str.rsplit(".", 1)[0]
        if candidate != self_module and candidate in known_modules:
            deps.add(candidate)
    return deps


if __name__ == "__main__":
    main()  # type: ignore[call-arg]
