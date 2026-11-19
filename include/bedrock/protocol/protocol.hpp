#pragma once

#include <cstddef>
#include <expected>
#include <optional>
#include <string>
#include <string_view>
#include <utility>

#include "bedrock/protocol/detail/reflect.hpp"
#include "bedrock/protocol/serializer.hpp"
#include "bedrock/protocol/stream.hpp"
#include "bedrock/protocol/version.hpp"

namespace bedrock::protocol {

class Protocol;

[[nodiscard]] constexpr std::optional<Protocol> protocol(int number);
[[nodiscard]] constexpr std::optional<Protocol> protocol(std::string_view release);

class Protocol {
public:
    [[nodiscard]] constexpr int version() const noexcept { return version_; }

    template <Reflected T, SerializationMode M = SerializationMode::Default>
    [[nodiscard]] auto encode(const T &value, serialization_mode_t<M> mode = serialization_mode_t<M>()) const
        -> std::expected<std::string, EncodeError>
    {
        std::string data;
        BinaryWriter writer{data};
        return encode(value, writer, mode).transform([&] { return std::move(data); });
    }

    template <Reflected T, SerializationMode M = SerializationMode::Default>
    [[nodiscard]] auto encode(const T &value, BinaryWriter &stream,
                              serialization_mode_t<M> mode = serialization_mode_t<M>()) const
        -> std::expected<void, EncodeError>
    {
        std::expected<void, EncodeError> encoded = std::unexpected(EncodeError{
            .reason = Errc::unknown_type,
            .type = struct_name<T>(),
            .path = {},
        });
        [&]<std::size_t... I>(std::index_sequence<I...>) {
            (
                [&] {
                    if constexpr (Serializable<T, versions[I], M>) {
                        if (version_ == versions[I]) {
                            encoded = ::bedrock::protocol::encode<versions[I]>(value, stream, mode);
                        }
                    }
                }(),
                ...);
        }(std::make_index_sequence<versions.size()>{});
        return encoded;
    }

    template <Reflected T, SerializationMode M = SerializationMode::Default>
    [[nodiscard]] auto decode(std::string_view data, serialization_mode_t<M> mode = serialization_mode_t<M>()) const
        -> std::expected<T, DecodeError>
    {
        BinaryReader reader{data};
        return decode<T>(reader, mode);
    }

    template <Reflected T, SerializationMode M = SerializationMode::Default>
    [[nodiscard]] auto decode(BinaryReader &stream, serialization_mode_t<M> mode = serialization_mode_t<M>()) const
        -> std::expected<T, DecodeError>
    {
        std::expected<T, DecodeError> decoded = std::unexpected(DecodeError{
            .reason = Errc::unknown_type,
            .type = struct_name<T>(),
            .path = {},
            .offset = stream.getReadPointer(),
            .length = stream.getLength(),
        });
        [&]<std::size_t... I>(std::index_sequence<I...>) {
            (
                [&] {
                    if constexpr (Serializable<T, versions[I], M>) {
                        if (version_ == versions[I]) {
                            decoded = ::bedrock::protocol::decode<versions[I], T>(stream, mode);
                        }
                    }
                }(),
                ...);
        }(std::make_index_sequence<versions.size()>{});
        return decoded;
    }

    friend constexpr bool operator==(Protocol, Protocol) noexcept = default;

private:
    constexpr explicit Protocol(int version) noexcept : version_(version) {}

    friend constexpr std::optional<Protocol> protocol(int number);
    friend constexpr std::optional<Protocol> protocol(std::string_view release);

    int version_;
};

constexpr std::optional<Protocol> protocol(int number)
{
    if (const std::optional<ProtocolVersion> found = protocol_version(number)) {
        return Protocol{found->snapshot};
    }
    return std::nullopt;
}

constexpr std::optional<Protocol> protocol(std::string_view release)
{
    if (const std::optional<ProtocolVersion> found = protocol_version(release)) {
        return Protocol{found->snapshot};
    }
    return std::nullopt;
}

}  // namespace bedrock::protocol
