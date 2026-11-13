#pragma once

#include <array>
#include <cstddef>
#include <optional>
#include <string>
#include <string_view>
#include <type_traits>
#include <unordered_map>
#include <utility>

namespace bedrock::protocol {

namespace detail {

template <typename E>
inline constexpr std::array<E, 0> values_v{};

// Lowercased wire names; schema_names_v keeps the schema's spelling.
template <typename E>
inline constexpr std::array<std::string_view, 0> names_v{};

template <typename E>
inline constexpr std::string_view type_name_v{};

template <typename E>
inline constexpr std::array<std::string_view, 0> schema_names_v{};

template <typename E>
inline constexpr std::array<bool, 0> deprecated_v{};

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

constexpr char to_lower(char c) noexcept
{
    return c >= 'A' && c <= 'Z' ? static_cast<char>(c - 'A' + 'a') : c;
}

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

}  // namespace detail

template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr std::string_view enum_type_name() noexcept
{
    return detail::type_name_v<E>;
}

template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr std::size_t enum_count() noexcept
{
    return detail::count_v<E>;
}

template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr E enum_value(std::size_t index) noexcept
{
    return detail::values_v<E>[index];
}

template <typename E, std::size_t I>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr E enum_value() noexcept
{
    static_assert(I < detail::count_v<E>, "enum_value out of range.");
    return detail::values_v<E>[I];
}

template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr const auto &enum_values() noexcept
{
    return detail::values_v<E>;
}

template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr const auto &enum_names() noexcept
{
    return detail::names_v<E>;
}

template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr const auto &enum_schema_names() noexcept
{
    return detail::schema_names_v<E>;
}

template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr bool enum_deprecated(std::size_t index) noexcept
{
    return index < detail::deprecated_v<E>.size() && detail::deprecated_v<E>[index];
}

template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr const auto &enum_entries() noexcept
{
    return detail::entries_v<E>;
}

template <typename E>
    requires std::is_enum_v<E>
[[nodiscard]] constexpr std::underlying_type_t<E> enum_integer(E value) noexcept
{
    return static_cast<std::underlying_type_t<E>>(value);
}

template <typename E>
    requires std::is_enum_v<E>
[[nodiscard]] constexpr std::underlying_type_t<E> enum_underlying(E value) noexcept
{
    return static_cast<std::underlying_type_t<E>>(value);
}

template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr std::optional<std::size_t> enum_index(E value) noexcept
{
    if !consteval {
        const auto &index = detail::value_index<E>();
        const auto it = index.find(static_cast<std::underlying_type_t<E>>(value));
        if (it == index.end()) {
            return std::nullopt;
        }
        return it->second;
    }
    for (std::size_t i = 0; i < detail::count_v<E>; ++i) {
        if (detail::values_v<E>[i] == value) {
            return i;
        }
    }
    return std::nullopt;
}

template <auto V>
    requires detail::is_reflected_v<decltype(V)>
[[nodiscard]] constexpr std::size_t enum_index() noexcept
{
    constexpr auto index = enum_index(V);
    static_assert(index.has_value(), "enum_index enum value does not have a index.");
    return *index;
}

template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr std::string_view enum_name(E value) noexcept
{
    const auto index = enum_index(value);
    if (!index) {
        return {};
    }
    return detail::names_v<E>[*index];
}

template <auto V>
    requires detail::is_reflected_v<decltype(V)>
[[nodiscard]] constexpr std::string_view enum_name() noexcept
{
    constexpr auto name = enum_name(V);
    static_assert(!name.empty(), "enum_name enum value does not have a name.");
    return name;
}

template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr std::optional<E> enum_cast(std::underlying_type_t<E> value) noexcept
{
    for (const auto v : detail::values_v<E>) {
        if (static_cast<std::underlying_type_t<E>>(v) == value) {
            return v;
        }
    }
    return std::nullopt;
}

template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr std::optional<E> enum_cast(std::string_view value) noexcept
{
    if !consteval {
        const auto &index = detail::name_index<E>();
        const auto it = detail::is_lowered(value) ? index.find(value) : index.find(detail::lowered(value));
        if (it == index.end()) {
            return std::nullopt;
        }
        return it->second;
    }
    for (std::size_t i = 0; i < detail::count_v<E>; ++i) {
        if (detail::equal_folded(value, detail::names_v<E>[i])) {
            return detail::values_v<E>[i];
        }
    }
    return std::nullopt;
}

template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr bool enum_contains(E value) noexcept
{
    return enum_index(value).has_value();
}

template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr bool enum_contains(std::underlying_type_t<E> value) noexcept
{
    return enum_cast<E>(value).has_value();
}

template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr bool enum_contains(std::string_view value) noexcept
{
    return enum_cast<E>(value).has_value();
}

}  // namespace bedrock::protocol
