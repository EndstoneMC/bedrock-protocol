"""`CodeGenerator` ABC and `GeneratorContext` — protoc analog of
`compiler/code_generator.h`.

A backend implements `CodeGenerator.generate(resolved, parameter, context)`.
The `context` is the only way a backend writes output; it never touches the
filesystem directly. This mirrors protoc's `GeneratorContext::Open`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Protocol, TextIO, runtime_checkable

from ..descriptor import ResolvedFileDescriptor


@runtime_checkable
class GeneratorContext(Protocol):
    """The single chokepoint a backend writes through."""
    out_dir: Path

    @contextmanager
    def open(self, relative_path: str) -> Iterator[TextIO]:
        """Open `out_dir / relative_path` for writing UTF-8 text.
        Parent directories are created. The file is fully written on context exit.
        """
        ...

    def error(self, msg: str) -> None:
        """Record a backend-level diagnostic. The CLI raises after the
        full pipeline has run if any context recorded an error."""
        ...

    def verbose(self, msg: str) -> None:
        """Emit a verbose-mode line to the user. No-op when verbose is off."""
        ...


class CodeGenerator(ABC):
    """One language target. Subclasses register by adding an entry to
    `compiler.registry.GENERATORS`, and the CLI dispatches by name.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short id, e.g. `"cpp"`. Used by the CLI as `--language <name>`."""
        ...

    @abstractmethod
    def generate(
        self,
        resolved: ResolvedFileDescriptor,
        parameter: str,
        context: GeneratorContext,
    ) -> None:
        """Generate one input file's output. `parameter` is the joined
        `--opt KEY=VAL,...` payload (empty when none was given). The
        backend writes results through `context.open(relative_path)`.
        """
        ...

    def supported_features(self) -> int:
        """Bitmask reserved for future feature negotiation. Default 0."""
        return 0


class FilesystemContext:
    """Default `GeneratorContext`: writes directly under `out_dir`. The CLI
    uses this; tests can substitute their own implementation.
    """

    def __init__(self, out_dir: Path, *, verbose: bool = False) -> None:
        self.out_dir = out_dir
        self._verbose = verbose
        self._errors: list[str] = []

    @contextmanager
    def open(self, relative_path: str) -> Iterator[TextIO]:
        target = self.out_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="\n") as fh:
            yield fh
        if self._verbose:
            print(f"wrote {target}")

    def error(self, msg: str) -> None:
        self._errors.append(msg)

    def verbose(self, msg: str) -> None:
        if self._verbose:
            print(msg)

    @property
    def errors(self) -> tuple[str, ...]:
        return tuple(self._errors)
