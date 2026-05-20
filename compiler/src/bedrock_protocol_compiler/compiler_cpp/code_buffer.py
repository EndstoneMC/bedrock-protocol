"""Indentation-tracking line buffer for C++ method bodies."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator


class CodeBuffer:
    """Append-only sequence of C++ source lines with managed indentation.

    Bodies open two levels deep (inside `struct` then method body); `block`
    nests one more.
    """

    def __init__(self, base_depth: int = 2) -> None:
        self._lines: list[str] = []
        self._depth = base_depth

    def write(self, text: str = "") -> None:
        self._lines.append("    " * self._depth + text if text else "")

    __call__ = write

    @contextmanager
    def block(self, head: str = "") -> Iterator[None]:
        self.write(f"{head} {{" if head else "{")
        self._depth += 1
        try:
            yield
        finally:
            self._depth -= 1
        self.write("}")

    @property
    def lines(self) -> list[str]:
        return self._lines
