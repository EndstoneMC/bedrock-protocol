"""Frontend — one loaded module to one `File` proto.

protoc analog: `compiler/parser.{h,cc}` (its `io::Tokenizer` has no counterpart --
griffe already hands us an AST). The DSL's decorators (`@packet`, `@type`) and
`field()` calls are runtime no-ops, so griffe never executes them, only reads them.

Which modules get parsed, and where they come from, is `importer.py`'s business.
"""

from __future__ import annotations

import keyword
from dataclasses import dataclass, field, replace
from typing import Callable

import griffe

from bedrock_protocol.descriptor import (
    BUILTIN_ANNOTATIONS,
    INTEGER_PRIMITIVES,
    PRIMITIVES,
    CompilerError,
    CondType,
    Enum,
    EnumType,
    EnumValue,
    Field,
    FieldType,
    FieldVersion,
    File,
    MappingType,
    OptionalType,
    Predicate,
    PrimitiveAlias,
    PrimitiveType,
    RepeatedType,
    Struct,
    StructType,
    TypeAlias,
    VariantType,
)

_Ann = griffe.Expr | str | None


@dataclass(frozen=True)
class SymbolTable:
    """Every name a schema declares, across all its files. protoc resolves type
    references in `DescriptorBuilder` and lets the parser record a bare name; we
    resolve while parsing, so the parser needs the whole table up front."""

    enum_names: frozenset[str]
    enum_underlying: dict[str, PrimitiveType | None]
    struct_names: frozenset[str]
    aliases_by_name: dict[str, PrimitiveAlias | TypeAlias]
    primitive_aliases_by_module: dict[str, tuple[PrimitiveAlias, ...]] = field(default_factory=dict)
    type_aliases_by_module: dict[str, tuple[TypeAlias, ...]] = field(default_factory=dict)


