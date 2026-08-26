"""`MessageGenerator` — one struct shape: its `struct { ... };` definition and
its `Serializer<T>` specialization (declaration in the header, out-of-line
bodies in the source). protoc analog: `compiler/cpp/cpp_message.{h,cc}`.

The serializer bodies iterate the struct's fields and delegate each to the
`FieldGenerator` its `FieldGeneratorMap` holds — protoc's
`field_generators_.get(field).GenerateSerialize...` pattern.
"""

from __future__ import annotations

from bedrock_protocol.descriptor import CondType, Enum, Field, FieldType, LiteralType, Predicate, Struct

from .enum import EnumGenerator
from .field import FieldGeneratorMap, FileContext, cpp_type, render_predicate, type_includes
from .helpers import INCLUDE_PREFIX, snapshot_namespace
from .printer import Printer


def _has_kind(pred: Predicate, kind: str) -> bool:
    return pred.kind == kind or any(_has_kind(o, kind) for o in pred.operands)


class MessageGenerator:
    """One (possibly snapshot-narrowed) `Struct` → its C++ struct + serializer.

    `qualified` is the `Serializer<...>` target spelling (`Foo` when
    unversioned, `v1001::Foo` for a snapshot); `snapshot` drives the
    snapshot-qualified references inside the serializer bodies.

    `nested_anchor` is the snapshot whose namespace holds the canonical
    definitions of this struct's nested types. When set, the body aliases them
    (`using ActionType = base::Owner::ActionType;`) instead of defining them
    again, so a nested type stays one C++ type across every snapshot of its
    owner. `fresh_nested` names the ones that do change, which are defined here
    even under an anchor -- a sibling moving must not cost the others their
    identity.

    `owner` is the namespace the struct *definition* is emitted into, which
    decides how a reference out of the pre-cereal tree is spelled there. The
    serializer bodies are emitted at file scope whatever the struct is, so they
    always spell a reference in full and carry no owner.

    `nested_of` is set on the generator for a nested type and names the owner
    whose nested namespace the definition lands in, so a sibling reference is
    spelled bare -- the owner class that would qualify it is not open yet."""

    def __init__(
        self,
        struct: Struct,
        ctx: FileContext,
        *,
        snapshot: int | None = None,
        qualified: str | None = None,
        nested_anchor: int | None = None,
        owner: str | None = None,
        fresh_nested: frozenset[str] = frozenset(),
        nested_of: str | None = None,
    ) -> None:
        self._struct = struct
        self._ctx = ctx
        self._snapshot = snapshot
        self._qualified = qualified if qualified is not None else struct.name
        self._anchor = nested_anchor
        self._fresh_nested = fresh_nested
        self._owner = owner
        self._nested_of = nested_of
        self._field_generators = FieldGeneratorMap(struct, ctx, snapshot)

    # --- type definition ----------------------------------------------------

    def generate_class_definition(self, p: Printer) -> None:
        """`struct Name { nested... [static constexpr int Id;] fields... };`.

        A member naming a versioned type is snapshot-qualified rather than left
        to the enclosing namespace. A snapshot namespace holds only the types
        its own file versions, and two files need not share a snapshot set, so
        an unqualified name in a namespace the referenced file does not emit
        escapes to file scope and binds the latest-version alias."""
        rendered: list[tuple[str, str]] = []
        for f in self._struct.fields:
            (version,) = f.versions
            if isinstance(version.type, LiteralType):  # a wire-only constant declares no member
                continue
            ctype = self._spell(version.type)
            if ctype is None:
                p.print(f"struct {self._struct.name} {{}};\n")
                return
            p.add_includes(*type_includes(version.type))
            rendered.append((ctype, f.name))
        self._generate_nested_namespace(p)
        p.print(f"struct {self._struct.name} {{\n")
        p.indent()
        has_body = self._struct.packet_id is not None or bool(rendered)
        for inner in self._struct.nested:
            p.print(f"using {inner.name} = {self._nested_namespace}::{inner.name};\n")
        if self._struct.nested and has_body:
            p.print("\n")
        if self._struct.packet_id is not None:
            p.print(f"static constexpr int Id = {self._struct.packet_id};\n")
        for ctype, fname in rendered:
            p.print(f"{ctype} {fname}{{}};\n")
        p.outdent()
        p.print("};\n")

    def _member_names(self) -> list[str] | None:
        """The members `generate_class_definition` emits, in order, or None where
        it emits an empty struct. Mirrors that walk exactly: reflection that
        disagreed with the definition would be worse than none."""
        names: list[str] = []
        for f in self._struct.fields:
            (version,) = f.versions
            if isinstance(version.type, LiteralType):  # a wire-only constant declares no member
                continue
            if self._spell(version.type) is None:
                return None
            names.append(f.name)
        return names

    # --- reflection (Boost.PFR-like member names and access) ----------------

    def generate_reflection(self, p: Printer, qualified: str, type_name: str | None = None) -> None:
        p.add_includes(f"<{INCLUDE_PREFIX}/detail/reflect.hpp>", "<array>", "<cstddef>", "<string_view>")
        names = self._member_names() or []
        spelled = type_name if type_name is not None else self._struct.name
        p.print("template <>\n")
        p.print(f"inline constexpr bool is_reflected_struct_v<{qualified}> = true;\n\n")
        p.print("template <>\n")
        p.print(f'inline constexpr std::string_view struct_name_v<{qualified}>{{"{spelled}"}};\n\n')
        p.print("template <>\n")
        p.print(f"inline constexpr std::array<std::string_view, {len(names)}> field_names_v<{qualified}>{{{{\n")
        p.indent()
        for name in names:
            p.print(f'"{name}",\n')
        p.outdent()
        p.print("}};\n")
        if not names:
            return
        p.print("\ntemplate <>\n")
        p.print(f"struct field_accessor<{qualified}> {{\n")
        p.indent()
        p.print("template <std::size_t I, typename S>\n")
        p.print("static constexpr auto &get(S &value) noexcept\n")
        with p.block():
            if len(names) == 1:
                p.print(f"return value.{names[0]};\n")
            else:
                for i, name in enumerate(names[:-1]):
                    head = "if constexpr" if i == 0 else "else if constexpr"
                    with p.block(f"{head} (I == {i})"):
                        p.print(f"return value.{name};\n")
                with p.block("else"):
                    p.print(f"return value.{names[-1]};\n")
        p.outdent()
        p.print("};\n")

    def _spell(self, t: FieldType | None) -> str | None:
        if t is None:
            return None
        return cpp_type(t, self._ctx, self._snapshot, self._owner, self._nested_of)

    @property
    def _dotted(self) -> str:
        """This struct's own dotted IR name, which its nested types hang off."""
        return f"{self._nested_of}.{self._struct.name}" if self._nested_of else self._struct.key

    @property
    def _nested_namespace(self) -> str:
        return f"{self._struct.name}_nested"

    def _generate_nested_namespace(self, p: Printer) -> None:
        """BDS's nested types, defined in a namespace ahead of their owner and
        aliased back into it, so `Owner::Inner` still names them everywhere.

        Defining them in the class body is the obvious spelling and libc++ and
        MSVC take it, but libstdc++ does not: a default member initializer is
        parsed only once the outermost enclosing class is complete, so while the
        owner is still open a sibling nested type reads as not
        default-constructible, and a `std::variant` over one instantiates with
        its default constructor deleted for good -- at the member that spells it
        and again at every later `emplace_back` in the serializer."""
        if not self._struct.nested:
            return
        p.print(f"namespace {self._nested_namespace} {{\n\n")
        for i, inner in enumerate(self._struct.nested):
            self._generate_nested(p, inner)
            # Definitions stand apart; a run of `using` aliases reads as one block.
            following = self._struct.nested[i + 1 : i + 2]
            run_of_aliases = following and self._aliases(inner) and self._aliases(following[0])
            if following and not run_of_aliases:
                p.print("\n")
        p.print(f"\n}}  // namespace {self._nested_namespace}\n\n")

    def _aliases(self, inner: Enum | Struct) -> bool:
        """Whether this nested type is emitted as an alias to an earlier
        snapshot's definition rather than defined here."""
        return self._anchor is not None and inner.name not in self._fresh_nested

    def _generate_nested(self, p: Printer, inner: Enum | Struct) -> None:
        if self._anchor is not None and self._aliases(inner):
            ns = snapshot_namespace(self._anchor)
            p.print(f"using {inner.name} = {ns}::{self._struct.name}::{inner.name};\n")
        elif isinstance(inner, Enum):
            EnumGenerator(inner).generate_definition(p)
        else:
            MessageGenerator(
                inner, self._ctx, snapshot=self._snapshot, owner=self._owner, nested_of=self._dotted
            ).generate_class_definition(p)

    # --- serializer ---------------------------------------------------------

    def generate_serializer_declaration(self, p: Printer) -> None:
        p.add_includes(
            f"<{INCLUDE_PREFIX}/serializer.hpp>", f"<{INCLUDE_PREFIX}/stream.hpp>", "<expected>", "<system_error>"
        )
        q = self._qualified
        p.print("template <>\n")
        p.print(f"struct Serializer<{q}> {{\n")
        p.indent()
        p.print(f"static void serialize(BinaryWriter &stream, const {q} &value);\n")
        p.print(f"static auto deserialize(BinaryReader &stream) -> std::expected<{q}, std::error_code>;\n")
        p.outdent()
        p.print("};\n")

    def generate_serializer_definition(self, p: Printer) -> None:
        p.add_includes(f"<{INCLUDE_PREFIX}/serializer.hpp>", f"<{INCLUDE_PREFIX}/stream.hpp>")
        q = self._qualified

        p.print(f"void Serializer<{q}>::serialize(BinaryWriter &stream, const {q} &value)\n")
        with p.block():
            for guard, group in self._groups():
                if guard is None:
                    (f,) = group
                    self._field_generators.get(f).generate_serialize(p, f"value.{f.name}")
                    continue
                with p.block(f"if ({self._condition(p, guard, 'value')})"):
                    for f in group:
                        self._field_generators.get(f).generate_serialize(p, f"value.{f.name}")
        p.print("\n")
        p.print(f"auto Serializer<{q}>::deserialize(BinaryReader &stream) -> std::expected<{q}, std::error_code>\n")
        with p.block():
            p.print(f"{q} out;\n")
            for guard, group in self._groups():
                if guard is None:
                    (f,) = group
                    with p.block():  # scope each field's read locals (v, present, len, tag, ...)
                        self._field_generators.get(f).generate_deserialize(p, f"out.{f.name}")
                    continue
                with p.block(f"if ({self._condition(p, guard, 'out')})"):
                    for f in group:
                        with p.block():
                            self._field_generators.get(f).generate_deserialize(p, f"out.{f.name}")
            p.print("return out;\n")

    # --- gated fields -------------------------------------------------------

    def _condition(self, p: Printer, guard: Predicate, base: str) -> str:
        # `.test(...)` spells a std::size_t cast; nothing else in the condition
        # names a header of its own.
        if _has_kind(guard, "bittest"):
            p.add_includes("<cstddef>")
        return render_predicate(guard, base, self._ctx, self._snapshot)

    def _groups(self) -> list[tuple[Predicate | None, list[Field]]]:
        """The fields partitioned into emission groups. Fields hoisted out of one
        `with field(when=...)` block share a `CondType.group` and emit under a
        single `if`; every other field stands alone."""
        groups: list[tuple[Predicate | None, list[Field]]] = []
        open_group: int | None = None
        for f in self._struct.fields:
            (version,) = f.versions
            t = version.type
            if not isinstance(t, CondType):
                groups.append((None, [f]))
                open_group = None
            elif t.group is not None and t.group == open_group:
                groups[-1][1].append(f)
            else:
                groups.append((t.predicate, [f]))
                open_group = t.group
        return groups
