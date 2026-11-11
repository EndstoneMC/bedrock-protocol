#pragma once

#include <bitset>
#include <cstddef>
#include <cstdint>
#include <expected>

#include <bedrock/protocol/serializer.hpp>
#include <bedrock/protocol/stream.hpp>

namespace bedrock::protocol {

template <std::size_t N>
struct Serializer<std::bitset<N>> {
    static void serialize(BinaryWriter &stream, const std::bitset<N> &value)
    {
        std::size_t top = 0;
        for (std::size_t i = N; i-- > 0;) {
            if (value.test(i)) {
                top = i + 1;
                break;
            }
        }
        const std::size_t groups = top == 0 ? 1 : (top + 6) / 7;
        for (std::size_t g = 0; g < groups; ++g) {
            std::uint8_t byte = 0;
            for (std::size_t k = 0; k < 7; ++k) {
                const std::size_t bit = g * 7 + k;
                if (bit < N && value.test(bit)) {
                    byte |= static_cast<std::uint8_t>(1U << k);
                }
            }
            if (g + 1 < groups) {
                byte |= 0x80U;
            }
            stream.write<std::uint8_t>(byte);
        }
    }

    static auto deserialize(BinaryReader &stream) -> std::expected<std::bitset<N>, Errc>
    {
        std::bitset<N> out;
        for (std::size_t g = 0;; ++g) {
            auto b = stream.read<std::uint8_t>();
            if (!b) {
                return std::unexpected(b.error());
            }
            for (std::size_t k = 0; k < 7; ++k) {
                if ((*b & (1U << k)) != 0) {
                    const std::size_t bit = g * 7 + k;
                    if (bit >= N) {
                        return std::unexpected(Errc::out_of_range);
                    }
                    out.set(bit);
                }
            }
            if ((*b & 0x80U) == 0) {
                return out;
            }
            if ((g + 1) * 7 >= N) {
                return std::unexpected(Errc::out_of_range);
            }
        }
    }
};

}  // namespace bedrock::protocol
