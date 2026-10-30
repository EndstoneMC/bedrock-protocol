"""The selected schema closure, keyed by canonical C++ shape."""

from __future__ import annotations

from dataclasses import dataclass

from bedrock_protocol.compiler.cpp.file import FileGenerator, _nested_names
from bedrock_protocol.compiler.cpp.helpers import cpp_qualified, outermost
from bedrock_protocol.descriptor import (
    CompilerError,
    Enum,
    FieldType,
    PrimitiveAlias,
    ResolvedFile,
    Struct,
    TypeAlias,
)


@dataclass(frozen=True)
class Shape:
    name: str
    cpp: str
    declaration: Enum | Struct | PrimitiveAlias
    resolved: ResolvedFile
    snapshot: int | None


class Model:
    def __init__(self, resolved: ResolvedFile) -> None:
        self.file_set = resolved.pool.file_set
        self.versions = self.file_set.supported_versions
        self.files = {
            name: resolved.pool.build_file(name) for name, file in self.file_set.files.items() if file.package
        }
        self.generators = {name: FileGenerator(file) for name, file in self.files.items()}
        self.owners: dict[str, str] = {}
        self.declared_names = {"UUID"}
        for name, file in self.files.items():
            declarations: tuple[Struct | Enum | PrimitiveAlias | TypeAlias, ...] = (
                *file.file.structs,
                *file.file.enums,
                *file.file.primitive_aliases,
                *file.file.type_aliases,
            )
            for declaration in declarations:
                key = declaration.key if isinstance(declaration, (Struct, Enum)) else declaration.name
                self.owners[key] = name
                self.declared_names.add(key)
                if isinstance(declaration, Struct):
                    self.declared_names.update(_nested_names(declaration, declaration.key))
        self.shapes: dict[str, Shape] = {}
        self.aliases: dict[int, dict[str, str]] = {v: {} for v in self.versions}
        self.packets: dict[int, dict[int, str]] = {v: {} for v in self.versions}
        self._visited: set[tuple[int, str]] = set()
        for version in self.versions:
            for file in self.files.values():
                for decl in file.file.structs:
                    if decl.packet_id is None or self._declaration_at(file, decl.key, version) is None:
                        continue
                    self.packets[version][decl.packet_id] = self.visit(decl.key, version)
            for file in self.files.values():
                for alias in file.file.type_aliases:
                    references = alias.target.referenced
                    if references and references <= self.aliases[version].keys():
                        self.visit(alias.name, version)

    @staticmethod
    def _declaration_at(file: ResolvedFile, name: str, version: int) -> Enum | Struct | None:
        if file.is_versioned(name):
            snap = file.present_at(name, version)
            return (snap.enum or snap.struct) if snap else None
        decl = file.lookup(name)
        if decl and (decl.since is None or version >= decl.since) and (decl.until is None or version < decl.until):
            return decl
        return None

    def shape_at(self, name: str, version: int) -> Shape:
        root = outermost(name)
        file = self.files[self.owners[root]]
        assert file.file.package is not None
        gen = self.generators[file.file.name]
        aliases = {a.name: a for a in file.file.primitive_aliases}
        if name in aliases:
            return Shape(name, f"{file.file.package.replace('.', '::')}::{name}", aliases[name], file, None)
        snap = file.present_at(root, version) if file.is_versioned(root) else None
        decl = self._declaration_at(file, root, version)
        if decl is None:
            raise CompilerError(f"nanobind: {name} unavailable at {version}")
        concrete = snap.concrete if snap else None
        if name != root:
            # Reuse the C++ backend's nested alias plan, including unchanged
            # children under owners whose surrounding fields changed.
            candidates = [v for v in gen._nested_views(root) if v[1] == name]
            eligible = [v for v in candidates if v[3] is None or v[3] <= version]
            if not eligible:
                raise CompilerError(f"nanobind: no nested shape for {name} at {version}")
            inner, _, qualified, concrete = eligible[-1]
            return Shape(name, f"{file.file.package.replace('.', '::')}::{qualified}", inner, file, concrete)
        qualified = cpp_qualified(root, concrete)
        return Shape(name, f"{file.file.package.replace('.', '::')}::{qualified}", decl, file, concrete)

    def visit(self, name: str, version: int) -> str:
        if name == "UUID":
            self.aliases[version][name] = "builtin:UUID"
            return "builtin:UUID"
        key = (version, name)
        if key in self._visited:
            return self.aliases[version][name]
        self._visited.add(key)
        root = outermost(name)
        if root not in self.owners:
            raise CompilerError(f"nanobind: missing declaration for {name}")
        file = self.files[self.owners[root]]
        alias = next((a for a in file.file.type_aliases if a.name == name), None)
        if alias is not None:
            # Structural aliases are resolved by their existing FieldType tree.
            self.aliases[version][name] = "alias:" + name
            self.visit_type(alias.target, version)
            return self.aliases[version][name]
        shape = self.shape_at(name, version)
        if isinstance(shape.declaration, Struct) and shape.declaration.builtin:
            self.aliases[version][name] = "builtin:" + name
            return self.aliases[version][name]
        self.aliases[version][name] = shape.cpp
        self.shapes.setdefault(shape.cpp, shape)
        if name != root:
            self.visit(root, version)
        if isinstance(shape.declaration, Struct):
            for field in shape.declaration.fields:
                if field.type_single is None:
                    raise CompilerError(f"nanobind: unresolved field {name}.{field.name}")
                self.visit_type(field.type_single, version, name)
            for nested in shape.declaration.nested:
                self.visit(f"{name}.{nested.name}", version)
        return shape.cpp

    def visit_type(self, field: FieldType, version: int, owner: str = "") -> None:
        for name in sorted(field.referenced):
            self.visit(self.resolve(name, owner), version)

    def resolve(self, name: str, owner: str = "") -> str:
        if name in self.declared_names:
            return name
        while owner:
            candidate = f"{owner}.{name}"
            if candidate in self.declared_names:
                return candidate
            owner = owner.rpartition(".")[0]
        raise CompilerError(f"nanobind: missing declaration for {name}")

    def type_alias(self, name: str) -> TypeAlias:
        file = self.files[self.owners[name]]
        return next(a for a in file.file.type_aliases if a.name == name)
