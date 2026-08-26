#pragma once

#include <array>
#include <cstddef>
#include <string_view>
#include <type_traits>
#include <utility>

// A Boost.PFR-alike over the generated structs. Boost.PFR recovers members by
// probing aggregate arity and binding them with structured bindings, which caps
// the member count, requires the type to be an aggregate, and recovers no names
// before C++26; here the compiler emits `field_names_v` and the accessor
// outright, so the arity cap, the aggregate requirement and the missing names
// all fall away.
//
// Names follow <bedrock/enum.hpp>'s `enum_` convention rather than PFR's own
// (`field_count` for `tuple_size_v`, `field_get` for `get`), keeping the two
// reflection surfaces spelled alike and leaving `get` to std. As there,
// `detail::is_reflected_v` is the gate and the primaries are empty, so a type
// the compiler did not emit is simply unreflected.
//
// The one visible divergence from PFR: it indexes members positionally because
// probing yields no names, which is why `structure_to_tuple` is its centrepiece.
// A name is always available here, so `field_index` is a consteval lookup and no
// tuple is ever materialised -- `field_get` hands back the member itself.

namespace bedrock::protocol {

namespace detail {

// Specialized by the compiler for every generated struct.
template <typename T>
inline constexpr bool is_reflected_struct_v = false;

template <typename T>
inline constexpr std::array<std::string_view, 0> field_names_v{};

template <typename T>
inline constexpr std::string_view struct_name_v{};

// Specialized alongside, holding the per-index member access. A struct rather
// than a function template so the compiler emits one block per type instead of
// one per field.
template <typename T>
struct field_accessor;

}  // namespace detail

template <typename T>
concept Reflected = std::is_class_v<T> && detail::is_reflected_struct_v<T>;

//: Index returned by `field_index` for a name the struct does not carry.
inline constexpr std::size_t field_npos = static_cast<std::size_t>(-1);

// Returns the struct's name, unqualified.
template <Reflected T>
[[nodiscard]] constexpr std::string_view struct_name() noexcept
{
    return detail::struct_name_v<T>;
}

// Returns the number of members. Wire-only constants declare no member and are
// absent, so two snapshots differing only in those report the same fields.
template <Reflected T>
[[nodiscard]] constexpr std::size_t field_count() noexcept
{
    return detail::field_names_v<T>.size();
}

// Returns std::array with member names, in declaration order.
template <Reflected T>
[[nodiscard]] constexpr const auto &field_names() noexcept
{
    return detail::field_names_v<T>;
}

// Returns the name of the member at the specified index.
template <std::size_t I, Reflected T>
[[nodiscard]] constexpr std::string_view field_name() noexcept
{
    static_assert(I < detail::field_names_v<T>.size(), "field_name out of range.");
    return detail::field_names_v<T>[I];
}

// Returns a reference to the member at the specified index, preserving the
// value category of the struct it came from.
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

// Returns the index of the member with this name, or `field_npos`. Consteval so
// the comparison never survives into the generated code.
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

// Whether the struct carries a member with this name.
template <Reflected T>
[[nodiscard]] consteval bool field_contains(std::string_view name) noexcept
{
    return field_index<T>(name) != field_npos;
}

// Applies `f` to every member in declaration order. The pack expands, so the
// call site sees each member by its own type and nothing is erased.
template <typename T, typename F>
    requires Reflected<std::remove_cvref_t<T>>
constexpr void for_each_field(T &&value, F &&f)
{
    [&]<std::size_t... I>(std::index_sequence<I...>) {
        (f(field_get<I>(std::forward<T>(value))), ...);
    }(std::make_index_sequence<field_count<std::remove_cvref_t<T>>()>{});
}

// Applies `f` to every (name, member) pair in declaration order.
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
