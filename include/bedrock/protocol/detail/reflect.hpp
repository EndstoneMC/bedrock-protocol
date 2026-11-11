#pragma once

#include <array>
#include <cstddef>
#include <string_view>
#include <type_traits>
#include <utility>

namespace bedrock::protocol {

namespace detail {

template <typename T>
inline constexpr bool is_reflected_struct_v = false;

template <typename T>
inline constexpr std::array<std::string_view, 0> field_names_v{};

template <typename T>
inline constexpr std::string_view struct_name_v{};

template <typename T>
struct field_accessor;

template <typename T>
struct primitive_alias {};

}  // namespace detail

template <typename T>
concept Reflected = std::is_class_v<T> && detail::is_reflected_struct_v<T>;

template <typename T>
concept PrimitiveAlias = requires { typename detail::primitive_alias<T>::type; };

template <PrimitiveAlias T>
using primitive_alias_t = typename detail::primitive_alias<T>::type;

template <typename... T>
struct type_list {};

inline constexpr std::size_t field_npos = static_cast<std::size_t>(-1);

template <Reflected T>
[[nodiscard]] constexpr std::string_view struct_name() noexcept
{
    return detail::struct_name_v<T>;
}

template <Reflected T>
[[nodiscard]] constexpr std::size_t field_count() noexcept
{
    return detail::field_names_v<T>.size();
}

template <Reflected T>
[[nodiscard]] constexpr const auto &field_names() noexcept
{
    return detail::field_names_v<T>;
}

template <std::size_t I, Reflected T>
[[nodiscard]] constexpr std::string_view field_name() noexcept
{
    static_assert(I < detail::field_names_v<T>.size(), "field_name out of range.");
    return detail::field_names_v<T>[I];
}

template <std::size_t I, typename T>
    requires Reflected<std::remove_cvref_t<T>>
[[nodiscard]] constexpr auto &&field_get(T &&value) noexcept
{
    static_assert(I < detail::field_names_v<std::remove_cvref_t<T>>.size(), "field_get out of range.");
    auto &member = detail::field_accessor<std::remove_cvref_t<T>>::template get<I>(value);
    if constexpr (std::is_lvalue_reference_v<T>) {
        return member;
    }
    else {
        return std::move(member);
    }
}

template <Reflected T>
[[nodiscard]] consteval std::size_t field_index(std::string_view name) noexcept
{
    for (std::size_t i = 0; i < detail::field_names_v<T>.size(); ++i) {
        if (detail::field_names_v<T>[i] == name) {
            return i;
        }
    }
    return field_npos;
}

template <Reflected T>
[[nodiscard]] consteval bool field_contains(std::string_view name) noexcept
{
    return field_index<T>(name) != field_npos;
}

template <typename T, typename F>
    requires Reflected<std::remove_cvref_t<T>>
constexpr void for_each_field(T &&value, F &&f)
{
    [&]<std::size_t... I>(std::index_sequence<I...>) {
        (f(field_get<I>(std::forward<T>(value))), ...);
    }(std::make_index_sequence<field_count<std::remove_cvref_t<T>>()>{});
}

template <typename T, typename F>
    requires Reflected<std::remove_cvref_t<T>>
constexpr void for_each_named_field(T &&value, F &&f)
{
    using S = std::remove_cvref_t<T>;
    [&]<std::size_t... I>(std::index_sequence<I...>) {
        (f(field_name<I, S>(), field_get<I>(std::forward<T>(value))), ...);
    }(std::make_index_sequence<field_count<S>()>{});
}

}  // namespace bedrock::protocol
