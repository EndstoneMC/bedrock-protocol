#pragma once

#include <algorithm>
#include <array>
#include <concepts>
#include <cstddef>
#include <cstdint>
#include <expected>
#include <format>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <tuple>
#include <type_traits>
#include <typeinfo>
#include <unordered_map>
#include <utility>
#include <variant>
#include <vector>

#include <nanobind/nanobind.h>

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

struct Scope {
    int number;
    nb::handle module;
    CodecTable *codecs;
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

struct Label {
    std::string_view type;
    std::string_view field;
};

[[noreturn]] void throw_cannot_hold(const Label &label, nb::handle src);

template <typename F>
F from_python(nb::handle src, const Label &label)
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
    throw_cannot_hold(label, src);
}

struct Field {
    std::ptrdiff_t offset;
    void (*assign)(void *field, nb::handle src, const Label &label);
    bool (*equal)(const void *a, const void *b);
    nb::object (*value)(const void *field);
};

struct StructInfo {
    const std::type_info *cpp_type;
    std::string_view name;
    const std::string *names;
    std::span<const Field> fields;
    void (*construct)(void *storage, PyObject **args, const StructInfo &info);
    PyTypeObject *type;
};

void *field_address(nb::handle self, const StructInfo &info, std::size_t index);
void assign_fields(void *value, PyObject **args, const StructInfo &info);
PyObject *construct_impl(void *capture, PyObject **args, std::uint8_t *flags, nb::rv_policy policy,
                         nb::detail::cleanup_list *cleanup);
nb::object copy_instance(nb::handle self, const StructInfo &info);
void def_eq(nb::handle cls, const StructInfo &info);
void def_repr(nb::handle cls, const StructInfo &info);

template <typename F>
void assign_at(void *field, nb::handle src, const Label &label)
{
    *static_cast<F *>(field) = from_python<F>(src, label);
}

template <typename F>
bool equal_at(const void *a, const void *b)
{
    return *static_cast<const F *>(a) == *static_cast<const F *>(b);
}

template <typename F>
nb::object value_at(const void *field)
{
    return to_python(*static_cast<const F *>(field));
}

template <typename T>
void construct_from(void *storage, PyObject **args, const StructInfo &info)
{
    T value{};
    assign_fields(&value, args, info);
    new (storage) T(std::move(value));
}

template <typename T>
StructInfo &struct_info()
{
    static const auto fields = [] {
        const T probe{};
        const auto *base = reinterpret_cast<const char *>(&probe);
        return [&]<std::size_t... I>(std::index_sequence<I...>) {
            return std::array<Field, sizeof...(I)>{Field{reinterpret_cast<const char *>(&field_get<I>(probe)) - base,
                                                         &assign_at<field_t<T, I>>, &equal_at<field_t<T, I>>,
                                                         &value_at<field_t<T, I>>}...};
        }(std::make_index_sequence<field_count<T>()>{});
    }();
    static StructInfo info{&typeid(T), struct_name<T>(), python_names<T>().data(), fields, &construct_from<T>, nullptr};
    return info;
}

template <typename F>
void bind_field(nb::handle cls, const StructInfo &info, std::size_t index)
{
    const StructInfo *owner = &info;
    nb::object get;
    if constexpr (holds_enum<F>()) {
        get = nb::cpp_function(
            [owner, index](nb::handle self) -> nb::typed<nb::object, python_type_t<F>> {
                return to_python(*static_cast<const F *>(field_address(self, *owner, index)));
            },
            nb::is_method(), nb::is_getter());
    }
    else if constexpr (Reflected<F>) {
        get = nb::cpp_function(
            [owner, index](nb::handle self) -> F & { return *static_cast<F *>(field_address(self, *owner, index)); },
            nb::is_method(), nb::is_getter(), nb::rv_policy::reference_internal);
    }
    else {
        get = nb::cpp_function(
            [owner, index](nb::handle self) -> const F & {
                return *static_cast<const F *>(field_address(self, *owner, index));
            },
            nb::is_method(), nb::is_getter(), nb::rv_policy::copy);
    }
    const nb::object set = nb::cpp_function(
        [owner, index](nb::handle self, field_arg<F> value) {
            assign_at<F>(field_address(self, *owner, index), value, Label{owner->name, owner->names[index]});
        },
        nb::is_method(), nb::arg("value").none(nullable_v<F>));
    nb::detail::property_install(cls.ptr(), owner->names[index].c_str(), get.ptr(), set.ptr());
}

