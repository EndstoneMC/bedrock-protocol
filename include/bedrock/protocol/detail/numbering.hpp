#pragma once

#include <algorithm>
#include <array>
#include <concepts>
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

template <typename E>
    requires std::is_enum_v<E>
struct Identity {
    static constexpr std::array<NumberPair<E>, 0> encoded{};
    static constexpr std::array<NumberPair<E>, 0> decoded{};
    static constexpr std::array<std::underlying_type_t<E>, 0> absent{};
    static constexpr std::array<std::underlying_type_t<E>, 0> lossy{};
};

struct Formless {};

template <typename E, int V>
    requires std::is_enum_v<E>
struct numbering_of : Identity<E> {};

template <typename E, int V>
    requires std::is_enum_v<E>
[[nodiscard]] constexpr auto to_number(E value) noexcept -> std::expected<std::underlying_type_t<E>, Errc>
{
    using Table = numbering_of<E, V>;
    if constexpr (std::derived_from<Table, Formless>) {
        return std::unexpected(Errc::unknown_value);
    }
    else {
        const auto from = std::to_underlying(value);
        if (std::ranges::binary_search(Table::absent, from)) {
            return std::unexpected(Errc::unknown_value);
        }
        const auto pair = std::ranges::lower_bound(Table::encoded, from, {}, &NumberPair<E>::from);
        if (pair != Table::encoded.end() && pair->from == from) {
            return pair->to;
        }
        return from;
    }
}

template <typename E, int V>
    requires std::is_enum_v<E>
[[nodiscard]] constexpr auto to_value(std::underlying_type_t<E> number) noexcept -> std::expected<E, Errc>
{
    using Table = numbering_of<E, V>;
    if constexpr (std::derived_from<Table, Formless>) {
        return std::unexpected(Errc::unknown_value);
    }
    else {
        if (std::ranges::binary_search(Table::lossy, number)) {
            return std::unexpected(Errc::unknown_value);
        }
        const auto pair = std::ranges::lower_bound(Table::decoded, number, {}, &NumberPair<E>::from);
        if (pair != Table::decoded.end() && pair->from == number) {
            return static_cast<E>(pair->to);
        }
        return static_cast<E>(number);
    }
}

}  // namespace bedrock::protocol::detail
