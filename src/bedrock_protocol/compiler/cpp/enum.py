"""`EnumGenerator` — emits one `enum class Name : int { ... };` block.

protoc analog: `compiler/cpp/cpp_enum.{h,cc}`.
"""

from __future__ import annotations

from ...descriptor import Enum
from .names import camel
from .printer import Printer


class EnumGenerator:
    """One `Enum` descriptor → its C++ enum declaration."""

    def __init__(self, enum: Enum) -> None:
        self._enum = enum

    def emit(self, p: Printer) -> None:
        p(f"enum class {self._enum.name} : int {{")
        for v in self._enum.values:
            attr = " [[deprecated]]" if v.deprecated else ""
            p(f"    {camel(v.name)}{attr} = {v.number},")
        p("};")