class Parser:
    """Turns one loaded module into one `File` proto — protoc's `Parser`.

    Reads griffe's AST rather than a token stream: the DSL's decorators and
    `field()` calls are runtime no-ops, so they are only ever read, never run.
    """

    def __init__(self, symbols: SymbolTable) -> None:
        self._symbols = symbols

    @property
    def enum_names(self) -> frozenset[str]:
        return self._symbols.enum_names

    @property
    def struct_names(self) -> frozenset[str]:
        return self._symbols.struct_names

    @property
    def enum_underlying(self) -> dict[str, PrimitiveType | None]:
        return self._symbols.enum_underlying

    @property
    def aliases(self) -> dict[str, PrimitiveAlias | TypeAlias]:
        return self._symbols.aliases_by_name

    def parse_file(
        self,
        name: str,
        mod: griffe.Module,
        stem: str,
        loaded: set[str],
        raw_imports: set[str],
        declarations: list[list[griffe.Class]],
    ) -> File:
        """One module to one `File` proto — protoc's `Parser::Parse`.

        Everything it reads is handed to it: `declarations` are the module's class
        statements grouped by name, and `raw_imports` the modules it draws from.
        Opening files is the `SourceTree`'s job, not the parser's."""
        enums: list[Enum] = []
        structs: list[Struct] = []
        order: list[str] = []
        for decls in declarations:
            if is_int_enum(decls[0]):
                if len(decls) > 1:
                    raise CompilerError(
                        f"{decls[0].name}: an enum cannot be redeclared; version-gate its members with value(since=)"
                    )
                e = self.enum(decls[0])
                enums.append(e)
                order.append(e.name)
            else:
                st = self.struct(decls)
                structs.append(st)
                order.append(st.name)
        imports = tuple(sorted(d for d in raw_imports if d in loaded and d != name))
        return File(
            name=name,
            stem=stem,
            package=_package_of(mod),
            enums=tuple(enums),
            structs=tuple(structs),
            primitive_aliases=self._symbols.primitive_aliases_by_module[name],
            type_aliases=self._symbols.type_aliases_by_module[name],
            imports=imports,
            declaration_order=tuple(order),
        )

    def parse_alias(self, name: str, value: griffe.Expr | str) -> PrimitiveAlias | TypeAlias | None:
        if isinstance(value, griffe.ExprName) and value.name in PRIMITIVES:
            return PrimitiveAlias(name, value.name)
        target = self.type(name, value, None)
        return None if target is None else TypeAlias(name, target)

    def enum(self, cls: griffe.Class) -> Enum:
        values: list[EnumValue] = []
        previous: int | None = None
        for name, attr in cls.attributes.items():
            if attr.value is None:
                continue
            number = _enum_number(cls.name, name, attr.value, previous)
            values.append(
                EnumValue(
                    name,
                    number,
                    is_auto=_is_auto(attr.value),
                    since=_int_kwarg(attr.value, "value", "since"),
                    until=_int_kwarg(attr.value, "value", "until"),
                )
            )
            previous = number
        return Enum(cls.name, tuple(values), enum_underlying_of(cls))

    def struct(self, decls: list[griffe.Class]) -> Struct:
        """One struct from every declaration of its name. A type redeclared over
        adjacent ranges models a wire reshape: each declaration's fields carry that
        declaration's range, so a snapshot narrows to exactly one shape -- including
        its field *order*, which a reshaped packet may change."""
        _check_redeclaration(decls)
        fields: list[Field] = []
        for decl in decls:
            lo, hi = _decl_since(decl), _decl_until(decl)
            earlier: set[str] = set()
            for attr in decl.attributes.values():
                (version,) = self.field(attr, frozenset(earlier)).versions
                earlier.add(_field_name(attr.name))
                narrowed = FieldVersion(
                    type=version.type,
                    since=_tighten(version.since, lo, max),
                    until=_tighten(version.until, hi, min),
                )
                fields.append(Field(_field_name(attr.name), (narrowed,)))
        return Struct(
            name=decls[0].name,
            fields=tuple(fields),
            packet_id=_decorator_int(decls[0], "packet", "id"),
            since=_decl_since(decls[0]),
            until=_decl_until(decls[-1]),
            builtin=any(_has_decorator(d, "builtin") for d in decls),
        )

    def field(self, attr: griffe.Attribute, earlier: frozenset[str] = frozenset()) -> Field:
        call = attr.value
        t = self._counted(self.type(attr.name, attr.annotation, call), call, attr.name, earlier)
        guard = self._guard(attr.name, call)
        if guard is not None and t is not None:
            if _call_arg(call, "field", "when") is not None and isinstance(t, (OptionalType, VariantType)):
                raise CompilerError(
                    f"{attr.name}: field(when=...) gates a bare payload -- it cannot also be optional or a union; "
                    "wrap it in a with field(when=...) block instead"
                )
            t = CondType(t, self._predicate(guard, attr.name, earlier), _int_kwarg(call, "field", "_group_id"))
        version = FieldVersion(
            type=t,
            since=_int_kwarg(call, "field", "since"),
            until=_int_kwarg(call, "field", "until"),
        )
        return Field(_field_name(attr.name), (version,))

    # ---- count= expressions ------------------------------------------------

    def _counted(
        self,
        t: FieldType | None,
        call: _Ann,
        field_name: str,
        earlier: frozenset[str],
    ) -> FieldType | None:
        """`field(count=...)`: the element count is an expression over earlier
        fields rather than a wire prefix."""
        lam = _call_arg(call, "field", "count")
        if lam is None or t is None:
            return t
        if not isinstance(t, RepeatedType):
            raise CompilerError(f"{field_name}: field(count=...) applies to a list[T] field, got {t.kind}")
        if _call_arg(call, "field", "prefix") is not None:
            raise CompilerError(
                f"{field_name}: field(count=...) and field(prefix=...) are mutually exclusive -- "
                "a counted list carries no length prefix on the wire"
            )
        return replace(t, count=self._predicate(lam, field_name, earlier))

    # ---- when= predicates --------------------------------------------------

    def _guard(self, field_name: str, call: _Ann) -> _Ann:
        """The field's gating lambda: its own `when=`, or the one a
        `with field(when=...)` block merged in as `_group_when=`."""
        own = _call_arg(call, "field", "when")
        group = _call_arg(call, "field", "_group_when")
        if own is not None and group is not None:
            raise CompilerError(
                f"{field_name}: a field inside a with field(when=...) block cannot carry its own field(when=...)"
            )
        return own if own is not None else group

    def _predicate(self, lam: _Ann, field_name: str, earlier: frozenset[str]) -> Predicate:
        if not isinstance(lam, griffe.ExprLambda):
            raise CompilerError(f"{field_name}: field(when=...) must be a lambda predicate")
        if len(lam.parameters) != 1:
            raise CompilerError(f"{field_name}: field(when=...) lambda takes exactly one parameter")
        return self._pred_node(lam.body, lam.parameters[0].name, field_name, earlier)

    def _pred_node(
        self,
        node: griffe.Expr | str,
        param: str,
        field_name: str,
        earlier: frozenset[str],
    ) -> Predicate:
        def child(n: griffe.Expr | str) -> Predicate:
            return self._pred_node(n, param, field_name, earlier)

        if isinstance(node, griffe.ExprBoolOp):
            return Predicate(node.operator, operands=tuple(child(v) for v in node.values))
        if isinstance(node, griffe.ExprUnaryOp) and node.operator == "not":
            return Predicate("not", operands=(child(node.value),))
        if isinstance(node, griffe.ExprCompare):
            if len(node.operators) != 1 or len(node.comparators) != 1:
                raise CompilerError(
                    f"{field_name}: field(when=...) takes one comparison per clause -- "
                    "split a chained comparison with `and`"
                )
            op = str(node.operators[0])
            if op in ("in", "not in"):
                return self._pred_membership(node, op, param, field_name, earlier)
            if op not in ("==", "!=", "<", ">", "<=", ">="):
                raise CompilerError(f"{field_name}: field(when=...) comparison {op!r} is unsupported")
            return Predicate(op, operands=(child(node.left), child(node.comparators[0])))
        if isinstance(node, griffe.ExprBinOp) and node.operator in ("*", "+", "-"):
            return Predicate(node.operator, operands=(child(node.left), child(node.right)))
        if isinstance(node, griffe.ExprAttribute):
            return self._pred_attr(node, param, field_name, earlier)
        literal = _as_int(node)
        if literal is not None:
            return Predicate("int", text=str(literal))
        raise CompilerError(f"{field_name}: field(when=...) contains an unsupported expression: {node}")

    def _pred_membership(
        self,
        node: griffe.ExprCompare,
        op: str,
        param: str,
        field_name: str,
        earlier: frozenset[str],
    ) -> Predicate:
        """Desugar set membership into a chain of equalities: `x in {a, b, c}`
        to `x == a or x == b or x == c`, `x not in {a, b}` to `x != a and
        x != b`. The right operand must be a set / list / tuple literal."""
        container = node.comparators[0]
        if not isinstance(container, (griffe.ExprSet, griffe.ExprList, griffe.ExprTuple)):
            raise CompilerError(
                f"{field_name}: field(when=...) `{op}` needs a set/list/tuple literal on the right, got {container}"
            )
        elements = list(container.elements)
        if not elements:
            raise CompilerError(f"{field_name}: field(when=...) `{op}` needs a non-empty set literal")
        left = self._pred_node(node.left, param, field_name, earlier)
        compare, join = ("==", "or") if op == "in" else ("!=", "and")
        clauses = tuple(
            Predicate(compare, operands=(left, self._pred_node(e, param, field_name, earlier))) for e in elements
        )
        return clauses[0] if len(clauses) == 1 else Predicate(join, operands=clauses)

    def _pred_attr(
        self,
        node: griffe.ExprAttribute,
        param: str,
        field_name: str,
        earlier: frozenset[str],
    ) -> Predicate:
        parts = [str(v) for v in node.values]
        spelled = ".".join(parts)
        if len(parts) != 2:
            raise CompilerError(
                f"{field_name}: field(when=...) reference {spelled!r} must be `{param}.field` or `Enum.MEMBER`"
            )
        head, tail = parts
        if head == param:
            name = _field_name(tail)
            if name not in earlier:
                raise CompilerError(
                    f"{field_name}: field(when=...) references {tail!r}, which is not a field declared before it"
                )
            return Predicate("field", text=name)
        if head in self.enum_names:
            return Predicate("enum", text=spelled)
        raise CompilerError(
            f"{field_name}: field(when=...) reference {spelled!r} is neither `{param}.field` nor `Enum.MEMBER`"
        )

    # ---- enum wire type ----------------------------------------------------

    def _enum_scalar(self, type_kw: str | None, field_name: str, enum_name: str) -> PrimitiveType | None:
        """The wire encoding of an enum-typed field: `field(type=)` if given
        (`str` marks it name-coded), else derived from the enum's underlying type."""
        if type_kw == "str":
            return None
        if type_kw is not None:
            if type_kw not in PRIMITIVES:
                raise CompilerError(f"{field_name}: unknown wire primitive {type_kw!r}; valid: {sorted(PRIMITIVES)}")
            return PrimitiveType(name=type_kw)
        underlying = self.enum_underlying.get(enum_name)
        if underlying is None:
            raise CompilerError(
                f"{field_name}: {enum_name} declares no underlying type, so its wire encoding "
                f"cannot be derived -- give the enum one as a second base "
                f"(class {enum_name}(IntEnum, uint8)) or pass field(type=...)"
            )
        return _default_enum_wire(underlying)

    # ---- field-type walker -------------------------------------------------

    def type(self, field_name: str, ann: _Ann, call: _Ann) -> FieldType | None:
        type_kw = _name_kwarg(call, "field", "type")
        prefix = _repeat_prefix(call, field_name)
        cases = _flatten_union(ann)
        if cases is not None:
            return self._union_type(cases, field_name, type_kw, prefix)
        return self._base_type(ann, type_kw, prefix, field_name)

    def _union_type(
        self,
        cases: list[griffe.Expr | str],
        field_name: str,
        type_kw: str | None,
        prefix: PrimitiveType,
    ) -> FieldType | None:
        if len(cases) == 2 and sum(_is_none(a) for a in cases) == 1:
            inner_ann = next(a for a in cases if not _is_none(a))
            base = self._base_type(inner_ann, type_kw, prefix, field_name)
            return None if base is None else OptionalType(base)
        types: list[FieldType | None] = []
        for case in cases:
            if _is_none(case):
                types.append(None)
                continue
            t = self._base_type(case, type_kw, prefix, field_name)
            if t is None:
                return None
            types.append(t)
        return VariantType(tuple(types))

    def _base_type(
        self,
        ann: _Ann,
        type_kw: str | None,
        prefix: PrimitiveType,
        field_name: str,
    ) -> FieldType | None:
        if isinstance(ann, griffe.ExprSubscript):
            opt = _optional_element(ann)
            if opt is not None:
                inner = self._base_type(opt, type_kw, prefix, field_name)
                return None if inner is None else OptionalType(inner)
            elem = _list_element(ann, field_name)
            if elem is not None:
                inner = self._base_type(elem, type_kw, prefix, field_name)
                return None if inner is None else RepeatedType(inner=inner, prefix=prefix)
            mapping = _map_parts(ann, field_name)
            if mapping is None:
                return None
            key = self._base_type(mapping[0], type_kw, prefix, field_name)
            value = self._base_type(mapping[1], type_kw, prefix, field_name)
            if key is None or value is None:
                return None
            return MappingType(key=key, value=value, prefix=prefix)
        cases = _flatten_union(ann)
        if cases is not None:
            return self._union_type(cases, field_name, type_kw, prefix)
        dotted = _dotted_name(ann)
        if dotted is not None and dotted in BUILTIN_ANNOTATIONS:
            return StructType(BUILTIN_ANNOTATIONS[dotted])
        if not isinstance(ann, griffe.ExprName):
            return None
        name = ann.name
        if name in self.enum_names:
            return EnumType(name, self._enum_scalar(type_kw, field_name, name))
        if name in self.struct_names:
            return StructType(name)
        if name in PRIMITIVES:
            return PrimitiveType(name=name, wire=_wire_override(type_kw, name, field_name))
        alias = self.aliases.get(name)
        if isinstance(alias, PrimitiveAlias):
            return PrimitiveType(
                name=alias.primitive,
                alias=alias.name,
                wire=_wire_override(type_kw, alias.primitive, field_name),
            )
        if isinstance(alias, TypeAlias):
            return alias.target
        return None


