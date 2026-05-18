"""griffe frontend: load DSL modules and lower them to the language-agnostic
`schema` IR. Every griffe-specific concern -- module loading, import following,
`Expr` parsing -- is confined to this class.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TypeGuard, cast

import griffe

from .schema import (
    PRIMITIVES,
    VARINT_PRIMITIVES,
    Alias,
    CompilerError,
    Enum,
    EnumMember,
    EnumRef,
    Field,
    Map,
    Mapping,
    Module,
    Named,
    Opt,
    Optional,
    Primitive,
    Repeat,
    Repeated,
    Scalar,
    Schema,
    Str,
    Struct,
    StructRef,
    TypeRef,
    Wire,
)

#: An annotation, decorator argument, or literal as griffe surfaces it: an
#: expression node, a raw-source literal string, or absent.
_Ann = griffe.Expr | str | None


class Frontend:
    def __init__(self, import_paths: list[Path]):
        self._import_paths = import_paths

    def load(self, inputs: tuple[Path, ...]) -> Schema:
        self._griffe: dict[str, griffe.Module] = {}
        self._stems: dict[str, str] = {}
        outputs: list[str] = []
        for inp in inputs:
            name, root = self._module_name_and_root(inp)
            self._griffe[name] = cast(
                griffe.Module,
                griffe.load(name, search_paths=[str(root)], allow_inspection=False),
            )
            self._stems[name] = inp.stem
            outputs.append(name)
        self._follow_imports(outputs)
        self._classify()
        modules = {name: self._module(name) for name in self._griffe}
        return Schema(modules, tuple(outputs))

    # --- module loading ------------------------------------------------------

    def _follow_imports(self, roots: list[str]) -> None:
        """Load modules referenced by `from X.Y import ...` so their types are
        resolvable. Imported-only modules supply context but produce no output."""
        pending = list(roots)
        while pending:
            for dep in self._imports_of(self._griffe[pending.pop()]):
                if dep in self._griffe:
                    continue
                parts = dep.split(".")
                for ip in self._import_paths:
                    candidate = ip.joinpath(*parts).with_suffix(".py")
                    if candidate.is_file():
                        self._griffe[dep] = cast(
                            griffe.Module,
                            griffe.load(
                                dep, search_paths=[str(ip)], allow_inspection=False
                            ),
                        )
                        pending.append(dep)
                        break

    def _module_name_and_root(self, path: Path) -> tuple[str, Path]:
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

    @staticmethod
    def _imports_of(mod: griffe.Module) -> set[str]:
        """Dotted source modules behind this module's `from X.Y import ...`
        bindings. Modules with a `_`-prefixed component (the DSL itself) are
        omitted: they have no header to emit or include."""
        out: set[str] = set()
        for member in mod.members.values():
            target = getattr(member, "target_path", None)
            if target is None or "." not in str(target):
                continue
            dep = str(target).rsplit(".", 1)[0]
            if not any(part.startswith("_") for part in dep.split(".")):
                out.add(dep)
        return out

    # --- type classification (spans every loaded module) ---------------------

    def _classify(self) -> None:
        self._enum_names: set[str] = set()
        self._struct_names: set[str] = set()
        self._alias_primitive: dict[str, str] = {}
        for mod in self._griffe.values():
            for cls in mod.classes.values():
                if cls.is_alias:
                    continue
                bucket = self._enum_names if self._is_int_enum(cls) else self._struct_names
                bucket.add(cls.name)
            for alias in self._aliases(mod):
                self._alias_primitive[alias.name] = alias.primitive

    # --- module lowering -----------------------------------------------------

    def _module(self, name: str) -> Module:
        mod = self._griffe[name]
        types: list[Enum | Struct] = []
        for cls in mod.classes.values():
            if cls.is_alias:
                continue
            types.append(self._enum(cls) if self._is_int_enum(cls) else self._struct(cls))
        imports = tuple(
            sorted(d for d in self._imports_of(mod) if d in self._griffe and d != name)
        )
        return Module(
            name, self._stems.get(name, name), self._package(mod),
            tuple(types), self._aliases(mod), imports,
        )

    @staticmethod
    def _package(mod: griffe.Module) -> str | None:
        attr = mod.attributes.get("package")
        if attr is None or attr.value is None:
            return None
        return str(attr.value).strip("'\"")

    def _aliases(self, mod: griffe.Module) -> tuple[Alias, ...]:
        """`Name = <primitive>` and PEP 695 `type Name = <primitive>`, skipping
        names that are themselves built-in primitives."""
        out: list[Alias] = []
        sources = list(mod.attributes.items()) + list(mod.type_aliases.items())
        for name, attr in sources:
            if name == "package" or name in PRIMITIVES or attr.value is None:
                continue
            if isinstance(attr.value, griffe.ExprName) and attr.value.name in PRIMITIVES:
                out.append(Alias(name, attr.value.name))
        return tuple(out)

    def _enum(self, cls: griffe.Class) -> Enum:
        members: list[EnumMember] = []
        for name, attr in cls.attributes.items():
            if attr.value is None:
                continue
            parsed = self._member_value(attr.value)
            if parsed is not None:
                members.append(EnumMember(name, *parsed))
        return Enum(cls.name, tuple(members), self._class_since(cls))

    def _struct(self, cls: griffe.Class) -> Struct:
        nested: list[Enum] = []
        for inner in cls.classes.values():
            if inner.is_alias or not self._is_int_enum(inner):
                continue
            enum = self._enum(inner)
            self._reject_versioned_nested(cls.name, enum)
            nested.append(enum)
        nested_names = frozenset(e.name for e in nested)
        fields = tuple(self._field(attr, nested_names) for attr in cls.attributes.values())
        return Struct(
            cls.name, fields, tuple(nested),
            self._packet_id(cls), self._packet_since(cls),
        )

    @staticmethod
    def _reject_versioned_nested(owner: str, enum: Enum) -> None:
        """A nested enum's member set is the owning packet's -- it has no
        version axis of its own. Version such an enum at module scope."""
        if enum.since is not None:
            raise CompilerError(
                f"{owner}.{enum.name}: a nested enum cannot carry @enum(since=); "
                f"declare it at module scope to version it"
            )
        for m in enum.members:
            if m.since is not None or m.until is not None:
                raise CompilerError(
                    f"{owner}.{enum.name}.{m.name}: a nested enum cannot have "
                    f"version-gated members; declare it at module scope to version it"
                )

    def _field(self, attr: griffe.Attribute, nested: frozenset[str]) -> Field:
        call = attr.value
        since = self._int_kwarg(call, "field", "since") if call is not None else None
        return Field(
            attr.name,
            self._typeref(attr.annotation, attr.name),
            self._wire(attr.name, attr.annotation, call, nested),
            since,
        )

    # --- type references -----------------------------------------------------

    def _typeref(self, ann: _Ann, field_name: str) -> TypeRef | None:
        if ann is None:
            return None
        if self._is_optional(ann):
            inner = self._typeref(self._optional_inner(ann), field_name)
            return Optional(inner) if inner is not None else None
        if isinstance(ann, griffe.ExprSubscript):
            repeat = self._repeat_parts(ann, field_name)
            if repeat is not None:
                elem_ann, count = repeat
                inner = self._typeref(elem_ann, field_name)
                return Repeated(inner, count) if inner is not None else None
            mapping = self._map_parts(ann, field_name)
            if mapping is not None:
                key = self._typeref(mapping[0], field_name)
                value = self._typeref(mapping[1], field_name)
                if key is None or value is None:
                    return None
                return Mapping(key, value)
            return None
        if isinstance(ann, griffe.ExprName):
            return Primitive(ann.name) if ann.name in PRIMITIVES else Named(ann.name)
        return None

    # --- wire encodings ------------------------------------------------------

    def _wire(
        self, field_name: str, ann: _Ann, call: _Ann, nested: frozenset[str]
    ) -> Wire | None:
        endian = self._str_kwarg(call, "field", "endian") if call is not None else None
        if endian is not None and endian not in ("big", "little"):
            raise CompilerError(
                f'{field_name}: field(endian=...) must be "big" or "little", '
                f"got {endian!r}"
            )
        type_kw = self._name_kwarg(call, "field", "type") if call is not None else None
        prefix = self._repeat_prefix(call, field_name)
        if self._is_optional(ann):
            base = self._base_wire(
                self._optional_inner(ann), type_kw, prefix, nested, field_name
            )
            if base is None:
                return None
            if endian is not None:
                raise CompilerError(self._endian_scope_error(field_name))
            discriminator = type_kw == "Union"
            if discriminator and isinstance(base, EnumRef):
                raise CompilerError(
                    f"{field_name}: an optional enum field needs field(type=) for "
                    f"the enum wire primitive and so cannot also use type=Union"
                )
            present_tag = 1 if discriminator and self._none_first(ann) else 0
            return Opt(base, discriminator, present_tag)
        base = self._base_wire(ann, type_kw, prefix, nested, field_name)
        if base is None:
            return None
        return self._with_endian(base, endian, field_name)

    def _repeat_prefix(self, call: _Ann, field_name: str) -> Scalar:
        """The length-prefix scalar a `list[T]` field uses -- `field(prefix=)`
        or the `uvarint32` default. Ignored by fixed-length `tuple` fields."""
        name = (
            self._name_kwarg(call, "field", "prefix") if call is not None else None
        )
        if name is None:
            return Scalar("uvarint32", varint=True)
        if name not in PRIMITIVES or name in ("str", "bool", "float", "double"):
            raise CompilerError(
                f"{field_name}: field(prefix=...) must be an integer primitive, "
                f"got {name!r}"
            )
        return Scalar(name, varint=name in VARINT_PRIMITIVES)

    def _repeat_parts(
        self, ann: griffe.ExprSubscript, field_name: str
    ) -> tuple[griffe.Expr | str, int | None] | None:
        """Classify a `list[T]` / `tuple[T, ...]` subscript into (element
        annotation, count) -- count None for a length-prefixed `list`, the
        element total for a fixed-length `tuple` -- or None for any other
        subscript. Rejects heterogeneous or variable-length tuples."""
        if not isinstance(ann.left, griffe.ExprName):
            return None
        if ann.left.name == "list":
            return ann.slice, None
        if ann.left.name != "tuple":
            return None
        slice_ = ann.slice
        elements: list[griffe.Expr | str] = (
            list(slice_.elements)
            if isinstance(slice_, griffe.ExprTuple)
            else [slice_]
        )
        named = [e for e in elements if isinstance(e, griffe.ExprName)]
        if not named or len(named) != len(elements):
            raise CompilerError(
                f"{field_name}: tuple[...] must spell out a fixed count of named "
                f"element types -- use list[T] for a variable-length list"
            )
        if any(e.name != named[0].name for e in named):
            raise CompilerError(
                f"{field_name}: tuple[...] elements must all be the same type"
            )
        return named[0], len(named)

    def _map_parts(
        self, ann: griffe.ExprSubscript, field_name: str
    ) -> tuple[griffe.Expr | str, griffe.Expr | str] | None:
        """The (key, value) annotations of a `dict[K, V]` subscript, or None
        for any other subscript."""
        if not (isinstance(ann.left, griffe.ExprName) and ann.left.name == "dict"):
            return None
        slice_ = ann.slice
        if not isinstance(slice_, griffe.ExprTuple) or len(slice_.elements) != 2:
            raise CompilerError(
                f"{field_name}: dict[...] needs exactly a key type and a value type"
            )
        return slice_.elements[0], slice_.elements[1]

    def _base_wire(
        self,
        ann: _Ann,
        type_kw: str | None,
        prefix: Scalar,
        nested: frozenset[str],
        field_name: str,
    ) -> Wire | None:
        if isinstance(ann, griffe.ExprSubscript):
            repeat = self._repeat_parts(ann, field_name)
            if repeat is not None:
                elem_ann, count = repeat
                inner = self._base_wire(elem_ann, type_kw, prefix, nested, field_name)
                if inner is None:
                    return None
                return Repeat(inner, prefix if count is None else None, count)
            mapping = self._map_parts(ann, field_name)
            if mapping is not None:
                key = self._base_wire(mapping[0], type_kw, prefix, nested, field_name)
                value = self._base_wire(mapping[1], type_kw, prefix, nested, field_name)
                if key is None or value is None:
                    return None
                return Map(key, value, prefix)
            return None
        if not isinstance(ann, griffe.ExprName):
            return None
        name = ann.name
        if name in nested or name in self._enum_names:
            scalar = self._enum_wire(type_kw, field_name)
            if scalar is None and name in nested:
                raise CompilerError(
                    f"{field_name}: a nested enum cannot be string-coded "
                    f"(field(type=str)) -- use an integer wire primitive, or lift "
                    f"the enum to module scope"
                )
            return EnumRef(name, scalar)
        if name in self._struct_names:
            return StructRef(name)
        if name == "str":
            return Str()
        if name in PRIMITIVES:
            return Scalar(name, varint=name in VARINT_PRIMITIVES)
        if name in self._alias_primitive:
            target = self._alias_primitive[name]
            return Scalar(target, varint=target in VARINT_PRIMITIVES)
        return None

    @staticmethod
    def _enum_wire(type_kw: str | None, field_name: str) -> Scalar | None:
        """Resolve `field(type=...)` for an enum field. `str` is name-coded
        (returns None); any other primitive is the integer wire."""
        if type_kw is None:
            raise CompilerError(
                f"{field_name}: enum-typed field requires field(type=<primitive>) "
                f"-- e.g. type=uvarint32 or type=str"
            )
        if type_kw == "str":
            return None
        if type_kw not in PRIMITIVES:
            raise CompilerError(
                f"{field_name}: unknown wire primitive {type_kw!r}; "
                f"valid: {sorted(PRIMITIVES)}"
            )
        return Scalar(type_kw, varint=type_kw in VARINT_PRIMITIVES)

    def _with_endian(self, base: Wire, endian: str | None, field_name: str) -> Wire:
        if endian is None:
            return base
        big = endian == "big"
        if isinstance(base, Scalar):
            return replace(base, big_endian=big)
        if isinstance(base, EnumRef) and base.scalar is not None and not base.scalar.varint:
            return replace(base, scalar=replace(base.scalar, big_endian=big))
        raise CompilerError(self._endian_scope_error(field_name))

    @staticmethod
    def _endian_scope_error(field_name: str) -> str:
        return (
            f"{field_name}: field(endian=...) only applies to fixed-width "
            f"primitive or fixed-width integer-coded enum fields"
        )

    # --- griffe Expr helpers -------------------------------------------------

    @staticmethod
    def _is_optional(ann: object) -> TypeGuard[griffe.ExprBinOp]:
        return (
            isinstance(ann, griffe.ExprBinOp)
            and ann.operator == "|"
            and (ann.right == "None" or ann.left == "None")
        )

    @staticmethod
    def _optional_inner(ann: griffe.ExprBinOp) -> griffe.Expr | str:
        return ann.left if ann.right == "None" else ann.right

    @staticmethod
    def _none_first(ann: griffe.ExprBinOp) -> bool:
        """True for `None | T`, False for `T | None` -- the union-index order
        that fixes which discriminator value means present."""
        return ann.left == "None"

    @staticmethod
    def _is_int_enum(cls: griffe.Class) -> bool:
        return any(
            isinstance(b, griffe.ExprName) and b.name == "IntEnum" for b in cls.bases
        )

    @staticmethod
    def _as_int(value: object) -> int | None:
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _call_arg(expr: _Ann, fn_name: str, kw: str) -> _Ann:
        """The value expression of `fn_name(..., kw=<value>)`, else None."""
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

    def _int_kwarg(self, expr: _Ann, fn_name: str, kw: str) -> int | None:
        value = self._call_arg(expr, fn_name, kw)
        return self._as_int(value) if value is not None else None

    def _name_kwarg(self, expr: _Ann, fn_name: str, kw: str) -> str | None:
        value = self._call_arg(expr, fn_name, kw)
        return value.name if isinstance(value, griffe.ExprName) else None

    def _str_kwarg(self, expr: _Ann, fn_name: str, kw: str) -> str | None:
        value = self._call_arg(expr, fn_name, kw)
        if isinstance(value, str) and len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
            return value[1:-1]
        return None

    def _class_since(self, cls: griffe.Class) -> int | None:
        for dec in cls.decorators:
            since = self._int_kwarg(dec.value, "enum", "since")
            if since is not None:
                return since
        return None

    def _packet_id(self, cls: griffe.Class) -> int | None:
        for dec in cls.decorators:
            pid = self._int_kwarg(dec.value, "packet", "id")
            if pid is not None:
                return pid
        return None

    def _packet_since(self, cls: griffe.Class) -> int | None:
        for dec in cls.decorators:
            since = self._int_kwarg(dec.value, "packet", "since")
            if since is not None:
                return since
        return None

    def _member_value(self, value: _Ann) -> tuple[int, int | None, int | None] | None:
        """Parse `0` or `value(N, since=V, until=U)` into (value, since, until)."""
        direct = self._as_int(value)
        if direct is not None:
            return direct, None, None
        if not (
            isinstance(value, griffe.ExprCall)
            and isinstance(value.function, griffe.ExprName)
            and value.function.name == "value"
            and value.arguments
        ):
            return None
        ivalue = self._as_int(value.arguments[0])
        if ivalue is None:
            return None
        return (
            ivalue,
            self._int_kwarg(value, "value", "since"),
            self._int_kwarg(value, "value", "until"),
        )
