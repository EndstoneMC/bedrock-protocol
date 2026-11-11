import ast
import builtins
import inspect
import keyword
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import TypeAliasType

from bedrock_protocol_compiler import dsl
from bedrock_protocol_compiler.descriptor import (
    Alias,
    AliasRef,
    Builtin,
    BuiltinRef,
    CompilerError,
    Family,
    Field,
    Module,
    Package,
    Primitive,
    Struct,
    StructDeclaration,
    StructRef,
    Type,
)

STDLIB_MODULES = ("enum", "typing", "uuid")
FOREIGN_MODULES = (*STDLIB_MODULES, "bedrock_protocol_compiler.dsl")
DECORATOR_ERROR = "is decorated with something other than a bare builtin or a called packet or type"
UUID = Builtin("UUID", "uuid")
PRIMITIVES: dict[object, str] = {
    **{alias: alias.__name__ for alias in vars(dsl).values() if isinstance(alias, TypeAliasType)},
    **{primitive: primitive.__name__ for primitive in (bool, float, str, bytes)},
}


class Scope:
    def __init__(self, parent: "Scope | None") -> None:
        self.parent = parent
        self.names: dict[str, object] = {}

    def lookup(self, name: str) -> object | None:
        scope: Scope | None = self
        while scope is not None:
            if name in scope.names:
                return scope.names[name]
            scope = scope.parent
        return getattr(builtins, name, None)


@dataclass
class Source:
    stem: str
    path: str
    tree: ast.Module
    scope: Scope
    package: str = ""
    families: dict[str, Family] = field(default_factory=dict)
    family_imports: list[ast.ImportFrom] = field(default_factory=list)


@dataclass
class PendingStruct:
    source: Source
    node: ast.ClassDef
    struct: Struct


@dataclass
class PendingAlias:
    source: Source
    node: ast.TypeAlias
    alias: Alias


def error(source: Source, node: ast.stmt | ast.expr | ast.alias | ast.keyword, name: str, reason: str) -> CompilerError:
    return CompilerError(f"{source.path}:{node.lineno}:{node.col_offset + 1}: {name}: {reason}")


def without_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    first = body[0] if body else None
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
        return body[1:]
    return body


def build(package_dir: Path) -> Package:
    return Builder(package_dir).build()


