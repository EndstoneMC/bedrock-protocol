"""Backend registry — protoc analog of `RegisterGenerator` calls in the CLI.

The CLI accepts `--language NAME` for any name in `GENERATORS.keys()`.
Adding a new backend is one entry in this dict.
"""

from __future__ import annotations

from typing import Callable

from .code_generator import CodeGenerator
from .cpp import CppGenerator

GENERATORS: dict[str, Callable[[], CodeGenerator]] = {
    "cpp": CppGenerator,
}
