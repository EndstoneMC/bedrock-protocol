#pragma once

#include <array>
#include <cstddef>
#include <string>
#include <string_view>
#include <type_traits>
#include <unordered_map>
#include <utility>

#include "bedrock/protocol/detail/naming.hpp"
#include "bedrock/protocol/detail/numbering.hpp"

namespace bedrock::protocol::detail {

template <typename E>
inline constexpr std::array<E, 0> values_v{};

// Lowercased encoded names; schema_names_v keeps the schema's spelling.
template <typename E>
inline constexpr std::array<std::string_view, 0> names_v{};

template <typename E>
inline constexpr std::string_view type_name_v{};

template <typename E>
inline constexpr std::array<std::string_view, 0> schema_names_v{};

template <typename E>
inline constexpr std::array<bool, 0> deprecated_v{};

template <typename E>
inline constexpr std::array<bool, 0> aliased_v{};

template <typename E>
inline constexpr auto count_v = values_v<E>.size();

template <typename E>
constexpr auto entries() noexcept
{
    std::array<std::pair<E, std::string_view>, count_v<E>> out{};
    for (std::size_t i = 0; i < out.size(); ++i) {
        out[i] = {values_v<E>[i], names_v<E>[i]};
    }
    return out;
}

template <typename E>
inline constexpr auto entries_v = entries<E>();

template <typename E>
inline constexpr bool is_reflected_v = std::is_enum_v<E> && count_v<E> != 0;

template <typename E>
const std::unordered_map<std::string_view, E> &name_index()
{
    static const auto index = [] {
        std::unordered_map<std::string_view, E> built;
        built.reserve(count_v<E>);
        for (std::size_t i = 0; i < count_v<E>; ++i) {
            built.emplace(names_v<E>[i], values_v<E>[i]);
        }
        return built;
    }();
    return index;
}

inline std::string lowered(std::string_view value)
{
    std::string out{value};
    for (auto &c : out) {
        c = to_lower(c);
    }
    return out;
}

template <typename E>
const std::unordered_map<std::underlying_type_t<E>, std::size_t> &value_index()
{
    static const auto index = [] {
        std::unordered_map<std::underlying_type_t<E>, std::size_t> built;
        built.reserve(count_v<E>);
        for (std::size_t i = 0; i < count_v<E>; ++i) {
            built.emplace(static_cast<std::underlying_type_t<E>>(values_v<E>[i]), i);
        }
        return built;
    }();
    return index;
}

constexpr bool is_lowered(std::string_view value) noexcept
{
    for (const char c : value) {
        if (c >= 'A' && c <= 'Z') {
            return false;
        }
    }
    return true;
}

template <typename E>
struct Numbered {
    std::array<E, count_v<E>> values;
    std::size_t count;
};

template <int V, typename E>
constexpr Numbered<E> numbered() noexcept
{
    Numbered<E> out{};
    for (std::size_t i = 0; i < count_v<E>; ++i) {
        if (!(i < aliased_v<E>.size() && aliased_v<E>[i]) && to_number<E, V>(values_v<E>[i])) {
            out.values[out.count++] = values_v<E>[i];
        }
    }
    return out;
}

template <int V, typename E>
inline constexpr Numbered<E> numbered_v = numbered<V, E>();

}  // namespace bedrock::protocol::detail
