"""CLI driver — protoc analog of `compiler/command_line_interface.h`.

    bpc --language cpp --out <dir> [--opt KEY=VAL]...
        [--import-path <dir>]... <inputs>...

`--language NAME` selects the registered backend; `--out DIR` is its output
directory; `--opt KEY=VAL` carries backend parameters. One backend per
invocation. The shape mirrors protoc's `--<name>_out` / `--<name>_opt`
without the Windows drive-letter ambiguity of `--cpp_out=opt:C:\\...`.
"""

from __future__ import annotations

from pathlib import Path

import click

from .compiler import (
    FilesystemContext,
    GENERATORS,
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
    "--opt",
    "opts",
    multiple=True,
    metavar="KEY=VAL",
    help="Backend option, e.g. --opt latest=974. Repeatable.",
)
@click.option(
    "--import-path",
    "import_paths",
    multiple=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Search root for resolving `from X.Y import ...` between inputs. "
         "Repeatable. Mirrors protoc's --proto_path.",
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
    opts: tuple[str, ...],
    import_paths: tuple[Path, ...],
    inputs: tuple[Path, ...],
) -> None:
    factory = GENERATORS.get(language)
    if factory is None:
        raise click.ClickException(
            f"unknown language {language!r}; known: {sorted(GENERATORS)}"
        )
    parameter = _join_opts(opts)

    try:
        file_set = SourceTree(list(import_paths)).load_all(inputs)
    except CompilerError as exc:
        raise click.ClickException(str(exc))

    error_seen = False
    for output_name in file_set.outputs:
        try:
            resolved = resolve(file_set.files[output_name], file_set)
        except CompilerError as exc:
            raise click.ClickException(str(exc))
        ctx = FilesystemContext(out_dir, verbose=verbose)
        try:
            factory().generate(resolved, parameter, ctx)
        except CompilerError as exc:
            raise click.ClickException(str(exc))
        for err in ctx.errors:
            click.echo(f"error: {language}: {err}", err=True)
            error_seen = True

    if error_seen:
        raise click.ClickException("backend reported errors")


def _join_opts(opts: tuple[str, ...]) -> str:
    """Merge repeated --opt KEY=VAL into one comma-separated parameter string.
    Each chunk must already be KEY=VAL; the backend parses the joined form."""
    for raw in opts:
        if "=" not in raw:
            raise click.ClickException(
                f"--opt expected KEY=VAL, got {raw!r}"
            )
    return ",".join(opts)


if __name__ == "__main__":
    main()
