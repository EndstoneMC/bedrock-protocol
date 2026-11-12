#pragma once

#include <array>
#include <bitset>
#include <charconv>
#include <cmath>
#include <concepts>
#include <cstddef>
#include <format>
#include <limits>
#include <map>
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
#include "bedrock/protocol/version.hpp"
#include "casters.hpp"

namespace bedrock::protocol::python {

namespace nb = nanobind;

struct Codec {
    nb::object (*decode)(BinaryReader &stream);
};

struct Version {
    int number;
    nb::handle module;
    nb::handle pre_cereal;
    nb::dict packets;
};

[[noreturn]] void throw_decode_error(DecodeError error);

void init_nbt(nb::module_ &parent);
void init_versions(nb::module_ &parent);

void init_types(std::span<const Version> bound);

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
inline constexpr bool is_map_v = false;
template <typename K, typename V, typename C, typename A>
inline constexpr bool is_map_v<std::map<K, V, C, A>> = true;
template <typename T>
inline constexpr bool is_bitset_v = false;
template <std::size_t N>
inline constexpr bool is_bitset_v<std::bitset<N>> = true;
template <typename T>
inline constexpr bool is_variant_v = false;
template <typename... Ts>
inline constexpr bool is_variant_v<std::variant<Ts...>> = true;

template <typename A>
constexpr std::string_view variant_tag()
{
    if constexpr (Reflected<A>) {
        return struct_name<A>().substr(struct_name<A>().rfind(':') + 1);
    }
    else if constexpr (std::is_enum_v<A>) {
        return enum_type_name<A>().substr(enum_type_name<A>().rfind(':') + 1);
    }
    else if constexpr (std::is_same_v<A, bool>) {
        return "bool";
    }
    else if constexpr (std::is_integral_v<A> || PrimitiveAlias<A>) {
        return "int";
    }
    else if constexpr (std::is_floating_point_v<A>) {
        return "float";
    }
    else if constexpr (std::is_same_v<A, std::string>) {
        return "str";
    }
    else if constexpr (std::is_same_v<A, std::vector<std::byte>>) {
        return "bytes";
    }
    else if constexpr (std::is_same_v<A, UUID>) {
        return "UUID";
    }
    else {
        static_assert(is_list_v<A> || is_array_v<A>, "a variant alternative has no JSON tag");
        return "list";
    }
}

template <typename F>
nb::object to_json(const F &value);

inline nb::object tag_to_json(const Tag &tag);

inline nb::object compound_to_json(const CompoundTag &compound)
{
    nb::dict out;
    for (const auto &[key, child] : compound) {
        out[nb::cast(key)] = tag_to_json(child);
    }
    return out;
}

inline nb::object tag_to_json(const Tag &tag)
{
    return tag.visit([](const auto &payload) -> nb::object {
        using V = std::decay_t<decltype(payload)>;
        nb::dict out;
        if constexpr (std::is_same_v<V, std::monostate>) {
            return nb::none();
        }
        else if constexpr (std::is_same_v<V, CompoundTag>) {
            out["CompoundTag"] = compound_to_json(payload);
        }
        else if constexpr (std::is_same_v<V, ListTag>) {
            nb::list tags;
            for (const auto &child : payload) {
                tags.append(tag_to_json(child));
            }
            nb::dict list;
            list["type"] = static_cast<int>(payload.type());
            list["tags"] = tags;
            out["ListTag"] = list;
        }
        else if constexpr (std::is_same_v<V, ByteArrayTag> || std::is_same_v<V, IntArrayTag>) {
            nb::list values;
            for (const auto v : payload) {
                values.append(v);
            }
            out[nb::type<V>().attr("__name__")] = values;
        }
        else {
            out[nb::type<V>().attr("__name__")] = to_json(payload.value());
        }
        return out;
    });
}

template <typename F>
nb::object to_json(const F &value)
{
    if constexpr (std::is_same_v<F, bool>) {
        return nb::bool_(value);
    }
    else if constexpr (std::is_enum_v<F>) {
        if (enum_contains(value)) {
            return nb::borrow(nb::cast(value).attr("name"));
        }
        return nb::int_(enum_integer(value));
    }
    else if constexpr (std::is_floating_point_v<F>) {
        if (std::isnan(value)) {
            return nb::str("NaN");
        }
        if (std::isinf(value)) {
            return nb::str(value > 0 ? "Infinity" : "-Infinity");
        }
        char text[32];
        *std::to_chars(text, text + sizeof text - 1, value).ptr = '\0';
        double wide = 0;
        std::from_chars(text, text + std::char_traits<char>::length(text), wide);
        return nb::float_(static_cast<F>(wide) == value ? wide : static_cast<double>(value));
    }
    else if constexpr (std::is_integral_v<F> || PrimitiveAlias<F> || std::is_same_v<F, std::string> ||
                       std::is_same_v<F, DynamicValue> || is_bitset_v<F>) {
        return nb::cast(value);
    }
    else if constexpr (std::is_same_v<F, std::vector<std::byte>>) {
        return nb::bytes(reinterpret_cast<const char *>(value.data()), value.size()).attr("hex")();
    }
    else if constexpr (std::is_same_v<F, UUID>) {
        return nb::str(nb::cast(value));
    }
    else if constexpr (std::is_same_v<F, CompoundTag> || std::is_same_v<F, CompoundTagData>) {
        return compound_to_json(value);
    }
    else if constexpr (std::is_same_v<F, Tag>) {
        return tag_to_json(value);
    }
    else if constexpr (is_optional_v<F>) {
        return value ? to_json(*value) : nb::none();
    }
    else if constexpr (is_list_v<F> || is_array_v<F>) {
        nb::list out;
        for (const auto &item : value) {
            out.append(to_json(item));
        }
        return out;
    }
    else if constexpr (is_map_v<F>) {
        nb::dict out;
        for (const auto &[key, item] : value) {
            nb::object k = to_json(key);
            out[nb::isinstance<nb::str>(k) ? k : nb::str(k)] = to_json(item);
        }
        return out;
    }
    else if constexpr (is_variant_v<F>) {
        return std::visit(
            [](const auto &alternative) -> nb::object {
                using A = std::decay_t<decltype(alternative)>;
                if constexpr (std::is_same_v<A, std::monostate>) {
                    return nb::none();
                }
                else {
                    nb::dict out;
                    out[nb::str(variant_tag<A>().data(), variant_tag<A>().size())] = to_json(alternative);
                    return out;
                }
            },
            value);
    }
    else {
        static_assert(Reflected<F>, "a field type has no JSON form");
        nb::dict out;
        [&]<std::size_t... I>(std::index_sequence<I...>) {
            ((out[nb::str(field_name<I, F>().data(), field_name<I, F>().size())] = to_json(field_get<I>(value))), ...);
        }(std::make_index_sequence<field_count<F>()>{});
        return out;
    }
}

[[noreturn]] inline void json_error(const std::string &label, nb::handle src)
{
    throw nb::value_error(std::format("{}: cannot hold {}", label, nb::repr(src).c_str()).c_str());
}

template <typename F>
F from_json(nb::handle src, const std::string &label);

inline Tag tag_from_json(nb::handle src, const std::string &label);

inline CompoundTag compound_from_json(nb::handle src, const std::string &label)
{
    if (!nb::isinstance<nb::dict>(src)) {
        json_error(label, src);
    }
    CompoundTag out;
    for (auto [key, child] : nb::borrow<nb::dict>(src)) {
        if (!nb::isinstance<nb::str>(key)) {
            json_error(label, key);
        }
        const auto name = nb::cast<std::string>(key);
        out.emplace(name, tag_from_json(child, std::format("{}.{}", label, name)));
    }
    return out;
}

inline Tag tag_from_json(nb::handle src, const std::string &label)
{
    if (src.is_none()) {
        return Tag{};
    }
    if (!nb::isinstance<nb::dict>(src) || nb::len(src) != 1) {
        json_error(label, src);
    }
    auto [kind, payload] = *nb::borrow<nb::dict>(src).begin();
    if (!nb::isinstance<nb::str>(kind)) {
        json_error(label, src);
    }
    const auto name = nb::cast<std::string>(kind);
    if (name == "CompoundTag") {
        return Tag{compound_from_json(payload, label)};
    }
    if (name == "ListTag") {
        if (!nb::isinstance<nb::dict>(payload)) {
            json_error(label, src);
        }
        const auto list = nb::borrow<nb::dict>(payload);
        if (list.size() != 2 || !list.contains("type") || !list.contains("tags") ||
            !nb::isinstance<nb::list>(list["tags"])) {
            json_error(label, src);
        }
        const auto type = from_json<std::uint8_t>(list["type"], label + ".type");
        ListTag out(static_cast<nbt::Type>(type));
        std::size_t i = 0;
        for (nb::handle child : nb::borrow<nb::list>(list["tags"])) {
            out.push_back(tag_from_json(child, std::format("{}[{}]", label, i++)));
        }
        return Tag{std::move(out)};
    }
    Tag out;
    const bool matched = [&]<typename... T>(type_list<T...>) {
        return ([&] {
            if (name != nb::cast<std::string>(nb::type<T>().attr("__name__"))) {
                return false;
            }
            if constexpr (std::is_same_v<T, ByteArrayTag> || std::is_same_v<T, IntArrayTag>) {
                out = Tag{T(from_json<std::vector<typename T::value_type>>(payload, label))};
            }
            else {
                out = Tag{T(from_json<typename T::value_type>(payload, label))};
            }
            return true;
        }() || ...);
    }(type_list<ByteTag, ShortTag, IntTag, Int64Tag, FloatTag, DoubleTag, StringTag, ByteArrayTag, IntArrayTag>{});
    if (!matched) {
        json_error(label, src);
    }
    return out;
}

template <typename F>
F from_json(nb::handle src, const std::string &label)
{
    if constexpr (std::is_same_v<F, bool>) {
        if (!PyBool_Check(src.ptr())) {
            json_error(label, src);
        }
        return src.ptr() == Py_True;
    }
    else if constexpr (std::is_enum_v<F>) {
        if (nb::isinstance<nb::str>(src)) {
            const nb::object members = nb::type<F>().attr("__members__");
            if (nb::cast<bool>(members.attr("__contains__")(src))) {
                return nb::cast<F>(members[src]);
            }
        }
        else if (PyLong_Check(src.ptr()) && !PyBool_Check(src.ptr())) {
            std::underlying_type_t<F> integer;
            if (nb::try_cast(src, integer, false)) {
                return static_cast<F>(integer);
            }
        }
        json_error(label, src);
    }
    else if constexpr (std::is_floating_point_v<F>) {
        if (nb::isinstance<nb::str>(src)) {
            const auto text = nb::cast<std::string>(src);
            if (text == "NaN") {
                return std::numeric_limits<F>::quiet_NaN();
            }
            if (text == "Infinity" || text == "-Infinity") {
                return text[0] == '-' ? -std::numeric_limits<F>::infinity() : std::numeric_limits<F>::infinity();
            }
        }
        else if (PyFloat_Check(src.ptr()) || (PyLong_Check(src.ptr()) && !PyBool_Check(src.ptr()))) {
            const double wide = nb::cast<double>(src);
            const auto narrow = static_cast<F>(wide);
            if (std::isinf(narrow) && !std::isinf(wide)) {
                json_error(label, src);
            }
            return narrow;
        }
        json_error(label, src);
    }
    else if constexpr (std::is_integral_v<F> || PrimitiveAlias<F> || is_bitset_v<F>) {
        F out;
        if (PyLong_Check(src.ptr()) && !PyBool_Check(src.ptr()) && nb::try_cast(src, out, false)) {
            return out;
        }
        json_error(label, src);
    }
    else if constexpr (std::is_same_v<F, std::string> || std::is_same_v<F, DynamicValue>) {
        F out;
        if (nb::try_cast(src, out, false)) {
            return out;
        }
        json_error(label, src);
    }
    else if constexpr (std::is_same_v<F, std::vector<std::byte>>) {
        if (nb::isinstance<nb::str>(src)) {
            try {
                return nb::cast<F>(nb::module_::import_("builtins").attr("bytes").attr("fromhex")(src));
            }
            catch (const nb::python_error &) {
                json_error(label, src);
            }
        }
        json_error(label, src);
    }
    else if constexpr (std::is_same_v<F, UUID>) {
        if (nb::isinstance<nb::str>(src)) {
            try {
                return nb::cast<F>(nb::module_::import_("uuid").attr("UUID")(src));
            }
            catch (const nb::python_error &) {
                json_error(label, src);
            }
        }
        json_error(label, src);
    }
    else if constexpr (std::is_same_v<F, CompoundTag> || std::is_same_v<F, CompoundTagData>) {
        return F{compound_from_json(src, label)};
    }
    else if constexpr (std::is_same_v<F, Tag>) {
        return tag_from_json(src, label);
    }
    else if constexpr (is_optional_v<F>) {
        return src.is_none() ? F{} : F{from_json<typename F::value_type>(src, label)};
    }
    else if constexpr (is_list_v<F> || is_array_v<F>) {
        if (!nb::isinstance<nb::list>(src)) {
            json_error(label, src);
        }
        F out{};
        if constexpr (is_array_v<F>) {
            if (nb::len(src) != out.size()) {
                json_error(label, src);
            }
        }
        std::size_t i = 0;
        for (nb::handle item : nb::borrow<nb::list>(src)) {
            auto element = from_json<typename F::value_type>(item, std::format("{}[{}]", label, i));
            if constexpr (is_array_v<F>) {
                out[i] = std::move(element);
            }
            else {
                out.push_back(std::move(element));
            }
            ++i;
        }
        return out;
    }
    else if constexpr (is_map_v<F>) {
        if (!nb::isinstance<nb::dict>(src)) {
            json_error(label, src);
        }
        F out;
        for (auto [key, item] : nb::borrow<nb::dict>(src)) {
            const auto where = std::format("{}[{}]", label, nb::repr(key).c_str());
            nb::object spelled = nb::borrow(key);
            if constexpr (!std::is_same_v<typename F::key_type, std::string> && !std::is_enum_v<typename F::key_type>) {
                if (!nb::isinstance<nb::str>(key)) {
                    json_error(where, key);
                }
                try {
                    spelled = nb::module_::import_("json").attr("loads")(key);
                }
                catch (const nb::python_error &) {
                    json_error(where, key);
                }
            }
            out.emplace(from_json<typename F::key_type>(spelled, where),
                        from_json<typename F::mapped_type>(item, where));
        }
        return out;
    }
    else if constexpr (is_variant_v<F>) {
        if (src.is_none()) {
            if constexpr (std::is_constructible_v<F, std::monostate>) {
                return F{std::monostate{}};
            }
            json_error(label, src);
        }
        return [&]<typename... A>(std::variant<A...> *) -> F {
            if (!nb::isinstance<nb::dict>(src) || nb::len(src) != 1) {
                json_error(label, src);
            }
            auto [tag, payload] = *nb::borrow<nb::dict>(src).begin();
            if (!nb::isinstance<nb::str>(tag)) {
                json_error(label, src);
            }
            const auto name = nb::cast<std::string>(tag);
            std::optional<F> out;
            (
                [&] {
                    if constexpr (!std::is_same_v<A, std::monostate>) {
                        if (!out && name == variant_tag<A>()) {
                            out.emplace(std::in_place_type<A>,
                                        from_json<A>(payload, std::format("{}.{}", label, name)));
                        }
                    }
                }(),
                ...);
            if (!out) {
                json_error(label, src);
            }
            return std::move(*out);
        }(static_cast<F *>(nullptr));
    }
    else {
        static_assert(Reflected<F>, "a field type has no JSON form");
        if (!nb::isinstance<nb::dict>(src)) {
            json_error(label, src);
        }
        const auto object = nb::borrow<nb::dict>(src);
        F out{};
        [&]<std::size_t... I>(std::index_sequence<I...>) {
            for (auto [key, item] : object) {
                if (!(... || (nb::isinstance<nb::str>(key) && nb::cast<std::string>(key) == field_name<I, F>()))) {
                    throw nb::value_error(std::format("{}: has no field {}", label, nb::repr(key).c_str()).c_str());
                }
            }
            (
                [&] {
                    const auto where = std::format("{}.{}", label, field_name<I, F>());
                    nb::object key = nb::str(field_name<I, F>().data(), field_name<I, F>().size());
                    if (!object.contains(key)) {
                        throw nb::value_error(std::format("{}: is missing", where).c_str());
                    }
                    field_get<I>(out) = from_json<field_t<F, I>>(object[key], where);
                }(),
                ...);
        }(std::make_index_sequence<field_count<F>()>{});
        return out;
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
    static_assert(!field_contains<T>("to_json") && !field_contains<T>("from_json"),
                  "a member named to_json or from_json hides the method");
    nb::class_<T> cls(scope, name, nb::supplement<Codec>());
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
            ((members += std::format("{}{}={}", I ? ", " : "", python_names<T>()[I],
                                     nb::repr(to_python(field_get<I>(self))).c_str())),
             ...);
        }(std::make_index_sequence<field_count<T>()>{});
        return std::format("{}({})", nb::cast<std::string>(nb::type<T>().attr("__qualname__")), members);
    });

    if constexpr (Serializable<T>) {
        cls.def("__bytes__", &encode<T>, "The wire form, without a packet header.");
        cls.def_static("from_bytes", &decode_all<T>, nb::arg("data"), "Reads one value that must span all of `data`.");
    }
    cls.def("to_json", &to_json<T>, "The canonical JSON value.");
    cls.def_static(
        "from_json", [](nb::handle value) { return from_json<T>(value, std::string(struct_name<T>())); },
        nb::arg("value").none(), "Reads a canonical JSON value strictly.");
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
