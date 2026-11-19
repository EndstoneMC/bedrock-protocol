#pragma once

#include <array>
#include <concepts>
#include <cstddef>
#include <cstdint>
#include <expected>
#include <string>
#include <string_view>
#include <utility>
#include <variant>

#include <bedrock/protocol/detail/reflect.hpp>
#include <bedrock/protocol/serializer.hpp>
#include <bedrock/protocol/stream.hpp>

namespace bedrock::protocol {

struct PacketHeader {
    std::uint16_t packet_id{};
    std::uint8_t recipient_sub_id{};
    std::uint8_t sender_sub_id{};

    friend bool operator==(const PacketHeader &, const PacketHeader &) = default;
};

template <int V>
struct Serializer<PacketHeader, V> {
    static auto serialize(BinaryWriter &stream, const PacketHeader &value) -> std::expected<void, Errc>
    {
        stream.writeVarInt<std::uint32_t>((value.packet_id & 0x3FFU) | ((value.recipient_sub_id & 3U) << 10) |
                                          ((value.sender_sub_id & 3U) << 12));
        return {};
    }

    static auto deserialize(BinaryReader &stream) -> std::expected<PacketHeader, Errc>
    {
        auto v = stream.readVarInt<std::uint32_t>();
        if (!v) {
            return std::unexpected(v.error());
        }
        return PacketHeader{
            .packet_id = static_cast<std::uint16_t>(*v & 0x3FFU),
            .recipient_sub_id = static_cast<std::uint8_t>((*v >> 10) & 3U),
            .sender_sub_id = static_cast<std::uint8_t>((*v >> 12) & 3U),
        };
    }
};

namespace detail {

template <>
inline constexpr bool is_reflected_struct_v<PacketHeader> = true;

template <>
inline constexpr std::string_view struct_name_v<PacketHeader>{"PacketHeader"};

template <>
inline constexpr std::array<std::string_view, 3> field_names_v<PacketHeader>{{
    "packet_id",
    "recipient_sub_id",
    "sender_sub_id",
}};

template <>
struct field_accessor<PacketHeader> {
    template <std::size_t I, typename S>
    static constexpr auto &get(S &value) noexcept
    {
        if constexpr (I == 0) {
            return value.packet_id;
        }
        else if constexpr (I == 1) {
            return value.recipient_sub_id;
        }
        else {
            return value.sender_sub_id;
        }
    }
};

template <int V, typename Packet>
struct encode_packet_fn;

template <int V, typename... P>
struct encode_packet_fn<V, std::variant<P...>> {
    template <typename T>
        requires(std::same_as<T, P> || ...)
    [[nodiscard]] auto operator()(const T &packet, std::uint8_t recipient_sub_id = 0,
                                  std::uint8_t sender_sub_id = 0) const -> std::expected<std::string, EncodeError>
    {
        std::string data;
        BinaryWriter writer{data};
        const PacketHeader header{
            .packet_id = T::Id,
            .recipient_sub_id = recipient_sub_id,
            .sender_sub_id = sender_sub_id,
        };
        return encode<V>(header, writer).and_then([&] { return encode<V>(packet, writer); }).transform([&] {
            return std::move(data);
        });
    }
};

template <int V, typename Packet>
struct decode_packet_fn;

template <int V, typename... P>
struct decode_packet_fn<V, std::variant<P...>> {
    [[nodiscard]] auto operator()(std::string_view data) const
        -> std::expected<std::pair<PacketHeader, std::variant<P...>>, DecodeError>
    {
        BinaryReader reader{data};
        auto header = Serializer<PacketHeader, V>::deserialize(reader);
        if (!header) {
            return std::unexpected(DecodeError{
                .reason = header.error(),
                .type = struct_name<PacketHeader>(),
                .path = {},
                .offset = reader.getReadPointer(),
                .length = reader.getLength(),
            });
        }
        std::expected<std::pair<PacketHeader, std::variant<P...>>, DecodeError> decoded = std::unexpected(DecodeError{
            .reason = Errc::unknown_value,
            .type = struct_name<PacketHeader>(),
            .path = {"packet_id"},
            .offset = reader.getReadPointer(),
            .length = reader.getLength(),
        });
        (
            [&] {
                if (header->packet_id == P::Id) {
                    decoded = decode<V, P>(reader).transform([&](P &&packet) {
                        return std::pair{*header, std::variant<P...>{std::in_place_type<P>, std::move(packet)}};
                    });
                }
            }(),
            ...);
        return decoded;
    }
};

}  // namespace detail

}  // namespace bedrock::protocol
