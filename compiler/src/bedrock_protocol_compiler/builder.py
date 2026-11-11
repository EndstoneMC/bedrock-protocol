import ast
import builtins
import enum
import inspect
import keyword
import math
import typing
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import TypeAliasType

from bedrock_protocol_compiler import dsl
from bedrock_protocol_compiler.descriptor import (
    Alias,
    AliasRef,
    Array,
    Binary,
    Bitset,
    Builtin,
    BuiltinRef,
    CompilerError,
    Enum,
    EnumDeclaration,
    EnumRef,
    Family,
    Field,
    Int,
    List,
    Literal,
    Map,
    Member,
    MemberRef,
    Module,
    Optional,
    Package,
    Primitive,
    Range,
    Struct,
    StructDeclaration,
    StructRef,
    Type,
    Variant,
)

STDLIB_MODULES = ("enum", "typing", "uuid")
FOREIGN_MODULES = (*STDLIB_MODULES, "bedrock_protocol_compiler.dsl")
ENUM_UNDERLYING = ("bool", "int8", "uint8", "int16", "uint16", "int32", "uint32")
LIST_PREFIXES = ("uint32", "uint16", "varint32")
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
class PendingEnum:
    source: Source
    scope: Scope
    node: ast.ClassDef
    enum: Enum


@dataclass
class PendingAlias:
    source: Source
    node: ast.TypeAlias
    alias: Alias


def error(source: Source, node: ast.stmt | ast.expr | ast.alias | ast.keyword, name: str, reason: str) -> CompilerError:
    return CompilerError(f"{source.path}:{node.lineno}:{node.col_offset + 1}: {name}: {reason}")


