from bedrock_protocol_compiler.cpp import names
from bedrock_protocol_compiler.cpp.alias import AliasGenerator
from bedrock_protocol_compiler.cpp.struct import shape_generator
from bedrock_protocol_compiler.descriptor import Alias, Enum, Module, Range, Struct
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import Schema, Shape, StructShape, roots_reached


def listed(schema: Schema, shape: Shape) -> list[str]:
    spelled = [names.qualified(schema, shape)]
    if isinstance(shape, StructShape):
        for child in shape.nested:
            spelled += listed(schema, child)
    return spelled


class FileGenerator:
    def __init__(self, schema: Schema, module: Module) -> None:
        self.schema = schema
        self.module = module
        self.own = [family for family in module.families if isinstance(family, Struct | Enum)]
        self.aliases = [AliasGenerator(each) for each in module.families if isinstance(each, Alias)]
        self.rank = {family: index for index, family in enumerate(self.own)}
        self.families: list[Struct | Enum] = []
        for family in self.own:
            self.place(family)
        self.generators = [
            shape_generator(schema, shape) for family in self.families for shape in schema.shapes(family)
        ]

    def place(self, family: Struct | Enum) -> None:
        if family in self.families:
            return
        for dependency in sorted(roots_reached(family) & self.rank.keys(), key=self.rank.__getitem__):
            self.place(dependency)
        self.families.append(family)

    def includes(self) -> set[str]:
        includes = {names.runtime("detail/reflect")}
        for generator in (*self.aliases, *self.generators):
            includes |= generator.includes()
        if any(family.packet_id is not None for family in self.families if isinstance(family, Struct)):
            includes.add(names.runtime("packet"))
        return includes - {names.generated(self.module.stem)}

    def generate(self, p: Printer) -> None:
        p.emit("#pragma once")
        p.emit("")
        includes = self.includes()
        groups = (
            [each for each in includes if not each.startswith(f"<{names.INCLUDE_DIR}/")],
            [each for each in includes if each.endswith(".hpp>")],
            [each for each in includes if each.endswith(".h>")],
        )
        for group in groups:
            for each in sorted(group):
                p.emit("#include $each$", each=each)
            if group:
                p.emit("")
        p.emit("namespace $namespace$ {", namespace=names.namespace(self.schema))
        p.emit("")
        self.primitive_aliases(p)
        self.definitions(p)
        self.selectors(p)
        self.packets(p)
        p.emit("namespace detail {")
        p.emit("")
        for generator in self.generators:
            generator.reflection(p)
        p.emit("}  // namespace detail")
        p.emit("")
        for generator in self.generators:
            generator.serializer_declaration(p)
        self.types(p)
        p.emit("}  // namespace $namespace$", namespace=names.namespace(self.schema))

    def primitive_aliases(self, p: Printer) -> None:
        if not self.aliases:
            return
        for alias in self.aliases:
            alias.definition(p)
        p.emit("namespace detail {")
        p.emit("")
        for alias in self.aliases:
            alias.trait(p)
        p.emit("}  // namespace detail")
        p.emit("")

    def definitions(self, p: Printer) -> None:
        current: tuple[str, ...] = ()
        for generator in self.generators:
            scope = names.scope(generator.shape)
            if scope != current:
                self.switch(p, current, scope)
                current = scope
            generator.definition(p)
            p.emit("")
        self.switch(p, current, ())

    def switch(self, p: Printer, closing: tuple[str, ...], opening: tuple[str, ...]) -> None:
        for part in reversed(closing):
            p.emit("}  // namespace $part$", part=part)
            p.emit("")
        for part in opening:
            p.emit("namespace $part$ {", part=part)
            p.emit("")

    def runs(self, family: Struct | Enum) -> list[tuple[Range, Shape]]:
        runs = [(run, shape) for shape in self.schema.shapes(family) for run in shape.ranges]
        return sorted(runs, key=lambda each: each[0].since or 0)

    def selectors(self, p: Printer) -> None:
        versioned = [family for family in self.families if self.schema.shapes(family)[0].versioned]
        for cereal in (True, False):
            families = [family for family in versioned if family.cereal == cereal]
            if not families:
                continue
            if not cereal:
                self.switch(p, (), ("legacy",))
            p.emit("namespace detail {")
            p.emit("")
            for family in families:
                p.emit(
                    """
                    template <int V>
                    struct $name$_;

                    """,
                    name=family.name,
                )
                for run, shape in self.runs(family):
                    p.emit(
                        """
                        template <int V> requires ($clause$)
                        struct $name$_<V> { using type = $type$; };

                        """,
                        clause=names.clause(run),
                        name=family.name,
                        type=names.qualified(self.schema, shape),
                    )
            p.emit("}  // namespace detail")
            p.emit("")
            for family in families:
                p.emit("template <int V> using $name$_ = typename detail::$name$_<V>::type;", name=family.name)
            p.emit("")
            for family in families:
                if (family, self.schema.latest) in self.schema.live:
                    p.emit("using $name$ = $name$_<$latest$>;", name=family.name, latest=self.schema.latest)
            p.emit("")
            if not cereal:
                self.switch(p, ("legacy",), ())

    def packets(self, p: Printer) -> None:
        packets = [family for family in self.families if isinstance(family, Struct) and family.packet_id is not None]
        for family in sorted(packets, key=lambda family: family.packet_id or 0):
            runs = self.runs(family)
            constraint = names.clause(Range(runs[0][0].since, runs[-1][0].until))
            spelled = (
                f"::{names.namespace(self.schema)}::{family.name}_<V>"
                if runs[0][1].versioned
                else names.qualified(self.schema, runs[0][1])
            )
            p.emit(
                """
                template <int V>$constraint$
                struct packet_of<V, $id$> { using type = $type$; };

                """,
                constraint=f" requires ({constraint})" if constraint else "",
                id=family.packet_id or 0,
                type=spelled,
            )

    def types(self, p: Printer) -> None:
        name = f"{self.module.stem}_types"
        plans: list[tuple[int | None, list[str], list[str]]] = []
        for version in self.schema.versions:
            cereal: list[str] = []
            legacy: list[str] = []
            for family in self.families:
                shape = self.schema.live.get((family, version))
                if shape is not None:
                    (cereal if family.cereal else legacy).extend(listed(self.schema, shape))
            if not plans or plans[-1][1:] != (cereal, legacy):
                plans.append((version if plans else None, cereal, legacy))
        if len(plans) > 1:
            p.emit(
                """
                template <int V>
                struct $name$;

                """,
                name=name,
            )
        for index, (since, cereal, legacy) in enumerate(plans):
            until = plans[index + 1][0] if index + 1 < len(plans) else None
            if len(plans) == 1:
                p.emit("template <int V>")
                p.emit("struct $name$ {", name=name)
            else:
                p.emit("template <int V> requires ($clause$)", clause=names.clause(Range(since, until)))
                p.emit("struct $name$<V> {", name=name)
            with p.indent():
                for member, entries in (("cereal", cereal), ("legacy", legacy)):
                    if not entries:
                        p.emit("using $member$ = type_list<>;", member=member)
                        continue
                    p.emit("using $member$ = type_list<", member=member)
                    with p.indent():
                        for entry in entries[:-1]:
                            p.emit("$entry$,", entry=entry)
                        p.emit("$entry$>;", entry=entries[-1])
            p.emit("};")
            p.emit("")
