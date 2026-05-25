"""`EnumGenerator` — emits one `enum class Name : int { ... };` block.

protoc analog: `compiler/cpp/cpp_enum.{h,cc}`.
"""

from __future__ import annotations

from ...descriptor import Enum
from .names import camel
from .printer import Printer


class EnumGenerator:
    """One `Enum` descriptor → its C++ enum declaration. Emits at the
    Printer's current depth, so a `with p.indented(...):` wrapper shifts
    the whole block deeper when the enum is nested inside another type."""

    def __init__(self, enum: Enum) -> None:
        self._enum = enum

    def emit(self, p: Printer) -> None:
        p(f"enum class {self._enum.name} : int {{")
        with p.indented(1):
            for v in self._enum.values:
                attr = f' [[deprecated("since v{v.deprecated}")]]' if v.deprecated is not None else ""
                p(f"{camel(v.name)}{attr} = {v.number},")
        p("};")
