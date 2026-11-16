#pragma once

#include <algorithm>
#include <array>
#include <cstddef>
#include <optional>
#include <string_view>
#include <type_traits>

#include "bedrock/protocol/enum.hpp"

namespace bedrock::protocol::detail {

template <typename E>
    requires std::is_enum_v<E>
struct NameEntry {
    E value;
    std::string_view name;
};

template <typename E, std::size_t K>
    requires std::is_enum_v<E>
[[nodiscard]] constexpr auto name_of(const std::array<NameEntry<E>, K> &table, E value) noexcept
    -> std::optional<std::string_view>
{
    const auto entry = std::ranges::find(table, value, &NameEntry<E>::value);
    if (entry == table.end()) {
        return std::nullopt;
    }
    return entry->name;
}

template <typename E, std::size_t K>
    requires std::is_enum_v<E>
[[nodiscard]] constexpr auto value_of(const std::array<NameEntry<E>, K> &table, std::string_view name) noexcept
    -> std::optional<E>
{
    const auto entry =
        std::ranges::find_if(table, [name](const NameEntry<E> &row) { return equal_folded(name, row.name); });
    if (entry == table.end()) {
        return std::nullopt;
    }
    return entry->value;
}

}  // namespace bedrock::protocol::detail
