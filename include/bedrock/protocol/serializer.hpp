#pragma once

#include <array>
#include <concepts>
#include <cstddef>
#include <expected>
#include <format>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

#include <bedrock/protocol/detail/reflect.hpp>
#include <bedrock/protocol/stream.hpp>

namespace bedrock::protocol {

template <typename T>
struct Serializer;

struct DecodeError {
    Errc reason;
    std::string_view type;
    std::vector<PathSegment> path;
    std::size_t offset;
    std::size_t length;
};

template <typename T>
void serialize(BinaryWriter &stream, const T &value)
{
    Serializer<T>::serialize(stream, value);
}

template <typename T, typename V>
    requires(!std::same_as<T, V>)
void serialize(BinaryWriter &stream, const V &value)
{
    Serializer<T>::serialize(stream, value);
}

template <Reflected T>
auto decode(BinaryReader &stream) -> std::expected<T, DecodeError>
{
    auto value = Serializer<T>::deserialize(stream);
    if (value && stream.getUnreadLength() == 0) {
        return std::move(*value);
    }
    return std::unexpected(DecodeError{
        .reason = value ? Errc::trailing_bytes : value.error(),
        .type = struct_name<T>(),
        .path = stream.getPath(),
        .offset = stream.getReadPointer(),
        .length = stream.getLength(),
    });
}

}  // namespace bedrock::protocol

template <>
struct std::formatter<bedrock::protocol::Errc> : std::formatter<std::string_view> {
    template <typename FormatContext>
    auto format(bedrock::protocol::Errc reason, FormatContext &ctx) const
    {
        static constexpr std::array<std::string_view, 6> reasons{
            "truncated", "out of range", "unknown value", "too large", "too deep", "trailing bytes",
        };
        return std::formatter<std::string_view>::format(reasons[std::to_underlying(reason)], ctx);
    }
};

template <>
struct std::formatter<bedrock::protocol::DecodeError> : std::formatter<std::string_view> {
    template <typename FormatContext>
    static auto format(const bedrock::protocol::DecodeError &error, FormatContext &ctx)
    {
        auto out = std::format_to(ctx.out(), "{}", error.type);
        for (const auto &segment : error.path) {
            if (const auto *name = std::get_if<std::string_view>(&segment)) {
                out = std::format_to(out, ".{}", *name);
            }
            else {
                out = std::format_to(out, "[{}]", std::get<std::size_t>(segment));
            }
        }
        return std::format_to(out, ": {} at byte {} of {}", error.reason, error.offset, error.length);
    }
};
