#pragma once

#include <algorithm>
#include <array>
#include <cstddef>
#include <optional>
#include <string_view>
#include <type_traits>
#include <utility>

namespace bedrock::protocol::detail {

constexpr char to_lower(char c) noexcept
{
    return c >= 'A' && c <= 'Z' ? static_cast<char>(c - 'A' + 'a') : c;
}

constexpr bool equal_folded(std::string_view lhs, std::string_view rhs) noexcept
{
    if (lhs.size() != rhs.size()) {
        return false;
    }
    for (std::size_t i = 0; i < lhs.size(); ++i) {
        if (to_lower(lhs[i]) != rhs[i]) {
            return false;
        }
    }
    return true;
}

template <typename E>
inline constexpr bool is_name_coded_v = false;

template <typename E, int N>
    requires std::is_enum_v<E>
struct Naming {
    static constexpr std::array<std::pair<E, std::string_view>, 0> written{};
    static constexpr std::array<std::pair<E, std::string_view>, 0> read{};
    static constexpr std::array<std::string_view, 0> names{};
};

template <typename E, std::size_t K>
    requires std::is_enum_v<E>
[[nodiscard]] constexpr auto name_of(const std::array<std::pair<E, std::string_view>, K> &table, E value) noexcept
    -> std::optional<std::string_view>
{
    const auto entry = std::ranges::find(table, value, &std::pair<E, std::string_view>::first);
    if (entry == table.end()) {
        return std::nullopt;
    }
    return entry->second;
}

template <typename E, std::size_t K>
    requires std::is_enum_v<E>
[[nodiscard]] constexpr auto value_of(const std::array<std::pair<E, std::string_view>, K> &table,
                                      std::string_view name) noexcept -> std::optional<E>
{
    const auto entry = std::ranges::find_if(
        table, [name](const std::pair<E, std::string_view> &row) { return equal_folded(name, row.second); });
    if (entry == table.end()) {
        return std::nullopt;
    }
    return entry->first;
}

}  // namespace bedrock::protocol::detail
