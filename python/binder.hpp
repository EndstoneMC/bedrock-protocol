#pragma once

#include <array>
#include <bitset>
#include <concepts>
#include <cstddef>
#include <format>
#include <map>
#include <optional>
#include <span>
#include <stdexcept>
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
    if constexpr (detail::is_reflected_v<E>) {
        const auto &values = enum_values<E>();
        const auto &names = enum_schema_names<E>();
        for (std::size_t i = 0; i < values.size(); ++i) {
            cls.value(std::string(names[i]).c_str(), values[i]);
        }
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
template <typename T>
inline constexpr bool is_map_v = false;
template <typename K, typename V, typename C, typename A>
inline constexpr bool is_map_v<std::map<K, V, C, A>> = true;
template <typename T>
inline constexpr bool is_variant_v = false;
template <typename... T>
inline constexpr bool is_variant_v<std::variant<T...>> = true;
template <typename T>
inline constexpr bool is_bitset_v = false;
template <std::size_t N>
inline constexpr bool is_bitset_v<std::bitset<N>> = true;

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
        if constexpr (detail::is_reflected_v<F>) {
            if (enum_contains(value)) {
                return nb::cast(value);
            }
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
F from_python(nb::handle src)
{
    if constexpr (std::is_enum_v<F>) {
        if (!PyLong_Check(src.ptr())) {
            throw nb::type_error("expected an int or an enum member");
        }
        F member;
        if (nb::try_cast(src, member)) {
            return member;
        }
        std::underlying_type_t<F> integer;
        if (!nb::try_cast(src, integer)) {
            throw nb::type_error(std::format("value {} does not fit the enum", nb::str(src).c_str()).c_str());
        }
        return static_cast<F>(integer);
    }
    else if constexpr (is_optional_v<F>) {
        return src.is_none() ? F{} : F{from_python<typename F::value_type>(src)};
    }
    else if constexpr (is_list_v<F>) {
        F out;
        for (nb::handle item : nb::iter(src)) {
            out.push_back(from_python<typename F::value_type>(item));
        }
        return out;
    }
    else if constexpr (is_array_v<F>) {
        F out{};
        std::size_t i = 0;
        for (nb::handle item : nb::iter(src)) {
            if (i == out.size()) {
                throw nb::type_error("too many elements");
            }
            out[i++] = from_python<typename F::value_type>(item);
        }
        if (i != out.size()) {
            throw nb::type_error("too few elements");
        }
        return out;
    }
    else {
        return nb::cast<F>(src);
    }
}

template <typename F>
nb::object annotation()
{
    const auto builtin = [](const char *name) {
        return nb::module_::import_("builtins").attr(name);
    };
    const auto typing = [](const char *name) {
        return nb::module_::import_("typing").attr(name);
    };
    if constexpr (std::is_same_v<F, bool>) {
        return builtin("bool");
    }
    else if constexpr (std::is_integral_v<F> || PrimitiveAlias<F> || is_bitset_v<F>) {
        return builtin("int");
    }
    else if constexpr (std::is_floating_point_v<F>) {
        return builtin("float");
    }
    else if constexpr (std::is_same_v<F, std::string>) {
        return builtin("str");
    }
    else if constexpr (std::is_same_v<F, std::vector<std::byte>>) {
        return builtin("bytes");
    }
    else if constexpr (std::is_same_v<F, UUID>) {
        return nb::module_::import_("uuid").attr("UUID");
    }
    else if constexpr (std::is_same_v<F, std::monostate>) {
        return nb::none();
    }
    else if constexpr (std::is_same_v<F, CompoundTagData>) {
        return annotation<CompoundTag>();
    }
    else if constexpr (is_optional_v<F>) {
        return typing("Optional")[annotation<typename F::value_type>()];
    }
    else if constexpr (is_list_v<F> || is_array_v<F>) {
        return builtin("list").attr("__class_getitem__")(annotation<typename F::value_type>());
    }
    else if constexpr (is_map_v<F>) {
        return builtin("dict").attr("__class_getitem__")(
            nb::make_tuple(annotation<typename F::key_type>(), annotation<typename F::mapped_type>()));
    }
    else if constexpr (is_variant_v<F>) {
        return [&]<typename... A>(std::type_identity<std::variant<A...>>) {
            return typing("Union")[nb::make_tuple(annotation<A>()...)];
        }(std::type_identity<F>{});
    }
    else if (nb::handle bound = nb::type<F>(); bound.is_valid()) {
        return nb::borrow(bound);
    }
    else {
        return typing("Any");
    }
}

template <typename T>
nb::dict annotations()
{
    nb::dict out;
    [&]<std::size_t... I>(std::index_sequence<I...>) {
        ((out[python_names<T>()[I].c_str()] = annotation<field_t<T, I>>()), ...);
    }(std::make_index_sequence<field_count<T>()>{});
    return out;
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
void bind_field(nb::class_<T> &cls)
{
    using F = field_t<T, I>;
    const char *name = python_names<T>()[I].c_str();
    if constexpr (holds_enum<F>()) {
        cls.def_prop_rw(
            name, [](const T &self) { return to_python(field_get<I>(self)); },
            [](T &self, nb::handle value) { field_get<I>(self) = from_python<F>(value); });
    }
    else if constexpr (Reflected<F>) {
        cls.def_prop_rw(
            name, [](T &self) -> F & { return field_get<I>(self); },
            [](T &self, const F &value) { field_get<I>(self) = value; }, nb::rv_policy::reference_internal);
    }
    else {
        cls.def_prop_rw(
            name, [](const T &self) -> const F & { return field_get<I>(self); },
            [](T &self, const F &value) { field_get<I>(self) = value; }, nb::rv_policy::copy);
    }
}

template <typename T, std::size_t I>
void assign(T &value, nb::handle src)
{
    try {
        field_get<I>(value) = from_python<field_t<T, I>>(src);
    }
    catch (const nb::cast_error &) {
        throw nb::type_error(
            std::format("{}.{} cannot hold {}", struct_name<T>(), python_names<T>()[I], nb::repr(src).c_str()).c_str());
    }
}

template <typename T>
T construct(nb::args args, nb::kwargs kwargs)
{
    constexpr std::size_t N = field_count<T>();
    if (args.size() > N) {
        throw nb::type_error(std::format("{} takes at most {} positional arguments", struct_name<T>(), N).c_str());
    }
    T value{};
    std::size_t used = 0;
    [&]<std::size_t... I>(std::index_sequence<I...>) {
        (
            [&] {
                const char *name = python_names<T>()[I].c_str();
                const bool keyword = kwargs.contains(name);
                if (I < args.size()) {
                    if (keyword) {
                        throw nb::type_error(
                            std::format("{} got multiple values for '{}'", struct_name<T>(), name).c_str());
                    }
                    assign<T, I>(value, args[I]);
                }
                else if (keyword) {
                    assign<T, I>(value, kwargs[name]);
                    ++used;
                }
            }(),
            ...);
    }(std::make_index_sequence<N>{});
    if (used != kwargs.size()) {
        for (auto [key, _] : kwargs) {
            bool known = false;
            [&]<std::size_t... I>(std::index_sequence<I...>) {
                ((known = known || nb::str(python_names<T>()[I].c_str()).equal(key)), ...);
            }(std::make_index_sequence<N>{});
            if (!known) {
                throw nb::type_error(
                    std::format("{} has no field '{}'", struct_name<T>(), nb::cast<std::string>(key)).c_str());
            }
        }
    }
    return value;
}

template <typename T>
void bind_struct(nb::handle scope, const char *name, Version *version)
{
    nb::class_<T> cls(scope, name, nb::supplement<Codec>());
    cls.def("__init__", [](T *self, nb::args args, nb::kwargs kwargs) { new (self) T(construct<T>(args, kwargs)); });
    [&]<std::size_t... I>(std::index_sequence<I...>) {
        (bind_field<T, I>(cls), ...);
    }(std::make_index_sequence<field_count<T>()>{});

    nb::list fields;
    for (std::size_t i = 0; i < field_count<T>(); ++i) {
        fields.append(nb::str(python_names<T>()[i].c_str()));
    }
    cls.attr("__match_args__") = nb::tuple(fields);
    annotators().emplace_back(cls, &annotations<T>);
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
        for (const std::string &field : python_names<T>()) {
            if (field == "from_bytes") {
                throw std::logic_error(std::format("{} has a member named from_bytes", struct_name<T>()));
            }
        }
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
void bind_type(nb::handle module, Version *version)
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
        (
            [&]<typename... C, typename... L>(Version version, type_list<C...>, type_list<L...>) {
                (bind_type<C>(version.module, &version), ...);
                (bind_type<L>(version.legacy, &version), ...);
            }(bound[I], typename Types<versions[I]>::cereal{}, typename Types<versions[I]>::legacy{}),
            ...);
    }(std::make_index_sequence<versions.size()>{});
}

}  // namespace bedrock::protocol::python
