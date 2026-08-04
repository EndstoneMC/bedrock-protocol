"""Compile one DSL module in isolation and hand back the C++ it emits.

The C++ suite exercises the schema end to end; these cases exercise the
compiler itself, so each one writes a throwaway `protocol` package whose
`__init__.py` is a copy of the real DSL surface and compiles a single module
against it. Nothing under `protocol/` is read, so a case says exactly what its
own source says.

Run with:

    uv run python -m unittest discover -s tests/compiler -t tests/compiler
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from bedrock_protocol.compiler import DescriptorPool, Importer, SourceTree
from bedrock_protocol.compiler.cpp.file import FileGenerator
from bedrock_protocol.descriptor import CompilerError

#: The DSL surface every case compiles against -- the real one, copied in.
DSL_SURFACE = Path(__file__).resolve().parents[2] / "protocol" / "__init__.py"


class CompilerCase(unittest.TestCase):
    def compile(self, source: str, module: str = "mod") -> tuple[str, str]:
        """The `(header, source)` C++ text for one DSL module."""
        root = Path(tempfile.mkdtemp(prefix="bpc-test-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        package = root / "protocol"
        package.mkdir()
        shutil.copyfile(DSL_SURFACE, package / "__init__.py")
        target = package / f"{module}.py"
        target.write_text(source, encoding="utf-8")

        file_set = Importer(SourceTree([root])).load_all((target,))
        assert file_set.version is not None
        resolved = DescriptorPool(file_set).build_file(f"protocol.{module}")
        generator = FileGenerator(resolved)
        return generator.render_header(file_set.version), generator.render_source()

    def rejects(self, source: str) -> str:
        """The `CompilerError` message a bad module raises."""
        with self.assertRaises(CompilerError) as caught:
            self.compile(source)
        return str(caught.exception)

    def namespace(self, text: str, name: str) -> str:
        """One snapshot namespace's body out of a generated header."""
        start = text.index(f"namespace {name} {{")
        return text[start : text.index(f"}}  // namespace {name}", start)]

    def body(self, text: str, signature: str) -> str:
        """One serializer body out of a generated `.cpp`, named by the line that
        opens it, so a case asserts against the function it means."""
        start = text.index(signature)
        opened = text.index("{", start)
        depth = 0
        for i in range(opened, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[opened : i + 1]
        raise AssertionError(f"unterminated body for {signature!r}")
