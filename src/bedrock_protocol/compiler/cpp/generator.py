"""`CppGenerator` — the `CodeGenerator` registered as `"cpp"`.

Parses its `parameter` for `latest=<int>`, drives `FileGenerator` over the
resolved descriptor, and writes the resulting C++ header to the
`GeneratorContext`.
"""

from __future__ import annotations

from ...descriptor import CompilerError, ResolvedFile
from ..code_generator import CodeGenerator, GeneratorContext
from .file import FileGenerator
from . import validate


_DEFAULT_LATEST = 974


class CppGenerator(CodeGenerator):
    @property
    def name(self) -> str:
        return "cpp"

    def generate(
        self,
        resolved: ResolvedFile,
        parameter: str,
        context: GeneratorContext,
    ) -> None:
        latest = _parse_parameter(parameter)
        try:
            validate.check(resolved)
            text = FileGenerator(resolved).render(latest)
        except CompilerError as exc:
            context.error(str(exc))
            return
        relative = f"{resolved.file.stem}.hpp"
        with context.open(relative) as fh:
            fh.write(text)
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
