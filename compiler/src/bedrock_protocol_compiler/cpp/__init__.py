from bedrock_protocol_compiler.context import GeneratorContext
from bedrock_protocol_compiler.cpp import names
from bedrock_protocol_compiler.cpp.file import FileGenerator
from bedrock_protocol_compiler.descriptor import Struct
from bedrock_protocol_compiler.schema import Numbering, Schema


def generate(schema: Schema, context: GeneratorContext) -> None:
    reached = {
        each
        for encoding in schema.encoded.values()
        for each in encoding.reached.values()
        if isinstance(each, Numbering) and not each.identity
    }
    files = [FileGenerator(schema, module, reached) for module in schema.modules]
    for file in files:
        file.header(context.open(f"{names.INCLUDE_DIR}/{file.module.stem}.h"))
        file.source(context.open(f"{names.INCLUDE_DIR}/{file.module.stem}.cpp"))
    registry = context.open(names.REGISTRY_HEADER)
    registry.emit(
        """
        #pragma once

        #include <type_traits>

        #include "$include_dir$/detail/reflect.hpp"
        #include "$include_dir$/serializer.hpp"

        """,
        include_dir=names.INCLUDE_DIR,
    )
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
    packets.sort(key=lambda each: each[0])
    for packet_id, file, family in packets:
        file.packet(registry, packet_id, family)
    for number in schema.versions:
        registry.emit(
            """
            namespace v$number$ {

            inline constexpr int version = $number$;

            inline constexpr ::$namespace$::detail::packet_encode_fn<version> encode{};

            template <::$namespace$::Packet<version> T>
            inline constexpr ::$namespace$::detail::packet_decode_fn<version, T> decode{};

            }  // namespace v$number$

            """,
            number=number,
            namespace=names.namespace(schema),
        )
    registry.emit("}  // namespace $namespace$", namespace=names.namespace(schema))
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
                for (const ProtocolVersion &version : SUPPORTED_VERSIONS) {
                    if (version.protocol_ == protocol) {
                        return version;
                    }
                }
                return std::nullopt;
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
