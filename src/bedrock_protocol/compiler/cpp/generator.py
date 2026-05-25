"""`CppGenerator` — the `CodeGenerator` registered as `"cpp"`.

Drives `FileGenerator` over the resolved descriptor and writes the
resulting C++ header to the `GeneratorContext`. The latest protocol
version targeted is read off `resolved.file_set.version` (originating
from `__version__` in the DSL surface module).
"""

from __future__ import annotations

from ...descriptor import CompilerError, ResolvedFile
from ..code_generator import CodeGenerator, GeneratorContext
from . import validate
from .file import FileGenerator


class CppGenerator(CodeGenerator):
    @property
    def name(self) -> str:
        return "cpp"

    def generate(
        self,
        resolved: ResolvedFile,
        context: GeneratorContext,
    ) -> None:
        if resolved.file_set.version is None:
            raise CompilerError("cpp: descriptor carries no version (expected __version__ in the DSL surface module)")
        try:
            validate.check(resolved)
            text = FileGenerator(resolved).render(resolved.file_set.version)
        except CompilerError as exc:
            context.error(str(exc))
            return
        relative = f"{resolved.file.stem}.hpp"
        with context.open(relative) as fh:
            fh.write(text)
        context.verbose(f"cpp: wrote {relative}")
