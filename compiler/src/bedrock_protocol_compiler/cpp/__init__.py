from bedrock_protocol_compiler.context import GeneratorContext
from bedrock_protocol_compiler.cpp import names
from bedrock_protocol_compiler.cpp.file import FileGenerator
from bedrock_protocol_compiler.descriptor import Struct
from bedrock_protocol_compiler.schema import Schema


def generate(schema: Schema, context: GeneratorContext) -> None:
    files = [FileGenerator(schema, module) for module in schema.modules]
    for file in files:
        file.header(context.open(f"{names.INCLUDE_DIR}/{file.module.stem}.h"))
        file.source(context.open(f"{names.INCLUDE_DIR}/{file.module.stem}.cpp"))
    registry = context.open(names.REGISTRY_HEADER)
    registry.emit("#pragma once")
    registry.emit("")
    registry.emit("#include <type_traits>")
    registry.emit("")
    for file in files:
        registry.emit("#include $header$", header=names.generated(file.module.stem))
    registry.emit(
        """

        namespace $namespace$ {

        template <int V, int Id>
        struct packet_of {
            using type = void;
        };

        template <int V, int Id>
        using packet_of_t = typename packet_of<V, Id>::type;

        template <int V, int Id>
        inline constexpr bool has_packet_v = !std::is_void_v<packet_of_t<V, Id>>;

        """,
        namespace=names.namespace(schema),
    )
    packets = [
        (family.packet_id, file, family)
        for file in files
        for family in file.families
        if isinstance(family, Struct) and family.packet_id is not None
    ]
    for packet_id, file, family in sorted(packets, key=lambda each: each[0]):
        file.packet(registry, packet_id, family)
    registry.emit("}  // namespace $namespace$", namespace=names.namespace(schema))
    context.open(f"{names.INCLUDE_DIR}/version.hpp").emit(
        """
        #pragma once

        #include <array>

        namespace $namespace$ {

        inline constexpr std::array versions{$versions$};

        inline constexpr int latest_version = $latest$;

        }  // namespace $namespace$
        """,
        namespace=names.namespace(schema),
        versions=", ".join(map(str, schema.versions)),
        latest=schema.latest,
    )
