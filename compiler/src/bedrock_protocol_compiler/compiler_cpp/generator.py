"""`CppGenerator` — the `CodeGenerator` registered as `"cpp"`.

Parses its `parameter` for `latest=<int>`, drives `FileGenerator` over the
resolved descriptor, then renders the result through Jinja.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ..descriptor import CompilerError, ResolvedFileDescriptor
from ..compiler.code_generator import CodeGenerator, GeneratorContext
from .file_generator import FileGenerator
from . import validate


_DEFAULT_LATEST = 974


class CppGenerator(CodeGenerator):
    @property
    def name(self) -> str:
        return "cpp"

    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            undefined=StrictUndefined,
        )
        self._template = self._env.get_template("header.hpp.jinja")

    def generate(
        self,
        resolved: ResolvedFileDescriptor,
        parameter: str,
        context: GeneratorContext,
    ) -> None:
        latest = _parse_parameter(parameter)
        try:
            validate.check(resolved)
            rendered = FileGenerator(resolved).render(latest)
        except CompilerError as exc:
            context.error(str(exc))
            return
        relative = f"{resolved.file.stem}.hpp"
        with context.open(relative) as fh:
            fh.write(self._template.render(m=rendered))
        context.verbose(f"cpp: wrote {relative}")


def _parse_parameter(parameter: str) -> int:
    """Parse `--opt latest=<int>`. Empty string is allowed (use default)."""
    if not parameter:
        return _DEFAULT_LATEST
    parts: dict[str, str] = {}
    for chunk in parameter.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise CompilerError(
                f"cpp: --opt expected key=value, got {chunk!r}"
            )
        k, v = chunk.split("=", 1)
        parts[k.strip()] = v.strip()
    latest_str = parts.pop("latest", str(_DEFAULT_LATEST))
    if parts:
        raise CompilerError(
            f"cpp: unknown opt key(s) {sorted(parts)}; supported: latest=<int>"
        )
    try:
        return int(latest_str)
    except ValueError:
        raise CompilerError(
            f"cpp: --opt latest must be an integer, got {latest_str!r}"
        )
