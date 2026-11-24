from bedrock_protocol_compiler.cpp import names
from bedrock_protocol_compiler.cpp.alias import AliasGenerator
from bedrock_protocol_compiler.cpp.enum import EnumGenerator
from bedrock_protocol_compiler.cpp.struct import StructGenerator
from bedrock_protocol_compiler.descriptor import Alias, Enum, Module, Range, Struct
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import EnumModel, EnumType, Schema, StructModel, roots_reached


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
        self.siblings: dict[Struct | Enum, Struct] = {
            schema.pair(family): family for family in self.families if isinstance(family, Struct) and not family.cereal
        }
        self.held: dict[Struct | Enum, dict[StructModel | EnumType, list[Range]]] = {}
        self.generators: list[StructGenerator | EnumGenerator] = []
        defined_models: set[StructModel] = set()
        for family in self.families:
            if isinstance(family, Struct):
                models = [model for model in schema.models(family) if isinstance(model, StructModel)]
                self.held[family] = {model: model.runs[family] for model in models}
                self.generators += [StructGenerator(schema, model) for model in models if model not in defined_models]
                defined_models.update(models)
                continue
            types: dict[EnumType, list[int]] = {}
            for version in schema.versions:
                for model in schema.models(family):
                    if isinstance(model, EnumModel) and any(run.contains(version) for run in model.runs[family]):
                        types.setdefault(schema.enum_type(family, version), []).append(version)
            self.held[family] = {enum_type: schema.ranges(versions) for enum_type, versions in types.items()}
            self.generators += [EnumGenerator(schema, enum_type) for enum_type in schema.enum_types(family)]
        holders = {
            generator.target: generator for generator in self.generators if isinstance(generator, StructGenerator)
        }
        self.early: list[dict[tuple[StructGenerator, ...], list[StructGenerator | EnumGenerator]]] = []
        defined: set[StructModel | EnumType] = set()
        for generator in self.generators:
            early: dict[tuple[StructGenerator, ...], list[StructGenerator | EnumGenerator]] = {}
            if isinstance(generator, StructGenerator):
                walk = list(generator.target.nested)
                while walk:
                    child = walk.pop(0)
                    owners: list[StructModel] = []
                    while (parent := schema.owner(owners[0] if owners else child)) is not None:
                        owners.insert(0, parent)
                    if not defined.intersection((*owners, child)) and owners[0] is not generator.target:
                        path = [holders[owners[0]]]
                        for owner in owners[1:]:
                            holder = path[-1].pending[owner]
                            assert isinstance(holder, StructGenerator)
                            path.append(holder)
                        early.setdefault(tuple(path), []).append(path[-1].pending.pop(child))
                    defined.add(child)
                    if isinstance(child, StructModel):
                        walk[0:0] = child.nested
            self.early.append(early)

    def place(self, family: Struct | Enum) -> None:
        if family in self.families:
            return
        for dependency in sorted(roots_reached(family) & self.rank.keys(), key=self.rank.__getitem__):
            self.place(dependency)
        self.families.append(family)

    def includes(self) -> set[str]:
        includes = {names.runtime("detail/reflect"), "<array>", "<string_view>"}
        for generator in (*self.aliases, *self.generators):
            includes |= generator.includes()
        return includes - {names.generated(self.module.stem)}

    def header(self, p: Printer) -> None:
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

    def source(self, p: Printer) -> None:
        p.emit(
            """
            #include $header$

            namespace $namespace$ {

            """,
            header=names.generated(self.module.stem),
            namespace=names.namespace(self.schema),
        )
        for generator in self.generators:
            generator.serializer_body(p)
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
        for generator, early in zip(self.generators, self.early, strict=True):
            for path, children in early.items():
                current = self.enter(p, current, names.scope(self.schema, path[0].target))
                path[-1].nested(p, children, path[:-1])
            current = self.enter(p, current, names.scope(self.schema, generator.target))
            generator.definition(p)
            p.emit("")
        self.switch(p, current, ())

    def enter(self, p: Printer, current: tuple[str, ...], scope: tuple[str, ...]) -> tuple[str, ...]:
        if scope != current:
            self.switch(p, current, scope)
        return scope

    def switch(self, p: Printer, closing: tuple[str, ...], opening: tuple[str, ...]) -> None:
        for part in reversed(closing):
            p.emit("}  // namespace $part$", part=part)
            p.emit("")
        for part in opening:
            p.emit("namespace $part$ {", part=part)
            p.emit("")

    def at(self, family: Struct | Enum, version: int) -> StructModel | EnumType | None:
        return next(
            (target for target, ranges in self.held[family].items() if any(run.contains(version) for run in ranges)),
            None,
        )

    def selectors(self, p: Printer) -> None:
        selectors: list[str] = []
        p.emit("namespace detail {")
        p.emit("")
        for family in self.families:
            if not family.cereal:
                continue
            sibling = self.siblings.get(family)
            labelled: dict[str, dict[StructModel | EnumType, list[int]]] = {}
            for version in self.schema.versions:
                for form in (*([sibling] if sibling is not None else []), family):
                    target = self.at(form, version)
                    if target is not None:
                        labelled.setdefault(self.schema.label(form, version), {}).setdefault(target, []).append(version)
            for label, targets in labelled.items():
                selector = names.selector(label)
                selectors.append(selector)
                runs = sorted(
                    ((run, target) for target, versions in targets.items() for run in self.schema.ranges(versions)),
                    key=lambda each: each[0].since or 0,
                )
                if len(runs) == 1 and runs[0][0] == Range(None, None):
                    p.emit(
                        """
                        template <int V>$requirement$
                        struct $selector$ { using type = $type$; };

                        """,
                        requirement=names.requirement(self.schema, runs[0][0]),
                        selector=selector,
                        type=names.qualified(self.schema, runs[0][1]),
                    )
                    continue
                p.emit(
                    """
                    template <int V>
                    struct $selector$;

                    """,
                    selector=selector,
                )
                for run, target in runs:
                    p.emit(
                        """
                        template <int V>$requirement$
                        struct $selector$<V> { using type = $type$; };

                        """,
                        requirement=names.requirement(self.schema, run),
                        selector=selector,
                        type=names.qualified(self.schema, target),
                    )
        p.emit("}  // namespace detail")
        p.emit("")
        for selector in selectors:
            p.emit("template <int V> using $selector$ = typename detail::$selector$<V>::type;", selector=selector)
        p.emit("")

    def listing(self, target: StructModel | EnumType, path: str) -> list[tuple[str, str, str]]:
        listed = [(names.qualified(self.schema, target), path, names.bare(self.schema, target))]
        if isinstance(target, StructModel):
            for child in target.nested:
                listed += self.listing(child, f"{path}::{child.family.name}")
        return listed

    def types(self, p: Printer) -> None:
        name = f"{self.module.stem}_types"
        plans: list[tuple[int | None, list[str], list[tuple[str, str]]]] = []
        for version in self.schema.versions:
            listed: dict[str, tuple[str, str]] = {}
            for family in self.families:
                target = self.at(family, version)
                if target is None:
                    continue
                for qualified, path, bare in self.listing(target, self.schema.label(family, version)):
                    listed.setdefault(qualified, (path, bare))
            types = list(listed)
            labelled = [(qualified, path) for qualified, (path, bare) in listed.items() if path != bare]
            if not plans or plans[-1][1:] != (types, labelled):
                plans.append((version if plans else None, types, labelled))
        if len(plans) > 1:
            p.emit(
                """
                template <int V>
                struct $name$;

                """,
                name=name,
            )
        for index, (since, types, labelled) in enumerate(plans):
            until = plans[index + 1][0] if index + 1 < len(plans) else None
            p.emit("template <int V>$requirement$", requirement=names.requirement(self.schema, Range(since, until)))
            if len(plans) == 1:
                p.emit("struct $name$ {", name=name)
            else:
                p.emit("struct $name$<V> {", name=name)
            with p.indent():
                for member, entries in (("types", types), ("labelled", [qualified for qualified, _ in labelled])):
                    if not entries:
                        p.emit("using $member$ = type_list<>;", member=member)
                        continue
                    p.emit("using $member$ = type_list<", member=member)
                    with p.indent():
                        for entry in entries[:-1]:
                            p.emit("$entry$,", entry=entry)
                        p.emit("$entry$>;", entry=entries[-1])
                if not labelled:
                    p.emit("static constexpr std::array<std::string_view, 0> labels{};")
                else:
                    p.emit("static constexpr std::array<std::string_view, $count$> labels{{", count=len(labelled))
                    with p.indent():
                        for _, path in labelled:
                            p.emit('"$path$",', path=path)
                    p.emit("}};")
            p.emit("};")
            p.emit("")
