"""CLI driver — protoc analog of `compiler/command_line_interface.h`.

    bpc --out cpp=<dir> [--opt cpp=key=val,...] \
        [--import-path <dir>]... <inputs>...

A single repeatable `--out NAME=DIR` selects the registered backend(s);
`--opt NAME=k=v,k=v` carries per-backend parameters. The shape mirrors
protoc's `--<name>_out` / `--<name>_opt` without the Windows drive-letter
ambiguity of `--cpp_out=opt:C:\\…`.
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
    "--out",
    "outs",
    multiple=True,
    required=True,
    metavar="NAME=DIR",
    help="Backend output directory, e.g. --out cpp=build/include/bedrock. "
         "Repeatable; one per registered backend you want to invoke.",
)
@click.option(
    "--opt",
    "opts",
    multiple=True,
    metavar="NAME=KEY=VAL[,KEY=VAL]",
    help="Per-backend option string, e.g. --opt cpp=latest=974.",
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
    outs: tuple[str, ...],
    opts: tuple[str, ...],
    import_paths: tuple[Path, ...],
    inputs: tuple[Path, ...],
) -> None:
    out_map = _parse_out_flags(outs)
    opt_map = _parse_opt_flags(opts, known=set(out_map))

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
        for name, out_dir in out_map.items():
            factory = GENERATORS.get(name)
            if factory is None:
                raise click.ClickException(
                    f"unknown backend {name!r}; known: {sorted(GENERATORS)}"
                )
            ctx = FilesystemContext(out_dir, verbose=verbose)
            try:
                factory().generate(resolved, opt_map.get(name, ""), ctx)
            except CompilerError as exc:
                raise click.ClickException(str(exc))
            for err in ctx.errors:
                click.echo(f"error: {name}: {err}", err=True)
                error_seen = True

    if error_seen:
        raise click.ClickException("one or more backends reported errors")


def _parse_out_flags(outs: tuple[str, ...]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for raw in outs:
        if "=" not in raw:
            raise click.ClickException(
                f"--out expected NAME=DIR, got {raw!r}"
            )
        name, dir_str = raw.split("=", 1)
        if name in result:
            raise click.ClickException(f"--out {name}= given twice")
        result[name] = Path(dir_str)
    return result


def _parse_opt_flags(opts: tuple[str, ...], known: set[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in opts:
        if "=" not in raw:
            raise click.ClickException(
                f"--opt expected NAME=KEY=VAL, got {raw!r}"
            )
        name, value = raw.split("=", 1)
        if name not in known:
            raise click.ClickException(
                f"--opt {name}: no matching --out {name}=<dir> was given"
            )
        if name in result:
            result[name] = f"{result[name]},{value}"
        else:
            result[name] = value
    return result


if __name__ == "__main__":
    main()
