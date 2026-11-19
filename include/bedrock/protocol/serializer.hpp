#pragma once

#include <array>
#include <concepts>
#include <cstddef>
#include <cstdint>
#include <expected>
#include <format>
#include <string>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

#include <bedrock/protocol/detail/reflect.hpp>
#include <bedrock/protocol/stream.hpp>

namespace bedrock::protocol {

enum class SerializationMode : std::uint8_t {
    Default = 0,
    Cereal = 1,
    Manual = 2,
};

template <SerializationMode M>
struct serialization_mode_t {
    explicit serialization_mode_t() = default;
};

inline constexpr serialization_mode_t<SerializationMode::Cereal> cereal{};
inline constexpr serialization_mode_t<SerializationMode::Manual> manual{};

template <typename T, int V, SerializationMode M = SerializationMode::Default>
struct Serializer;

template <typename T, int V, SerializationMode M = SerializationMode::Default>
concept Serializable = requires(BinaryWriter &writer, BinaryReader &reader, const T &value) {
    { Serializer<T, V, M>::serialize(writer, value) } -> std::same_as<std::expected<void, Errc>>;
    { Serializer<T, V, M>::deserialize(reader) } -> std::same_as<std::expected<T, Errc>>;
};

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

template <int V>
struct encode_fn {
    template <Reflected T, SerializationMode M = SerializationMode::Default>
        requires Serializable<T, V, M>
    [[nodiscard]] auto operator()(const T &value, BinaryWriter &stream,
                                  serialization_mode_t<M> = serialization_mode_t<M>()) const
        -> std::expected<void, EncodeError>
    {
        auto written = Serializer<T, V, M>::serialize(stream, value);
        if (written) {
            return {};
        }
        return std::unexpected(EncodeError{
            .reason = written.error(),
            .type = struct_name<T>(),
            .path = stream.takePath(),
        });
    }

    template <Reflected T, SerializationMode M = SerializationMode::Default>
        requires Serializable<T, V, M>
    [[nodiscard]] auto operator()(const T &value, serialization_mode_t<M> mode = serialization_mode_t<M>()) const
        -> std::expected<std::string, EncodeError>
    {
        std::string data;
        BinaryWriter writer{data};
        return (*this)(value, writer, mode).transform([&] { return std::move(data); });
    }
};

template <int V, Reflected T>
struct decode_fn {
    template <SerializationMode M = SerializationMode::Default>
        requires Serializable<T, V, M>
    [[nodiscard]] auto operator()(BinaryReader &stream, serialization_mode_t<M> = serialization_mode_t<M>()) const
        -> std::expected<T, DecodeError>
    {
        auto value = Serializer<T, V, M>::deserialize(stream);
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

    template <SerializationMode M = SerializationMode::Default>
        requires Serializable<T, V, M>
    [[nodiscard]] auto operator()(std::string_view data, serialization_mode_t<M> mode = serialization_mode_t<M>()) const
        -> std::expected<T, DecodeError>
    {
        BinaryReader reader{data};
        return (*this)(reader, mode);
    }
};

}  // namespace detail

template <int V>
inline constexpr detail::encode_fn<V> encode{};

template <int V, Reflected T>
inline constexpr detail::decode_fn<V, T> decode{};

}  // namespace bedrock::protocol

template <>
struct std::formatter<bedrock::protocol::Errc> : std::formatter<std::string_view> {
    template <typename FormatContext>
    auto format(bedrock::protocol::Errc reason, FormatContext &ctx) const
    {
        static constexpr std::array<std::string_view, 5> reasons{
            "truncated", "out of range", "unknown value", "trailing bytes", "unknown type",
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
