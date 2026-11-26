#pragma once

#include <cstddef>
#include <optional>
#include <span>
#include <string_view>
#include <type_traits>
#include <utility>

#include "bedrock/protocol/detail/enum.hpp"
#include "bedrock/protocol/detail/naming.hpp"
#include "bedrock/protocol/detail/numbering.hpp"
#include "bedrock/protocol/version.hpp"

namespace bedrock::protocol {

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

template <int V, typename E>
    requires(ProtocolVersion::get(V).has_value() && detail::is_reflected_v<E>)
[[nodiscard]] constexpr std::optional<std::underlying_type_t<E>> enum_integer_(E value) noexcept
{
    const auto number = detail::to_number<E, V>(value);
    if (!number) {
        return std::nullopt;
    }
    return *number;
}

template <int V, typename E>
    requires(ProtocolVersion::get(V).has_value() && detail::is_reflected_v<E>)
[[nodiscard]] constexpr std::optional<E> enum_cast_(std::underlying_type_t<E> number) noexcept
{
    const auto value = detail::to_value<E, V>(number);
    if (!value) {
        return std::nullopt;
    }
    return *value;
}

template <int V, typename E>
    requires(ProtocolVersion::get(V).has_value() && detail::is_reflected_v<E>)
[[nodiscard]] constexpr bool enum_contains_(E value) noexcept
{
    return detail::to_number<E, V>(value).has_value();
}

template <int V, typename E>
    requires(ProtocolVersion::get(V).has_value() && detail::is_reflected_v<E>)
[[nodiscard]] constexpr bool enum_contains_(std::underlying_type_t<E> number) noexcept
{
    return detail::to_value<E, V>(number).has_value();
}

template <int V, typename E>
    requires(ProtocolVersion::get(V).has_value() && detail::is_reflected_v<E>)
[[nodiscard]] constexpr std::span<const E> enum_values_() noexcept
{
    return {detail::numbered_v<V, E>.values.data(), detail::numbered_v<V, E>.count};
}

template <int V, typename E>
    requires(ProtocolVersion::get(V).has_value() && detail::is_reflected_v<E>)
[[nodiscard]] constexpr std::size_t enum_count_() noexcept
{
    return detail::numbered_v<V, E>.count;
}

template <int V, typename E>
    requires(ProtocolVersion::get(V).has_value() && detail::is_name_coded_v<E>)
[[nodiscard]] constexpr std::optional<std::string_view> enum_name_(E value) noexcept
{
    return detail::name_of(detail::Naming<E, V>::written, value);
}

template <int V, typename E>
    requires(ProtocolVersion::get(V).has_value() && detail::is_name_coded_v<E>)
[[nodiscard]] constexpr std::optional<E> enum_cast_(std::string_view name) noexcept
{
    return detail::value_of(detail::Naming<E, V>::read, name);
}

template <int V, typename E>
    requires(ProtocolVersion::get(V).has_value() && detail::is_name_coded_v<E>)
[[nodiscard]] constexpr bool enum_contains_(std::string_view name) noexcept
{
    return detail::value_of(detail::Naming<E, V>::read, name).has_value();
}

template <int V, typename E>
    requires(ProtocolVersion::get(V).has_value() && detail::is_name_coded_v<E>)
[[nodiscard]] constexpr std::span<const std::string_view> enum_names_() noexcept
{
    return detail::Naming<E, V>::names;
}

template <int V, typename E>
    requires(ProtocolVersion::get(V).has_value() && detail::is_name_coded_v<E>)
[[nodiscard]] constexpr std::span<const std::pair<E, std::string_view>> enum_entries_() noexcept
{
    return detail::Naming<E, V>::written;
}

}  // namespace bedrock::protocol
