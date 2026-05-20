"""Frontend + backend dispatch — protoc analog of `compiler/`.

The pipeline:

    parser.SourceTree(import_paths).load(source) ─► FileDescriptor
                                                          │
                                  resolver.resolve(file, set) ─► ResolvedFileDescriptor
                                                          │
                                  registry.GENERATORS[name]() ─► CodeGenerator
                                                          │
                                  .generate(resolved, parameter, GeneratorContext)
"""

from .code_generator import CodeGenerator, GeneratorContext, FilesystemContext
from .parser import SourceTree
from .registry import GENERATORS
from .resolver import resolve, resolve_all

__all__ = [
    "CodeGenerator",
    "FilesystemContext",
    "GENERATORS",
    "GeneratorContext",
    "SourceTree",
    "resolve",
    "resolve_all",
]
