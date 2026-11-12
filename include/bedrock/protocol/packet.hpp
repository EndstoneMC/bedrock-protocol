#pragma once

#include <array>
#include <cstdint>
#include <expected>
#include <string_view>

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

template <>
struct Serializer<PacketHeader> {
    static void serialize(BinaryWriter &stream, const PacketHeader &value)
    {
        stream.writeVarInt<std::uint32_t>((value.packet_id & 0x3FFU) | ((value.recipient_sub_id & 3U) << 10) |
                                          ((value.sender_sub_id & 3U) << 12));
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

}  // namespace detail

}  // namespace bedrock::protocol