def literal[T](source: Source, node: ast.expr, kind: type[T], name: str) -> T:
    try:
        parsed = ast.literal_eval(node)
    except (ValueError, TypeError):
        parsed = None
    if type(parsed) is not kind:
        raise error(source, node, name, f"is not a literal {kind.__name__}")
    if parsed == "":
        raise error(source, node, name, "is an empty string")
    return parsed


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
        self.enums: list[PendingEnum] = []
        self.aliases: list[PendingAlias] = []

    def build(self) -> Package:
        versions = self.declare_init(self.init)
        for source in self.sources.values():
            self.declare_module(source)
        for source in self.sources.values():
            self.bind_family_imports(source)
        for pending_alias in self.aliases:
            self.build_alias(pending_alias)
        for pending_enum in self.enums:
            self.build_enum(pending_enum)
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
                    except (ValueError, TypeError):
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
        if node.keywords:
            raise error(source, node, node.name, "keywords are not supported")
        if node.type_params:
            raise error(source, node, node.name, "type parameters are not allowed")
        kinds: list[object] = []
        packet_id = None
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                function = self.resolve(source, scope, decorator.func)
                if function is not dsl.packet and function is not dsl.type:
                    raise error(source, decorator, node.name, DECORATOR_ERROR)
                arguments = self.bind(source, decorator, function, ("id",))
                if function is dsl.packet:
                    packet_id = literal(source, arguments["id"], int, "packet")
            else:
                function = self.resolve(source, scope, decorator)
                if function is not dsl.builtin:
                    raise error(source, decorator, node.name, DECORATOR_ERROR)
            kinds.append(function)
        if len(kinds) > 1:
            raise error(source, node, node.name, "takes only one of packet, type and builtin")
        if node.bases and kinds not in ([], [dsl.type]):
            raise error(source, node, node.name, "an enum takes no decorator but type")
        if kinds == [dsl.builtin]:
            if owner is not None:
                raise error(source, node, node.name, "a builtin is declared at the top of a module")
            if any(not isinstance(statement, ast.Pass) for statement in without_docstring(node.body)):
                raise error(source, node, node.name, "a builtin has no body")
            self.declare_family(source, node, Builtin(node.name, source.stem))
            return
        family: Struct | Enum = (
            Enum(node.name, owner, source.stem) if node.bases else Struct(node.name, owner, source.stem, packet_id)
        )
        if owner is None:
            self.declare_family(source, node, family)
        else:
            owner.nested.append(family)
            self.add(source, scope, node, node.name, family)
        if isinstance(family, Enum):
            self.enums.append(PendingEnum(source, scope, node, family))
            return
        inner = Scope(scope)
        self.scopes[family] = inner
        for statement in node.body:
            if isinstance(statement, ast.ClassDef):
                self.declare_class(source, inner, statement, family)
        self.structs.append(PendingStruct(source, node, family))

    def build_enum(self, pending: PendingEnum) -> None:
        source = pending.source
        node = pending.node
        if len(node.bases) > 2:
            raise error(source, node, node.name, "takes an enum base and at most an underlying type")
        if self.resolve(source, pending.scope, node.bases[0]) not in (enum.IntEnum, enum.Enum):
            raise error(source, node.bases[0], node.name, "is not IntEnum or Enum")
        underlying = None
        if len(node.bases) == 2:
            base = self.type_of(source, pending.scope, node.bases[1])
            if not (isinstance(base, Primitive) and base.name in ENUM_UNDERLYING):
                raise error(source, node.bases[1], node.name, "is not an enum underlying type")
            underlying = base
        members: list[Member] = []
        for statement in without_docstring(node.body):
            if not (
                isinstance(statement, ast.Assign)
                and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
            ):
                raise error(source, statement, pending.enum.name, "holds only members and a docstring")
            name = statement.targets[0].id
            expression = statement.value
            function = (
                self.resolve(source, pending.scope, expression.func) if isinstance(expression, ast.Call) else None
            )
            wire_name = name.replace("_", "")
            derived = "".join(part[:1].upper() + part[1:].lower() for part in name.split("_"))
            cpp_name = derived
            since = None
            until = None
            value: Int | MemberRef | Binary | None
            if isinstance(expression, ast.Tuple):
                if len(expression.elts) != 2:
                    raise error(source, expression, name, "a pair is a value and a wire name")
                wire_name = literal(source, expression.elts[1], str, name)
                value = Int(literal(source, expression.elts[0], int, name))
            elif isinstance(expression, ast.Call) and function is dsl.value:
                arguments = self.bind(source, expression, dsl.value, ("v", "name", "cpp_name", "since", "until"))
                if "name" in arguments:
                    wire_name = literal(source, arguments["name"], str, name)
                if "cpp_name" in arguments:
                    cpp_name = literal(source, arguments["cpp_name"], str, name)
                    if cpp_name.lower() != derived.lower():
                        raise error(
                            source, expression, name, f"cpp_name {cpp_name!r} is not a case variant of {derived!r}"
                        )
                if "since" in arguments:
                    since = literal(source, arguments["since"], int, name)
                if "until" in arguments:
                    until = literal(source, arguments["until"], int, name)
                value = Int(literal(source, arguments["v"], int, name)) if "v" in arguments else None
            elif (
                isinstance(expression, ast.Call)
                and function is enum.auto
                and not expression.args
                and not expression.keywords
            ):
                value = None
            elif isinstance(expression, ast.Name | ast.BinOp):
                offset = None
                if isinstance(expression, ast.BinOp):
                    if not (isinstance(expression.op, ast.Sub) and isinstance(expression.left, ast.Name)):
                        raise error(source, expression, name, "is not a member minus an integer")
                    offset = literal(source, expression.right, int, name)
                    expression = expression.left
                if not any(member.name == expression.id for member in members):
                    raise error(source, expression, name, f"{expression.id} is not a member declared above it")
                value = MemberRef(pending.enum, expression.id)
                if offset is not None:
                    value = Binary("-", value, Int(offset))
            else:
                value = Int(literal(source, expression, int, name))
            wire_name = wire_name.lower()
            for earlier in members:
                if earlier.name == name and max(earlier.range.since or 0, since or 0) < min(
                    earlier.range.until or math.inf, until or math.inf
                ):
                    raise error(source, statement, name, "is declared twice over overlapping versions")
            members.append(Member(name, value, Range(since, until), cpp_name, wire_name))
        if not members:
            raise error(source, node, pending.enum.name, "has no members")
        pending.enum.declarations.append(EnumDeclaration(underlying, tuple(members)))

    def build_alias(self, pending: PendingAlias) -> None:
        if pending.node.type_params:
            raise error(pending.source, pending.node, pending.alias.name, "type parameters are not allowed")
        target = self.type_of(pending.source, pending.source.scope, pending.node.value)
        if not isinstance(target, Primitive | Variant):
            raise error(pending.source, pending.node.value, pending.alias.name, "is not a primitive or a union")
        pending.alias.target = target

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
                arguments = self.bind(source, call, dsl.field, ("prefix",))
            field_type = self.type_of(source, scope, statement.annotation)
            if call is not None and "prefix" in arguments:
                prefix = self.type_of(source, scope, arguments["prefix"])
                if not isinstance(field_type, List):
                    raise error(source, call, name, "prefix is given to something other than a list")
                if not (isinstance(prefix, Primitive) and prefix.name in LIST_PREFIXES):
                    raise error(source, arguments["prefix"], name, "prefix is not uint32, uint16 or varint32")
                field_type = replace(field_type, prefix=prefix)
            fields.append(Field(name, field_type))
        pending.struct.declarations.append(StructDeclaration(tuple(fields)))

    def bind(
        self,
        source: Source,
        call: ast.Call,
        function: Callable[..., object],
        read: tuple[str, ...],
    ) -> dict[str, ast.expr]:
        name = function.__name__
        if any(isinstance(arg, ast.Starred) for arg in call.args) or any(kw.arg is None for kw in call.keywords):
            raise error(source, call, name, "takes its arguments written out")
        names = [kw.arg for kw in call.keywords]
        for kw in call.keywords:
            if names.count(kw.arg) > 1:
                raise error(source, kw, str(kw.arg), "is repeated")
        try:
            bound = inspect.signature(function).bind(*call.args, **{kw.arg: kw.value for kw in call.keywords if kw.arg})
        except TypeError as reason:
            raise error(source, call, name, str(reason)) from None
        unread = [argument for argument in bound.arguments if argument not in read]
        if unread:
            raise error(source, call, name, f"{unread[0]} is not supported yet")
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
        operands: list[ast.expr] | None = None
        pipe = False
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            pipe = True
            operands = [node.right]
            left = node.left
            while isinstance(left, ast.BinOp) and isinstance(left.op, ast.BitOr):
                operands.insert(0, left.right)
                left = left.left
            operands.insert(0, left)
        elif isinstance(node, ast.Subscript):
            container = self.resolve(source, scope, node.value)
            arguments = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
            if container is typing.Union and len(arguments) > 1:
                operands = arguments
            elif container is list and len(arguments) == 1:
                return List(self.type_of(source, scope, arguments[0]), None)
            elif container is dict and len(arguments) == 2:
                return Map(self.type_of(source, scope, arguments[0]), self.type_of(source, scope, arguments[1]))
            elif container is dsl.array and len(arguments) == 2:
                return Array(self.type_of(source, scope, arguments[0]), literal(source, arguments[1], int, "array"))
            elif container is dsl.bitset and len(arguments) == 1:
                return Bitset(self.member_of(source, scope, arguments[0]))
            elif container is typing.Literal and len(arguments) == 1:
                if isinstance(arguments[0], ast.Constant) and isinstance(arguments[0].value, bool | str):
                    return Literal(arguments[0].value)
                return Literal(self.member_of(source, scope, arguments[0]))
            else:
                raise error(source, node, ast.unparse(node), "is not a type with these arguments")
        if operands is not None:
            cases = [
                None
                if isinstance(operand, ast.Constant) and operand.value is None
                else self.type_of(source, scope, operand)
                for operand in operands
            ]
            if pipe and len(cases) == 2 and cases[0] is not None and cases[1] is None:
                return Optional(cases[0])
            return Variant(tuple(cases))
        if not isinstance(node, ast.Name | ast.Attribute):
            raise error(source, node, ast.unparse(node), "is not supported yet")
        target = self.resolve(source, scope, node)
        if isinstance(target, TypeAliasType | type) and target in PRIMITIVES:
            return Primitive(PRIMITIVES[target])
        if target is uuid.UUID:
            return BuiltinRef(UUID)
        if isinstance(target, Struct):
            return StructRef(target)
        if isinstance(target, Enum):
            return EnumRef(target)
        if isinstance(target, Alias):
            if target.target is None:
                raise error(source, node, ast.unparse(node), "is used before it is built")
            return target.target if isinstance(target.target, Variant) else AliasRef(target)
        if isinstance(target, Builtin):
            return BuiltinRef(target)
        raise error(source, node, ast.unparse(node), "is not a type")

    def member_of(self, source: Source, scope: Scope, node: ast.expr) -> MemberRef:
        owner = self.resolve(source, scope, node.value) if isinstance(node, ast.Attribute) else None
        if not (
            isinstance(node, ast.Attribute)
            and isinstance(owner, Enum)
            and any(member.name == node.attr for declaration in owner.declarations for member in declaration.members)
        ):
            raise error(source, node, ast.unparse(node), "is not an enum member")
        return MemberRef(owner, node.attr)