# --- module-free helpers ------------------------------------------------------


def _package_of(mod: griffe.Module) -> str | None:
    attr = mod.attributes.get("package")
    if attr is None or attr.value is None:
        return None
    return str(attr.value).strip("'\"")


def _base_name(base: griffe.Expr | str) -> str | None:
    """Last component of a base-class expression. Both the bare `IntEnum` and
    the dotted `enum.IntEnum` spelling yield "IntEnum"."""
    if isinstance(base, griffe.ExprAttribute):
        base = base.values[-1]
    return base.name if isinstance(base, griffe.ExprName) else None


def is_int_enum(cls: griffe.Class) -> bool:
    return any(_base_name(b) in ("IntEnum", "IntFlag") for b in cls.bases)


#: DSL primitive an enum may declare as its C++ underlying type -> (size in bytes,
#: signed). A varint is an encoding, not a type, so it is not among them. `bool` is:
#: BDS really does declare `enum class NetherWorldType : bool`.
_INT_WIDTHS: dict[str, tuple[int, bool]] = {
    "bool": (1, False),
    "int8": (1, True),
    "uint8": (1, False),
    "int16": (2, True),
    "uint16": (2, False),
    "int": (4, True),
    "int32": (4, True),
    "uint32": (4, False),
    "int64": (8, True),
    "uint64": (8, False),
}


