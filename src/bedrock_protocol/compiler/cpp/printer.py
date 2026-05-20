"""Indentation-tracking line buffer — analog of protoc's `io::Printer`.

`Printer` is the single place output text flows through. It tracks
indentation, opens / closes braced blocks, and produces a final string
terminated by a newline.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator


class Printer:
    """Append-only sequence of C++ source lines with managed indentation."""

    def __init__(self, base_depth: int = 0) -> None:
        self._lines: list[str] = []
        self._depth = base_depth

    def line(self, text: str = "") -> None:
        self._lines.append("    " * self._depth + text if text else "")

    __call__ = line

    @contextmanager
    def block(self, head: str = "") -> Iterator[None]:
        self.line(f"{head} {{" if head else "{")
        self._depth += 1
        try:
            yield
        finally:
            self._depth -= 1
        self.line("}")

    @contextmanager
    def indented(self, n: int = 1) -> Iterator[None]:
        """Push the indentation by `n` levels without emitting braces."""
        self._depth += n
        try:
            yield
        finally:
            self._depth -= n

    @property
    def lines(self) -> list[str]:
        return self._lines

    @property
    def text(self) -> str:
        """The joined output. Always ends with a single trailing newline."""
        return "\n".join(self._lines) + "\n"
