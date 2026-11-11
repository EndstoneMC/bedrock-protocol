import ast
import builtins
import enum
import inspect
import typing
import uuid
from collections import Counter
from collections.abc import Callable, Iterator
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
    EnumName,
    EnumRef,
    Expression,
    Family,
    Field,
    Int,
    List,
    Literal,
    Map,
    Member,
    MemberRef,
    Module,
    Not,
    Optional,
    Package,
    Primitive,
    Range,
    Struct,
    StructDeclaration,
    StructRef,
    Test,
    Type,
    Variant,
)
from bedrock_protocol_compiler.lambdas import field_name, parse_count, parse_predicate, read_lambda

STDLIB_MODULES = ("enum", "typing", "uuid")
FOREIGN_MODULES = (*STDLIB_MODULES, "bedrock_protocol_compiler.dsl")
ENUM_UNDERLYING = ("bool", "int8", "uint8", "int16", "uint16", "int32", "uint32")
LIST_PREFIXES = ("uint32", "uint16", "varint32")
BYTE_ORDERED = ("int16", "uint16", "int32", "uint32", "int64", "uint64")
INTEGERS = ("int8", "uint8", *BYTE_ORDERED, "varint32", "varint64", "uvarint32", "uvarint64")
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
    order: list[Family] = field(default_factory=list)
    legacies: dict[str, tuple[ast.ClassDef, Struct | Enum]] = field(default_factory=dict)
    unions: dict[str, "UnionAlias"] = field(default_factory=dict)
    family_imports: list[ast.ImportFrom] = field(default_factory=list)


@dataclass
class PendingStruct:
    source: Source
    node: ast.ClassDef
    struct: Struct
    range: Range


@dataclass
class PendingEnum:
    source: Source
    scope: Scope
    node: ast.ClassDef
    enum: Enum
    range: Range


@dataclass(eq=False)
class UnionAlias:
    source: Source
    node: ast.TypeAlias


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


def rewire(node: Type, wire: str | None, endian: str | None) -> Type | None:
    match node:
        case Optional(element=element) | List(element=element):
            rewired = rewire(element, wire, endian)
            return None if rewired is None else replace(node, element=rewired)
        case Map(key=key, value=value):
            rewired_key = rewire(key, wire, endian)
            rewired_value = rewire(value, wire, endian)
            if (rewired_key is None) == (rewired_value is None):
                return None
            return Map(rewired_key or key, rewired_value or value)
        case EnumRef(enum=enum):
            if wire == "str":
                return None if endian else EnumName(enum)
            if wire is None or (endian and wire not in BYTE_ORDERED):
                return None
            return EnumRef(enum, wire, endian)
        case Primitive(name=name):
            if name not in INTEGERS or wire == "str" or (endian and (wire or name) not in BYTE_ORDERED):
                return None
            return replace(node, wire=wire, endian=endian)
        case AliasRef(alias=alias):
            if alias.primitive.name not in INTEGERS or wire == "str" or endian:
                return None
            return replace(node, wire=wire)
    return None


def reaches(node: Type | Expression | None) -> Iterator[Struct | Enum | MemberRef]:
    match node:
        case StructRef(struct=family) | EnumRef(enum=family) | EnumName(enum=family):
            yield family
        case MemberRef():
            yield node
        case Literal(value=MemberRef() as member) | Bitset(width=member) | Test(member=member):
            yield member
        case Optional(element=element) | List(element=element) | Array(element=element):
            yield from reaches(element)
        case Not(operand=operand):
            yield from reaches(operand)
        case Binary(left=left, right=right):
            yield from reaches(left)
            yield from reaches(right)
        case Map(key=key, value=value):
            yield from reaches(key)
            yield from reaches(value)
        case Variant(cases=cases):
            for case in cases:
                yield from reaches(case)


def check(package: Package) -> None:
    for module in package.modules:
        if module.package != package.modules[0].package:
            raise CompilerError(f"{module.stem}.py: package: differs from {package.modules[0].stem}.py's")
        for family in module.families:
            if isinstance(family, Struct):
                check_struct(package.versions, f"{module.stem}.py", family, family.name)
            elif isinstance(family, Enum):
                check_enum(package.versions, f"{module.stem}.py", family, family.name)


