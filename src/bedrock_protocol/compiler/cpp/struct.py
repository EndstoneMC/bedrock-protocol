"""`StructGenerator` — emits a `struct Name { ... };` block.

The body holds, in order: nested type declarations (each followed by a
blank line), `static constexpr` constants (e.g. packet `Id`), and the
field declarations. protoc analog: `compiler/cpp/cpp_message.{h,cc}`.
"""

from __future__ import annotations

from ...descriptor import Enum, Struct
from .enum import EnumGenerator
from .field import FileContext, cpp_type
from .names import snapshot_namespace
from .printer import Printer


class StructGenerator:
    """One `Struct` descriptor → its C++ struct declaration.

    `nested_anchor` is the snapshot whose namespace owns the canonical
    nested-type definitions for this struct. When set, every nested type
    in the body becomes `using Name = vN::Owner::Name;` instead of a fresh
    definition, so a packet's nested types survive as a single C++ type
    across every snapshot of the outer struct. Today the only nesting
    shape is an `IntEnum`; nested structs / aliases plug into the same
    anchor when they land.
    """

    def __init__(
        self,
        struct: Struct,
        ctx: FileContext,
        *,
        nested_anchor: int | None = None,
    ) -> None:
        self._struct = struct
        self._ctx = ctx
        self._anchor = nested_anchor
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
        with p.indented(1):
            for e in s.nested_enums:
                self._emit_nested_enum(p, e)
                p()
            if s.packet_id is not None:
                p(f"static constexpr int Id = {s.packet_id};")
            for ctype, fname in rendered_fields:
                p(f"{ctype} {fname};")
        p("};")

    def _emit_nested_enum(self, p: Printer, e: Enum) -> None:
        """Alias `e` from the anchor snapshot or fall through to the full
        body. The body is `EnumGenerator` again -- there's only one place
        in the codebase that knows how to format an enum value line."""
        if self._anchor is not None:
            ns = snapshot_namespace(self._anchor)
            p(f"using {e.name} = {ns}::{self._struct.name}::{e.name};")
        else:
            EnumGenerator(e).emit(p)
