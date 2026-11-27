from graphlib import CycleError, TopologicalSorter

from bedrock_protocol_compiler.context import GeneratorContext
from bedrock_protocol_compiler.cpp import names
from bedrock_protocol_compiler.cpp.file import FileGenerator
from bedrock_protocol_compiler.descriptor import CompilerError, Range, Struct
from bedrock_protocol_compiler.schema import EnumType, Schema, StructModel


def generate(schema: Schema, context: GeneratorContext) -> None:
    files = [FileGenerator(schema, module) for module in schema.modules]
    graph = {
        path: {each[1:-1] for each in file.includes(path) if each.endswith(".h>")}
        for file in files
        for path in file.headers
    }
    try:
        TopologicalSorter(graph).prepare()
    except CycleError as error:
        cycle = error.args[1][::-1]
        raise CompilerError(f"{cycle[0]}: includes itself through {' -> '.join(cycle[1:-1])}") from error
    for file in files:
        for path in file.headers:
            file.detail_header(context.open(path), path)
        file.header(context.open(f"{names.INCLUDE_DIR}/{file.module.stem}.h"))
        file.source(context.open(f"{names.INCLUDE_DIR}/{file.module.stem}.cpp"))
    registered: list[tuple[int, Range, StructModel | EnumType]] = []
    for file in files:
        for family in file.families:
            if isinstance(family, Struct) and family.packet_id is not None:
                registered += [
                    (family.packet_id, run, target) for target, runs in file.held[family].items() for run in runs
                ]
    registered.sort(key=lambda each: (each[0], each[1].since or 0))
    declared: dict[tuple[str, ...], list[str]] = {}
    targets = dict.fromkeys(target for _, _, target in registered)
    for target in sorted(targets, key=lambda each: schema.scope(each) or 0):
        declared.setdefault(names.scope(schema, target), []).append(names.declared(schema, target))
    registry = context.open(names.REGISTRY_HEADER)
    registry.emit(
        """
        #pragma once

        #include <type_traits>

        namespace $namespace$ {

        """,
        namespace=names.namespace(schema),
    )
    for scope, structs in declared.items():
        for part in scope:
            registry.emit("namespace $part$ {", part=part)
            registry.emit("")
        for struct in structs:
            registry.emit("struct $struct$;", struct=struct)
        registry.emit("")
        for part in reversed(scope):
            registry.emit("}  // namespace $part$", part=part)
            registry.emit("")
    registry.emit(
        """
        template <int V, int Id>
        struct packet_of {
            using type = void;
        };

        template <int V, int Id>
        using packet_of_t = typename packet_of<V, Id>::type;

        template <int V, int Id>
        inline constexpr bool has_packet_v = !std::is_void_v<packet_of_t<V, Id>>;

        """
    )
    for packet_id, run, target in registered:
        registry.emit(
            """
            template <int V>$requirement$
            struct packet_of<V, $id$> { using type = $type$; };

            """,
            requirement=names.requirement(schema, run),
            id=packet_id,
            type=names.qualified(schema, target),
        )
    registry.emit("}  // namespace $namespace$", namespace=names.namespace(schema))
    packets = context.open(names.PACKETS_HEADER)
    packets.emit(
        """
        #pragma once

        #include "$include_dir$/detail/reflect.hpp"
        #include "$include_dir$/packets_fwd.hpp"
        #include "$include_dir$/serializer.hpp"

        """,
        include_dir=names.INCLUDE_DIR,
    )
    for file in files:
        packets.emit("#include $header$", header=names.generated(file.module.stem))
    packets.emit(
        """

        namespace $namespace$ {

        """,
        namespace=names.namespace(schema),
    )
    for number in schema.versions:
        packets.emit(
            """
            $inline$namespace v$number$ {

            inline constexpr int version = $number$;

            inline constexpr ::$namespace$::detail::packet_encode_fn<version> encode{};

            template <::$namespace$::Packet<version> T>
            inline constexpr ::$namespace$::detail::packet_decode_fn<version, T> decode{};

            }  // namespace v$number$

            """,
            inline="inline " if number == schema.latest else "",
            number=number,
            namespace=names.namespace(schema),
        )
    packets.emit("}  // namespace $namespace$", namespace=names.namespace(schema))
    version = context.open(f"{names.INCLUDE_DIR}/version.hpp")
    version.emit(
        """
        #pragma once

        #include <array>
        #include <optional>
        #include <string_view>

        namespace $namespace$ {

        class ProtocolVersion {
        public:
            static const std::array<ProtocolVersion, $count$> SUPPORTED_VERSIONS;
            static const ProtocolVersion MINIMUM_VERSION;
            static const ProtocolVersion MAXIMUM_VERSION;

            constexpr ProtocolVersion(int protocol, std::string_view name) : protocol_(protocol), name_(name) {}

            [[nodiscard]] static constexpr std::optional<ProtocolVersion> get(int protocol)
            {
                if (protocol < $minimum$ || protocol > $maximum$) {
                    return std::nullopt;
                }
                std::string_view name;
                for (const ProtocolVersion &version : SUPPORTED_VERSIONS) {
                    if (version.protocol_ <= protocol) {
                        name = version.name_;
                    }
                }
                return ProtocolVersion(protocol, name);
            }

            [[nodiscard]] constexpr int getProtocol() const { return protocol_; }

            [[nodiscard]] constexpr std::string_view getName() const { return name_; }

        private:
            int protocol_;
            std::string_view name_;
        };

        inline constexpr std::array<ProtocolVersion, $count$> ProtocolVersion::SUPPORTED_VERSIONS{{
        """,
        namespace=names.namespace(schema),
        count=len(schema.releases),
        minimum=schema.versions[0],
        maximum=schema.latest,
    )
    with version.indent():
        for release in schema.releases:
            version.emit('{$number$, "$first$"},', number=release.number, first=release.first)
    version.emit(
        """
        }};

        inline constexpr ProtocolVersion ProtocolVersion::MINIMUM_VERSION = SUPPORTED_VERSIONS.front();
        inline constexpr ProtocolVersion ProtocolVersion::MAXIMUM_VERSION = SUPPORTED_VERSIONS.back();

        namespace detail {

        inline constexpr std::array versions{$versions$};

        }  // namespace detail

        }  // namespace $namespace$
        """,
        versions=", ".join(map(str, schema.versions)),
        namespace=names.namespace(schema),
    )
