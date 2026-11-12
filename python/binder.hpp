#pragma once

#include <array>
#include <concepts>
#include <cstddef>
#include <format>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <variant>
#include <vector>

#include <nanobind/nanobind.h>
#include <nanobind/operators.h>

#include "bedrock/protocol/detail/reflect.hpp"
#include "bedrock/protocol/enum.hpp"
#include "bedrock/protocol/serializer.hpp"
#include "bedrock/protocol/stream.hpp"
#include "casters.hpp"
#include "module.hpp"
#include "versions.hpp"

namespace bedrock::protocol::python {

template <typename T>
concept Serializable = requires(BinaryWriter &writer, BinaryReader &reader, const T &value) {
    Serializer<T>::serialize(writer, value);
    Serializer<T>::deserialize(reader);
};

template <typename T>
concept Packet = Reflected<T> && Serializable<T> && requires {
    { T::Id } -> std::convertible_to<int>;
};

template <typename T, std::size_t I>
using field_t = std::remove_cvref_t<decltype(field_get<I>(std::declval<T &>()))>;

inline std::string python_name(std::string_view name)
{
    const nb::object iskeyword = nb::module_::import_("keyword").attr("iskeyword");
    const bool keyword = nb::cast<bool>(iskeyword(nb::str(name.data(), name.size())));
    return keyword ? std::format("{}_", name) : std::string(name);
}

template <typename T>
const auto &python_names()
{
    static const auto names = [] {
        std::array<std::string, field_count<T>()> out{};
        for (std::size_t i = 0; i < out.size(); ++i) {
            out[i] = python_name(field_names<T>()[i]);
        }
        return out;
    }();
    return names;
}

inline nb::object owner_of(nb::handle module, std::string_view qualified, std::string_view &leaf)
{
    nb::object scope = nb::borrow(module);
    for (auto pos = qualified.find("::"); pos != std::string_view::npos; pos = qualified.find("::")) {
        scope = scope.attr(nb::str(qualified.data(), pos));
        qualified.remove_prefix(pos + 2);
    }
    leaf = qualified;
    return scope;
}

template <typename T>
nb::bytes encode(const T &value)
{
    std::string buffer;
    BinaryWriter writer{buffer};
    Serializer<T>::serialize(writer, value);
    return nb::bytes(buffer.data(), buffer.size());
}

template <typename T>
T decode_or_raise(BinaryReader &reader)
{
    auto value = protocol::decode<T>(reader);
    if (!value) {
        throw_decode_error(value.error());
    }
    return std::move(*value);
}

template <typename T>
T decode_all(nb::bytes data)
{
    BinaryReader reader{std::string_view(data.c_str(), data.size())};
    return decode_or_raise<T>(reader);
}

template <typename E>
void bind_enum(nb::handle scope, const char *name)
{
    nb::enum_<E> cls(scope, name, nb::is_arithmetic());
    const auto &values = enum_values<E>();
    const auto &names = enum_schema_names<E>();
    for (std::size_t i = 0; i < values.size(); ++i) {
        cls.value(std::string(names[i]).c_str(), values[i]);
    }
}

template <typename T>
inline constexpr bool is_optional_v = false;
template <typename T>
inline constexpr bool is_optional_v<std::optional<T>> = true;
template <typename T>
inline constexpr bool is_list_v = false;
template <typename T, typename A>
inline constexpr bool is_list_v<std::vector<T, A>> = true;
template <>
inline constexpr bool is_list_v<std::vector<std::byte>> = false;
template <typename T>
inline constexpr bool is_array_v = false;
template <typename T, std::size_t N>
inline constexpr bool is_array_v<std::array<T, N>> = true;

template <typename F>
inline constexpr bool nullable_v = is_optional_v<F>;
template <typename... Ts>
inline constexpr bool nullable_v<std::variant<Ts...>> = (std::is_same_v<Ts, std::monostate> || ...);
template <>
inline constexpr bool nullable_v<DynamicValue> = true;

template <typename F>
struct python_type {
    using type = F;
};
template <typename F>
    requires std::is_enum_v<F>
struct python_type<F> {
    using type = std::variant<F, int>;
};
template <typename T>
struct python_type<std::optional<T>> {
    using type = std::optional<typename python_type<T>::type>;
};
template <typename T, typename A>
struct python_type<std::vector<T, A>> {
    using type = std::vector<typename python_type<T>::type>;
};
template <>
struct python_type<std::vector<std::byte>> {
    using type = std::vector<std::byte>;
};
template <typename F>
using python_type_t = typename python_type<F>::type;

template <typename F>
constexpr bool holds_enum()
{
    if constexpr (std::is_enum_v<F>) {
        return true;
    }
    else if constexpr (is_optional_v<F> || is_list_v<F> || is_array_v<F>) {
        return holds_enum<typename F::value_type>();
    }
    else {
        return false;
    }
}

template <typename F>
nb::object to_python(const F &value)
{
    if constexpr (std::is_enum_v<F>) {
        if (enum_contains(value)) {
            return nb::cast(value);
        }
        return nb::cast(enum_integer(value));
    }
    else if constexpr (is_optional_v<F>) {
        return value ? to_python(*value) : nb::none();
    }
    else if constexpr (is_list_v<F> || is_array_v<F>) {
        nb::list out;
        for (const auto &item : value) {
            out.append(to_python(item));
        }
        return out;
    }
    else {
        return nb::cast(value, nb::rv_policy::copy);
    }
}

template <typename F>
F from_python(nb::handle src, const std::string &label)
{
    if constexpr (std::is_enum_v<F>) {
        if (PyLong_Check(src.ptr())) {
            F member;
            if (nb::try_cast(src, member)) {
                return member;
            }
            std::underlying_type_t<F> integer;
            if (nb::try_cast(src, integer)) {
                return static_cast<F>(integer);
            }
        }
    }
    else if constexpr (is_optional_v<F>) {
        return src.is_none() ? F{} : F{from_python<typename F::value_type>(src, label)};
    }
    else if constexpr (is_list_v<F>) {
        std::vector<nb::object> items;
        if (nb::try_cast(src, items)) {
            F out;
            for (const nb::object &item : items) {
                out.push_back(from_python<typename F::value_type>(item, label));
            }
            return out;
        }
    }
    else if constexpr (is_array_v<F>) {
        std::vector<nb::object> items;
        F out{};
        if (nb::try_cast(src, items) && items.size() == out.size()) {
            for (std::size_t i = 0; i < out.size(); ++i) {
                out[i] = from_python<typename F::value_type>(items[i], label);
            }
            return out;
        }
    }
    else {
        F out;
        if (nb::try_cast(src, out)) {
            return out;
        }
    }
    throw nb::type_error(std::format("{}: cannot hold {}", label, nb::repr(src).c_str()).c_str());
}

template <typename T>
std::string describe(const T &value)
{
    try {
        return nb::repr(to_python(value)).c_str();
    }
    catch (const std::exception &) {
        PyErr_Clear();
        return "<?>";
    }
}

template <typename T, std::size_t I>
const std::string &field_label()
{
    static const std::string label = std::format("{}.{}", struct_name<T>(), python_names<T>()[I]);
    return label;
}

template <typename T, std::size_t I>
void bind_field(nb::class_<T> &cls)
{
    using F = field_t<T, I>;
    const char *name = python_names<T>()[I].c_str();
    const auto setter = [](T &self, nb::typed<nb::handle, python_type_t<nb::remove_opt_mono_t<F>>> value) {
        field_get<I>(self) = from_python<F>(value, field_label<T, I>());
    };
    const auto value_arg = nb::for_setter(nb::arg("value").none(nullable_v<F>));
    if constexpr (holds_enum<F>()) {
        cls.def_prop_rw(
            name,
            [](const T &self) -> nb::typed<nb::object, python_type_t<F>> { return to_python(field_get<I>(self)); },
            setter, value_arg);
    }
    else if constexpr (Reflected<F>) {
        cls.def_prop_rw(
            name, [](T &self) -> F & { return field_get<I>(self); }, setter, nb::rv_policy::reference_internal,
            value_arg);
    }
    else {
        cls.def_prop_rw(
            name, [](const T &self) -> const F & { return field_get<I>(self); }, setter, nb::rv_policy::copy,
            value_arg);
    }
}

template <typename T>
void bind_struct(nb::handle scope, const char *name, const Version *version)
{
    static_assert(!field_contains<T>("from_bytes"), "a member named from_bytes hides T.from_bytes");
    nb::class_<T> cls(scope, name, nb::supplement<Codec>(), nb::is_final());
    [&]<std::size_t... I>(std::index_sequence<I...>) {
        if constexpr (sizeof...(I) == 0) {
            cls.def(nb::init<>());
        }
        else {
            cls.def(
                "__init__",
                [](T *self, nb::typed<nb::handle, python_type_t<nb::remove_opt_mono_t<field_t<T, I>>>>... values) {
                    T value{};
                    (
                        [&] {
                            if (!values.is(nb::ellipsis())) {
                                field_get<I>(value) = from_python<field_t<T, I>>(values, field_label<T, I>());
                            }
                        }(),
                        ...);
                    new (self) T(std::move(value));
                },
                nb::kw_only(),
                (nb::arg(python_names<T>()[I].c_str()).none(nullable_v<field_t<T, I>>).sig("...") = nb::ellipsis())...);
        }
        (bind_field<T, I>(cls), ...);
    }(std::make_index_sequence<field_count<T>()>{});

    cls.def(nb::self == nb::self);
    cls.attr("__hash__") = nb::none();
    cls.def("__copy__", [](const T &self) { return T(self); });
    cls.def("__deepcopy__", [](const T &self, nb::handle) { return T(self); }, nb::arg("memo"));
    cls.def("__repr__", [](const T &self) {
        std::string members;
        [&]<std::size_t... I>(std::index_sequence<I...>) {
            ((members += std::format("{}{}={}", I ? ", " : "", python_names<T>()[I], describe(field_get<I>(self)))),
             ...);
        }(std::make_index_sequence<field_count<T>()>{});
        return std::format("{}({})", struct_name<T>().substr(struct_name<T>().rfind(':') + 1), members);
    });

    if constexpr (Serializable<T>) {
        cls.def("__bytes__", &encode<T>, "The wire form, without a packet header.");
        cls.def_static("from_bytes", &decode_all<T>, nb::arg("data"), "Reads one value that must span all of `data`.");
    }
    if constexpr (Packet<T>) {
        cls.attr("ID") = T::Id;
        nb::type_supplement<Codec>(cls).decode = [](BinaryReader &stream) -> nb::object {
            return nb::cast(decode_or_raise<T>(stream));
        };
        if (version != nullptr) {
            version->packets[nb::int_(T::Id)] = cls;
        }
    }
}

template <typename T>
void bind_type(nb::handle module, const Version *version)
{
    std::string_view qualified;
    if constexpr (std::is_enum_v<T>) {
        qualified = enum_type_name<T>();
    }
    else {
        qualified = struct_name<T>();
    }
    std::string_view leaf;
    nb::object scope = owner_of(module, qualified, leaf);
    const std::string name(leaf);

    if (nb::handle existing = nb::type<T>(); existing.is_valid()) {
        scope.attr(name.c_str()) = existing;
        if constexpr (Packet<T>) {
            if (version != nullptr) {
                version->packets[nb::int_(T::Id)] = existing;
            }
        }
        return;
    }
    if constexpr (std::is_enum_v<T>) {
        bind_enum<T>(scope, name.c_str());
    }
    else {
        bind_struct<T>(scope, name.c_str(), version);
    }
}

template <template <int> class Types>
void bind_schema_types(std::span<const Version> bound)
{
    [&]<std::size_t... I>(std::index_sequence<I...>) {
        constexpr std::size_t newest = versions.size() - 1;
        (
            [&]<typename... C, typename... P>(const Version &version, type_list<C...>, type_list<P...>) {
                (bind_type<C>(version.module, &version), ...);
                (bind_type<P>(version.pre_cereal, &version), ...);
            }(bound[newest - I], typename Types<versions[newest - I]>::cereal{},
              typename Types<versions[newest - I]>::pre_cereal{}),
            ...);
    }(std::make_index_sequence<versions.size()>{});
}

}  // namespace bedrock::protocol::python
