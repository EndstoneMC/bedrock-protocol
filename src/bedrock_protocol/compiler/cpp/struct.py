"""`StructGenerator` — emits a `struct Name { ... };` block.

The body holds, in order: nested enum declarations (each followed by a
blank line), `static constexpr` constants (e.g. packet `Id`), and the
field declarations. protoc analog: `compiler/cpp/cpp_message.{h,cc}`.
"""

from __future__ import annotations

from ...descriptor import Struct
from .field import FileContext, cpp_type
from .names import camel
from .printer import Printer


class StructGenerator:
    """One `Struct` descriptor → its C++ struct declaration."""

    def __init__(self, struct: Struct, ctx: FileContext) -> None:
        self._struct = struct
        self._ctx = ctx
        self._nested: frozenset[str] = frozenset(
            e.name for e in struct.nested_enums
        )

    def emit(self, p: Printer) -> None:
        s = self._struct
        rendered_fields: list[tuple[str, str]] = []
        for f in s.fields:
            (version,) = f.versions
            ctype = (
                cpp_type(version.type, self._ctx, self._nested)
                if version.type is not None
                else None
            )
            if ctype is None:
                p(f"struct {s.name} {{}};")
                return
            rendered_fields.append((ctype, f.name))

        p(f"struct {s.name} {{")
        for e in s.nested_enums:
            p(f"    enum class {e.name} : int {{")
            for v in e.values:
                p(f"        {camel(v.name)} = {v.number},")
            p("    };")
            p()
        if s.packet_id is not None:
            p(f"    static constexpr int Id = {s.packet_id};")
        for ctype, fname in rendered_fields:
            p(f"    {ctype} {fname};")
        p("};")
