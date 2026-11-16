#pragma once

#include <algorithm>
#include <expected>
#include <type_traits>
#include <utility>

#include "bedrock/protocol/stream.hpp"

namespace bedrock::protocol::detail {

template <typename E>
    requires std::is_enum_v<E>
struct NumberPair {
    std::underlying_type_t<E> from;
    std::underlying_type_t<E> to;
};

template <typename E, int N>
    requires std::is_enum_v<E>
struct Numbering;

template <typename E, int N>
    requires std::is_enum_v<E>
[[nodiscard]] constexpr auto to_number(E value) noexcept -> std::expected<std::underlying_type_t<E>, Errc>
{
    using Table = Numbering<E, N>;
    const auto from = std::to_underlying(value);
    if (std::ranges::find(Table::absent, from) != Table::absent.end()) {
        return std::unexpected(Errc::unknown_value);
    }
    const auto pair = std::ranges::find(Table::encoded, from, &NumberPair<E>::from);
    if (pair != Table::encoded.end()) {
        return pair->to;
    }
    return from;
}

template <typename E, int N>
    requires std::is_enum_v<E>
[[nodiscard]] constexpr auto to_value(std::underlying_type_t<E> number) noexcept -> std::expected<E, Errc>
{
    using Table = Numbering<E, N>;
    if (std::ranges::find(Table::lossy, number) != Table::lossy.end()) {
        return std::unexpected(Errc::unknown_value);
    }
    const auto pair = std::ranges::find(Table::decoded, number, &NumberPair<E>::from);
    if (pair != Table::decoded.end()) {
        return static_cast<E>(pair->to);
    }
    return static_cast<E>(number);
}

}  // namespace bedrock::protocol::detail
