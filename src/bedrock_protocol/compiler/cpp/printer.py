"""Output text sink — analog of protoc's `io::Printer`.

`Print` substitutes `$name$` markers from a variable map (`$$` is a literal
`$`) and re-indents every line of a multi-line template at the current depth.
`Indent`/`Outdent` move that depth; `block()` is a convenience that brackets a
`{ ... }` region. All output flows through one `Printer`.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Mapping

_INDENT = "    "


class Printer:
    def __init__(self) -> None:
        self._out: list[str] = []
        self._depth = 0
        self._at_line_start = True

    # --- protoc-style API ---------------------------------------------------

    def print(self, *args: object) -> None:
        """`print(text)` or `print(vars, text)`. `$name$` markers in `text` are
        replaced from `vars`; `$$` emits a literal `$`."""
        if len(args) == 2 and isinstance(args[0], Mapping):
            variables, text = args[0], str(args[1])
        else:
            variables, text = {}, str(args[0]) if args else ""
        self._write(_substitute(text, variables))

    def indent(self) -> None:
        self._depth += 1

    def outdent(self) -> None:
        self._depth -= 1

    @contextmanager
    def block(self, head: str = "") -> Iterator[None]:
        self.print(f"{head} {{\n" if head else "{\n")
        self.indent()
        try:
            yield
        finally:
            self.outdent()
        self.print("}\n")

    @property
    def text(self) -> str:
        out = "".join(self._out)
        return out if out.endswith("\n") else out + "\n"

    # --- internals ----------------------------------------------------------

    def _write(self, text: str) -> None:
        for ch in text:
            if self._at_line_start and ch != "\n":
                self._out.append(_INDENT * self._depth)
                self._at_line_start = False
            self._out.append(ch)
            if ch == "\n":
                self._at_line_start = True


def _substitute(text: str, variables: Mapping[str, object]) -> str:
    out: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch != "$":
            out.append(ch)
            i += 1
            continue
        if i + 1 < len(text) and text[i + 1] == "$":
            out.append("$")
            i += 2
            continue
        end = text.index("$", i + 1)
        out.append(str(variables[text[i + 1 : end]]))
        i = end + 1
    return "".join(out)
