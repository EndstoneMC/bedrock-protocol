"""CLI entry point: read protocol definitions and emit C++ headers."""

from pathlib import Path

import click
import griffe
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .filters import module_aliases, type_alias_wires
from .parse import is_int_enum
from .versioning import plan_module


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
    "--import-path",
    "import_paths",
    multiple=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Search root for resolving `from X.Y import ...` between inputs. "
    "Repeatable. Mirrors protoc's `--proto_path`.",
)
@click.option(
    "--latest",
    "latest_version",
    type=int,
    default=974,
    show_default=True,
    help="Protocol version exposed as the default template argument via the "
    "bare-name `using XXX = XXX_<latest>` aliases.",
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
    import_paths: tuple[Path, ...],
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
    template = env.get_template("header.hpp.jinja")
    out_dir.mkdir(parents=True, exist_ok=True)

    resolved_import_paths = tuple(p.resolve() for p in import_paths)

    # Load explicit inputs, anchoring each on the nearest --import-path so its
    # dotted name matches what `from X.Y import ...` would use elsewhere.
    mods: dict[str, tuple] = {}
    output_modules: set[str] = set()
    for inp in inputs:
        name, root = _module_name_and_root(inp, resolved_import_paths)
        mod = griffe.load(name, search_paths=[str(root)], allow_inspection=False)
        mods[name] = (mod, inp)
        output_modules.add(name)

    # Follow imports out of the explicit inputs to load referenced modules from
    # --import-path roots. Modules loaded this way provide context for type
    # resolution but do not themselves produce output. Same protobuf split as
    # `--proto_path` vs the explicit `.proto` arguments.
    pending = list(output_modules)
    while pending:
        cur = pending.pop()
        cur_mod, _ = mods[cur]
        for dep_name in _imports_from(cur_mod):
            if dep_name in mods:
                continue
            parts = dep_name.split(".")
            for ip in resolved_import_paths:
                candidate = ip.joinpath(*parts).with_suffix(".py")
                if candidate.is_file():
                    dep_mod = griffe.load(
                        dep_name, search_paths=[str(ip)], allow_inspection=False
                    )
                    mods[dep_name] = (dep_mod, None)
                    pending.append(dep_name)
                    break

    known_modules = set(mods)

    for module_name in output_modules:
        mod, inp = mods[module_name]
        deps = sorted(_module_dependencies(mod, known_modules, module_name))
        own_classes = [c for c in mod.classes.values() if not c.is_alias]
        dep_classes: list = []
        extra_alias_wires: dict[str, dict] = {}
        for dep in deps:
            dep_mod = mods[dep][0]
            dep_classes.extend(c for c in dep_mod.classes.values() if not c.is_alias)
            extra_alias_wires.update(type_alias_wires(dep_mod))
        resolvable = own_classes + dep_classes
        class_names = {c.name for c in resolvable}
        enum_names = {c.name for c in resolvable if is_int_enum(c)}
        alias_wires = {**extra_alias_wires, **type_alias_wires(mod)}
        module_alias_list = module_aliases(mod, class_names, enum_names)
        if not own_classes and not module_alias_list:
            if verbose:
                click.echo(f"skip {inp} (nothing to emit)")
            continue

        plan = plan_module(
            mod, own_classes, dep_classes, class_names, enum_names, alias_wires
        )
        attr = mod.members.get("package")
        package = str(attr.value).strip("'\"") if attr and attr.value else None
        target = out_dir / f"{inp.stem}.hpp"
        dep_includes = [d.replace(".", "/") + ".hpp" for d in deps]
        target.write_text(
            template.render(
                package=package.replace(".", "::") if package else None,
                module_aliases=module_alias_list,
                dep_includes=dep_includes,
                latest_version=latest_version,
                **plan,
            )
        )
        if verbose:
            click.echo(f"wrote {target}")


def _imports_from(mod) -> set[str]:
    """Dotted source modules referenced by `from X.Y import ...` aliases.

    Walks `mod.members` for griffe Alias entries (one per imported binding)
    and extracts the source module from each alias's target path. Modules
    whose path contains any component starting with `_` (private modules
    like `protocol._dsl`) are skipped: they exist only to support the
    schema DSL and have no header to emit or include.
    """
    out: set[str] = set()
    for _, member in mod.members.items():
        target = getattr(member, "target_path", None)
        if target is None:
            continue
        target_str = str(target)
        if "." not in target_str:
            continue
        dep = target_str.rsplit(".", 1)[0]
        if any(part.startswith("_") for part in dep.split(".")):
            continue
        out.add(dep)
    return out


def _module_name_and_root(
    path: Path, import_paths: tuple[Path, ...]
) -> tuple[str, Path]:
    """Return (dotted module name, search root) for `path`.

    Anchored on the nearest containing `--import-path`. Falls back to
    `<parent.name>.<stem>` and `path.parent` when no import-path contains it.
    """
    path = path.resolve()
    for ip in import_paths:
        try:
            rel = path.relative_to(ip)
        except ValueError:
            continue
        return ".".join(rel.with_suffix("").parts), ip
    return (
        (f"{path.parent.name}.{path.stem}" if path.parent.name else path.stem),
        path.parent,
    )


def _module_dependencies(mod, known_modules: set[str], self_module: str) -> set[str]:
    """Return the set of `known_modules` that `mod` imports from."""
    return {d for d in _imports_from(mod) if d != self_module and d in known_modules}


if __name__ == "__main__":
    main()  # type: ignore[call-arg]
