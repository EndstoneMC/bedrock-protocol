"""`StructGenerator` — emits a `struct Name { ... };` block.

The body holds, in order: nested type declarations (each followed by a
blank line), `static constexpr` constants (e.g. packet `Id`), and the
field declarations. protoc analog: `compiler/cpp/cpp_message.{h,cc}`.
"""

from __future__ import annotations

from ...descriptor import Struct
from .field import FileContext, cpp_type
from .names import camel, snapshot_namespace
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
        for e in s.nested_enums:
            self._emit_nested(p, e.name, lambda: self._emit_enum_body(p, e))
        if s.packet_id is not None:
            p(f"    static constexpr int Id = {s.packet_id};")
        for ctype, fname in rendered_fields:
            p(f"    {ctype} {fname};")
        p("};")

    def _emit_nested(self, p: Printer, name: str, body) -> None:
        """Either alias `name` from the anchor snapshot, or call `body` to
        emit the fresh definition. Followed by a blank line."""
        if self._anchor is not None:
            ns = snapshot_namespace(self._anchor)
            p(f"    using {name} = {ns}::{self._struct.name}::{name};")
        else:
            body()
        p()

    def _emit_enum_body(self, p: Printer, e) -> None:
        p(f"    enum class {e.name} : int {{")
        for v in e.values:
            attr = (
                f' [[deprecated("since v{v.deprecated}")]]'
                if v.deprecated is not None
                else ""
            )
            p(f"        {camel(v.name)}{attr} = {v.number},")
        p("    };")
