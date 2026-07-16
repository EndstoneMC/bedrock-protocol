"""`CppGenerator` — the `CodeGenerator` registered as `"cpp"`.

Drives `FileGenerator` over the resolved descriptor and writes the
resulting C++ header to the `GeneratorContext`. The latest protocol
version targeted is read off `resolved.pool.file_set.version` (originating
from `__version__` in the DSL surface module).
"""

from __future__ import annotations

from bedrock_protocol.compiler.code_generator import CodeGenerator, GeneratorContext
from bedrock_protocol.descriptor import CompilerError, ResolvedFile

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
        if resolved.pool.file_set.version is None:
            raise CompilerError("cpp: descriptor carries no version (expected __version__ in the DSL surface module)")
        try:
            gen = FileGenerator(resolved)
            header = gen.render_header(resolved.pool.file_set.version)
            source = gen.render_source()
        except CompilerError as exc:
            context.error(str(exc))
            return
        stem = resolved.file.stem
        with context.open(f"{stem}.h") as fh:
            fh.write(header)
        with context.open(f"{stem}.cpp") as fh:
            fh.write(source)
        context.verbose(f"cpp: wrote {stem}.h + {stem}.cpp")