def _default_enum_wire(underlying: PrimitiveType) -> PrimitiveType:
    """The default wire encoding: underlying type, enum-as-value and compression.
    One byte has nothing to compress and goes as-is; wider compresses to
    `[u]varint32`, or `[u]varint64` at eight, signedness following the underlying."""
    size, signed = _INT_WIDTHS[underlying.name]
    if size == 1:
        return underlying
    width = 64 if size == 8 else 32
    return PrimitiveType(name=f"{'' if signed else 'u'}varint{width}")


def enum_underlying_of(cls: griffe.Class) -> PrimitiveType | None:
    """The enum's C++ underlying type, written as a second base
    (`class MemoryCategory(IntEnum, uint8)`). None means the C++ default, `int`."""
    for base in cls.bases:
        name = _base_name(base)
        if name is None or name in ("IntEnum", "IntFlag"):
            continue
        if name not in _INT_WIDTHS:
            raise CompilerError(
                f"{cls.name}: enum underlying type must be a fixed-width primitive, got {name!r}; "
                f"valid: {sorted(_INT_WIDTHS)}"
            )
        return PrimitiveType(name=name)
    return None


def _wire_override(type_kw: str | None, own: str, field_name: str) -> str | None:
    """`field(type=)` on a primitive-typed field: the annotation keeps owning the
    in-memory type and the override takes the wire, for a BDS member declared
    narrow but written as a varint. Both halves must be integers."""
    if type_kw is None or type_kw == own:
        return None
    if own not in INTEGER_PRIMITIVES or type_kw not in INTEGER_PRIMITIVES:
        raise CompilerError(
            f"{field_name}: field(type={type_kw}) overrides the wire encoding of an integer primitive; "
            f"{own!r} -> {type_kw!r} is not one"
        )
    return type_kw


