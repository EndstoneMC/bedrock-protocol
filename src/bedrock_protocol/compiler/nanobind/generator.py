"""nanobind output using the same resolved shapes as the C++ backend."""

from __future__ import annotations

import ast
import hashlib
import json
import keyword
from collections import defaultdict

from bedrock_protocol.compiler.code_generator import CodeGenerator, GeneratorContext
from bedrock_protocol.compiler.cpp.field import render_count, render_predicate
from bedrock_protocol.compiler.cpp.file import FileGenerator, _has_wire_shape
from bedrock_protocol.compiler.cpp.helpers import PRIMITIVE_TYPES
from bedrock_protocol.descriptor import (
    INT_WIDTHS,
    ArrayType,
    BitsetType,
    CompilerError,
    CondType,
    Enum,
    EnumType,
    FieldType,
    LiteralType,
    MappingType,
    OptionalType,
    PrimitiveAlias,
    PrimitiveType,
    RepeatedType,
    ResolvedFile,
    Struct,
    StructType,
    VariantType,
)

from .model import Model, Shape


def py_name(name: str) -> str:
    return name + "_" if keyword.iskeyword(name) else name


def quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def enum_numbers(decl: Enum) -> dict[str, int]:
    numbers: dict[str, int] = {}
    for value in decl.values:
        number = value.number
        if value.derived is not None:
            reference, offset = value.derived
            number = numbers[reference] + offset
        numbers[value.name] = number
    return numbers


class NanobindGenerator(CodeGenerator):
    @property
    def name(self) -> str:
        return "nanobind"

    def generate(self, resolved: ResolvedFile, context: GeneratorContext) -> None:
        # CLI constructs a backend per output; the FileSet owns aggregation.
        if resolved.file.name != resolved.pool.file_set.outputs[0]:
            return
        model = Model(resolved)
        writer = BindingWriter(model)
        for path, contents in writer.render().items():
            with context.open(path) as output:
                output.write(contents)