class Builder:
    def __init__(self, package_dir: Path) -> None:
        self.name = package_dir.name
        self.sources: dict[str, Source] = {}
        for path in sorted(package_dir.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            self.sources[path.stem] = Source(path.stem, str(path), tree, Scope(None))
        if "__init__" not in self.sources:
            raise CompilerError(f"{package_dir}: __init__.py: missing")
        self.init = self.sources.pop("__init__")
        self.scopes: dict[Struct, Scope] = {}
        self.declared: dict[str, Family] = {}
        self.structs: list[PendingStruct] = []
        self.aliases: list[PendingAlias] = []

    def build(self) -> Package:
        versions = self.declare_init(self.init)
        for source in self.sources.values():
            self.declare_module(source)
        for source in self.sources.values():
            self.bind_family_imports(source)
        for pending_alias in self.aliases:
            self.build_alias(pending_alias)
        for pending_struct in self.structs:
            self.build_struct(pending_struct)
        modules = tuple(
            Module(source.stem, source.package, tuple(source.families.values())) for source in self.sources.values()
        )
        return Package(versions, modules)

    def declare_init(self, source: Source) -> tuple[int, ...]:
        versions: tuple[int, ...] | None = None
        for statement in without_docstring(source.tree.body):
            match statement:
                case ast.ImportFrom(module=str() as module) if module.startswith(f"{self.name}."):
                    raise error(source, statement, module, "is not importable from __init__")
                case ast.Import() | ast.ImportFrom():
                    self.bind_import(source, statement)
                case ast.Assign(targets=[ast.Name(id="versions")], value=value):
                    if versions is not None:
                        raise error(source, statement, "versions", "is declared twice")
                    try:
                        parsed = ast.literal_eval(value)
                    except ValueError:
                        parsed = None
                    if not (
                        isinstance(parsed, tuple)
                        and parsed
                        and all(type(version) is int for version in parsed)
                        and list(parsed) == sorted(set(parsed))
                    ):
                        raise error(source, statement, "versions", "is not a tuple of ascending integers")
                    versions = parsed
                case _:
                    raise error(source, statement, "module", "holds only imports, a docstring and versions")
        if versions is None:
            raise CompilerError(f"{source.path}: versions: missing")
        return versions

    def declare_module(self, source: Source) -> None:
        for statement in without_docstring(source.tree.body):
            match statement:
                case ast.Import() | ast.ImportFrom():
                    self.bind_import(source, statement)
                case ast.ClassDef():
                    self.declare_class(source, source.scope, statement, None)
                case ast.TypeAlias():
                    alias = Alias(statement.name.id, source.stem)
                    self.declare_family(source, statement, alias)
                    self.aliases.append(PendingAlias(source, statement, alias))
                case ast.Assign(targets=[ast.Name(id="package")], value=ast.Constant(value=str() as package)):
                    if source.package:
                        raise error(source, statement, "package", "is declared twice")
                    source.package = package
                case _:
                    raise error(
                        source,
                        statement,
                        "module",
                        "holds only imports, classes, type aliases, a docstring and package",
                    )
        if not source.package:
            raise CompilerError(f"{source.path}: package: missing")

    def add(self, source: Source, scope: Scope, node: ast.stmt | ast.alias, name: str, value: object) -> None:
        if name in scope.names:
            raise error(source, node, name, "is already declared")
        scope.names[name] = value

    def declare_family(self, source: Source, node: ast.stmt, family: Family) -> None:
        if family.name in self.declared:
            raise error(source, node, family.name, "is already declared")
        self.add(source, source.scope, node, family.name, family)
        self.declared[family.name] = family
        source.families[family.name] = family

    def bind_import(self, source: Source, statement: ast.Import | ast.ImportFrom) -> None:
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                if alias.name not in STDLIB_MODULES:
                    raise error(source, alias, alias.name, "is not an importable module")
                self.add(source, source.scope, statement, alias.asname or alias.name, import_module(alias.name))
            return
        module = statement.module or ""
        in_package = module == self.name or module.startswith(f"{self.name}.")
        if statement.level or not (module in FOREIGN_MODULES or in_package):
            raise error(source, statement, "." * statement.level + module, "is not an importable module")
        if module != self.name and in_package:
            source.family_imports.append(statement)
            return
        for alias in statement.names:
            if module == self.name:
                imported = self.init.scope.names.get(alias.name)
            else:
                imported = getattr(import_module(module), alias.name, None)
            if imported is None:
                raise error(source, alias, alias.name, f"is not exported by {module}")
            self.add(source, source.scope, statement, alias.asname or alias.name, imported)

    def bind_family_imports(self, source: Source) -> None:
        for statement in source.family_imports:
            module = self.sources.get((statement.module or "").removeprefix(f"{self.name}."))
            for alias in statement.names:
                family = module.families.get(alias.name) if module else None
                if family is None:
                    raise error(source, alias, alias.name, f"is not declared in {statement.module}")
                self.add(source, source.scope, statement, alias.asname or alias.name, family)

    def declare_class(self, source: Source, scope: Scope, node: ast.ClassDef, owner: Struct | None) -> None:
        if node.bases or node.keywords:
            raise error(source, node, node.name, "bases are not supported yet")
        kinds: list[object] = []
        packet_id = None
        for decorator in node.decorator_list:
            arguments: dict[str, ast.expr] = {}
            if isinstance(decorator, ast.Call):
                function = self.resolve(source, scope, decorator.func)
                if not (callable(function) and (function is dsl.packet or function is dsl.type)):
                    raise error(source, decorator, node.name, DECORATOR_ERROR)
                arguments = self.bind(source, decorator, function, decorator.args, decorator.keywords, ("id",))
            else:
                function = self.resolve(source, scope, decorator)
                if function is not dsl.builtin:
                    raise error(source, decorator, node.name, DECORATOR_ERROR)
            if "id" in arguments:
                try:
                    packet_id = ast.literal_eval(arguments["id"])
                except ValueError:
                    packet_id = None
                if type(packet_id) is not int:
                    raise error(source, decorator, "packet", "id is not an integer literal")
            kinds.append(function)
        if len(kinds) > 1:
            raise error(source, node, node.name, "takes only one of packet, type and builtin")
        if kinds == [dsl.builtin]:
            if owner is not None:
                raise error(source, node, node.name, "a builtin is declared at the top of a module")
            if any(not isinstance(statement, ast.Pass) for statement in without_docstring(node.body)):
                raise error(source, node, node.name, "a builtin has no body")
            self.declare_family(source, node, Builtin(node.name, source.stem))
            return
        struct = Struct(node.name, owner, source.stem, packet_id)
        inner = Scope(scope)
        self.scopes[struct] = inner
        if owner is None:
            self.declare_family(source, node, struct)
        else:
            owner.nested.append(struct)
            self.add(source, scope, node, node.name, struct)
        for statement in node.body:
            if isinstance(statement, ast.ClassDef):
                self.declare_class(source, inner, statement, struct)
        self.structs.append(PendingStruct(source, node, struct))

    def build_alias(self, pending: PendingAlias) -> None:
        if pending.node.type_params:
            raise error(pending.source, pending.node, pending.alias.name, "type parameters are not allowed")
        primitive = self.type_of(pending.source, pending.source.scope, pending.node.value)
        if not isinstance(primitive, Primitive):
            raise error(pending.source, pending.node.value, pending.alias.name, "is not a primitive")
        pending.alias.primitive = primitive

    def build_struct(self, pending: PendingStruct) -> None:
        source = pending.source
        scope = self.scopes[pending.struct]
        fields: list[Field] = []
        for statement in without_docstring(pending.node.body):
            if isinstance(statement, ast.Pass | ast.ClassDef):
                continue
            if isinstance(statement, ast.With):
                raise error(source, statement, pending.struct.name, "with blocks are not supported yet")
            if not (isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)):
                raise error(
                    source, statement, pending.struct.name, "holds only fields, nested classes, a docstring and pass"
                )
            name = statement.target.id
            if name.endswith("_") and keyword.iskeyword(name[:-1]):
                name = name[:-1]
            if any(name == existing.name for existing in fields):
                raise error(source, statement, name, "is declared twice")
            call = statement.value
            if call is not None:
                if not (isinstance(call, ast.Call) and self.resolve(source, scope, call.func) is dsl.field):
                    raise error(source, call, name, "is assigned something other than field(...)")
                self.bind(source, call, dsl.field, call.args, call.keywords, ())
            fields.append(Field(name, self.type_of(source, scope, statement.annotation)))
        pending.struct.declarations.append(StructDeclaration(tuple(fields)))

    def bind(
        self,
        source: Source,
        node: ast.expr,
        function: Callable[..., object],
        args: Sequence[ast.expr],
        keywords: Sequence[ast.keyword],
        read: tuple[str, ...],
    ) -> dict[str, ast.expr]:
        name = function.__name__
        if any(isinstance(arg, ast.Starred) for arg in args) or any(kw.arg is None for kw in keywords):
            raise error(source, node, name, "takes its arguments written out")
        names = [kw.arg for kw in keywords]
        for kw in keywords:
            if names.count(kw.arg) > 1:
                raise error(source, kw, str(kw.arg), "is repeated")
        try:
            bound = inspect.signature(function).bind(*args, **{kw.arg: kw.value for kw in keywords if kw.arg})
        except TypeError as reason:
            raise error(source, node, name, str(reason)) from None
        unread = [argument for argument in bound.arguments if argument not in read]
        if unread:
            raise error(source, node, name, f"{unread[0]} is not supported yet")
        return bound.arguments

    def resolve(self, source: Source, scope: Scope, node: ast.expr) -> object:
        if isinstance(node, ast.Name):
            found = scope.lookup(node.id)
        elif isinstance(node, ast.Attribute):
            owner = self.resolve(source, scope, node.value)
            if isinstance(owner, Struct):
                found = self.scopes[owner].names.get(node.attr)
            else:
                found = getattr(owner, node.attr, None) if isinstance(owner, ModuleType) else None
        else:
            raise error(source, node, ast.unparse(node), "is not a name")
        if found is None:
            raise error(source, node, ast.unparse(node), "is not defined")
        return found

    def type_of(self, source: Source, scope: Scope, node: ast.expr) -> Type:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            raise error(source, node, node.value, "string annotations are not allowed")
        if not isinstance(node, ast.Name | ast.Attribute):
            raise error(source, node, ast.unparse(node), "is not supported yet")
        target = self.resolve(source, scope, node)
        if target in PRIMITIVES:
            return Primitive(PRIMITIVES[target])
        if target is uuid.UUID:
            return BuiltinRef(UUID)
        if isinstance(target, Struct):
            return StructRef(target)
        if isinstance(target, Alias):
            return AliasRef(target)
        if isinstance(target, Builtin):
            return BuiltinRef(target)
        raise error(source, node, ast.unparse(node), "is not a type")