def _is_none(case: object) -> bool:
    """A literal `None` in source. griffe spells a keyword literal as the bare
    string `'None'` (vs `ExprName('Other')` for a name reference)."""
    return case == "None"


def _dotted_name(ann: _Ann) -> str | None:
    """`uuid.UUID` as the string "uuid.UUID"; None for anything not a dotted path."""
    if not isinstance(ann, griffe.ExprAttribute):
        return None
    parts = [v.name for v in ann.values if isinstance(v, griffe.ExprName)]
    return ".".join(parts) if len(parts) == len(ann.values) else None


def _has_decorator(cls: griffe.Class, name: str) -> bool:
    """A bare decorator like `@builtin`, which carries no call parentheses."""
    return any(_base_name(d.value) == name for d in cls.decorators)


def _decl_since(cls: griffe.Class) -> int | None:
    since = _decorator_int(cls, "packet", "since")
    return since if since is not None else _decorator_int(cls, "type", "since")


def _decl_until(cls: griffe.Class) -> int | None:
    until = _decorator_int(cls, "packet", "until")
    return until if until is not None else _decorator_int(cls, "type", "until")


def _tighten(own: int | None, decl: int | None, pick: Callable[[int, int], int]) -> int | None:
    """A field's bound against its declaration's: the narrower of the two wins, so
    `field(since=486)` inside an `until=1001` declaration spans [486, 1001)."""
    if own is None:
        return decl
    if decl is None:
        return own
    return pick(own, decl)


