#pragma once

#include <cstddef>
#include <cstdint>
#include <expected>
#include <string>
#include <utility>

#include "bedrock/protocol/command.h"
#include "bedrock/protocol/serializer.hpp"
#include "bedrock/protocol/stream.hpp"

namespace bedrock::protocol {

inline auto Serializer<AvailableCommandsPacket::EnumData, 630>::serialize(
    BinaryWriter &stream, const AvailableCommandsPacket::EnumData &value, std::int64_t argument)
    -> std::expected<void, Errc>
{
    stream.write(value.name);
    stream.writeVarInt<std::uint32_t>(value.values.size());
    for (std::size_t i = 0; i < value.values.size(); ++i) {
        const auto index = value.values[i];
        if (argument <= 0x100) {
            if (!std::in_range<std::uint8_t>(index)) {
                return stream.fail(Errc::out_of_range, "values", i);
            }
            stream.write<std::uint8_t>(index);
        }
        else if (argument <= 0x10000) {
            if (!std::in_range<std::uint16_t>(index)) {
                return stream.fail(Errc::out_of_range, "values", i);
            }
            stream.write<std::uint16_t>(index);
        }
        else {
            stream.write<std::uint32_t>(index);
        }
    }
    return {};
}

inline auto Serializer<AvailableCommandsPacket::EnumData, 630>::deserialize(BinaryReader &stream, std::int64_t argument)
    -> std::expected<AvailableCommandsPacket::EnumData, Errc>
{
    AvailableCommandsPacket::EnumData out;
    auto name = stream.read<std::string>();
    if (!name) {
        return stream.fail(name.error(), "name");
    }
    out.name = std::move(*name);
    auto count = stream.readVarInt<std::uint32_t>();
    if (!count) {
        return stream.fail(count.error(), "values");
    }
    const auto widen = [](auto narrow) -> std::uint32_t {
        return narrow;
    };
    out.values.reserve(detail::initialCapacity(*count));
    for (std::size_t i = 0; i < *count; ++i) {
        std::expected<std::uint32_t, Errc> index;
        if (argument <= 0x100) {
            index = stream.read<std::uint8_t>().transform(widen);
        }
        else if (argument <= 0x10000) {
            index = stream.read<std::uint16_t>().transform(widen);
        }
        else {
            index = stream.read<std::uint32_t>();
        }
        if (!index) {
            return stream.fail(index.error(), "values", i);
        }
        out.values.push_back(*index);
    }
    return out;
}

}  // namespace bedrock::protocol
