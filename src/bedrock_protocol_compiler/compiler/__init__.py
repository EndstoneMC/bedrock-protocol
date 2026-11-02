"""Frontend + backend dispatch — protoc analog of `compiler/`.

The pipeline:

    Importer(SourceTree(import_paths)).load_all(sources) ─► FileSet   (File protos)
                                                          │
                              DescriptorPool(file_set).build_file(name) ─► ResolvedFile
                                                          │
                                  registry.GENERATORS[name]() ─► CodeGenerator
                                                          │
                                  .generate(resolved, GeneratorContext)
"""

from .code_generator import CodeGenerator, FilesystemContext, GeneratorContext
from .descriptor_pool import DescriptorPool
from .importer import Importer, SourceTree
from .registry import GENERATORS

__all__ = [
    "CodeGenerator",
    "DescriptorPool",
    "FilesystemContext",
    "GENERATORS",
    "GeneratorContext",
    "Importer",
    "SourceTree",
]