def _check_redeclaration(decls: list[griffe.Class]) -> None:
    """Redeclarations must tile one range: same id, each `until` meeting the next
    `since`, and only the last left open. Anything else silently drops or
    double-counts a shape at some snapshot."""
    if len(decls) == 1:
        return
    name = decls[0].name
    ids = {_decorator_int(d, "packet", "id") for d in decls}
    if len(ids) > 1:
        raise CompilerError(f"{name}: every redeclaration must share one packet id, got {sorted(map(str, ids))}")
    for current, following in zip(decls, decls[1:]):
        until, since = _decl_until(current), _decl_since(following)
        if until is None:
            raise CompilerError(f"{name}: only the last declaration may omit until=; an earlier one leaves it open")
        if until != since:
            raise CompilerError(
                f"{name}: redeclarations must be adjacent -- until={until} is followed by since={since}"
            )


def _is_auto(value: griffe.Expr | str) -> bool:
    """`auto()`, or `value()` with no positional number — both mean previous + 1."""
    if not isinstance(value, griffe.ExprCall):
        return False
    name = _base_name(value.function)
    if name == "auto":
        return True
    return name == "value" and not any(not isinstance(a, griffe.ExprKeyword) for a in value.arguments)


def _enum_number(enum_name: str, name: str, value: griffe.Expr | str, previous: int | None) -> int:
    """A member's wire number: an int literal, or `auto()` for previous + 1."""
    if isinstance(value, griffe.ExprCall) and _base_name(value.function) == "auto":
        return 0 if previous is None else previous + 1
    if isinstance(value, griffe.ExprCall) and _base_name(value.function) == "value":
        # value(N, since=, until=): N is positional, and mandatory when gated --
        # auto-numbering a member that is absent at some snapshot would shift its
        # siblings' wire numbers.
        for arg in value.arguments:
            if not isinstance(arg, griffe.ExprKeyword):
                explicit = _as_int(arg)
                if explicit is not None:
                    return explicit
        raise CompilerError(f"{enum_name}.{name}: value() needs an explicit wire number, e.g. value(601, since=1001)")
    number = _as_int(value)
    if number is None:
        raise CompilerError(f"{enum_name}.{name}: enum member must be an int literal or auto(), got {value!r}")
    return number