class BindingWriter:
    def __init__(self, model: Model) -> None:
        self.model = model
        self.names = {cpp: f"_T{i}" for i, cpp in enumerate(sorted(model.shapes))}
        self.containers: dict[str, tuple[str, str]] = {}

    def adapter(self, field: FieldType | None, version: int, *, construction: bool = False) -> str:
        if field is None:
            return "Empty"
        if isinstance(field, PrimitiveType):
            wire = PRIMITIVE_TYPES[field.encoding]
            native = PRIMITIVE_TYPES[field.name]
            encoding = f", {wire}" if construction and wire != native else ""
            if field.alias:
                shape = self.model.shape_at(field.alias, version)
                return f"Alias<{shape.cpp}, {native}{encoding}>"
            if field.name == "str":
                return "Text"
            if field.name == "bytes":
                return "Binary"
            return f"Scalar<{native}{encoding}>"
        if isinstance(field, (StructType, EnumType)):
            if field.name == "UUID":
                return "Uuid"
            value = self.model.aliases[version].get(field.name)
            if value and value.startswith("alias:"):
                return self.adapter(self.model.type_alias(field.name).target, version, construction=construction)
            shape = self.model.shape_at(field.name, version)
            if isinstance(shape.declaration, Struct) and shape.declaration.builtin:
                if field.name == "CompoundTag":
                    return "Compound"
                if field.name == "DynamicValue":
                    return "Dynamic"
                raise CompilerError(f"nanobind: unsupported builtin {field.name}")
            category = "Enumeration" if isinstance(field, EnumType) else "Record"
            named = ", true" if isinstance(field, EnumType) and field.scalar is None else ""
            if isinstance(field, EnumType) and field.scalar is not None:
                assert isinstance(shape.declaration, Enum)
                wire = PRIMITIVE_TYPES[field.scalar.encoding]
                if wire != PRIMITIVE_TYPES[shape.declaration.sole_underlying.name]:
                    named = f", false, {wire}"
            return f"{category}<{shape.cpp}{named}>"
        if isinstance(field, CondType):
            return self.adapter(field.inner, version, construction=construction)
        if isinstance(field, OptionalType):
            return f"Optional<{self.adapter(field.inner, version, construction=construction)}>"
        if isinstance(field, VariantType):
            return f"Union<{', '.join(self.adapter(c, version, construction=construction) for c in field.cases)}>"
        if isinstance(field, BitsetType):
            return f"Bits<{field.size}>"
        if isinstance(field, (RepeatedType, ArrayType)):
            inner = self.adapter(field.inner, version, construction=construction)
            container = (
                f"std::vector<typename {inner}::Type>"
                if isinstance(field, RepeatedType)
                else f"std::array<typename {inner}::Type, {field.size}>"
            )
            prefix = (
                f", {PRIMITIVE_TYPES[field.prefix.encoding]}"
                if construction and isinstance(field, RepeatedType) and field.count is None
                else ""
            )
            result = f"Sequence<{container}, {inner}{prefix}>"
            if not construction:
                self.containers[result] = ("bindSequence", "_S" + hashlib.sha256(result.encode()).hexdigest()[:16])
            return result
        if isinstance(field, MappingType):
            key = self.adapter(field.key, version, construction=construction)
            value = self.adapter(field.value, version, construction=construction)
            prefix = f", {PRIMITIVE_TYPES[field.prefix.encoding]}" if construction else ""
            result = f"Mapping<{key}, {value}{prefix}>"
            if not construction:
                self.containers[result] = ("bindMap", "_M" + hashlib.sha256(result.encode()).hexdigest()[:16])
            return result
        raise CompilerError(f"nanobind: no adapter for {field}")

    def version(self, shape: Shape) -> int:
        preferred = (
            (2193, 1001)
            if shape.cpp in {"bedrock::protocol::v844::GameRule", "bedrock::protocol::v844::GameRulesChangedPacketData"}
            else (1001, 2193)
        )
        priority = (*preferred, *self.model.versions)
        return next(v for v in priority if self.model.aliases.get(v, {}).get(shape.name) == shape.cpp)

    def literal(self, field: LiteralType, version: int, owner: str) -> str:
        if field.enum_members and field.enum_members[0]:
            name, member = field.enum_members[0]
            name = self.model.resolve(name, owner)
            shape = self.model.shape_at(name, version)
            return f"Enumeration<{shape.cpp}>::type().attr({quote(member)})"
        value = field.written
        if isinstance(value, str):
            return f"nb::str({quote(value)})"
        if isinstance(value, bool):
            return f"nb::bool_({'true' if value else 'false'})"
        return f"nb::int_({value})"

    def record(self, shape: Shape) -> list[str]:
        decl, cpp = shape.declaration, shape.cpp
        assert isinstance(decl, Struct)
        version = self.version(shape)
        ctx = FileGenerator(shape.resolved)._ctx
        internal = self.names[cpp]
        out = ["{", f"using T = {cpp};", f"auto cls = recordClass<T>(types, {quote(internal)});"]
        out += [
            f'cls.attr("__name__") = {quote(decl.name)};',
            f'cls.attr("__qualname__") = {quote(shape.name.replace("legacy:", "legacy."))};',
            f'cls.attr("__module__") = "bedrock_protocol.v{version}";',
        ]
        fields = [(f, f.type_single) for f in decl.fields]
        t: FieldType | None
        params = [(f, t) for f, t in fields if not isinstance(t, LiteralType)]
        signature = ", ".join(f"nb::handle a{i}" for i in range(len(params)))
        out.append(f"cls.def(nb::new_([]({signature}) {{")
        out.append("T value{};")
        for i, (field, t) in enumerate(params):
            adapter = self.adapter(t, version, construction=True)
            if isinstance(t, CondType):
                condition = render_predicate(t.predicate, "value", ctx, shape.snapshot)
                out += [
                    f"if ({condition}) value.{field.name} = {adapter}::load(a{i});",
                    f'else if (!a{i}.is_none()) throw nb::value_error("{py_name(field.name)} '
                    'must be None when its condition is false");',
                ]
            else:
                out.append(f"value.{field.name} = {adapter}::load(a{i});")
        # A count predicate is a public construction invariant too.
        for field, t in params:
            current: FieldType | None = t
            target = f"value.{field.name}"
            guards = []
            while isinstance(current, (CondType, OptionalType)):
                if isinstance(current, CondType):
                    guards.append(render_predicate(current.predicate, "value", ctx, shape.snapshot))
                else:
                    guards.append(f"{target}.has_value()")
                    target = f"(*{target})"
                current = current.inner
            if isinstance(current, RepeatedType) and current.count:
                count = render_count(current.count, "value", ctx, shape.snapshot).replace("detail::", "bp::detail::")
                guard = " && ".join(f"({condition})" for condition in guards) or "true"
                out.append(
                    f"if ({guard}) {{ auto count = {count}; if (!count || {target}.size() != *count) "
                    f'throw nb::value_error("{py_name(field.name)} length disagrees with its count"); }}'
                )
        out.append("return owned(std::move(value));")
        arguments = [
            f"nb::arg({quote(py_name(f.name))})" + (".none()" if isinstance(t, (CondType, OptionalType)) else "")
            for f, t in params
        ]
        annotations = ", nb::kw_only(), " + ", ".join(arguments) if params else ""
        out.append("})" + annotations + ");")
        out.append('nb::delattr(cls, "__init__");')
        out.append(f'cls.def("__init__", [](nb::handle{", " if params else ""}{signature}) {{}}' + annotations)
        signature = ", ".join(f"{py_name(f.name)}: {self.hint(t, version, True)}" for f, t in params)
        signature = f"def __init__(self{', *, ' if params else ''}{signature}) -> None"
        out.append(f", nb::sig({quote(signature)}));")
        for field, t in fields:
            if isinstance(t, LiteralType):
                result = self.literal(t, version, shape.name)
            else:
                result = f"{self.adapter(t, version)}::get(child(self.value, self.value->{field.name}), self.protocol)"
            guard = ""
            if isinstance(t, CondType):
                condition = render_predicate(t.predicate, "(*self.value)", ctx, shape.snapshot)
                guard = f"if (!({condition})) return nb::none(); "
            out.append(
                f"cls.def_prop_ro({quote(py_name(field.name))}, [](const View<T> &self) -> nb::object "
                f"{{ {guard}return {result}; }});"
            )
        out += ['cls.def("to_dict", [](nb::handle self) { nb::dict result;']
        for field, _ in fields:
            name = quote(py_name(field.name))
            out.append(f"result[{name}] = materialize(self.attr({name}));")
        out += ["return result; });"]
        if _has_wire_shape(decl):
            out.append("wireMethod(cls);")
        if decl.packet_id is not None:
            out.append(f'cls.attr("packet_id") = {decl.packet_id};')
        out.append("}")
        return out

    def enum(self, shape: Shape) -> list[str]:
        decl, cpp = shape.declaration, shape.cpp
        assert isinstance(decl, Enum)
        internal = self.names[cpp]
        version = self.version(shape)
        width, signed = INT_WIDTHS[decl.sole_underlying.name]
        lower = -(1 << (width * 8 - 1)) if signed else 0
        upper = (1 << (width * 8 - (1 if signed else 0))) - 1
        if decl.sole_underlying.name == "bool":
            upper = 1
        out = ["{", "nb::dict members;"]
        numbers = enum_numbers(decl)
        for value in decl.values:
            number = numbers[value.name]
            out.append(
                f"members[{quote(value.name)}] = nb::int_({number}{'ULL' if number >= 2**63 else 'LL'});"
            )
        out += [
            f"auto cls = nb::class_<EnumMarker<{cpp}>>(types, {quote(internal + 'Marker')});",
            'auto enum_type = nb::module_::import_("bedrock_protocol._api").attr("_open_enum")'
            f'({quote(decl.name)}, members, nb::int_({lower}LL), nb::int_({upper}ULL), "bedrock_protocol.v{version}");',
            'cls.attr("enum_type") = enum_type;',
            f"types.attr({quote(internal)}) = enum_type;",
            "}",
        ]
        return out

    def render(self) -> dict[str, str]:
        by_file: defaultdict[str, list[str]] = defaultdict(list)
        # Adapter registrations are collected while rendering each file.
        for cpp, shape in sorted(self.model.shapes.items()):
            if isinstance(shape.declaration, Struct):
                code = self.record(shape)
            elif isinstance(shape.declaration, Enum):
                code = self.enum(shape)
            else:
                code = [f'types.attr({quote(self.names[cpp])}) = nb::module_::import_("builtins").attr("int");']
            by_file[shape.resolved.file.name].extend(code)
        outputs = {}
        declarations, registrations = [], []
        for filename, file in self.model.files.items():
            stem = file.file.name.rsplit(".", 1)[-1]
            body = [
                '#include "codec.h"',
                f"#include <bedrock/protocol/{stem}.h>",
                "namespace bedrock::protocol::python {",
                f"void bind_{stem}(nb::module_ &types) {{",
                *by_file[filename],
                "}",
            ]
            declarations.append(f"void bind_{stem}(nb::module_ &);")
            for version in self.model.versions:
                for packet_id, cpp in sorted(self.model.packets[version].items()):
                    if self.model.shapes[cpp].resolved.file.name == filename:
                        name = f"packet_{version}_{packet_id}"
                        declarations.append(f"extern const PacketEntry {name};")
                        body.append(
                            f"extern const PacketEntry {name} = "
                            f"packetEntry<bp::packet_of_t<{version}, {packet_id}>>({packet_id});"
                        )
            body.append("}")
            outputs[f"{stem}.cpp"] = "\n".join(body) + "\n"
            registrations.append(f"bind_{stem}(types);")
        # Containers can reference any schema type, so the aggregate includes the umbrella.
        main = [
            '#include "codec.h"',
            "#include <bedrock/protocol.hpp>",
            "namespace bedrock::protocol::python {",
            *declarations,
            "void bindGenerated(nb::module_ &module) {",
            'auto types = module.def_submodule("_types");',
            *registrations,
        ]
        for adapter, (function, name) in sorted(self.containers.items()):
            main.append(f"{function}<{adapter}>(types, {quote(name)});")
        for version in self.model.versions:
            for name, cpp in sorted(self.model.aliases[version].items()):
                if "." in name and cpp in self.names:
                    parent, _, child = name.rpartition(".")
                    parent_cpp = self.model.aliases[version][parent]
                    if parent_cpp in self.names:
                        main.append(
                            f"types.attr({quote(self.names[parent_cpp])}).attr({quote(child)}) = "
                            f"types.attr({quote(self.names[cpp])});"
                        )
        main += ["}", "std::span<const PacketEntry *const> packetEntries(int protocol) {"]
        for version in self.model.versions:
            entries = ", ".join(f"&packet_{version}_{id}" for id in sorted(self.model.packets[version]))
            main += [
                f"static const PacketEntry *const entries{version}[] = {{{entries}}};",
                f"if (protocol == {version}) return entries{version};",
            ]
        main += ["return {};", "}", "std::span<const int> supportedPacketIds(int protocol) {"]
        for version in self.model.versions:
            main += [
                f"static constexpr int ids{version}[] = "
                f"{{{', '.join(map(str, sorted(self.model.packets[version])))}}};",
                f"if (protocol == {version}) return ids{version};",
            ]
        main += ["return {};", "}"]
        main += [
            "std::span<const int> supportedVersions() {",
            "static constexpr int versions[] = {" + ", ".join(map(str, self.model.versions)) + "};",
            "return versions;",
            "}",
        ]
        main.append("}")
        outputs["bindings.cpp"] = "\n".join(main) + "\n"
        for version in self.model.versions:
            outputs[f"bedrock_protocol/v{version}.py"] = self.module(version)
            outputs[f"bedrock_protocol/v{version}.pyi"] = self.stub(version)
        return outputs

    def module(self, version: int) -> str:
        out = [
            '"""Generated immutable protocol values."""',
            "from types import SimpleNamespace as _Namespace",
            "from uuid import UUID as UUID",
            "from ._native import _types, Nbt as Nbt, NbtType as NbtType, Variant as Variant",
            "legacy = _Namespace()",
        ]
        deferred = []
        for name, cpp in sorted(self.model.aliases[version].items()):
            if "." in name:
                continue
            lhs = name.replace("legacy:", "legacy.")
            if cpp in self.names:
                out.append(f"{lhs} = _types.{self.names[cpp]}")
            elif cpp == "builtin:CompoundTag":
                out.append(f"{lhs} = Nbt")
            elif cpp == "builtin:DynamicValue":
                out.append(f"{lhs} = Variant")
            elif cpp == "builtin:UUID":
                pass
            elif cpp.startswith("alias:"):
                deferred.append((lhs, self.model.type_alias(name).target))
        for lhs, field in deferred:
            if isinstance(field, (StructType, EnumType)):
                target = self.model.aliases[version][field.name]
                out.append(f"{lhs} = _types.{self.names[target]}")
            elif isinstance(field, VariantType):
                out.append(f"{lhs} = Variant")
            else:
                out.append(f"{lhs} = {self.hint(field, version)}")
        out.append("del _types, _Namespace")
        used = {node.id for node in ast.walk(ast.parse("\n".join(out))) if isinstance(node, ast.Name)}
        for module, candidates in (
            ("typing", ("Literal",)),
            (".", ("BinaryView", "MapView", "SequenceView")),
        ):
            needed = [name for name in candidates if name in used]
            if needed:
                out.insert(4, f"from {module} import {', '.join(needed)}")
        return "\n".join(out) + "\n"

    def hint(self, t: FieldType | None, version: int, constructor: bool = False, owner: str = "") -> str:
        if t is None:
            return "None"
        if isinstance(t, PrimitiveType):
            return {
                "str": "str",
                "bytes": "ReadableBuffer" if constructor else "BinaryView",
                "bool": "bool",
                "float": "float",
                "double": "float",
            }.get(t.name, "int")
        if isinstance(t, (StructType, EnumType)):
            if t.name == "DynamicValue":
                return "_DynamicInput" if constructor else "_DynamicOutput"
            return "Nbt" if t.name == "CompoundTag" else t.name.replace("legacy:", "legacy.")
        if isinstance(t, (CondType, OptionalType)):
            return f"{self.hint(t.inner, version, constructor)} | None"
        if isinstance(t, BitsetType):
            return "int"
        if isinstance(t, (RepeatedType, ArrayType)):
            return f"{'Iterable' if constructor else 'SequenceView'}[{self.hint(t.inner, version, constructor)}]"
        if isinstance(t, MappingType):
            arguments = f"{self.hint(t.key, version, constructor)}, {self.hint(t.value, version, constructor)}"
            return f"Mapping[{arguments}] | MapView[{arguments}]" if constructor else f"MapView[{arguments}]"
        if isinstance(t, VariantType):
            return f"Variant[{' | '.join(dict.fromkeys(self.hint(case, version, constructor) for case in t.cases))}]"
        if isinstance(t, LiteralType):
            values = []
            for i, value in enumerate(t.values):
                member = t.enum_members[i] if i < len(t.enum_members) else None
                if member:
                    enum = self.model.resolve(member[0], owner).replace("legacy:", "legacy.")
                    values.append(f"{enum}.{member[1]}")
                else:
                    values.append(repr(value))
            return f"Literal[{', '.join(values)}]"
        raise CompilerError(f"nanobind: no type hint for {t}")

    def stub(self, version: int) -> str:
        out: list[str] = []
        aliases = self.model.aliases[version]
        owners = sorted(
            {self.version(self.model.shapes[cpp]) for cpp in aliases.values() if cpp in self.names} - {version}
        )
        if "CompoundTag" in aliases:
            out.append("CompoundTag = Nbt")
        if "DynamicValue" in aliases:
            out += [
                "DynamicValue = Variant",
                "_DynamicOutput: TypeAlias = Variant[None | bool | int | float | str | "
                "SequenceView[_DynamicOutput] | MapView[str, _DynamicOutput]]",
                "_DynamicInput: TypeAlias = Variant[None | bool | int | float | str | list[_DynamicInput] | "
                "tuple[_DynamicInput, ...] | dict[str, _DynamicInput] | SequenceView[_DynamicOutput] | "
                "MapView[str, _DynamicOutput]]",
                "",
            ]

        def emit(name: str, indent: int) -> None:
            cpp = aliases[name]
            if cpp not in self.names:
                return
            shape = self.model.shapes[cpp]
            decl = shape.declaration
            pad = " " * indent
            canonical = self.version(shape)
            if version != canonical:
                reference = shape.name.replace("legacy:", "legacy.")
                out.append(f"{pad}{decl.name}: TypeAlias = _v{canonical}.{reference}")
                return
            if isinstance(decl, PrimitiveAlias):
                out.append(f"{pad}{decl.name}: TypeAlias = int")
                return
            if isinstance(decl, Enum):
                out.append(f"{pad}class {decl.name}(IntEnum):")
                numbers = enum_numbers(decl)
                for value in decl.values:
                    out.append(f"{pad}    {value.name} = {numbers[value.name]}")
                if not decl.values:
                    out.append(pad + "    ...")
                return
            out.append(f"{pad}class {decl.name}({'Packet' if decl.packet_id is not None else 'Value'}):")
            for inner in decl.nested:
                if f"{name}.{inner.name}" in aliases:
                    emit(f"{name}.{inner.name}", indent + 4)
            args = ", ".join(
                f"{py_name(f.name)}: {self.hint(f.type_single, version, True)}"
                for f in decl.fields
                if not isinstance(f.type_single, LiteralType)
            )
            out.append(f"{pad}    def __init__(self{', *, ' if args else ''}{args}) -> None: ...")
            for field in decl.fields:
                out.extend(
                    [
                        pad + "    @_property",
                        f"{pad}    def {py_name(field.name)}(self) -> "
                        f"{self.hint(field.type_single, version, owner=name)}: ...",
                    ]
                )
            out.append(f"{pad}    def to_dict(self) -> dict[str, object]: ...")
            if _has_wire_shape(decl):
                out.append(f"{pad}    def wire_bytes(self) -> bytes: ...")
            out.append("")

        for name in sorted(aliases):
            if "." not in name and not name.startswith("legacy:"):
                emit(name, 0)
        legacy = [name for name in sorted(aliases) if name.startswith("legacy:") and "." not in name]
        if legacy:
            out.append("class legacy:")
            for name in legacy:
                emit(name, 4)
        for name, cpp in sorted(aliases.items()):
            if cpp.startswith("alias:"):
                out.append(f"{name}: TypeAlias = {self.hint(self.model.type_alias(name).target, version)}")
        body = "\n".join(out) + "\n"
        used = {node.id for node in ast.walk(ast.parse(body)) if isinstance(node, ast.Name)}
        imports = [f"import bedrock_protocol.v{v} as _v{v}" for v in owners if f"_v{v}" in used]
        if "_property" in used:
            imports.append("from builtins import property as _property")
        for module, candidates in (
            ("collections.abc", ("Iterable", "Mapping")),
            ("enum", ("IntEnum",)),
            ("typing", ("Literal", "TypeAlias")),
            (".", ("BinaryView", "MapView", "Packet", "ReadableBuffer", "SequenceView", "Value")),
        ):
            needed = [name for name in candidates if name in used]
            if needed:
                imports.append(f"from {module} import {', '.join(needed)}")
        imports += [
            "from uuid import UUID as UUID",
            "from . import Nbt as Nbt, NbtType as NbtType, Variant as Variant",
        ]
        return "\n".join(imports) + "\n\n" + body