template <std::size_t N>
void def_init(nb::handle cls, const StructInfo &info, const char *descr, const std::type_info **types,
              const std::array<bool, N> &nullable)
{
    nb::detail::func_data_prelim<N> record{};
    record.capture[0] = const_cast<StructInfo *>(&info);
    record.impl = &construct_impl;
    record.descr = descr;
    record.descr_types = types;
    record.flags = static_cast<std::uint32_t>(nb::detail::func_flags::has_args) |
                   static_cast<std::uint32_t>(nb::detail::func_flags::is_method) |
                   static_cast<std::uint32_t>(nb::detail::func_flags::has_name) |
                   static_cast<std::uint32_t>(nb::detail::func_flags::has_scope);
    record.nargs = N + 1;
    record.nargs_pos = 1;
    record.name = "__init__";
    record.scope = cls.ptr();
    for (std::size_t i = 0; i < N; ++i) {
        const auto none = nullable[i] ? nb::detail::cast_flags::accepts_none : nb::detail::cast_flags{};
        record.args[i] = {info.names[i].c_str(), "...", nullptr, Py_Ellipsis,
                          static_cast<std::uint8_t>(static_cast<std::uint8_t>(none) |
                                                    static_cast<std::uint8_t>(nb::detail::cast_flags::convert))};
    }
    nb::detail::nb_func_new(&record);
}

template <typename T, std::size_t... I>
void bind_init(nb::handle cls, const StructInfo &info, std::index_sequence<I...>)
{
    static constexpr auto descr = nb::detail::const_name("(") +
                                  concat(type_descr(nb::detail::make_caster<T>::Name),
                                         type_descr(nb::detail::make_caster<field_arg<field_t<T, I>>>::Name)...) +
                                  nb::detail::const_name(") -> ") +
                                  nb::detail::make_caster<nb::detail::void_type>::Name;
    static constexpr std::array<bool, sizeof...(I)> nullable{nullable_v<field_t<T, I>>...};
    std::array<const std::type_info *, descr.type_count() + 1> types{};
    descr.put_types(types.data());
    def_init<sizeof...(I)>(cls, info, descr.text, types.data(), nullable);
}

template <typename T>
void bind_struct(nb::handle scope, const char *name)
{
    nb::class_<T> cls(scope, name, nb::is_final());
    StructInfo &info = struct_info<T>();
    info.type = reinterpret_cast<PyTypeObject *>(cls.ptr());
    if constexpr (field_count<T>() == 0) {
        cls.def(nb::init<>());
    }
    else {
        bind_init<T>(cls, info, std::make_index_sequence<field_count<T>()>{});
    }
    [&]<std::size_t... I>(std::index_sequence<I...>) {
        (bind_field<field_t<T, I>>(cls, info, I), ...);
    }(std::make_index_sequence<field_count<T>()>{});

    def_eq(cls, info);
    cls.attr("__hash__") = nb::none();
    cls.def("__copy__",
            [](nb::handle self) -> nb::typed<nb::object, T> { return copy_instance(self, struct_info<T>()); });
    cls.def(
        "__deepcopy__",
        [](nb::handle self, nb::handle) -> nb::typed<nb::object, T> { return copy_instance(self, struct_info<T>()); },
        nb::arg("memo"));
    def_repr(cls, info);

    if constexpr (requires { T::Id; }) {
        cls.attr("ID") = T::Id;
    }
}

struct ModeCodec {
    int since;
    const Codec *codec;
};

struct VersionBinding {
    std::array<ModeCodec, mode_count> modes;
    std::optional<int> packet;
};

void bind_version(nb::handle home, const Scope &scope, std::string_view label, std::string_view declared,
                  const std::type_info *cpp_type, void (*bind)(nb::handle, const char *),
                  const VersionBinding &binding);

template <typename T, int V, SerializationMode M>
constexpr ModeCodec mode_codec()
{
    if constexpr (Serializable<T, V, M>) {
        constexpr int since = Serializer<T, V, M>::since;
        return {since, &codec<T, since, implementation<T, V, M>>};
    }
    else {
        return {};
    }
}

template <typename T, int V>
constexpr VersionBinding version_binding()
{
    VersionBinding out{};
    if constexpr (!std::is_enum_v<T>) {
        if constexpr (Serializable<T, V, SerializationMode::Default>) {
            out.modes[std::to_underlying(SerializationMode::Default)] = mode_codec<T, V, SerializationMode::Default>();
        }
        else {
            out.modes[std::to_underlying(SerializationMode::Cereal)] = mode_codec<T, V, SerializationMode::Cereal>();
            out.modes[std::to_underlying(SerializationMode::Manual)] = mode_codec<T, V, SerializationMode::Manual>();
        }
    }
    if constexpr (Packet<T, V>) {
        out.packet = T::Id;
    }
    return out;
}

template <typename T, int V>
inline constexpr VersionBinding version_binding_v = version_binding<T, V>();

template <typename T>
void bind_new_type(nb::handle scope, const char *name)
{
    if constexpr (std::is_enum_v<T>) {
        bind_enum<T>(scope, name);
    }
    else {
        bind_struct<T>(scope, name);
    }
}

template <typename T, int V>
void bind_type(nb::handle home, const Scope &scope, std::string_view label)
{
    std::string_view declared;
    if constexpr (std::is_enum_v<T>) {
        declared = enum_type_name<T>();
    }
    else {
        declared = struct_name<T>();
    }
    bind_version(home, scope, label, declared, &typeid(T), &bind_new_type<T>, version_binding_v<T, V>);
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
