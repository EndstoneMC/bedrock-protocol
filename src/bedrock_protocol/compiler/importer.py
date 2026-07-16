"""Import driving + file access — protoc analog of `compiler/importer.{h,cc}`.

protoc keeps three jobs apart: a `SourceTree` opens files by name, a `Parser` turns
one file's syntax into a `FileDescriptorProto`, and an `Importer` decides which
files to open and drives the other two. This module holds the first and third.

The DSL has no `import` statement of its own, so `Importer` reads Python's: it
follows `from X.Y import ...` between modules, and additionally pulls in each
input's owning package (where `__version__` lives) and the `version` submodule
(which declares the compiler-owned `ProtocolVersion`), neither of which a schema
file necessarily names.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import griffe

from bedrock_protocol.descriptor import (
    PRIMITIVES,
    FileSet,
    PrimitiveAlias,
    PrimitiveType,
    TypeAlias,
)

from .parser import Parser, SymbolTable, enum_underlying_of, is_int_enum


class _DeclarationCollector(griffe.Extension):
    """Every `class` statement, in source order, grouped by module.

    griffe keeps members in a dict, so a type declared twice to model a wire
    reshape survives only as its last declaration -- silently. This hook fires per
    `ClassDef` once its body is attached, before that overwrite, so both shapes
    reach the parser."""

    def __init__(self) -> None:
        self.by_module: dict[str, list[griffe.Class]] = {}

    def on_class_members(self, *, node: object, cls: griffe.Class, agent: object, **kwargs: object) -> None:
        parent = cls.parent
        if isinstance(parent, griffe.Module):
            self.by_module.setdefault(parent.path, []).append(cls)


class SourceTree:
    """Opens DSL modules by name — protoc's `SourceTree` / `DiskSourceTree`.

    File access only: it maps a dotted module name onto a file under one of the
    `import_paths` (protoc's `--proto_path`) and hands back griffe's parse of it.
    What the modules mean is the `Parser`'s business; which of them to load is the
    `Importer`'s."""

    def __init__(self, import_paths: list[Path]) -> None:
        self._import_paths = [p.resolve() for p in import_paths]
        self._declarations: dict[str, list[griffe.Class]] = {}

    @property
    def import_paths(self) -> list[Path]:
        """The roots a module name is resolved against — protoc's `--proto_path`."""
        return self._import_paths

    def open(self, name: str, root: Path) -> griffe.Module:
        collector = _DeclarationCollector()
        module = cast(
            griffe.Module,
            griffe.load(
                name,
                search_paths=[str(root)],
                allow_inspection=False,
                extensions=griffe.Extensions(collector),
            ),
        )
        # A load may reach modules a previous one already covered; replace rather
        # than append so a module's declarations are never counted twice.
        self._declarations.update(collector.by_module)
        return module

    def declarations_of(self, module_name: str) -> list[list[griffe.Class]]:
        """The module's classes grouped by name, each group in source order. A
        group of more than one is a version-redeclared type."""
        groups: dict[str, list[griffe.Class]] = {}
        for cls in self._declarations.get(module_name, []):
            if cls.is_alias:
                continue
            groups.setdefault(cls.name, []).append(cls)
        return list(groups.values())

    def module_name_and_root(self, path: Path) -> tuple[str, Path]:
        path = path.resolve()
        for ip in self._import_paths:
            try:
                rel = path.relative_to(ip)
            except ValueError:
                continue
            return ".".join(rel.with_suffix("").parts), ip
        parent = path.parent
        name = f"{parent.name}.{path.stem}" if parent.name else path.stem
        return name, parent


class Importer:
    """Loads a schema and everything it reaches — protoc's `Importer`.

    Owns the cross-file symbol table: unlike protoc, whose parser records a type
    reference as a name string for `DescriptorBuilder` to resolve later, ours
    resolves references while parsing, so every module must be loaded and
    classified before any is parsed.
    """

    def __init__(self, source_tree: SourceTree) -> None:
        self._source_tree = source_tree

    def load_all(self, sources: tuple[Path, ...]) -> FileSet:
        """Load every source file plus its transitive imports, returning the
        complete `FileSet`. The order in `sources` is preserved in `outputs`."""
        griffe_modules: dict[str, griffe.Module] = {}
        stems: dict[str, str] = {}
        output_names: list[str] = []
        for src in sources:
            name, root = self._source_tree.module_name_and_root(src)
            griffe_modules[name] = self._source_tree.open(name, root)
            stems[name] = src.stem
            output_names.append(name)
        self._load_owning_packages(griffe_modules, output_names)
        self._load_version_module(griffe_modules, output_names)
        self._follow_imports(griffe_modules, output_names)
        symbols = self._classify(griffe_modules)
        parser = Parser(symbols)
        files = {
            name: parser.parse_file(
                name,
                mod,
                stems.get(name, name),
                set(griffe_modules),
                self._imports_of(mod),
                self._source_tree.declarations_of(name),
            )
            for name, mod in griffe_modules.items()
        }
        return FileSet(
            files=files,
            outputs=tuple(output_names),
            version=_dsl_version(griffe_modules),
        )

    def _load_owning_packages(self, loaded: dict[str, griffe.Module], seed: list[str]) -> None:
        """Load each input's parent package(s) so the DSL surface module is
        available even when the input has no `from <package> import ...` line
        (it is where `__version__` lives)."""
        for name in seed:
            parts = name.split(".")
            for cut in range(len(parts) - 1, 0, -1):
                parent = ".".join(parts[:cut])
                if parent in loaded:
                    continue
                for ip in self._source_tree.import_paths:
                    if ip.joinpath(*parts[:cut], "__init__.py").is_file():
                        loaded[parent] = self._source_tree.open(parent, ip)
                        break

    def _load_version_module(self, loaded: dict[str, griffe.Module], seed: list[str]) -> None:
        """Always load the DSL's `version` submodule (which declares the
        compiler-owned `ProtocolVersion` enum) so any file with versioned types
        can spell the typed `_<ProtocolVersion V>` selector without importing
        it. The enum stays DSL-owned; the import is just no longer boilerplate."""
        for name in seed:
            parts = name.split(".")
            for cut in range(len(parts) - 1, 0, -1):
                mod_name = ".".join(parts[:cut] + ["version"])
                if mod_name in loaded:
                    break
                for ip in self._source_tree.import_paths:
                    if ip.joinpath(*parts[:cut], "version.py").is_file():
                        loaded[mod_name] = self._source_tree.open(mod_name, ip)
                        break
                else:
                    continue
                break

    def _follow_imports(self, loaded: dict[str, griffe.Module], seed: list[str]) -> None:
        pending = list(seed)
        while pending:
            for dep in self._imports_of(loaded[pending.pop()]):
                if dep in loaded:
                    continue
                parts = dep.split(".")
                for ip in self._source_tree.import_paths:
                    module = ip.joinpath(*parts).with_suffix(".py")
                    package = ip.joinpath(*parts, "__init__.py")
                    if module.is_file() or package.is_file():
                        loaded[dep] = self._source_tree.open(dep, ip)
                        pending.append(dep)
                        break

    @staticmethod
    def _imports_of(mod: griffe.Module) -> set[str]:
        """Source modules `mod`'s `from X.Y import ...` lines refer to. Names
        with a `_`-prefixed component (the DSL surface itself) are omitted."""
        out: set[str] = set()
        for member in mod.members.values():
            target = getattr(member, "target_path", None)
            if target is None or "." not in str(target):
                continue
            dep = str(target).rsplit(".", 1)[0]
            if not any(part.startswith("_") for part in dep.split(".")):
                out.add(dep)
        return out

    def _classify(self, loaded: dict[str, griffe.Module]) -> SymbolTable:
        enum_names: set[str] = set()
        enum_underlying: dict[str, PrimitiveType | None] = {}
        struct_names: set[str] = set()
        aliases_by_name: dict[str, PrimitiveAlias | TypeAlias] = {}
        primitive_aliases_by_module: dict[str, tuple[PrimitiveAlias, ...]] = {}
        type_aliases_by_module: dict[str, tuple[TypeAlias, ...]] = {}

        for mod_name in loaded:
            for decls in self._source_tree.declarations_of(mod_name):
                cls = decls[0]
                if is_int_enum(cls):
                    enum_names.add(cls.name)
                    enum_underlying[cls.name] = enum_underlying_of(cls)
                else:
                    struct_names.add(cls.name)

        # Alias pass — after classification, since an alias may reference any
        # class. Declaration order is the resolution order.
        for name, mod in loaded.items():
            primitives: list[PrimitiveAlias] = []
            others: list[TypeAlias] = []
            parser = Parser(
                SymbolTable(
                    enum_names=frozenset(enum_names),
                    enum_underlying=enum_underlying,
                    struct_names=frozenset(struct_names),
                    aliases_by_name=aliases_by_name,
                )
            )
            for attr_name, attr in list(mod.attributes.items()) + list(mod.type_aliases.items()):
                if attr_name == "package" or attr_name in PRIMITIVES or attr.value is None:
                    continue
                if getattr(attr, "is_alias", False):
                    continue
                alias = parser.parse_alias(attr_name, attr.value)
                if alias is None:
                    continue
                aliases_by_name[alias.name] = alias
                if isinstance(alias, PrimitiveAlias):
                    primitives.append(alias)
                else:
                    others.append(alias)
            primitive_aliases_by_module[name] = tuple(primitives)
            type_aliases_by_module[name] = tuple(others)

        return SymbolTable(
            enum_names=frozenset(enum_names),
            enum_underlying=enum_underlying,
            struct_names=frozenset(struct_names),
            aliases_by_name=aliases_by_name,
            primitive_aliases_by_module=primitive_aliases_by_module,
            type_aliases_by_module=type_aliases_by_module,
        )


def _dsl_version(loaded: dict[str, griffe.Module]) -> int | None:
    """Pull `__version__` off any loaded module that declares it -- in practice
    the DSL surface module (`protocol/__init__.py`). The single source for the
    protocol version this project targets; the CLI raises if it is missing."""
    for mod in loaded.values():
        attr = mod.attributes.get("__version__")
        if attr is None or attr.value is None:
            continue
        try:
            return int(str(attr.value))
        except ValueError:
            continue
    return None