def _as_int(value: object) -> int | None:
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    if isinstance(value, griffe.ExprUnaryOp) and value.operator == "-":
        inner = _as_int(value.value)
        return None if inner is None else -inner
    return None


def _flatten_union(ann: _Ann) -> list[griffe.Expr | str] | None:
    if not (isinstance(ann, griffe.ExprBinOp) and ann.operator == "|"):
        return None
    cases: list[griffe.Expr | str] = []
    stack: list[griffe.Expr | str] = [ann]
    while stack:
        node = stack.pop()
        if isinstance(node, griffe.ExprBinOp) and node.operator == "|":
            stack.append(node.right)
            stack.append(node.left)
        else:
            cases.append(node)
    return cases


def _list_element(ann: griffe.ExprSubscript, field_name: str) -> griffe.Expr | str | None:
    """The element annotation of a `list[T]` subscript, or None for anything else."""
    if isinstance(ann.left, griffe.ExprName) and ann.left.name == "list":
        return ann.slice
    return None


def _optional_element(ann: griffe.ExprSubscript) -> griffe.Expr | str | None:
    """The `T` of an `Optional[T]` subscript, or None. An explicit spelling of
    `T | None` that, unlike the union form, nests: `Optional[Optional[T]]` is a
    two-level optional, which `| None` cannot express (it flattens)."""
    if isinstance(ann.left, griffe.ExprName) and ann.left.name == "Optional":
        return ann.slice
    return None


def _field_name(name: str) -> str:
    """The emitted name of a DSL field. A single trailing underscore escapes a
    Python keyword (PEP 8's `pass_`) and is dropped, so a BDS `mPass` field can
    keep its name; any other trailing underscore is part of the name."""
    return name[:-1] if name.endswith("_") and keyword.iskeyword(name[:-1]) else name


def _map_parts(ann: griffe.ExprSubscript, field_name: str) -> tuple[griffe.Expr | str, griffe.Expr | str] | None:
    """The key / value annotations of a `dict[K, V]` subscript, or None for
    anything else."""
    if not (isinstance(ann.left, griffe.ExprName) and ann.left.name == "dict"):
        return None
    slice_ = ann.slice
    if not isinstance(slice_, griffe.ExprTuple) or len(slice_.elements) != 2:
        raise CompilerError(f"{field_name}: dict[...] needs exactly a key type and a value type")
    return slice_.elements[0], slice_.elements[1]


def _repeat_prefix(call: _Ann, field_name: str) -> PrimitiveType:
    name = _name_kwarg(call, "field", "prefix")
    if name is None:
        return PrimitiveType(name="uvarint32")
    if name not in PRIMITIVES:
        raise CompilerError(f"{field_name}: field(prefix=...) must be an integer primitive, got {name!r}")
    return PrimitiveType(name=name)


def _call_arg(expr: _Ann, fn_name: str, kw: str) -> _Ann:
    if not (
        isinstance(expr, griffe.ExprCall)
        and isinstance(expr.function, griffe.ExprName)
        and expr.function.name == fn_name
    ):
        return None
    for arg in expr.arguments:
        if isinstance(arg, griffe.ExprKeyword) and arg.name == kw:
            return arg.value
    return None


def _int_kwarg(expr: _Ann, fn_name: str, kw: str) -> int | None:
    return _as_int(_call_arg(expr, fn_name, kw))


def _name_kwarg(expr: _Ann, fn_name: str, kw: str) -> str | None:
    value = _call_arg(expr, fn_name, kw)
    return value.name if isinstance(value, griffe.ExprName) else None


def _decorator_int(cls: griffe.Class, decorator: str, kwarg: str) -> int | None:
    for dec in cls.decorators:
        v = _int_kwarg(dec.value, decorator, kwarg)
        if v is not None:
            return v
    return None
