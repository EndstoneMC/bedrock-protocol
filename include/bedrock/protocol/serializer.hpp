#pragma once

#include <array>
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

template <typename T, int V>
struct Serializer;

struct DecodeError {
    Errc reason;
    std::string_view type;
    std::vector<PathSegment> path;
    std::size_t offset;
    std::size_t length;
};

struct EncodeError {
    Errc reason;
    std::string_view type;
    std::vector<PathSegment> path;
};

template <int V, Reflected T>
[[nodiscard]] auto encode(BinaryWriter &stream, const T &value) -> std::expected<void, EncodeError>
{
    auto written = Serializer<T, V>::serialize(stream, value);
    if (written) {
        return {};
    }
    return std::unexpected(EncodeError{
        .reason = written.error(),
        .type = struct_name<T>(),
        .path = stream.takePath(),
    });
}

template <int V, Reflected T>
[[nodiscard]] auto decode(BinaryReader &stream) -> std::expected<T, DecodeError>
{
    auto value = Serializer<T, V>::deserialize(stream);
    if (value && stream.getUnreadLength() == 0) {
        return std::move(*value);
    }
    return std::unexpected(DecodeError{
        .reason = value ? Errc::trailing_bytes : value.error(),
        .type = struct_name<T>(),
        .path = stream.takePath(),
        .offset = stream.getReadPointer(),
        .length = stream.getLength(),
    });
}

namespace detail {
template <typename Out>
auto formatPath(Out out, std::string_view type, const std::vector<PathSegment> &path) -> Out
{
    out = std::format_to(out, "{}", type);
    for (const auto &segment : path) {
        if (const auto *name = std::get_if<std::string_view>(&segment)) {
            out = std::format_to(out, ".{}", *name);
        }
        else {
            out = std::format_to(out, "[{}]", std::get<std::size_t>(segment));
        }
    }
    return out;
}
}  // namespace detail

}  // namespace bedrock::protocol

template <>
struct std::formatter<bedrock::protocol::Errc> : std::formatter<std::string_view> {
    template <typename FormatContext>
    auto format(bedrock::protocol::Errc reason, FormatContext &ctx) const
    {
        static constexpr std::array<std::string_view, 4> reasons{
            "truncated",
            "out of range",
            "unknown value",
            "trailing bytes",
        };
        return std::formatter<std::string_view>::format(reasons[std::to_underlying(reason)], ctx);
    }
};

template <>
struct std::formatter<bedrock::protocol::DecodeError> : std::formatter<std::string_view> {
    template <typename FormatContext>
    static auto format(const bedrock::protocol::DecodeError &error, FormatContext &ctx) -> FormatContext::iterator
    {
        auto out = bedrock::protocol::detail::formatPath(ctx.out(), error.type, error.path);
        return std::format_to(out, ": {} at byte {} of {}", error.reason, error.offset, error.length);
    }
};

template <>
struct std::formatter<bedrock::protocol::EncodeError> : std::formatter<std::string_view> {
    template <typename FormatContext>
    static auto format(const bedrock::protocol::EncodeError &error, FormatContext &ctx) -> FormatContext::iterator
    {
        auto out = bedrock::protocol::detail::formatPath(ctx.out(), error.type, error.path);
        return std::format_to(out, ": {}", error.reason);
    }
};
