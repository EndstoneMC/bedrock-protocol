#pragma once

#include <cstdint>

#include <expected>
#include "serializer.hpp"
#include "stream.hpp"

namespace bedrock::protocol {

struct UUID {
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

    static auto deserialize(BinaryReader &stream) -> std::expected<UUID, std::error_code>
    {
        auto msb = stream.read<std::uint64_t>();
        if (!msb) {
            return std::unexpected(msb.error());
        }
        auto lsb = stream.read<std::uint64_t>();
        if (!lsb) {
            return std::unexpected(lsb.error());
        }
        return UUID{*msb, *lsb};
    }
};

}  // namespace bedrock::protocol
