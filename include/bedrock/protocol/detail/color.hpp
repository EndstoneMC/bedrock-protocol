#pragma once

#include <concepts>
#include <cstdint>
#include <cstdlib>
#include <expected>
#include <format>
#include <string>

#include "bedrock/protocol/serializer.hpp"
#include "bedrock/protocol/stream.hpp"

namespace bedrock::protocol {

namespace detail {

template <typename T, typename Encoded, auto Alpha, auto Red, auto Green, auto Blue>
struct Color;

}  // namespace detail

template <typename T, typename Encoded, auto Alpha, auto Red, auto Green, auto Blue, int V>
struct Serializer<detail::Color<T, Encoded, Alpha, Red, Green, Blue>, V> {
    static auto serialize(BinaryWriter &stream, const T &value) -> std::expected<void, Errc>
    {
        std::uint32_t packed = 0;
        for (const float channel : {value.*Alpha, value.*Red, value.*Green, value.*Blue}) {
            if (!(channel >= 0.0F && channel <= 1.0F)) {
                return std::unexpected(Errc::out_of_range);
            }
            packed = packed << 8U | static_cast<std::uint32_t>(channel * 255.0F);
        }
        if constexpr (std::same_as<Encoded, std::string>) {
            stream.write(std::format("#{:x}", packed));
        }
        else if constexpr (std::same_as<Encoded, VarInt32>) {
            stream.writeVarInt<std::int32_t>(static_cast<std::int32_t>(packed));
        }
        else if constexpr (std::same_as<Encoded, UVarInt32>) {
            stream.writeVarInt<std::uint32_t>(packed);
        }
        else {
            stream.write<Encoded>(static_cast<Encoded>(packed));
        }
        return {};
    }

    static auto deserialize(BinaryReader &stream) -> std::expected<T, Errc>
    {
        std::uint32_t packed = 0;
        if constexpr (std::same_as<Encoded, std::string>) {
            auto text = stream.read<std::string>();
            if (!text) {
                return std::unexpected(text.error());
            }
            if (!text->empty()) {
                const std::uint64_t parsed = std::strtoull(text->c_str() + 1, nullptr, 16);
                const bool clamped = parsed > 0xFFFF'FFFFU && parsed < 0xFFFF'FFFF'0000'0000U;
                packed = clamped ? 0xFFFF'FFFFU : static_cast<std::uint32_t>(parsed);
            }
        }
        else if constexpr (std::same_as<Encoded, VarInt32>) {
            auto read = stream.readVarInt<std::int32_t>();
            if (!read) {
                return std::unexpected(read.error());
            }
            packed = static_cast<std::uint32_t>(*read);
        }
        else if constexpr (std::same_as<Encoded, UVarInt32>) {
            auto read = stream.readVarInt<std::uint32_t>();
            if (!read) {
                return std::unexpected(read.error());
            }
            packed = *read;
        }
        else {
            auto read = stream.read<Encoded>();
            if (!read) {
                return std::unexpected(read.error());
            }
            packed = static_cast<std::uint32_t>(*read);
        }
        T value{};
        value.*Alpha = static_cast<float>(packed >> 24U) / 255.0F;
        value.*Red = static_cast<float>(packed >> 16U & 0xFFU) / 255.0F;
        value.*Green = static_cast<float>(packed >> 8U & 0xFFU) / 255.0F;
        value.*Blue = static_cast<float>(packed & 0xFFU) / 255.0F;
        return value;
    }
};

}  // namespace bedrock::protocol
