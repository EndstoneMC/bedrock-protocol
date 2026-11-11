import re
import textwrap
from collections.abc import Callable, Iterator
from contextlib import contextmanager

INDENT = "    "
MARKER = re.compile(r"\$(\w+)\$")

class Printer:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.prefix = ""

    @property
    def text(self) -> str:
        return "".join(f"{line}\n" for line in self.lines)

    @contextmanager
    def indent(self) -> Iterator[None]:
        outer = self.prefix
        self.prefix += INDENT
        yield
        self.prefix = outer

    def emit(self, template: str, **variables: str | int | Callable[[], None]) -> None:
        for line in textwrap.dedent(template).removeprefix("\n").removesuffix("\n").split("\n"):
            body = line.lstrip(" ")
            whole_line = MARKER.fullmatch(body)
            body_writer = variables.get(whole_line[1]) if whole_line else None
            if callable(body_writer):
                outer = self.prefix
                self.prefix += line[: len(line) - len(body)]
                body_writer()
                self.prefix = outer
                continue
            for name in MARKER.findall(line):
                if name not in variables:
                    raise ValueError(f"${name}$: no such variable")
                if callable(variables[name]):
                    raise ValueError(f"${name}$: a callable must be alone on its line")
            filled = MARKER.sub(lambda marker: str(variables[marker[1]]), line)
            self.lines.append(f"{self.prefix}{filled}".rstrip())
