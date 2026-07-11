"""C++ backend — analog of protoc's `compiler/cpp/`.

The public surface is the `CppGenerator` class. Everything else is
implementation detail: `FileGenerator` assembles a header/source pair,
delegating to `ClassGenerator` / `EnumGenerator` and the `FieldGenerator`
codec, all printed through `Printer`.
"""

from .generator import CppGenerator

__all__ = ["CppGenerator"]
