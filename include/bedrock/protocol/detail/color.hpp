#pragma once

#include <cstdint>
#include <cstdlib>
#include <expected>
#include <string>

#include "bedrock/protocol/stream.hpp"

namespace bedrock::protocol::detail {

template <typename T, auto Alpha, auto Red, auto Green, auto Blue>
struct Color {
    static auto pack(const T &value) -> std::expected<std::uint32_t, Errc>
    {
        std::uint32_t packed = 0;
        for (const float channel : {value.*Alpha, value.*Red, value.*Green, value.*Blue}) {
            if (!(channel >= 0.0F && channel <= 1.0F)) {
                return std::unexpected(Errc::out_of_range);
            }
            packed = packed << 8U | static_cast<std::uint32_t>(channel * 255.0F);
        }
        return packed;
    }

    static auto unpack(std::uint32_t packed) -> T
    {
        T value{};
        value.*Alpha = static_cast<float>(packed >> 24U) / 255.0F;
        value.*Red = static_cast<float>(packed >> 16U & 0xFFU) / 255.0F;
        value.*Green = static_cast<float>(packed >> 8U & 0xFFU) / 255.0F;
        value.*Blue = static_cast<float>(packed & 0xFFU) / 255.0F;
        return value;
    }
};

// Reads text past its first byte as strtoull in base 16, saturating a value in [2^32, 2^64 - 2^32).
inline auto parse_color(const std::string &text) -> std::uint32_t
{
    if (text.empty()) {
        return 0;
    }
    const std::uint64_t parsed = std::strtoull(text.c_str() + 1, nullptr, 16);
    const bool clamped = parsed > 0xFFFF'FFFFU && parsed < 0xFFFF'FFFF'0000'0000U;
    return clamped ? 0xFFFF'FFFFU : static_cast<std::uint32_t>(parsed);
}

}  // namespace bedrock::protocol::detail
