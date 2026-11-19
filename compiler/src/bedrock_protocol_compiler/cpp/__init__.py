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
        #include <variant>

        #include $reflect$
        #include $packet$
        #include $serializer$

        """,
        reflect=names.runtime("detail/reflect"),
        packet=names.runtime("packet"),
        serializer=names.runtime("serializer"),
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
        held = [
            names.qualified(schema, target)
            for _, file, family in packets
            if (target := file.at(family, number)) is not None
        ]
        registry.emit(
            """
            namespace v$number$ {

            inline constexpr int version = $number$;

            """,
            number=number,
        )
        if not held:
            registry.emit("using Packet = std::variant<>;")
        else:
            registry.emit("using Packet = std::variant<")
            with registry.indent():
                for spelled in held[:-1]:
                    registry.emit("$spelled$,", spelled=spelled)
                registry.emit("$spelled$>;", spelled=held[-1])
        registry.emit(
            """

            inline constexpr const auto &encode = ::$namespace$::encode<version>;

            template <::$namespace$::Reflected T>
            inline constexpr const auto &decode = ::$namespace$::decode<version, T>;

            inline constexpr ::$namespace$::detail::encode_packet_fn<version, Packet> encode_packet{};

            inline constexpr ::$namespace$::detail::decode_packet_fn<version, Packet> decode_packet{};

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
        #include <charconv>
        #include <cstddef>
        #include <optional>
        #include <string_view>
        #include <system_error>

        namespace $namespace$ {

        struct ProtocolVersion {
            int number;
            int snapshot;
            std::string_view name;
            std::string_view first;
            std::string_view last;
        };

        inline constexpr std::array versions{$versions$};

        inline constexpr int latest_version = $latest$;

        inline constexpr std::array releases{
        """,
        namespace=names.namespace(schema),
        versions=", ".join(map(str, schema.versions)),
        latest=schema.latest,
    )
    with version.indent():
        for release in schema.releases:
            version.emit(
                'ProtocolVersion{$number$, $snapshot$, "$name$", "$first$", "$last$"},',
                number=release.number,
                snapshot=max(each for each in schema.versions if each <= release.number),
                name=release.name,
                first=release.first,
                last=release.last,
            )
    version.emit(
        """
        };

        [[nodiscard]] constexpr std::optional<ProtocolVersion> protocol_version(int number)
        {
            for (const ProtocolVersion &version : releases) {
                if (version.number == number) {
                    return version;
                }
            }
            return std::nullopt;
        }

        [[nodiscard]] constexpr std::optional<ProtocolVersion> protocol_version(std::string_view release)
        {
            constexpr auto parse = [](std::string_view text) -> std::optional<std::array<int, 3>> {
                std::array<int, 3> parts{};
                const char *cursor = text.data();
                const char *const end = cursor + text.size();
                for (std::size_t i = 0; i < parts.size(); ++i) {
                    if (i > 0 && (cursor == end || *cursor++ != '.')) {
                        return std::nullopt;
                    }
                    const auto [next, error] = std::from_chars(cursor, end, parts[i]);
                    if (error != std::errc{}) {
                        return std::nullopt;
                    }
                    cursor = next;
                }
                if (cursor != end) {
                    return std::nullopt;
                }
                return parts;
            };
            const auto wanted = parse(release);
            if (!wanted) {
                return std::nullopt;
            }
            for (const ProtocolVersion &version : releases) {
                if (*parse(version.first) <= *wanted && *wanted <= *parse(version.last)) {
                    return version;
                }
            }
            return std::nullopt;
        }

        }  // namespace $namespace$
        """,
        namespace=names.namespace(schema),
    )
