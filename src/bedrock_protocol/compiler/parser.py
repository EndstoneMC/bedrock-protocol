"""Frontend — one loaded module to one `File` proto.

protoc analog: `compiler/parser.{h,cc}` (its `io::Tokenizer` has no counterpart --
griffe already hands us an AST). The DSL's decorators (`@packet`, `@type`) and
`field()` calls are runtime no-ops, so griffe never executes them, only reads them.

Which modules get parsed, and where they come from, is `importer.py`'s business.
"""

from __future__ import annotations

import keyword
from dataclasses import dataclass, field, replace
from typing import Callable, Mapping, cast

import griffe

from bedrock_protocol.descriptor import (
    BUILTIN_ANNOTATIONS,
    INTEGER_PRIMITIVES,
    PRIMITIVES,
    BitsetType,
    CompilerError,
    CondType,
    Endian,
    Enum,
    EnumType,
    EnumValue,
    Field,
    FieldType,
    FieldVersion,
    File,
    LiteralType,
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
    resolve while parsing, so the parser needs the whole table up front.

    A nested type is keyed by its dotted path (`Owner.Inner`); a reference
    spelled inside `Owner` finds it by walking the enclosing scopes outward."""

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

    def lookup(self, name: str, scope: str) -> str | None:
        """The declared name a reference resolves to, or None. Mirrors C++
        unqualified lookup: try the reference inside `scope`, then each
        enclosing scope outward, and finally at module scope."""
        parts = scope.split(".") if scope else []
        for cut in range(len(parts), -1, -1):
            candidate = ".".join([*parts[:cut], name])
            if candidate in self.enum_names or candidate in self.struct_names:
                return candidate
        return None

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
            if is_enum(decls[0]):
                e = self.enum(decls)
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

    def enum(self, decls: list[griffe.Class]) -> Enum:
        """One enum from every declaration of its name. A renumbering is a
        reshape, so it is redeclared over adjacent ranges the way a struct is:
        each declaration's members carry that declaration's range, so a member
        that moved holds its era's value in each, and one that went away simply
        stops. `value(since=)` still covers a member arriving inside a range."""
        _check_redeclaration(decls)
        underlying = _one_underlying(decls)
        values: list[EnumValue] = []
        for decl in decls:
            _check_decorators(decl)
            lo, hi = _decl_since(decl), _decl_until(decl)
            previous: int | None = None
            for name, attr in decl.attributes.items():
                if attr.value is None:
                    continue
                spelled, wire = _split_wire_name(attr.value, decl.name, name, _takes_paired_value(decl))
                _check_keywords(spelled, "value", _VALUE_KEYWORDS, f"{decl.name}.{name}", positional=2)
                number = _enum_number(decl.name, name, spelled, previous)
                values.append(
                    EnumValue(
                        name,
                        number,
                        is_auto=_is_auto(spelled),
                        since=_tighten(_int_kwarg(spelled, "value", "since"), lo, max),
                        until=_tighten(_int_kwarg(spelled, "value", "until"), hi, min),
                        wire=wire,
                    )
                )
                previous = number
        return Enum(
            name=decls[0].name,
            values=tuple(values),
            underlying=underlying,
            since=_decl_since(decls[0]),
            until=_decl_until(decls[-1]),
        )

    def struct(self, decls: list[griffe.Class], scope: str = "") -> Struct:
        """One struct from every declaration of its name. A type redeclared over
        adjacent ranges models a wire reshape: each declaration's fields carry that
        declaration's range, so a snapshot narrows to exactly one shape -- including
        its field *order*, which a reshaped packet may change."""
        _check_redeclaration(decls)
        qualified = f"{scope}.{decls[0].name}" if scope else decls[0].name
        fields: list[Field] = []
        for decl in decls:
            _check_decorators(decl)
            lo, hi = _decl_since(decl), _decl_until(decl)
            earlier: dict[str, FieldType | None] = {}
            for attr in decl.attributes.values():
                (version,) = self.field(attr, qualified, earlier).versions
                earlier[_field_name(attr.name)] = version.type
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
            nested=self._nested(decls, qualified),
        )

    def _nested(self, decls: list[griffe.Class], qualified: str) -> tuple[Enum | Struct, ...]:
        """The types declared inside the class, in source order. A redeclared
        owner repeats each nested type in every body -- Python needs the name in
        scope to annotate against it -- so identical repeats collapse to one;
        bodies that disagree are a version-redeclared nested type."""
        out: list[Enum | Struct] = []
        for group in nested_declarations(decls):
            if is_enum(group[0]):
                each = [self.enum([c]) for c in group]
                out.append(each[0] if all(e == each[0] for e in each) else self.enum(group))
            else:
                one = [self.struct([c], qualified) for c in group]
                out.append(one[0] if all(s == one[0] for s in one) else self.struct(group, qualified))
        return tuple(out)

    def field(self, attr: griffe.Attribute, scope: str = "", earlier: Mapping[str, FieldType | None] = {}) -> Field:
        call = attr.value
        _check_keywords(call, "field", _FIELD_KEYWORDS, attr.name)
        t = self._counted(self.type(attr.name, attr.annotation, call, scope), call, attr.name, scope, earlier)
        t = _pinned(t, _int_kwarg(call, "field", "snapshot"), attr.name)
        guard = self._guard(attr.name, call)
        if guard is not None and t is not None:
            if _call_arg(call, "field", "when") is not None and isinstance(t, (OptionalType, VariantType)):
                raise CompilerError(
                    f"{attr.name}: field(when=...) gates a bare payload -- it cannot also be optional or a union; "
                    "wrap it in a with field(when=...) block instead"
                )
            t = CondType(t, self._predicate(guard, attr.name, scope, earlier), _int_kwarg(call, "field", "_group_id"))
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
        scope: str,
        earlier: Mapping[str, FieldType | None],
    ) -> FieldType | None:
        """`field(count=...)`: the element count is an expression over earlier
        fields rather than a wire prefix. Presence is a separate axis, so the
        count applies to the list inside an optional as readily as to a bare
        one -- a cerealised member is flagged present and still has its length
        written somewhere else."""
        lam = _call_arg(call, "field", "count")
        if lam is None or t is None:
            return t
        inner: FieldType = t.inner if isinstance(t, OptionalType) else t
        if not isinstance(inner, RepeatedType):
            raise CompilerError(f"{field_name}: field(count=...) applies to a list[T] field, got {inner.kind}")
        if _call_arg(call, "field", "prefix") is not None:
            raise CompilerError(
                f"{field_name}: field(count=...) and field(prefix=...) are mutually exclusive -- "
                "a counted list carries no length prefix on the wire"
            )
        counted: FieldType = replace(inner, count=self._predicate(lam, field_name, scope, earlier))
        return OptionalType(counted) if isinstance(t, OptionalType) else counted

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

    def _predicate(self, lam: _Ann, field_name: str, scope: str, earlier: Mapping[str, FieldType | None]) -> Predicate:
        if not isinstance(lam, griffe.ExprLambda):
            raise CompilerError(f"{field_name}: field(when=...) must be a lambda predicate")
        if len(lam.parameters) != 1:
            raise CompilerError(f"{field_name}: field(when=...) lambda takes exactly one parameter")
        return self._pred_node(lam.body, lam.parameters[0].name, field_name, scope, earlier)

    def _pred_node(
        self,
        node: griffe.Expr | str,
        param: str,
        field_name: str,
        scope: str,
        earlier: Mapping[str, FieldType | None],
    ) -> Predicate:
        def child(n: griffe.Expr | str) -> Predicate:
            return self._pred_node(n, param, field_name, scope, earlier)

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
                return self._pred_membership(node, op, param, field_name, scope, earlier)
            if op not in ("==", "!=", "<", ">", "<=", ">="):
                raise CompilerError(f"{field_name}: field(when=...) comparison {op!r} is unsupported")
            return Predicate(op, operands=(child(node.left), child(node.comparators[0])))
        if isinstance(node, griffe.ExprBinOp) and node.operator in ("*", "+", "-", "&"):
            return Predicate(node.operator, operands=(child(node.left), child(node.right)))
        if isinstance(node, griffe.ExprCall):
            return self._pred_call(node, param, field_name, scope, earlier)
        if isinstance(node, griffe.ExprAttribute):
            return self._pred_attr(node, param, field_name, scope, earlier)
        literal = _as_int(node)
        if literal is not None:
            return Predicate("int", text=str(literal))
        raise CompilerError(f"{field_name}: field(when=...) contains an unsupported expression: {node}")

    def _pred_call(
        self,
        node: griffe.ExprCall,
        param: str,
        field_name: str,
        scope: str,
        earlier: Mapping[str, FieldType | None],
    ) -> Predicate:
        """The two calls a predicate may make: `len(p.<field>)` and
        `p.<field>.test(<bit>)`."""
        if isinstance(node.function, griffe.ExprName) and node.function.name == "len":
            return self._pred_len(node, param, field_name, scope, earlier)
        if isinstance(node.function, griffe.ExprAttribute) and str(node.function.values[-1]) == "test":
            return self._pred_bittest(node, param, field_name, scope, earlier)
        raise CompilerError(
            f"{field_name}: a predicate calls only len(<field>) or <field>.test(<bit>), got {node}"
        )

    def _pred_len(
        self,
        node: griffe.ExprCall,
        param: str,
        field_name: str,
        scope: str,
        earlier: Mapping[str, FieldType | None],
    ) -> Predicate:
        """`len(p.<field>)` — the element count of an earlier list, map or
        string. BDS writes several parallel runs behind one count, so the
        second run's length is the first run's and nothing on the wire repeats
        it."""
        args = _positional(node)
        if len(args) != 1:
            raise CompilerError(f"{field_name}: len(...) takes exactly one argument, got {node}")
        operand = self._pred_node(args[0], param, field_name, scope, earlier)
        if operand.kind != "field" or not _is_sized(earlier.get(operand.text)):
            raise CompilerError(
                f"{field_name}: len(...) applies to an earlier list, map or string field, got {args[0]}"
            )
        return Predicate("len", operands=(operand,))

    def _pred_bittest(
        self,
        node: griffe.ExprCall,
        param: str,
        field_name: str,
        scope: str,
        earlier: Mapping[str, FieldType | None],
    ) -> Predicate:
        """`p.<field>.test(<bit>)` — one bit of an earlier `bitset[N]` field.

        BDS packs PlayerAuthInput's input flags into a `std::bitset<65>` and
        gates the rest of the packet on individual bits, so the predicate has
        to reach a bit rather than compare a whole value. The bit is an integer
        literal or an `Enum.MEMBER` naming the flag."""
        receiver = node.function
        assert isinstance(receiver, griffe.ExprAttribute)
        parts = [str(v) for v in receiver.values]
        if len(parts) != 3 or parts[0] != param:
            raise CompilerError(
                f"{field_name}: a bit test reads `{param}.<earlier-field>.test(<bit>)`, got {receiver}"
            )
        target = _field_name(parts[1])
        if target not in earlier:
            raise CompilerError(
                f"{field_name}: .test(...) references {parts[1]!r}, which is not a field declared before it"
            )
        if not isinstance(_unwrapped(earlier[target]), BitsetType):
            raise CompilerError(f"{field_name}: .test(...) applies to an earlier bitset[N] field, got {parts[1]!r}")
        args = _positional(node)
        if len(args) != 1:
            raise CompilerError(f"{field_name}: .test(...) takes exactly one bit index, got {node}")
        operand = self._pred_node(args[0], param, field_name, scope, earlier)
        if operand.kind not in ("int", "enum"):
            raise CompilerError(
                f"{field_name}: .test(...) takes an integer literal or Enum.MEMBER bit index, got {args[0]}"
            )
        return Predicate("bittest", text=target, operands=(operand,))

    def _pred_membership(
        self,
        node: griffe.ExprCompare,
        op: str,
        param: str,
        field_name: str,
        scope: str,
        earlier: Mapping[str, FieldType | None],
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
        left = self._pred_node(node.left, param, field_name, scope, earlier)
        compare, join = ("==", "or") if op == "in" else ("!=", "and")
        clauses = tuple(
            Predicate(compare, operands=(left, self._pred_node(e, param, field_name, scope, earlier))) for e in elements
        )
        return clauses[0] if len(clauses) == 1 else Predicate(join, operands=clauses)

    def _pred_attr(
        self,
        node: griffe.ExprAttribute,
        param: str,
        field_name: str,
        scope: str,
        earlier: Mapping[str, FieldType | None],
    ) -> Predicate:
        parts = [str(v) for v in node.values]
        spelled = ".".join(parts)
        if parts[0] == param:
            if len(parts) != 2:
                raise CompilerError(
                    f"{field_name}: field(when=...) reference {spelled!r} must be `{param}.field` or `Enum.MEMBER`"
                )
            name = _field_name(parts[1])
            if name not in earlier:
                raise CompilerError(
                    f"{field_name}: field(when=...) references {parts[1]!r}, which is not a field declared before it"
                )
            return Predicate("field", text=name)
        # Everything but the last component names the enum, so a nested one is
        # reachable both bare (`ActionType.PLACE`) and qualified (`Owner.ActionType.PLACE`).
        enum = self.lookup(".".join(parts[:-1]), scope)
        if enum is not None and enum in self.enum_names:
            return Predicate("enum", text=f"{enum}.{parts[-1]}")
        raise CompilerError(
            f"{field_name}: field(when=...) reference {spelled!r} is neither `{param}.field` nor `Enum.MEMBER`"
        )

    # ---- declared type references ------------------------------------------

    def _declared_type(
        self, qualified: str, type_kw: str | None, field_name: str, endian: Endian | None
    ) -> FieldType | None:
        if qualified in self.enum_names:
            return EnumType(qualified, self._enum_scalar(type_kw, field_name, qualified, endian))
        return StructType(qualified)

    # ---- enum wire type ----------------------------------------------------

    def _enum_scalar(
        self, type_kw: str | None, field_name: str, enum_name: str, endian: Endian | None
    ) -> PrimitiveType | None:
        """The wire encoding of an enum-typed field: `field(type=)` if given
        (`str` marks it name-coded), else derived from the enum's underlying type."""
        if type_kw == "str":
            return None
        if type_kw is not None:
            if type_kw not in PRIMITIVES:
                raise CompilerError(f"{field_name}: unknown wire primitive {type_kw!r}; valid: {sorted(PRIMITIVES)}")
            return _with_endian(PrimitiveType(name=type_kw), endian, field_name)
        underlying = self.enum_underlying.get(enum_name)
        if underlying is None:
            raise CompilerError(
                f"{field_name}: {enum_name} declares no underlying type, so its wire encoding "
                f"cannot be derived -- give the enum one as a second base "
                f"(class {enum_name}(IntEnum, uint8)) or pass field(type=...)"
            )
        return _with_endian(_default_enum_wire(underlying), endian, field_name)

    # ---- field-type walker -------------------------------------------------

    def type(self, field_name: str, ann: _Ann, call: _Ann, scope: str = "") -> FieldType | None:
        type_kw = _name_kwarg(call, "field", "type")
        prefix = _repeat_prefix(call, field_name)
        endian = _endian_kwarg(call, field_name)
        values = _literal_values(ann, field_name)
        if values is not None:
            return self._literal_type(values, field_name, type_kw, endian)
        cases = _flatten_union(ann)
        if cases is not None:
            return self._union_type(cases, field_name, type_kw, prefix, endian, scope)
        return self._base_type(ann, type_kw, prefix, field_name, endian, scope)

    def _literal_type(
        self, values: tuple[bool | int, ...], field_name: str, type_kw: str | None, endian: Endian | None
    ) -> LiteralType:
        """`Literal[V, ...]`: the wire carries a constant the read checks against.
        A bool takes the one-byte wire by itself; an integer needs `field(type=)`
        to say how wide it is."""
        if all(isinstance(v, bool) for v in values):
            wire = PrimitiveType(name="bool")
        elif type_kw is not None and type_kw in INTEGER_PRIMITIVES:
            wire = PrimitiveType(name=type_kw)
        else:
            raise CompilerError(
                f"{field_name}: an integer Literal[...] needs its wire width -- spell field(type=<integer primitive>)"
            )
        return LiteralType(values, _with_endian(wire, endian, field_name))

    def _union_type(
        self,
        cases: list[griffe.Expr | str],
        field_name: str,
        type_kw: str | None,
        prefix: PrimitiveType,
        endian: Endian | None,
        scope: str,
    ) -> FieldType | None:
        if len(cases) == 2 and sum(_is_none(a) for a in cases) == 1:
            inner_ann = next(a for a in cases if not _is_none(a))
            base = self._base_type(inner_ann, type_kw, prefix, field_name, endian, scope)
            return None if base is None else OptionalType(base)
        types: list[FieldType | None] = []
        for case in cases:
            if _is_none(case):
                types.append(None)
                continue
            t = self._base_type(case, type_kw, prefix, field_name, endian, scope)
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
        endian: Endian | None,
        scope: str = "",
    ) -> FieldType | None:
        if isinstance(ann, griffe.ExprSubscript):
            bits = _bitset_size(ann, field_name)
            if bits is not None:
                return BitsetType(size=bits)
            elem = _list_element(ann, field_name)
            if elem is not None:
                inner = self._base_type(elem, type_kw, prefix, field_name, endian, scope)
                return None if inner is None else RepeatedType(inner=inner, prefix=prefix)
            mapping = _map_parts(ann, field_name)
            if mapping is None:
                return None
            key = self._base_type(mapping[0], type_kw, prefix, field_name, endian, scope)
            value = self._base_type(mapping[1], type_kw, prefix, field_name, endian, scope)
            if key is None or value is None:
                return None
            return MappingType(key=key, value=value, prefix=prefix)
        cases = _flatten_union(ann)
        if cases is not None:
            return self._union_type(cases, field_name, type_kw, prefix, endian, scope)
        dotted = _dotted_name(ann)
        if dotted is not None:
            if dotted in BUILTIN_ANNOTATIONS:
                return StructType(BUILTIN_ANNOTATIONS[dotted])
            # `Owner.Inner` names a nested type from outside its owner.
            qualified = self.lookup(dotted, scope)
            if qualified is not None:
                return self._declared_type(qualified, type_kw, field_name, endian)
        if not isinstance(ann, griffe.ExprName):
            return None
        name = ann.name
        resolved = self.lookup(name, scope)
        if resolved is not None:
            return self._declared_type(resolved, type_kw, field_name, endian)
        if name in PRIMITIVES:
            return _with_endian(
                PrimitiveType(name=name, wire=_wire_override(type_kw, name, field_name)), endian, field_name
            )
        alias = self.aliases.get(name)
        if isinstance(alias, PrimitiveAlias):
            return _with_endian(
                PrimitiveType(
                    name=alias.primitive,
                    alias=alias.name,
                    wire=_wire_override(type_kw, alias.primitive, field_name),
                ),
                endian,
                field_name,
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


#: The enum bases the DSL recognises. Only a plain `Enum` takes a `3, "Wire"` member:
#: `IntEnum` and `StrEnum` coerce a member to their own type and a pair is not one.
_ENUM_BASES = ("Enum", "IntEnum", "IntFlag", "StrEnum")


def is_enum(cls: griffe.Class) -> bool:
    return any(_base_name(b) in _ENUM_BASES for b in cls.bases)


def _takes_paired_value(cls: griffe.Class) -> bool:
    return any(_base_name(b) == "Enum" for b in cls.bases)


def nested_declarations(decls: list[griffe.Class]) -> list[list[griffe.Class]]:
    """The classes declared inside `decls`, grouped by name in source order --
    `SourceTree.declarations_of` one level down. A redeclared owner contributes
    each of its bodies, so a name declared in several lands in one group."""
    groups: dict[str, list[griffe.Class]] = {}
    for decl in decls:
        for cls in decl.classes.values():
            if cls.is_alias:
                continue
            groups.setdefault(cls.name, []).append(cls)
    return list(groups.values())


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


#: Primitive encoding -> size in bytes, for the encodings whose bytes have an order.
_FIXED_WIDTHS: dict[str, int] = {name: size for name, (size, _) in _INT_WIDTHS.items()} | {"float": 4, "double": 8}


def _default_enum_wire(underlying: PrimitiveType) -> PrimitiveType:
    """The default wire encoding: underlying type, enum-as-value and compression.
    One byte has nothing to compress and goes as-is; wider compresses to
    `[u]varint32`, or `[u]varint64` at eight, signedness following the underlying."""
    size, signed = _INT_WIDTHS[underlying.name]
    if size == 1:
        return underlying
    width = 64 if size == 8 else 32
    return PrimitiveType(name=f"{'' if signed else 'u'}varint{width}")


def _positional(node: griffe.ExprCall) -> list[griffe.Expr | str]:
    return [a for a in node.arguments if not isinstance(a, griffe.ExprKeyword)]


def _unwrapped(t: FieldType | None) -> FieldType | None:
    """A gated field is spelled as its bare payload, so a predicate reading it
    sees through the `when=`."""
    return _unwrapped(t.inner) if isinstance(t, CondType) else t


def _is_sized(t: FieldType | None) -> bool:
    """Whether the field's C++ spelling has a `.size()`. An optional is a
    `std::optional`, which has none."""
    t = _unwrapped(t)
    if isinstance(t, (RepeatedType, MappingType)):
        return True
    return isinstance(t, PrimitiveType) and t.name in ("str", "bytes")


def _one_underlying(decls: list[griffe.Class]) -> PrimitiveType | None:
    """The underlying type every declaration of an enum shares. A redeclaration
    renumbers members; changing the C++ type under them would change the wire
    encoding of every field that names the enum, silently."""
    underlying = [enum_underlying_of(d) for d in decls]
    if any(u != underlying[0] for u in underlying):
        spelled = sorted({"int" if u is None else u.name for u in underlying})
        raise CompilerError(
            f"{decls[0].name}: every redeclaration must share one underlying type, got {', '.join(spelled)}"
        )
    return underlying[0]


def enum_underlying_of(cls: griffe.Class) -> PrimitiveType | None:
    """The enum's C++ underlying type, written as a second base
    (`class MemoryCategory(IntEnum, uint8)`). None means the C++ default, `int`."""
    for base in cls.bases:
        name = _base_name(base)
        if name is None or name in _ENUM_BASES:
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
        # value(N, since=, until=): N is the first positional, and mandatory when
        # gated -- auto-numbering a member that is absent at some snapshot would
        # shift its siblings' wire numbers.
        positionals = _positionals(value)
        if positionals:
            explicit = _as_int(positionals[0])
            if explicit is not None:
                return explicit
        raise CompilerError(f"{enum_name}.{name}: value() needs an explicit wire number, e.g. value(601, since=1001)")
    number = _as_int(value)
    if number is None:
        raise CompilerError(f"{enum_name}.{name}: enum member must be an int literal or auto(), got {value!r}")
    return number


def _positionals(call: griffe.ExprCall) -> list[_Ann]:
    return [a for a in call.arguments if not isinstance(a, griffe.ExprKeyword)]


def _split_wire_name(
    value: griffe.Expr | str, enum_name: str, member: str, paired: bool
) -> tuple[griffe.Expr | str, str | None]:
    """The member's value, then the exact string BDS writes for a member whose PEP 8
    spelling does not map back onto it.

    A plain `Enum` pairs the two the way `enum` itself does —
    `DOWNLOADING_FINISHED = 3, "DownloadingFinished"`. `IntEnum` and `StrEnum` coerce a
    member to their own type, so a pair is not a value there and `value()` takes the
    string as its second positional instead."""
    if isinstance(value, griffe.ExprTuple):
        if not paired:
            raise CompilerError(
                f"{enum_name}.{member}: only a plain Enum pairs a value with a wire name -- declare "
                f'`class {enum_name}(Enum, ...)`, or spell it value({member.lower()}_number, "WireName")'
            )
        if len(value.elements) != 2:
            raise CompilerError(
                f"{enum_name}.{member}: an enum member is a value or a (value, wire name) pair, "
                f"got {len(value.elements)} elements"
            )
        return value.elements[0], _wire_text(value.elements[1], enum_name, member)
    if _is_call(value, "value"):
        positionals = _positionals(cast(griffe.ExprCall, value))
        if len(positionals) > 1:
            return value, _wire_text(positionals[1], enum_name, member)
        spelled = _call_arg(value, "value", "name")
        if spelled is not None:
            return value, _wire_text(spelled, enum_name, member)
    return value, None


def _pinned(t: FieldType | None, snapshot: int | None, field_name: str) -> FieldType | None:
    """`field(snapshot=)` — resolve this reference at a fixed snapshot rather than
    at the declaring context's.

    BDS cerealised packets one at a time, so one class name meant two wire shapes
    at one protocol version, chosen by the packet that contained it. Where BDS gave
    the two forms separate names they are separate declarations; where it reused the
    name, the older shape is still declared -- gated to the era before the migration
    -- and only unreachable. This names it."""
    if snapshot is None or t is None:
        return t
    pinned = _pin(t, snapshot)
    if pinned is None:
        raise CompilerError(
            f"{field_name}: field(snapshot=...) pins a struct or enum reference, got {t.kind}"
        )
    return pinned


def _pin(t: FieldType, snapshot: int) -> FieldType | None:
    """The type with its struct/enum leaf pinned, or None if it has none."""
    if isinstance(t, (StructType, EnumType)):
        return replace(t, pin=snapshot)
    if isinstance(t, (OptionalType, RepeatedType)):
        inner = _pin(t.inner, snapshot)
        return None if inner is None else replace(t, inner=inner)
    return None


def _wire_text(spelled: _Ann, enum_name: str, member: str) -> str:
    if not isinstance(spelled, str) or spelled[:1] not in "'\"":
        raise CompilerError(f"{enum_name}.{member}: the wire name must be a string literal, got {spelled}")
    text = spelled.strip("'\"")
    if not text:
        raise CompilerError(f"{enum_name}.{member}: the wire name must be a non-empty string literal")
    return text


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


def _literal_values(ann: _Ann, field_name: str) -> tuple[bool | int, ...] | None:
    """The values of a `Literal[...]` annotation, or None for anything else. They
    are the set the read accepts, so several may be listed; all take one type."""
    if not (isinstance(ann, griffe.ExprSubscript) and isinstance(ann.left, griffe.ExprName)):
        return None
    if ann.left.name != "Literal":
        return None
    slice_ = ann.slice
    spelled = slice_.elements if isinstance(slice_, griffe.ExprTuple) else [slice_]
    values: list[bool | int] = []
    for element in spelled:
        text = str(element)
        number = _as_int(text)
        if text in ("True", "False"):
            values.append(text == "True")
        elif number is not None:
            values.append(number)
        else:
            raise CompilerError(f"{field_name}: Literal[...] takes bool or integer values, got {text}")
    if len({isinstance(v, bool) for v in values}) != 1:
        raise CompilerError(f"{field_name}: Literal[...] values must all take one type")
    return tuple(values)


def _bitset_size(ann: griffe.ExprSubscript, field_name: str) -> int | None:
    """The width of a `bitset[N]` subscript, or None for anything else. The
    width is baked into the C++ type, so it has to be an int literal."""
    if not (isinstance(ann.left, griffe.ExprName) and ann.left.name == "bitset"):
        return None
    size = _as_int(ann.slice)
    if size is None or size <= 0:
        raise CompilerError(f"{field_name}: bitset[...] needs a positive integer width, got {ann.slice}")
    return size


def _list_element(ann: griffe.ExprSubscript, field_name: str) -> griffe.Expr | str | None:
    """The element annotation of a `list[T]` subscript, or None for anything else."""
    if isinstance(ann.left, griffe.ExprName) and ann.left.name == "list":
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


def _endian_kwarg(call: _Ann, field_name: str) -> Endian | None:
    value = _call_arg(call, "field", "endian")
    if value is None:
        return None
    order = str(value).strip("'\"")
    if order not in ("big", "little"):
        raise CompilerError(f'{field_name}: field(endian=...) must be "big" or "little", got {order!r}')
    return cast(Endian, order)


def _with_endian(prim: PrimitiveType, endian: Endian | None, field_name: str) -> PrimitiveType:
    """Applies `field(endian=...)` to a primitive, rejecting an encoding whose
    bytes carry no order."""
    if endian is None:
        return prim
    if prim.encoding not in _FIXED_WIDTHS:
        raise CompilerError(
            f"{field_name}: field(endian=...) applies to a fixed-width primitive, got {prim.encoding!r}"
        )
    if _FIXED_WIDTHS[prim.encoding] == 1:
        raise CompilerError(f"{field_name}: field(endian=...) on a one-byte {prim.encoding} has no effect")
    return replace(prim, endian=endian)


def _is_call(expr: _Ann, fn_name: str) -> bool:
    return (
        isinstance(expr, griffe.ExprCall)
        and isinstance(expr.function, griffe.ExprName)
        and expr.function.name == fn_name
    )


def _call_arg(expr: _Ann, fn_name: str, kw: str) -> _Ann:
    if not _is_call(expr, fn_name):
        return None
    assert isinstance(expr, griffe.ExprCall)
    for arg in expr.arguments:
        if isinstance(arg, griffe.ExprKeyword) and arg.name == kw:
            return arg.value
    return None


#: What each DSL callable accepts: the keywords the compiler reads, and the
#: ones it does not implement paired with what to do instead. A keyword dropped
#: in silence is this compiler's worst failure -- the modeller believes the wire
#: changed and nothing did, and no golden can catch it -- so an unread keyword
#: is a parse error, the way protoc rejects an unknown field option.
_Keywords = tuple[frozenset[str], Mapping[str, str]]

_NO_DEPRECATION = "the compiler emits no [[deprecated]] attribute; drop the keyword or say it in the commit message"

_FIELD_KEYWORDS: _Keywords = (
    frozenset(
        {"type", "since", "until", "when", "endian", "prefix", "count", "snapshot", "_group_when", "_group_id"}
    ),
    {
        "tag": (
            "a union is always prefixed by a uvarint32 index over its cases in declaration order -- "
            "for an enum-discriminated one, declare the discriminator as a real field and gate each "
            "arm on it with field(when=...)"
        ),
    },
)

_VALUE_KEYWORDS: _Keywords = (frozenset({"name", "since", "until"}), {"deprecated": _NO_DEPRECATION})

_PACKET_KEYWORDS: _Keywords = (frozenset({"id", "since", "until"}), {})

_TYPE_KEYWORDS: _Keywords = (frozenset({"since", "until"}), {"deprecated": _NO_DEPRECATION})


def _check_keywords(expr: _Ann, fn_name: str, keywords: _Keywords, where: str, positional: int = 0) -> None:
    """Reject a call the compiler cannot honour as written."""
    if not _is_call(expr, fn_name):
        return
    assert isinstance(expr, griffe.ExprCall)
    known, unimplemented = keywords
    seen = 0
    for arg in expr.arguments:
        if not isinstance(arg, griffe.ExprKeyword):
            seen += 1
            if seen > positional:
                allowed = "keyword arguments only" if positional == 0 else f"{positional} positional argument(s)"
                raise CompilerError(f"{where}: {fn_name}() takes {allowed}, got {arg}")
            continue
        if arg.name in unimplemented:
            raise CompilerError(
                f"{where}: {fn_name}({arg.name}=...) is documented but not implemented -- {unimplemented[arg.name]}"
            )
        if arg.name not in known:
            spellable = ", ".join(sorted(k for k in known if not k.startswith("_")))
            raise CompilerError(f"{where}: {fn_name}() has no {arg.name!r} keyword; valid: {spellable}")


def _check_decorators(cls: griffe.Class) -> None:
    for dec in cls.decorators:
        _check_keywords(dec.value, "packet", _PACKET_KEYWORDS, cls.name)
        _check_keywords(dec.value, "type", _TYPE_KEYWORDS, cls.name)


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
