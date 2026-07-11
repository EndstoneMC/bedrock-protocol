"""CLI driver — protoc analog of `compiler/command_line_interface.h`.

    bpc --language cpp --out <dir> [--import-path <dir>]... <inputs>...

`--language NAME` selects the registered backend; `--out DIR` is its output
directory. One backend per invocation. The protocol version a backend
targets is sourced from the DSL itself (`__version__` in
`protocol/__init__.py`), so there is no command-line knob for it.
"""

from __future__ import annotations

from pathlib import Path

import click

from .compiler import (
    GENERATORS,
    FilesystemContext,
    SourceTree,
    resolve,
)
from .descriptor import CompilerError


@click.command()
@click.version_option(version="0.1.0", prog_name="bpc")
@click.option("-v", "--verbose", is_flag=True, help="Print one line per output file.")
@click.option(
    "--language",
    "--lang",
    "language",
    required=True,
    metavar="NAME",
    help="Target backend, e.g. --language cpp. One per invocation.",
)
@click.option(
    "--out",
    "out_dir",
    required=True,
    metavar="DIR",
    type=click.Path(file_okay=False, path_type=Path),
    help="Backend output directory.",
)
@click.option(
    "--import-path",
    "import_paths",
    multiple=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Search root for resolving `from X.Y import ...` between inputs. Repeatable. Mirrors protoc's --proto_path.",
)
@click.argument(
    "inputs",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def main(
    verbose: bool,
    language: str,
    out_dir: Path,
    import_paths: tuple[Path, ...],
    inputs: tuple[Path, ...],
) -> None:
    factory = GENERATORS.get(language)
    if factory is None:
        raise click.ClickException(f"unknown language {language!r}; known: {sorted(GENERATORS)}")

    try:
        file_set = SourceTree(list(import_paths)).load_all(inputs)
    except CompilerError as exc:
        raise click.ClickException(str(exc))

    if file_set.version is None:
        raise click.ClickException(
            "no __version__ declared in the DSL surface (expected `__version__ = <int>` in protocol/__init__.py)"
        )

    error_seen = False
    for output_name in file_set.outputs:
        try:
            resolved = resolve(file_set.files[output_name], file_set)
        except CompilerError as exc:
            raise click.ClickException(str(exc))
        ctx = FilesystemContext(out_dir, verbose=verbose)
        try:
            factory().generate(resolved, ctx)
        except CompilerError as exc:
            raise click.ClickException(str(exc))
        for err in ctx.errors:
            click.echo(f"error: {language}: {err}", err=True)
            error_seen = True

    if error_seen:
        raise click.ClickException("backend reported errors")


if __name__ == "__main__":
    main()
