// Adapted from bedrock-bot (Apache-2.0); generated schema adapters and immutable construction added.
#pragma once

#include <array>
#include <bitset>
#include <limits>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <tuple>
#include <utility>
#include <variant>
#include <vector>

#include <bedrock/protocol/enum.hpp>
#include <bedrock/protocol/data_store.hpp>
#include <bedrock/protocol/nbt.hpp>
#include <bedrock/protocol/uuid.hpp>
#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>

namespace bedrock::protocol::python {
namespace nb = nanobind;
namespace bp = bedrock::protocol;

struct Value {};
struct Packet : Value {};
struct SequenceBase : Value {};
struct MapBase : Value {};

template <class T>
struct ValueBaseType {
    using type = Value;
};

template <class T>
    requires requires { T::Id; }
struct ValueBaseType<T> {
    using type = Packet;
};

template <class T>
using ValueBase = typename ValueBaseType<T>::type;

template <class T>
struct View : ValueBase<T> {
    std::shared_ptr<const T> value;
    int protocol = 0;
    View(std::shared_ptr<const T> value, int protocol = 0) : value(std::move(value)), protocol(protocol) {}
};

template <class T>
View<T> owned(T value, int protocol = 0)
{
    return {std::make_shared<const T>(std::move(value)), protocol};
}

template <class T, class U>
std::shared_ptr<const U> child(const std::shared_ptr<const T> &owner, const U &value)
{
    return {owner, &value};
}

inline nb::object provenance(int protocol)
{
    return protocol ? nb::object(nb::int_(protocol)) : nb::object(nb::none());
}

inline std::size_t index(Py_ssize_t offset, std::size_t size)
{
    if (offset < 0) {
        offset += static_cast<Py_ssize_t>(size);
    }
    if (offset < 0 || static_cast<std::size_t>(offset) >= size) {
        throw nb::index_error();
    }
    return static_cast<std::size_t>(offset);
}

std::string snapshotBuffer(nb::handle value, std::size_t maximum = std::numeric_limits<std::size_t>::max());
nb::object freeze(nb::handle value);

struct BinaryView : Value {
    std::shared_ptr<const void> owner;
    const char *data;
    std::size_t size;
    int protocol = 0;
    BinaryView(std::shared_ptr<const void> owner, const char *data, std::size_t size, int protocol = 0)
        : owner(std::move(owner)), data(data), size(size), protocol(protocol)
    {
    }
};

struct Variant {
    std::size_t index;
    nb::object value;
};

struct NbtView : Value {
    std::shared_ptr<const void> owner;
    const bp::Tag *tag = nullptr;
    const bp::CompoundTag *compound = nullptr;
    int protocol = 0;
    NbtView(std::shared_ptr<const void> owner, const bp::Tag *tag, const bp::CompoundTag *compound, int protocol = 0)
        : owner(std::move(owner)), tag(tag), compound(compound), protocol(protocol)
    {
    }
};
nb::dict nbtDict(const NbtView &view);
bp::Tag nbtTag(nb::handle object);
void bindNbt(nb::module_ &module);
void bindViews(nb::module_ &module);

template <class T>
T castValue(nb::handle value)
{
    try {
        return nb::cast<T>(value);
    }
    catch (const nb::cast_error &) {
        throw nb::type_error("invalid field type or range");
    }
}

inline nb::tuple mappingPair(nb::handle value)
{
    if (!PyTuple_Check(value.ptr()) || PyTuple_GET_SIZE(value.ptr()) != 2) {
        throw nb::type_error("items() must yield 2-tuples");
    }
    return nb::borrow<nb::tuple>(value);
}

template <class T, class Wire = T>
struct Scalar {
    using Type = T;
    static T load(nb::handle value)
    {
        auto result = castValue<T>(value);
        if constexpr (std::is_integral_v<T> && std::is_integral_v<Wire> && sizeof(Wire) < sizeof(T)) {
            if (!std::in_range<Wire>(result)) {
                throw nb::type_error("invalid field type or range");
            }
        }
        return result;
    }
    static nb::object get(std::shared_ptr<const T> value, int) { return nb::cast(*value); }
};

template <class T, class U, class Wire = U>
struct Alias {
    using Type = T;
    static T load(nb::handle value) { return T{Scalar<U, Wire>::load(value)}; }
    static nb::object get(std::shared_ptr<const T> value, int) { return nb::cast(static_cast<U>(*value)); }
};

struct Text : Scalar<std::string> {
    static std::string load(nb::handle value)
    {
        if (!PyUnicode_Check(value.ptr())) {
            throw nb::type_error("expected str");
        }
        return nb::cast<std::string>(value);
    }
};

struct Binary {
    using Type = std::string;
    static Type load(nb::handle value) { return snapshotBuffer(value); }
    static nb::object get(std::shared_ptr<const Type> value, int protocol)
    {
        return nb::cast(BinaryView{value, value->data(), value->size(), protocol});
    }
};

struct Dynamic {
    using Type = bp::DynamicValue;
    static Type load(nb::handle value);
    static nb::object get(std::shared_ptr<const Type> value, int protocol);
};

template <class T>
struct EnumMarker {};

template <class T, bool NameCoded = false, class Wire = std::underlying_type_t<T>>
struct Enumeration {
    using Type = T;
    static nb::object type() { return nb::borrow<nb::object>(nb::type<EnumMarker<T>>().attr("enum_type")); }
    static T lookup(nb::handle value)
    {
        if (!nb::isinstance(value, type())) {
            throw nb::type_error("expected the matching protocol enum");
        }
        using Underlying = std::underlying_type_t<T>;
        using PythonInteger = std::conditional_t<std::is_same_v<Underlying, bool>, int, Underlying>;
        return static_cast<T>(castValue<PythonInteger>(value));
    }
    static T load(nb::handle value)
    {
        const auto result = lookup(value);
        if constexpr (NameCoded) {
            if (bp::enum_name(result).empty()) {
                throw nb::value_error("name-coded enum value has no wire name");
            }
        }
        else if (static_cast<T>(static_cast<Wire>(result)) != result) {
            throw nb::value_error("enum value cannot be represented by its field encoding");
        }
        return result;
    }
    static nb::object get(std::shared_ptr<const T> value, int)
    {
        return type()(nb::int_(static_cast<std::underlying_type_t<T>>(*value)));
    }
};

template <class T>
struct Record {
    using Type = T;
    static T load(nb::handle value) { return *castValue<const View<T> &>(value).value; }
    static nb::object get(std::shared_ptr<const T> value, int protocol)
    {
        return nb::cast(View<T>{std::move(value), protocol});
    }
};

struct Compound {
    using Type = bp::CompoundTag;
    static Type load(nb::handle value)
    {
        const auto &view = nb::cast<const NbtView &>(value);
        if (view.compound) {
            return *view.compound;
        }
        const auto *compound = view.tag->get_if<bp::CompoundTag>();
        if (!compound) {
            throw nb::type_error("expected a compound Nbt");
        }
        return *compound;
    }
    static nb::object get(std::shared_ptr<const Type> value, int protocol)
    {
        return nb::cast(NbtView{value, nullptr, value.get(), protocol});
    }
};

struct Uuid {
    using Type = bp::UUID;
    static Type load(nb::handle value);
    static nb::object get(std::shared_ptr<const Type> value, int protocol);
};

template <std::size_t N>
struct Bits {
    using Type = std::bitset<N>;
    static Type load(nb::handle value)
    {
        if (!PyLong_Check(value.ptr()) || PyBool_Check(value.ptr())) {
            throw nb::type_error("expected a nonnegative bitset integer");
        }
        auto number = nb::steal<nb::object>(PyNumber_Index(value.ptr()));
        if (!number.is_valid()) {
            throw nb::python_error();
        }
        if (nb::cast<bool>(number.attr("__lt__")(0)) || nb::cast<std::size_t>(number.attr("bit_length")()) > N) {
            throw nb::value_error("bitset exceeds its declared width");
        }
        Type result;
        auto bytes = nb::cast<nb::bytes>(number.attr("to_bytes")((N + 7) / 8, "little"));
        if (bytes.size() != (N + 7) / 8) {
            throw nb::value_error("invalid bitset byte length");
        }
        for (std::size_t i = 0; i < N; ++i) {
            result[i] = (static_cast<unsigned char>(bytes.c_str()[i / 8]) >> (i % 8)) & 1;
        }
        return result;
    }
    static nb::object get(std::shared_ptr<const Type> value, int)
    {
        std::array<unsigned char, (N + 7) / 8> data{};
        for (std::size_t i = 0; i < N; ++i) {
            if ((*value)[i]) {
                data[i / 8] |= 1u << (i % 8);
            }
        }
        return nb::module_::import_("builtins")
            .attr("int")
            .attr("from_bytes")(nb::bytes(data.data(), data.size()), "little");
    }
};

template <class A>
struct Optional {
    using Type = std::optional<typename A::Type>;
    static Type load(nb::handle value) { return value.is_none() ? Type{} : Type{A::load(value)}; }
    static nb::object get(std::shared_ptr<const Type> value, int protocol)
    {
        return *value ? A::get(child(value, **value), protocol) : nb::object(nb::none());
    }
};

struct Empty {
    using Type = std::monostate;
    static Type load(nb::handle value)
    {
        if (!value.is_none()) {
            throw nb::type_error("this variant alternative requires None");
        }
        return {};
    }
    static nb::object get(std::shared_ptr<const Type>, int) { return nb::none(); }
};

template <class... A>
struct Union {
    using Type = std::variant<typename A::Type...>;
    template <std::size_t I = 0>
    static Type loadCase(std::size_t index, nb::handle value)
    {
        if constexpr (I == sizeof...(A)) {
            throw nb::value_error("variant index is outside the declared alternatives");
        }
        else {
            if (index == I) {
                return Type(std::in_place_index<I>, std::tuple_element_t<I, std::tuple<A...>>::load(value));
            }
            return loadCase<I + 1>(index, value);
        }
    }
    static Type load(nb::handle value)
    {
        const auto &variant = castValue<const Variant &>(value);
        return loadCase(variant.index, variant.value);
    }
    template <std::size_t I = 0>
    static nb::object exposeCase(const std::shared_ptr<const Type> &value, int protocol)
    {
        if constexpr (I == sizeof...(A)) {
            throw nb::value_error("invalid native variant");
        }
        else {
            if (value->index() == I) {
                return std::tuple_element_t<I, std::tuple<A...>>::get(child(value, std::get<I>(*value)), protocol);
            }
            return exposeCase<I + 1>(value, protocol);
        }
    }
    static nb::object get(std::shared_ptr<const Type> value, int protocol)
    {
        return nb::cast(Variant{value->index(), exposeCase(value, protocol)});
    }
};

template <class A>
struct SequenceView;
template <class A>
struct MappingView;

template <class Container, class A, class Prefix = std::size_t>
struct Sequence {
    using Type = Container;
    using Item = A;
    static Type load(nb::handle value)
    {
        Type result{};
        nb::object iterator = nb::steal<nb::object>(PyObject_GetIter(value.ptr()));
        if (!iterator.is_valid()) {
            throw nb::python_error();
        }
        std::size_t offset = 0;
        while (auto *next = PyIter_Next(iterator.ptr())) {
            auto item = nb::steal<nb::object>(next);
            if constexpr (requires { result.emplace_back(); }) {
                if (offset >= std::numeric_limits<Prefix>::max()) {
                    throw nb::value_error("sequence has too many elements for its length prefix");
                }
                result.emplace_back(A::load(item));
            }
            else {
                if (offset >= result.size()) {
                    throw nb::value_error("fixed array has too many elements");
                }
                result[offset] = A::load(item);
            }
            ++offset;
        }
        if (PyErr_Occurred()) {
            throw nb::python_error();
        }
        if constexpr (!requires { result.emplace_back(); }) {
            if (offset != result.size()) {
                throw nb::value_error("fixed array has too few elements");
            }
        }
        return result;
    }
    static nb::object get(std::shared_ptr<const Type> value, int protocol)
    {
        return nb::cast(SequenceView<Sequence>{std::move(value), protocol});
    }
};

template <class K, class V, class Prefix = std::size_t>
struct Mapping {
    using Type = std::map<typename K::Type, typename V::Type>;
    using Key = K;
    using Item = V;
    static Type load(nb::handle value)
    {
        Type result;
        if (nb::isinstance<MappingView<Mapping<K, V>>>(value)) {
            result = *castValue<const MappingView<Mapping<K, V>> &>(value).value;
        }
        else {
            auto items = nb::borrow<nb::object>(value).attr("items")();
            for (auto entry : items) {
                auto pair = mappingPair(entry);
                result.insert_or_assign(K::load(nb::handle(PyTuple_GET_ITEM(pair.ptr(), 0))),
                                        V::load(nb::handle(PyTuple_GET_ITEM(pair.ptr(), 1))));
            }
        }
        if (result.size() > std::numeric_limits<Prefix>::max()) {
            throw nb::value_error("map has too many elements for its length prefix");
        }
        return result;
    }
    static nb::object get(std::shared_ptr<const Type> value, int protocol)
    {
        return nb::cast(MappingView<Mapping<K, V>>{std::move(value), protocol});
    }
};

template <class A>
struct SequenceView : SequenceBase {
    std::shared_ptr<const typename A::Type> value;
    int protocol;
    SequenceView(std::shared_ptr<const typename A::Type> value, int protocol)
        : value(std::move(value)), protocol(protocol)
    {
    }
};
template <class A>
struct SequenceIterator {
    SequenceView<A> view;
    std::size_t offset = 0;
};
template <class A>
struct MappingView : MapBase {
    std::shared_ptr<const typename A::Type> value;
    int protocol;
    MappingView(std::shared_ptr<const typename A::Type> value, int protocol)
        : value(std::move(value)), protocol(protocol)
    {
    }
};
template <class A>
struct MappingIterator {
    MappingView<A> view;
    typename A::Type::const_iterator current;
};

nb::object materialize(nb::handle object);

template <class A>
nb::object sequenceItem(const SequenceView<A> &self, std::size_t i)
{
    if constexpr (std::is_same_v<typename A::Type, std::vector<bool>>) {
        return nb::bool_((*self.value)[i]);
    }
    else {
        return A::Item::get(child(self.value, (*self.value)[i]), self.protocol);
    }
}

template <class A>
void bindSequence(nb::module_ &module, const char *name)
{
    using V = SequenceView<A>;
    using It = SequenceIterator<A>;
    if (nb::type<V>().is_valid()) {
        return;
    }
    auto iterator_name = std::string(name) + "Iterator";
    nb::class_<It>(module, iterator_name.c_str())
        .def(
            "__iter__", [](It &self) -> It & { return self; }, nb::rv_policy::reference)
        .def("__next__", [](It &self) {
            if (self.offset == self.view.value->size()) {
                throw nb::stop_iteration();
            }
            return sequenceItem(self.view, self.offset++);
        });
    nb::class_<V, SequenceBase>(module, name)
        .def_prop_ro("protocol", [](const V &self) { return provenance(self.protocol); })
        .def("__len__", [](const V &self) { return self.value->size(); })
        .def("__getitem__",
             [](const V &self, Py_ssize_t i) { return sequenceItem(self, index(i, self.value->size())); })
        .def("__iter__", [](const V &self) { return It{self}; })
        .def("copy",
             [](const V &self) { return V{std::make_shared<const typename A::Type>(*self.value), self.protocol}; })
        .def("to_list", [](const V &self) {
            nb::list result;
            for (std::size_t i = 0; i < self.value->size(); ++i) {
                result.append(materialize(sequenceItem(self, i)));
            }
            return result;
        });
}

template <class A>
void bindMap(nb::module_ &module, const char *name)
{
    using V = MappingView<A>;
    using It = MappingIterator<A>;
    if (nb::type<V>().is_valid()) {
        return;
    }
    auto iterator_name = std::string(name) + "Iterator";
    nb::class_<It>(module, iterator_name.c_str())
        .def(
            "__iter__", [](It &self) -> It & { return self; }, nb::rv_policy::reference)
        .def("__next__", [](It &self) {
            if (self.current == self.view.value->end()) {
                throw nb::stop_iteration();
            }
            return A::Key::get(child(self.view.value, (self.current++)->first), self.view.protocol);
        });
    nb::class_<V, MapBase>(module, name)
        .def_prop_ro("protocol", [](const V &self) { return provenance(self.protocol); })
        .def("__len__", [](const V &self) { return self.value->size(); })
        .def("__getitem__",
             [](const V &self, nb::handle key) {
                 auto native_key = [&] {
                     if constexpr (requires { A::Key::lookup(key); }) {
                         return A::Key::lookup(key);
                     }
                     else {
                         return A::Key::load(key);
                     }
                 }();
                 auto found = self.value->find(native_key);
                 if (found == self.value->end()) {
                     PyErr_SetObject(PyExc_KeyError, key.ptr());
                     throw nb::python_error();
                 }
                 return A::Item::get(child(self.value, found->second), self.protocol);
             })
        .def("__iter__", [](const V &self) { return It{self, self.value->begin()}; })
        .def("copy",
             [](const V &self) { return V{std::make_shared<const typename A::Type>(*self.value), self.protocol}; })
        .def("to_dict", [](const V &self) {
            nb::dict result;
            for (const auto &[key, value] : *self.value) {
                result[A::Key::get(child(self.value, key), self.protocol)] =
                    materialize(A::Item::get(child(self.value, value), self.protocol));
            }
            return result;
        });
}

template <class T>
nb::class_<View<T>, ValueBase<T>> recordClass(nb::module_ &module, const char *name)
{
    return nb::class_<View<T>, ValueBase<T>>(module, name)
        .def_prop_ro("protocol", [](const View<T> &self) { return provenance(self.protocol); })
        .def("copy", [](const View<T> &self) { return owned(*self.value, self.protocol); });
}

template <class T>
void wireMethod(nb::class_<View<T>, ValueBase<T>> &cls)
{
    cls.def("wire_bytes", [](const View<T> &self) {
        std::string bytes;
        bp::BinaryWriter writer(bytes);
        bp::serialize(writer, *self.value);
        return nb::bytes(bytes.data(), bytes.size());
    });
}
}  // namespace bedrock::protocol::python
