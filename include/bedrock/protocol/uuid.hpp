#pragma once

#include <cstddef>
#include <cstdint>
#include <expected>
#include <format>
#include <optional>
#include <string>
#include <string_view>

#include <bedrock/protocol/serializer.hpp>
#include <bedrock/protocol/stream.hpp>

namespace bedrock::protocol {

struct UUID {
    [[nodiscard]] static constexpr std::optional<UUID> fromString(std::string_view text) noexcept
    {
        const bool hyphenated = text.size() == 36;
        if (!hyphenated && text.size() != 32) {
            return std::nullopt;
        }
        UUID out{};
        std::size_t digits = 0;
        for (std::size_t i = 0; i < text.size(); ++i) {
            const char c = text[i];
            if (hyphenated && (i == 8 || i == 13 || i == 18 || i == 23)) {
                if (c != '-') {
                    return std::nullopt;
                }
                continue;
            }
            int nibble = 0;
            if (c >= '0' && c <= '9') {
                nibble = c - '0';
            }
            else if (c >= 'a' && c <= 'f') {
                nibble = c - 'a' + 10;
            }
            else if (c >= 'A' && c <= 'F') {
                nibble = c - 'A' + 10;
            }
            else {
                return std::nullopt;
            }
            auto &half = digits < 16 ? out.most_significant_bits : out.least_significant_bits;
            half = half << 4U | static_cast<std::uint64_t>(nibble);
            ++digits;
        }
        return out;
    }

    [[nodiscard]] std::string asString() const
    {
        return std::format("{:08x}-{:04x}-{:04x}-{:04x}-{:012x}", most_significant_bits >> 32U,
                           most_significant_bits >> 16U & 0xFFFFU, most_significant_bits & 0xFFFFU,
                           least_significant_bits >> 48U, least_significant_bits & 0xFFFF'FFFF'FFFFU);
    }

    friend bool operator==(const UUID &, const UUID &) = default;

    std::uint64_t most_significant_bits;
    std::uint64_t least_significant_bits;
};

template <>
struct Serializer<UUID> {
    static void serialize(BinaryWriter &stream, const UUID &value)
    {
        stream.write<std::uint64_t>(value.most_significant_bits);
        stream.write<std::uint64_t>(value.least_significant_bits);
    }

    static auto deserialize(BinaryReader &stream) -> std::expected<UUID, Errc>
    {
        auto msb = stream.read<std::uint64_t>();
        if (!msb) {
            return std::unexpected(msb.error());
        }
        auto lsb = stream.read<std::uint64_t>();
        if (!lsb) {
            return std::unexpected(lsb.error());
        }
        return UUID{.most_significant_bits = *msb, .least_significant_bits = *lsb};
    }
};

}  // namespace bedrock::protocol
