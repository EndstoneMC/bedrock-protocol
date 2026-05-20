"""Backend registry — protoc analog of `RegisterGenerator` calls in the CLI.

The CLI builds its `--out <name>=<dir>` choices from `GENERATORS.keys()`.
Adding a new backend is one entry in this dict.
"""

from __future__ import annotations

from typing import Callable

from .code_generator import CodeGenerator

GENERATORS: dict[str, Callable[[], CodeGenerator]] = {}


def register(name: str, factory: Callable[[], CodeGenerator]) -> None:
    GENERATORS[name] = factory


def lookup(name: str) -> CodeGenerator:
    factory = GENERATORS.get(name)
    if factory is None:
        raise KeyError(
            f"unknown backend {name!r}; known: {sorted(GENERATORS) or '(none registered)'}"
        )
    return factory()


# In-tree backends register themselves on import. Listed here (not via
# entry-points) because adding a backend means editing this repo anyway,
# and a flat dict keeps mypy honest.
def _register_builtin_backends() -> None:
    # Imported here to avoid an import cycle at module load.
    from ..compiler_cpp import CppGenerator

    register("cpp", CppGenerator)


_register_builtin_backends()
