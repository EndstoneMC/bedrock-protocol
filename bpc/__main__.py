#!/usr/bin/env -S uv run --script
#
# /// script
# dependencies = [
#   "click",
#   "griffe",
#   "jinja2",
# ]
# ///

from pathlib import Path

import click
import griffe
from jinja2 import Environment, FileSystemLoader, StrictUndefined


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
    out_dir.mkdir(parents=True, exist_ok=True)
    for inp in inputs:
        mod = griffe.load(inp.stem, search_paths=[str(inp.parent)])
        print(mod.__repr__())


if __name__ == "__main__":
    main()  # type: ignore[call-arg]
