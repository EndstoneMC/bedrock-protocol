#pragma once

#include <array>
#include <cstddef>
#include <optional>
#include <string>
#include <string_view>
#include <type_traits>
#include <unordered_map>
#include <utility>

// A magic_enum-alike over the generated enums. magic_enum recovers enumerators
// from compiler-specific `__PRETTY_FUNCTION__` text over a bounded value range;
// here the compiler emits `values_v` / `names_v` outright, so the range limit,
// the sparse-enum and flags subtypes, and the hashed switch all fall away.
//
// Names and semantics track magic_enum, including `detail::is_reflected_v` as
// the gate -- spelled as a `requires` clause where magic_enum, being C++17,
// spells `enable_if_t` plus a `static_assert`.
//
// Two visible divergences. magic_enum's arrays are sorted by value because
// reflection walks a range; these are in declaration order, matching the enum as
// generated, so `min_v` / `max_v` are absent. And the name tables are lowercased,
// because a name-coded enum's wire string is BDS's folded one -- so `enum_cast`
// folds what it is given and there is no `case_insensitive` predicate to pass.

namespace bedrock::protocol {

namespace detail {

// Specialized by the compiler for every generated enum. The primaries are
// empty, so an enum it did not emit is simply unreflected.
template <typename E>
inline constexpr std::array<E, 0> values_v{};

template <typename E>
inline constexpr std::array<std::string_view, 0> names_v{};

template <typename E>
inline constexpr std::string_view type_name_v{};

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

// ASCII only and locale-free, as magic_enum's is: a name is an identifier.
constexpr char to_lower(char c) noexcept
{
    return c >= 'A' && c <= 'Z' ? static_cast<char>(c - 'A' + 'a') : c;
}

// The lookups below are linear under constant evaluation, matching magic_enum, and go
// through these at runtime. Built on first use, one per enum: a name-coded enum runs to
// 600 members and its codec reads one on every packet that carries it. `names_v` is
// lowercased, so these keys are too and a folded probe hits them directly.
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

// A name straight off the wire is already folded, so the probe borrows it and the
// common read allocates nothing.
constexpr bool is_lowered(std::string_view value) noexcept
{
    for (const char c : value) {
        if (c >= 'A' && c <= 'Z') {
            return false;
        }
    }
    return true;
}

// `rhs` comes from `names_v` and is lowercased already.
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

// Returns type name of enum.
template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr std::string_view enum_type_name() noexcept
{
    return detail::type_name_v<E>;
}

// Returns number of enum values.
template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr std::size_t enum_count() noexcept
{
    return detail::count_v<E>;
}

// Returns enum value at specified index.
// No bounds checking is performed: the behavior is undefined if index >= number of enum values.
template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr E enum_value(std::size_t index) noexcept
{
    return detail::values_v<E>[index];
}

// Returns enum value at specified index.
template <typename E, std::size_t I>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr E enum_value() noexcept
{
    static_assert(I < detail::count_v<E>, "enum_value out of range.");
    return detail::values_v<E>[I];
}

// Returns std::array with enum values, in declaration order.
template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr const auto &enum_values() noexcept
{
    return detail::values_v<E>;
}

// Returns std::array with names, in declaration order.
template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr const auto &enum_names() noexcept
{
    return detail::names_v<E>;
}

// Returns std::array with pairs (value, name), in declaration order.
template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr const auto &enum_entries() noexcept
{
    return detail::entries_v<E>;
}

// Returns integer value from enum value.
template <typename E>
    requires std::is_enum_v<E>
[[nodiscard]] constexpr std::underlying_type_t<E> enum_integer(E value) noexcept
{
    return static_cast<std::underlying_type_t<E>>(value);
}

// Returns underlying value from enum value.
template <typename E>
    requires std::is_enum_v<E>
[[nodiscard]] constexpr std::underlying_type_t<E> enum_underlying(E value) noexcept
{
    return static_cast<std::underlying_type_t<E>>(value);
}

// Returns index in enum values from enum value.
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

// Returns index in enum values from static storage enum variable.
template <auto V>
    requires detail::is_reflected_v<decltype(V)>
[[nodiscard]] constexpr std::size_t enum_index() noexcept
{
    constexpr auto index = enum_index(V);
    static_assert(index.has_value(), "enum_index enum value does not have a index.");
    return *index;
}

// Returns name from enum value.
// If enum value does not have name or value out of range, returns empty string.
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

// Returns name from static storage enum variable.
template <auto V>
    requires detail::is_reflected_v<decltype(V)>
[[nodiscard]] constexpr std::string_view enum_name() noexcept
{
    constexpr auto name = enum_name(V);
    static_assert(!name.empty(), "enum_name enum value does not have a name.");
    return name;
}

// Returns enum value from integer value.
// Returns optional with enum value.
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

// Returns enum value from name, whatever its casing: the tables are lowercased and
// the name given is folded onto them.
// Returns optional with enum value.
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

// Returns true if enum contains value with such value.
template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr bool enum_contains(E value) noexcept
{
    return enum_index(value).has_value();
}

// Returns true if enum contains value with such integer value.
template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr bool enum_contains(std::underlying_type_t<E> value) noexcept
{
    return enum_cast<E>(value).has_value();
}

// Returns true if enum contains enumerator with such name.
template <typename E>
    requires detail::is_reflected_v<E>
[[nodiscard]] constexpr bool enum_contains(std::string_view value) noexcept
{
    return enum_cast<E>(value).has_value();
}

}  // namespace bedrock::protocol
