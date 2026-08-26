#pragma once

#include <bitset>
#include <cstddef>
#include <cstdint>
#include <system_error>

#include <expected>
#include <bedrock/protocol/serializer.hpp>
#include <bedrock/protocol/stream.hpp>

namespace bedrock::protocol {

// A base-128 little-endian dump of the bitset's numeric value: seven payload
// bits per byte, the top bit a continuation flag, and a lone 0x00 byte for the
// empty bitset. N routinely exceeds 64 (PlayerAuthInputPacket's is 65), so the
// value is never staged in an integer -- both halves walk the bits.
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

    static auto deserialize(BinaryReader &stream) -> std::expected<std::bitset<N>, std::error_code>
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
                    // A bit past the declared width means the wire is not this
                    // bitset; accepting it would drop information silently.
                    if (bit >= N) {
                        return std::unexpected(std::make_error_code(std::errc::value_too_large));
                    }
                    out.set(bit);
                }
            }
            if ((*b & 0x80U) == 0) {
                return out;
            }
            if ((g + 1) * 7 >= N) {
                return std::unexpected(std::make_error_code(std::errc::value_too_large));
            }
        }
    }
};

}  // namespace bedrock::protocol