def check_struct(versions: tuple[int, ...], path: str, struct: Struct, qualified: str) -> None:
    for declaration in struct.declarations:
        for struct_field in declaration.fields:
            for target in (*reaches(struct_field.type), *reaches(struct_field.when)):
                for version in versions:
                    if not struct_field.range.contains(version):
                        continue
                    if isinstance(target, MemberRef):
                        found = any(
                            member.name == target.name and member.range.contains(version)
                            for declared in target.enum.declarations
                            for member in declared.members
                        )
                        missing = f"{target.enum.name}.{target.name}"
                    else:
                        found = any(declared.range.contains(version) for declared in target.declarations)
                        missing = target.name
                    if not found:
                        where = f"{path}: {qualified}.{struct_field.name}"
                        raise CompilerError(f"{where}: reaches {missing}, which does not exist at {version}")
    for nested in struct.nested:
        if isinstance(nested, Struct):
            check_struct(versions, path, nested, f"{qualified}.{nested.name}")
        else:
            check_enum(versions, path, nested, f"{qualified}.{nested.name}")


def check_enum(versions: tuple[int, ...], path: str, enum: Enum, qualified: str) -> None:
    for version in versions:
        members = [
            member
            for declaration in enum.declarations
            for member in declaration.members
            if member.range.contains(version)
        ]
        if members and members[0].value is None:
            raise CompilerError(
                f"{path}: {qualified}.{members[0].name}: has no earlier member to number from at {version}"
            )
        for label, names in (
            ("C++ name", [member.cpp_name for member in members]),
            ("wire name", [member.wire_name for member in members]),
        ):
            for name, count in Counter(names).items():
                if count > 1:
                    raise CompilerError(f"{path}: {qualified}: has the {label} {name} twice at {version}")
        earlier: set[str] = set()
        for member in members:
            match member.value:
                case MemberRef(name=name) | Binary(left=MemberRef(name=name)) if name not in earlier:
                    raise CompilerError(
                        f"{path}: {qualified}.{member.name}: names {name}, which does not exist at {version}"
                    )
            earlier.add(member.name)


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
        self.versions: tuple[int, ...] = ()
        self.homes: dict[tuple[str, bool], Source] = {}
        self.packets: dict[int, list[tuple[Struct, Range]]] = {}
        self.legacies: dict[Struct | Enum, Struct | Enum] = {}
        self.structs: list[PendingStruct] = []
        self.enums: list[PendingEnum] = []
        self.aliases: list[PendingAlias] = []
        self.unions: list[UnionAlias] = []
        self.expanding: list[UnionAlias] = []

    def build(self) -> Package:
        self.versions = self.declare_init(self.init)
        for source in self.sources.values():
            self.declare_module(source)
        for source in self.sources.values():
            self.pair_legacies(source)
            self.bind_family_imports(source)
        for pending_enum in self.enums:
            self.build_enum(pending_enum)
        for pending_alias in self.aliases:
            self.build_alias(pending_alias)
        for union in self.unions:
            self.expand(union.source, union.node, union)
        for pending_struct in self.structs:
            self.build_struct(pending_struct)
        modules = tuple(
            Module(
                source.stem,
                source.package,
                tuple(source.order),
            )
            for source in self.sources.values()
        )
        package = Package(self.versions, modules)
        check(package)
        return package

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
                    self.declare_class(source, source.scope, statement, None, Range(None, None))
                case ast.TypeAlias():
                    name = statement.name.id
                    if statement.type_params:
                        raise error(source, statement, name, "type parameters are not allowed")
                    if isinstance(statement.value, ast.Name | ast.Attribute):
                        alias = Alias(name, source.stem)
                        self.declare_family(source, statement, alias)
                        self.aliases.append(PendingAlias(source, statement, alias))
                    else:
                        union = UnionAlias(source, statement)
                        self.claim(source, statement, name, True)
                        self.add(source, source.scope, statement, name, union)
                        source.unions[name] = union
                        self.unions.append(union)
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

    def claim(self, source: Source, node: ast.stmt, name: str, cereal: bool) -> None:
        home = self.homes.setdefault((name, cereal), source)
        if home is not source:
            raise error(source, node, name, f"is already declared in {home.stem}")

    def declare_family(self, source: Source, node: ast.stmt, family: Family) -> None:
        self.claim(source, node, family.name, True)
        self.add(source, source.scope, node, family.name, family)
        source.families[family.name] = family
        source.order.append(family)

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

    def pair_legacies(self, source: Source) -> None:
        for name, (node, legacy) in source.legacies.items():
            family = source.families.get(name)
            if not isinstance(family, type(legacy)):
                raise error(source, node, name, "a cereal=False declaration needs a cereal one beside it")
            self.legacies[family] = legacy

    def bind_family_imports(self, source: Source) -> None:
        for statement in source.family_imports:
            module = self.sources.get((statement.module or "").removeprefix(f"{self.name}."))
            for alias in statement.names:
                declared = (module.families.get(alias.name) or module.unions.get(alias.name)) if module else None
                if declared is None:
                    raise error(source, alias, alias.name, f"is not declared in {statement.module}")
                self.add(source, source.scope, statement, alias.asname or alias.name, declared)

    def declare_class(
        self, source: Source, scope: Scope, node: ast.ClassDef, owner: Struct | None, outer: Range
    ) -> None:
        if node.keywords:
            raise error(source, node, node.name, "keywords are not supported")
        if node.type_params:
            raise error(source, node, node.name, "type parameters are not allowed")
        kinds: list[object] = []
        packet_id = None
        cereal = True
        own = Range(None, None)
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                function = self.resolve(source, scope, decorator.func)
                if function is not dsl.packet and function is not dsl.type:
                    raise error(source, decorator, node.name, DECORATOR_ERROR)
                arguments = self.bind(source, decorator, function)
                own = self.read_range(source, decorator, node.name, arguments)
                if function is dsl.packet:
                    packet_id = literal(source, arguments["id"], int, "packet")
                if "cereal" in arguments:
                    cereal = literal(source, arguments["cereal"], bool, "type")
            else:
                function = self.resolve(source, scope, decorator)
                if function is not dsl.builtin:
                    raise error(source, decorator, node.name, DECORATOR_ERROR)
            kinds.append(function)
        if len(kinds) > 1:
            raise error(source, node, node.name, "takes only one of packet, type and builtin")
        if not cereal and owner is not None:
            raise error(source, node, node.name, "cereal=False marks a module-scope declaration")
        if owner is not None:
            cereal = owner.cereal
        if not own.overlaps(outer):
            raise error(source, node, node.name, "is empty within its owner")
        range = own.intersect(outer)
        if node.bases and kinds not in ([], [dsl.type]):
            raise error(source, node, node.name, "an enum takes no decorator but type")
        if kinds == [dsl.builtin]:
            if owner is not None:
                raise error(source, node, node.name, "a builtin is declared at the top of a module")
            if any(not isinstance(statement, ast.Pass) for statement in without_docstring(node.body)):
                raise error(source, node, node.name, "a builtin has no body")
            self.declare_family(source, node, Builtin(node.name, source.stem))
            return
        if owner is not None:
            existing = scope.names.get(node.name)
        elif cereal:
            existing = source.families.get(node.name)
        else:
            existing = source.legacies[node.name][1] if node.name in source.legacies else None
        family: Struct | Enum
        if existing is None:
            family = (
                Enum(node.name, owner, source.stem, cereal)
                if node.bases
                else Struct(node.name, owner, source.stem, cereal, packet_id)
            )
            if owner is not None:
                owner.nested.append(family)
                self.add(source, scope, node, node.name, family)
            elif not cereal:
                self.claim(source, node, node.name, False)
                source.legacies[node.name] = (node, family)
                source.order.append(family)
            else:
                self.declare_family(source, node, family)
        elif isinstance(existing, Enum if node.bases else Struct):
            if isinstance(existing, Struct) and existing.packet_id != packet_id:
                raise error(
                    source, node, node.name, f"is declared with packet ids {existing.packet_id} and {packet_id}"
                )
            family = existing
        else:
            raise error(source, node, node.name, "is already declared")
        if isinstance(family, Enum):
            self.enums.append(PendingEnum(source, scope, node, family, range))
            return
        inner = self.scopes.setdefault(family, Scope(scope))
        for statement in node.body:
            if isinstance(statement, ast.ClassDef):
                self.declare_class(source, inner, statement, family, range)
        self.structs.append(PendingStruct(source, node, family, range))

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
            own = Range(None, None)
            value: Int | MemberRef | Binary | None
            if isinstance(expression, ast.Tuple):
                if len(expression.elts) != 2:
                    raise error(source, expression, name, "a pair is a value and a wire name")
                wire_name = literal(source, expression.elts[1], str, name)
                value = Int(literal(source, expression.elts[0], int, name))
            elif isinstance(expression, ast.Call) and function is dsl.value:
                arguments = self.bind(source, expression, dsl.value)
                if "name" in arguments:
                    wire_name = literal(source, arguments["name"], str, name)
                if "cpp_name" in arguments:
                    cpp_name = literal(source, arguments["cpp_name"], str, name)
                    if cpp_name.lower() != derived.lower():
                        raise error(
                            source, expression, name, f"cpp_name {cpp_name!r} is not a case variant of {derived!r}"
                        )
                own = self.read_range(source, expression, name, arguments)
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
            member_range = self.narrow(source, statement, name, own, pending.range)
            for earlier in members:
                if earlier.name == name and earlier.range.overlaps(member_range):
                    raise error(source, statement, name, "is declared twice over overlapping versions")
            members.append(Member(name, value, member_range, cpp_name, wire_name))
        if not members:
            raise error(source, node, pending.enum.name, "has no members")
        self.tile(source, node, pending.enum, pending.range)
        pending.enum.declarations.append(EnumDeclaration(pending.range, underlying, tuple(members)))

    def build_alias(self, pending: PendingAlias) -> None:
        primitive = self.type_of(pending.source, pending.source.scope, pending.node.value)
        if not isinstance(primitive, Primitive):
            raise error(pending.source, pending.node.value, pending.alias.name, "is not a primitive")
        pending.alias.primitive = primitive

    def expand(self, source: Source, node: ast.expr | ast.stmt, union: UnionAlias) -> Variant:
        name = union.node.name.id
        if union in self.expanding:
            raise error(source, node, name, "names itself")
        self.expanding.append(union)
        expanded = self.type_of(union.source, union.source.scope, union.node.value)
        self.expanding.pop()
        if not isinstance(expanded, Variant):
            raise error(union.source, union.node.value, name, "is not a union")
        return expanded

    def build_struct(self, pending: PendingStruct) -> None:
        source = pending.source
        scope = self.scopes[pending.struct]
        fields: list[Field] = []
        statements: list[tuple[ast.stmt, ast.expr | None]] = []
        for statement in without_docstring(pending.node.body):
            if not isinstance(statement, ast.With):
                statements.append((statement, None))
                continue
            single = len(statement.items) == 1 and statement.items[0].optional_vars is None
            block = statement.items[0].context_expr if single else None
            if not (isinstance(block, ast.Call) and self.resolve(source, scope, block.func) is dsl.field):
                raise error(source, statement, pending.struct.name, "is not a with field(when=...) block")
            arguments = self.bind(source, block, dsl.field)
            if list(arguments) != ["when"]:
                raise error(source, block, pending.struct.name, "a with block takes only when=")
            statements.extend((inner, arguments["when"]) for inner in statement.body)
        for statement, block_when in statements:
            if block_when is not None and not isinstance(statement, ast.AnnAssign):
                raise error(source, statement, pending.struct.name, "a with block holds only fields")
            if isinstance(statement, ast.Pass | ast.ClassDef):
                continue
            if not (isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)):
                raise error(
                    source, statement, pending.struct.name, "holds only fields, nested classes, a docstring and pass"
                )
            name = field_name(statement.target.id)
            if any(name == existing.name for existing in fields):
                raise error(source, statement, name, "is declared twice")
            call = statement.value
            if call is not None:
                if not (isinstance(call, ast.Call) and self.resolve(source, scope, call.func) is dsl.field):
                    raise error(source, call, name, "is assigned something other than field(...)")
                arguments = self.bind(source, call, dsl.field)
            annotation = statement.annotation
            cereal = True
            if call is not None and "cereal" in arguments:
                cereal = literal(source, arguments["cereal"], bool, name)
            if (
                isinstance(annotation, ast.Subscript)
                and self.resolve(source, scope, annotation.value) is typing.Literal
            ):
                values = annotation.slice.elts if isinstance(annotation.slice, ast.Tuple) else [annotation.slice]
                if len(values) != 1:
                    raise error(source, annotation, ast.unparse(annotation), "is not a type with these arguments")
                if not cereal:
                    raise error(source, annotation, name, "has no cereal=False declaration")
                if isinstance(values[0], ast.Constant) and isinstance(values[0].value, bool | str):
                    field_type: Type = Literal(values[0].value)
                else:
                    field_type = Literal(self.member_of(source, scope, values[0]))
            else:
                field_type = self.type_of(source, scope, annotation, cereal)
            if call is not None and "prefix" in arguments:
                prefix = self.type_of(source, scope, arguments["prefix"])
                if not isinstance(field_type, List):
                    raise error(source, call, name, "prefix is given to something other than a list")
                if not (isinstance(prefix, Primitive) and prefix.name in LIST_PREFIXES):
                    raise error(source, arguments["prefix"], name, "prefix is not uint32, uint16 or varint32")
                field_type = replace(field_type, prefix=prefix)
            wire = None
            endian = None
            if call is not None and "type" in arguments:
                wire_type = self.type_of(source, scope, arguments["type"])
                if not (isinstance(wire_type, Primitive) and wire_type.name in ("str", *INTEGERS)):
                    raise error(source, arguments["type"], name, "type is not str or an integer primitive")
                wire = wire_type.name
            if call is not None and "endian" in arguments:
                if literal(source, arguments["endian"], str, name) != "big":
                    raise error(source, arguments["endian"], name, 'endian is not "big"')
                endian = "big"
            if wire or endian:
                rewired = rewire(field_type, wire, endian)
                if rewired is None:
                    raise error(
                        source, statement, name, "type and endian do not reach exactly one scalar that takes them"
                    )
                field_type = rewired
            own = self.read_range(source, call, name, arguments) if call is not None else Range(None, None)
            field_range = self.narrow(source, statement, name, own, pending.range)
            if call is not None and "count" in arguments:
                if not isinstance(field_type, List):
                    raise error(source, call, name, "count is given to something other than a bare list")
                if "prefix" in arguments:
                    raise error(source, call, name, "count and prefix are both given")
                count = read_lambda(
                    arguments["count"],
                    fields,
                    field_range,
                    self.versions,
                    lambda node: self.member_of(source, scope, node),
                    lambda node, reason: error(source, node, name, reason),
                )
                field_type = replace(field_type, prefix=None, count=parse_count(count))
            guard = block_when
            if call is not None and "when" in arguments:
                if block_when is not None:
                    raise error(source, call, name, "has its own when= inside a with block")
                guard = arguments["when"]
            when = None
            if guard is not None:
                when = parse_predicate(
                    read_lambda(
                        guard,
                        fields,
                        field_range,
                        self.versions,
                        lambda node: self.member_of(source, scope, node),
                        lambda node, reason: error(source, node, name, reason),
                    )
                )
            fields.append(Field(name, field_type, field_range, when))
        struct = pending.struct
        self.tile(source, pending.node, struct, pending.range)
        if struct.packet_id is not None:
            claimed = self.packets.setdefault(struct.packet_id, [])
            for other, other_range in claimed:
                if other_range.overlaps(pending.range):
                    raise error(
                        source, pending.node, struct.name, f"takes packet id {struct.packet_id} from {other.name}"
                    )
            claimed.append((struct, pending.range))
        struct.declarations.append(StructDeclaration(pending.range, tuple(fields)))

    def read_range(self, source: Source, node: ast.expr, name: str, arguments: dict[str, ast.expr]) -> Range:
        bounds: dict[str, int | None] = {"since": None, "until": None}
        for bound in bounds:
            if bound in arguments:
                bounds[bound] = literal(source, arguments[bound], int, name)
                if bounds[bound] not in self.versions:
                    raise error(source, arguments[bound], name, f"{bound} {bounds[bound]} is not a modelled version")
        since, until = bounds["since"], bounds["until"]
        if since is not None and until is not None and since >= until:
            raise error(source, node, name, "has an empty version range")
        return Range(since, until)

    def narrow(self, source: Source, node: ast.stmt, name: str, own: Range, within: Range) -> Range:
        for gate in (Range(own.since, None), Range(None, own.until)):
            if gate != Range(None, None) and (not gate.overlaps(within) or gate.intersect(within) == within):
                raise error(source, node, name, "has a gate its declaration already decides")
        return own.intersect(within)

    def tile(self, source: Source, node: ast.ClassDef, family: Struct | Enum, range: Range) -> None:
        if not family.declarations:
            return
        previous = family.declarations[-1].range
        if previous.until is None:
            raise error(source, node, family.name, "is declared again after an open declaration")
        if previous.until != range.since:
            raise error(
                source,
                node,
                family.name,
                f"starts at {range.since}, but its previous declaration ends at {previous.until}",
            )

    def bind(
        self,
        source: Source,
        call: ast.Call,
        function: Callable[..., object],
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

    def cases_of(self, source: Source, scope: Scope, operands: list[ast.expr], cereal: bool) -> tuple[Type | None, ...]:
        return tuple(
            None
            if isinstance(operand, ast.Constant) and operand.value is None
            else self.type_of(source, scope, operand, cereal)
            for operand in operands
        )

    def type_of(self, source: Source, scope: Scope, node: ast.expr, cereal: bool = True) -> Type:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            raise error(source, node, node.value, "string annotations are not allowed")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            operands = [node.right]
            left = node.left
            while isinstance(left, ast.BinOp) and isinstance(left.op, ast.BitOr):
                operands.insert(0, left.right)
                left = left.left
            operands.insert(0, left)
            cases = self.cases_of(source, scope, operands, cereal)
            if len(cases) == 2 and cases[0] is not None and cases[1] is None:
                return Optional(cases[0])
            return Variant(cases)
        if isinstance(node, ast.Subscript):
            container = self.resolve(source, scope, node.value)
            arguments = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
            if container is typing.Union and len(arguments) > 1:
                return Variant(self.cases_of(source, scope, arguments, cereal))
            if container is list and len(arguments) == 1:
                return List(self.type_of(source, scope, arguments[0], cereal), Primitive("uvarint32"))
            if container is dict and len(arguments) == 2:
                return Map(
                    self.type_of(source, scope, arguments[0], cereal), self.type_of(source, scope, arguments[1], cereal)
                )
            if container is dsl.array and len(arguments) == 2:
                return Array(
                    self.type_of(source, scope, arguments[0], cereal), literal(source, arguments[1], int, "array")
                )
            if container is dsl.bitset and len(arguments) == 1:
                return Bitset(self.member_of(source, scope, arguments[0]))
            raise error(source, node, ast.unparse(node), "is not a type with these arguments")
        if not isinstance(node, ast.Name | ast.Attribute):
            raise error(source, node, ast.unparse(node), "is not a type")
        target = self.resolve(source, scope, node)
        if not cereal:
            legacy = self.legacies.get(target) if isinstance(target, Struct | Enum) else None
            if legacy is None:
                raise error(source, node, ast.unparse(node), "has no cereal=False declaration")
            target = legacy
        if isinstance(target, TypeAliasType | type) and target in PRIMITIVES:
            return Primitive(PRIMITIVES[target])
        if target is uuid.UUID:
            return BuiltinRef(UUID)
        if isinstance(target, Struct):
            return StructRef(target)
        if isinstance(target, Enum):
            return EnumRef(target)
        if isinstance(target, Alias):
            return AliasRef(target)
        if isinstance(target, UnionAlias):
            return self.expand(source, node, target)
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
