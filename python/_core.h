#pragma once

#include <algorithm>
#include <array>
#include <concepts>
#include <cstddef>
#include <expected>
#include <format>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <tuple>
#include <type_traits>
#include <unordered_map>
#include <utility>
#include <variant>
#include <vector>

#include <nanobind/nanobind.h>
#include <nanobind/operators.h>

#include "bedrock/protocol/detail/reflect.hpp"
#include "bedrock/protocol/enum.hpp"
#include "bedrock/protocol/serializer.hpp"
#include "bedrock/protocol/stream.hpp"
#include "bedrock/protocol/version.hpp"
#include "casters.hpp"

namespace bedrock::protocol {

template <typename... As, typename... Bs>
constexpr type_list<As..., Bs...> operator+(type_list<As...>, type_list<Bs...>)
{
    return {};
}

}  // namespace bedrock::protocol

namespace bedrock::protocol::python {

namespace nb = nanobind;

inline constexpr const char *eq_signature = "def __eq__(self, arg: object, /) -> bool";

struct Codec {
    std::expected<void, EncodeError> (*encode)(BinaryWriter &stream, nb::handle value);
    nb::object (*decode)(BinaryReader &stream);
};

inline constexpr std::size_t mode_count = 3;

using CodecTable = std::unordered_map<PyObject *, std::array<const Codec *, mode_count>>;

struct EnumNumbering {
    nb::object (*integer)(nb::handle value);
    nb::object (*cast)(nb::handle number);
    nb::object (*values)();
};

using EnumTable = std::unordered_map<PyObject *, const EnumNumbering *>;

struct EnumNaming {
    nb::object (*name)(nb::handle value);
    nb::object (*cast)(std::string_view name);
    nb::object (*names)();
    nb::object (*entries)();
};

using NamingTable = std::unordered_map<PyObject *, const EnumNaming *>;

struct Scope {
    int number;
    nb::handle module;
    CodecTable *codecs;
    EnumTable *enums;
    NamingTable *namings;
    nb::object names;
    nb::dict encodings;
    nb::dict modes;
    nb::dict packets;
};

[[noreturn]] void throw_decode_error(const DecodeError &error);
[[noreturn]] void throw_encode_error(const EncodeError &error);

void init_nbt(nb::module_ &parent);
void init_versions(nb::module_ &core, nb::module_ &package);

void init_types(nb::handle package, std::span<const Scope> bound);

std::tuple<nb::object, nb::object, std::string_view> claim_owner(const Scope &scope, nb::handle home,
                                                                 std::string_view declared, std::string_view label,
                                                                 bool create);
void register_mode(const Scope &scope, nb::handle cls, SerializationMode mode, int since, const Codec *codec);
void register_packet(const Scope &scope, int id, nb::handle cls);
void bind_name(nb::handle owner, std::string_view leaf, nb::handle cls);

template <typename S, typename T, int N, SerializationMode K>
concept Derives = std::derived_from<S, Serializer<T, N, K>> && !std::same_as<S, Serializer<T, N, K>>;

template <typename T, int V, SerializationMode M>
inline constexpr SerializationMode implementation = [] {
    using Self = Serializer<T, V, M>;
    constexpr int since = Self::since;
    constexpr std::array found{Derives<Self, T, since, SerializationMode::Default>,
                               Derives<Self, T, since, SerializationMode::Cereal>,
                               Derives<Self, T, since, SerializationMode::Manual>};
    constexpr auto count = std::ranges::count(found, true);
    static_assert(count <= 1, "a serializer derives from more than one implementation");
    static_assert(count == 1 || since == V, "a serializer derives from no implementation");
    return count == 0 ? M : static_cast<SerializationMode>(std::ranges::find(found, true) - found.begin());
}();

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

template <typename T, int N, SerializationMode M>
inline constexpr Codec codec{
    .encode =
        [](BinaryWriter &stream, nb::handle value) {
            return detail::encode_fn<N>{}(*nb::inst_ptr<T>(value), stream, detail::serialization_mode_t<M>());
        },
    .decode = [](BinaryReader &stream) -> nb::object {
        auto value = detail::decode_fn<N, T>{}(stream, detail::serialization_mode_t<M>());
        if (!value) {
            throw_decode_error(value.error());
        }
        return nb::cast(std::move(*value));
    },
};

template <typename E>
void bind_enum(nb::handle scope, const char *name)
{
    nb::enum_<E> cls(scope, name, nb::is_arithmetic());
    const auto &values = enum_values<E>();
    const auto &names = enum_schema_names<E>();
    for (std::size_t i = 0; i < values.size(); ++i) {
        cls.value(std::string(names[i]).c_str(), values[i], enum_deprecated<E>(i) ? "Deprecated." : nullptr);
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
struct arg_type {
    using type = F;
};
template <typename T>
struct arg_type<std::optional<T>> : arg_type<T> {};
template <typename... Ts>
struct arg_type<type_list<Ts...>> {
    using type = std::variant<Ts...>;
};
template <typename... Ts>
struct arg_type<std::variant<Ts...>>
    : arg_type<decltype((type_list<>{} + ... +
                         std::conditional_t<std::is_same_v<Ts, std::monostate>, type_list<>,
                                            type_list<typename arg_type<Ts>::type>>{}))> {};

template <typename D>
struct arg_descr {
    D name;
};

template <typename D>
constexpr auto type_descr(const arg_descr<D> &descr)
{
    return arg_descr{nb::detail::type_descr(descr.name)};
}

template <typename D>
struct descr_traits;
template <std::size_t N, typename... Ts>
struct descr_traits<nb::detail::descr<N, Ts...>> {
    static constexpr std::size_t size = N;
    using types = type_list<Ts...>;
};

template <typename D, typename... Ds>
constexpr auto concat(const arg_descr<D> &first, const arg_descr<Ds> &...rest)
{
    constexpr std::string_view separator = ", ";
    constexpr std::size_t size = (descr_traits<D>::size + ... + (separator.size() + descr_traits<Ds>::size));
    std::array<char, size> text{};
    auto out = std::copy_n(first.name.text, descr_traits<D>::size, text.begin());
    ((out = std::copy_n(rest.name.text, descr_traits<Ds>::size, std::copy(separator.begin(), separator.end(), out))),
     ...);
    return [&]<std::size_t... Is, typename... Ts>(std::index_sequence<Is...>, type_list<Ts...>) {
        return nb::detail::descr<size, Ts...>(text[Is]...);
    }(std::make_index_sequence<size>{}, (typename descr_traits<D>::types{} + ... + typename descr_traits<Ds>::types{}));
}

template <typename F>
struct field_arg : nb::handle {
    static constexpr auto Name = arg_descr{nb::detail::make_caster<python_type_t<typename arg_type<F>::type>>::Name};

    using nb::handle::handle;
    field_arg(const nb::handle &h) : nb::handle(h) {}
};

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
        for (const typename F::value_type &item : value) {
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

template <typename E, int V>
inline constexpr EnumNumbering enum_numbering{
    .integer = [](nb::handle value) -> nb::object {
        const auto number = enum_integer_<V>(nb::cast<E>(value));
        return number ? nb::cast(*number) : nb::none();
    },
    .cast = [](nb::handle number) -> nb::object {
        const auto value = enum_cast_<V, E>(from_python<std::underlying_type_t<E>>(number, "number"));
        return value ? to_python(*value) : nb::none();
    },
    .values = []() -> nb::object {
        nb::list out;
        for (const E value : enum_values_<V, E>()) {
            out.append(nb::cast(value));
        }
        return nb::tuple(out);
    },
};

template <typename E, int V>
inline constexpr EnumNaming enum_naming{
    .name = [](nb::handle value) -> nb::object {
        const auto name = enum_name_<V>(nb::cast<E>(value));
        return name ? nb::cast(std::string(*name)) : nb::none();
    },
    .cast = [](std::string_view name) -> nb::object {
        const auto value = enum_cast_<V, E>(name);
        return value ? nb::cast(*value) : nb::none();
    },
    .names = []() -> nb::object {
        nb::list out;
        for (const std::string_view name : enum_names_<V, E>()) {
            out.append(std::string(name));
        }
        return nb::tuple(out);
    },
    .entries = []() -> nb::object {
        nb::list out;
        for (const auto &[value, name] : enum_entries_<V, E>()) {
            out.append(nb::make_tuple(value, std::string(name)));
        }
        return nb::tuple(out);
    },
};

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
    const auto setter = [](T &self, field_arg<F> value) {
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
void bind_struct(nb::handle scope, const char *name)
{
    nb::class_<T> cls(scope, name, nb::is_final());
    [&]<std::size_t... I>(std::index_sequence<I...>) {
        if constexpr (sizeof...(I) == 0) {
            cls.def(nb::init<>());
        }
        else {
            cls.def(
                "__init__",
                [](T *self, field_arg<field_t<T, I>>... values) {
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

    cls.def(nb::self == nb::self, nb::sig(eq_signature));
    cls.attr("__hash__") = nb::none();
    cls.def("__copy__", [](const T &self) { return T(self); });
    cls.def("__deepcopy__", [](const T &self, nb::handle) { return T(self); }, nb::arg("memo"));
    cls.def("__repr__", [](const T &self) {
        std::string members;
        [&]<std::size_t... I>(std::index_sequence<I...>) {
            ((members += std::format("{}{}={}", I ? ", " : "", python_names<T>()[I],
                                     nb::repr(to_python(field_get<I>(self))).c_str())),
             ...);
        }(std::make_index_sequence<field_count<T>()>{});
        return std::format("{}({})", nb::cast<std::string>(nb::type<T>().attr("__qualname__")), members);
    });

    if constexpr (requires { T::Id; }) {
        cls.attr("ID") = T::Id;
    }
}

template <typename T, int V>
void bind_type(nb::handle home, const Scope &scope, std::span<const Scope> bound, std::string_view label)
{
    std::string_view declared;
    if constexpr (std::is_enum_v<T>) {
        declared = enum_type_name<T>();
    }
    else {
        declared = struct_name<T>();
    }
    nb::handle cls = nb::type<T>();
    const auto [owner, parent, leaf] = claim_owner(scope, home, declared, label, !cls.is_valid());
    if (!cls.is_valid()) {
        const std::string name(declared.substr(declared.find_last_of(':') + 1));
        if constexpr (std::is_enum_v<T>) {
            bind_enum<T>(parent, name.c_str());
            [&]<std::size_t... J>(std::index_sequence<J...>) {
                (((*bound[J].enums)[nb::type<T>().ptr()] = &enum_numbering<T, detail::versions[J]>), ...);
                if constexpr (detail::is_name_coded_v<T>) {
                    (((*bound[J].namings)[nb::type<T>().ptr()] = &enum_naming<T, detail::versions[J]>), ...);
                }
            }(std::make_index_sequence<detail::versions.size()>{});
        }
        else {
            bind_struct<T>(parent, name.c_str());
        }
        cls = nb::type<T>();
    }
    bind_name(owner, leaf, cls);
    const auto bind_modes = [&]<std::size_t... I>(std::index_sequence<I...>) {
        (
            [&] {
                constexpr auto mode = static_cast<SerializationMode>(I);
                if constexpr (Serializable<T, V, mode>) {
                    constexpr int since = Serializer<T, V, mode>::since;
                    register_mode(scope, cls, mode, since, &codec<T, since, implementation<T, V, mode>>);
                }
            }(),
            ...);
    };
    if constexpr (!std::is_enum_v<T>) {
        if constexpr (Serializable<T, V, SerializationMode::Default>) {
            bind_modes(std::index_sequence<std::to_underlying(SerializationMode::Default)>{});
        }
        else {
            bind_modes(std::index_sequence<std::to_underlying(SerializationMode::Cereal),
                                           std::to_underlying(SerializationMode::Manual)>{});
        }
    }
    if constexpr (Packet<T, V>) {
        register_packet(scope, T::Id, cls);
    }
}

template <typename T, typename List>
inline constexpr bool listed_v = false;

template <typename T, typename... L>
inline constexpr bool listed_v<T, type_list<L...>> = (std::is_same_v<T, L> || ...);

template <typename T, typename List>
struct label_position;

template <typename T, typename... L>
struct label_position<T, type_list<L...>> {
    static constexpr std::array<bool, sizeof...(L)> found{std::is_same_v<T, L>...};
    static constexpr std::size_t value = std::ranges::find(found, true) - found.begin();
};

template <typename T, template <int> class Types,
          typename Protocols = std::make_index_sequence<detail::versions.size()>>
struct holders;

template <typename T, template <int> class Types, std::size_t... J>
struct holders<T, Types, std::index_sequence<J...>> {
    static constexpr std::array<bool, sizeof...(J)> held{listed_v<T, typename Types<detail::versions[J]>::types>...};
    static constexpr std::size_t first = std::ranges::find(held, true) - held.begin();
};

template <template <int> class Types>
void bind_schema_types(nb::handle package, std::span<const Scope> bound)
{
    [&]<std::size_t... I>(std::index_sequence<I...>) {
        constexpr std::size_t newest = detail::versions.size() - 1;
        (
            [&] {
                constexpr int number = detail::versions[newest - I];
                const Scope &scope = bound[newest - I];
                [&]<typename... T>(type_list<T...>) {
                    (bind_type<T, number>(
                         holders<T, Types>::held.back() ? package : bound[holders<T, Types>::first].module, scope,
                         bound,
                         label_position<T, typename Types<number>::labelled>::value < Types<number>::labels.size()
                             ? Types<number>::labels[label_position<T, typename Types<number>::labelled>::value]
                             : std::string_view{}),
                     ...);
                }(typename Types<number>::types{});
            }(),
            ...);
    }(std::make_index_sequence<detail::versions.size()>{});
}

}  // namespace bedrock::protocol::python
