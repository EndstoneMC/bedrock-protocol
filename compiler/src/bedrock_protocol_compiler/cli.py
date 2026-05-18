"""CLI entry point: read protocol definitions and emit C++ headers.

The pipeline is frontend -> IR -> backend -> template: `Frontend` parses the
DSL into the language-agnostic `schema`, `VersionPlan` analyses versioning,
`CppBackend` lowers both into a render model, and one Jinja template prints it.
"""

from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .cpp import CppBackend
from .frontend import Frontend
from .schema import CompilerError
from .versioning import VersionPlan


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
) -> None:
    env = Environment(
        loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )
    template = env.get_template("header.hpp.jinja")
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        schema = Frontend([p.resolve() for p in import_paths]).load(inputs)
        for name in schema.outputs:
            module = schema.modules[name]
            plan = VersionPlan(module.types)
            rendered = CppBackend(module, schema, plan).render(latest_version)
            target = out_dir / f"{module.stem}.hpp"
            target.write_text(template.render(m=rendered))
            if verbose:
                click.echo(f"wrote {target}")
    except CompilerError as exc:
        raise click.ClickException(str(exc))


if __name__ == "__main__":
    main()
