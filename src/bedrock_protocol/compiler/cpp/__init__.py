"""C++ backend — analog of protoc's `compiler/cpp/`.

The public surface is the `CppGenerator` class. Everything else in this
package is implementation detail: `file_generator` assembles a render model,
`enum_generator` / `struct_generator` / `serializer_generator` lower the IR
into that model, and `templates/` prints it.
"""

from .generator import CppGenerator

__all__ = ["CppGenerator"]
