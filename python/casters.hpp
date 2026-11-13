#pragma once

#include <bitset>
#include <cstddef>
#include <cstdint>
#include <map>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <variant>
#include <vector>

#include <nanobind/nanobind.h>
#include <nanobind/stl/array.h>
#include <nanobind/stl/map.h>
#include <nanobind/stl/optional.h>
#include <nanobind/stl/variant.h>
#include <nanobind/stl/vector.h>

#include "bedrock/protocol/data_store.hpp"
#include "bedrock/protocol/detail/reflect.hpp"
#include "bedrock/protocol/nbt.hpp"
#include "bedrock/protocol/uuid.hpp"

NAMESPACE_BEGIN(NB_NAMESPACE)
NAMESPACE_BEGIN(detail)

template <>
struct type_caster<std::string> {
    NB_TYPE_CASTER(std::string, const_name("str"))

    bool from_python(handle src, uint8_t, cleanup_list *) noexcept
    {
        if (!PyUnicode_Check(src.ptr())) {
            return false;
        }
        PyObject *encoded = PyUnicode_AsEncodedString(src.ptr(), "utf-8", "surrogateescape");
        if (encoded == nullptr) {
            PyErr_Clear();
            return false;
        }
        char *data = nullptr;
        Py_ssize_t size = 0;
        PyBytes_AsStringAndSize(encoded, &data, &size);
        value.assign(data, static_cast<std::size_t>(size));
        Py_DECREF(encoded);
        return true;
    }

    static handle from_cpp(const std::string &value, rv_policy, cleanup_list *) noexcept
    {
        return PyUnicode_DecodeUTF8(value.data(), static_cast<Py_ssize_t>(value.size()), "surrogateescape");
    }
};

template <>
struct type_caster<std::vector<std::byte>> {
    NB_TYPE_CASTER(std::vector<std::byte>, const_name("bytes"))

    bool from_python(handle src, uint8_t, cleanup_list *) noexcept
    {
        if (!PyBytes_Check(src.ptr())) {
            return false;
        }
        const auto *data = reinterpret_cast<const std::byte *>(PyBytes_AsString(src.ptr()));
        value.assign(data, data + PyBytes_Size(src.ptr()));
        return true;
    }

    static handle from_cpp(const std::vector<std::byte> &value, rv_policy, cleanup_list *) noexcept
    {
        return PyBytes_FromStringAndSize(reinterpret_cast<const char *>(value.data()),
                                         static_cast<Py_ssize_t>(value.size()));
    }
};

template <bedrock::protocol::PrimitiveAlias T>
struct type_caster<T> {
    using Underlying = bedrock::protocol::primitive_alias_t<T>;
    using Caster = make_caster<Underlying>;

    NB_TYPE_CASTER(T, Caster::Name)

    bool from_python(handle src, uint8_t flags, cleanup_list *cleanup) noexcept
    {
        Caster caster;
        if (!caster.from_python(src, flags, cleanup)) {
            return false;
        }
        value = T{caster.operator cast_t<Underlying>()};
        return true;
    }

    static handle from_cpp(const T &value, rv_policy policy, cleanup_list *cleanup) noexcept
    {
        return Caster::from_cpp(static_cast<Underlying>(value), policy, cleanup);
    }
};

template <std::size_t N>
struct type_caster<std::bitset<N>> {
    NB_TYPE_CASTER(std::bitset<N>, const_name("int"))

    bool from_python(handle src, uint8_t, cleanup_list *) noexcept
    {
        if (!PyLong_Check(src.ptr())) {
            return false;
        }
        const str text = steal<str>(PyNumber_ToBase(src.ptr(), 2));
        if (!text.is_valid()) {
            PyErr_Clear();
            return false;
        }
        std::string_view digits = text.c_str();
        if (digits.starts_with('-')) {
            return false;
        }
        digits.remove_prefix(2);
        if (digits.size() > N) {
            return false;
        }
        value = std::bitset<N>(digits.data(), digits.size());
        return true;
    }

    static handle from_cpp(const std::bitset<N> &value, rv_policy, cleanup_list *) noexcept
    {
        return PyLong_FromString(value.to_string().c_str(), nullptr, 2);
    }
};

template <>
struct type_caster<bedrock::protocol::UUID> {
    NB_TYPE_CASTER(bedrock::protocol::UUID, const_name("uuid.UUID"))

    bool from_python(handle src, uint8_t, cleanup_list *) noexcept
    {
        try {
            const object cls = module_::import_("uuid").attr("UUID");
            if (!isinstance(src, cls)) {
                return false;
            }
            const object number = src.attr("int");
            const object mask = steal(PyLong_FromUnsignedLongLong(~0ULL));
            const object shift = steal(PyLong_FromLong(64));
            const object low = steal(PyNumber_And(number.ptr(), mask.ptr()));
            const object high = steal(PyNumber_Rshift(number.ptr(), shift.ptr()));
            value.most_significant_bits = PyLong_AsUnsignedLongLong(high.ptr());
            value.least_significant_bits = PyLong_AsUnsignedLongLong(low.ptr());
            return true;
        }
        catch (...) {
            PyErr_Clear();
            return false;
        }
    }

    static handle from_cpp(const bedrock::protocol::UUID &value, rv_policy, cleanup_list *) noexcept
    {
        try {
            const object high = steal(PyLong_FromUnsignedLongLong(value.most_significant_bits));
            const object low = steal(PyLong_FromUnsignedLongLong(value.least_significant_bits));
            const object shift = steal(PyLong_FromLong(64));
            const object shifted = steal(PyNumber_Lshift(high.ptr(), shift.ptr()));
            const object number = steal(PyNumber_Or(shifted.ptr(), low.ptr()));
            return module_::import_("uuid").attr("UUID")(arg("int") = number).release();
        }
        catch (python_error &e) {
            e.restore();
            return handle();
        }
    }
};

template <>
struct type_caster<bedrock::protocol::DynamicValue> {
    using DynamicValue = bedrock::protocol::DynamicValue;

    NB_TYPE_CASTER(DynamicValue,
                   io_name("bool | int | float | str | list | dict", "bool | int | float | str | list | dict | None"))

    bool from_python(handle src, uint8_t flags, cleanup_list *cleanup) noexcept
    {
        if (src.is_none()) {
            value = DynamicValue{};
        }
        else if (PyBool_Check(src.ptr())) {
            value = DynamicValue{src.ptr() == Py_True};
        }
        else if (PyLong_Check(src.ptr())) {
            const long long v = PyLong_AsLongLong(src.ptr());
            if (v == -1 && PyErr_Occurred()) {
                PyErr_Clear();
                return false;
            }
            value = DynamicValue{static_cast<DynamicValue::Integer>(v)};
        }
        else if (PyFloat_Check(src.ptr())) {
            value = DynamicValue{PyFloat_AsDouble(src.ptr())};
        }
        else if (PyUnicode_Check(src.ptr())) {
            make_caster<std::string> s;
            if (!s.from_python(src, flags, cleanup)) {
                return false;
            }
            value = DynamicValue{std::move(s.value)};
        }
        else if (PyList_Check(src.ptr()) || PyTuple_Check(src.ptr())) {
            DynamicValue::Array out;
            for (handle item : borrow<sequence>(src)) {
                type_caster element;
                if (!element.from_python(item, flags, cleanup)) {
                    return false;
                }
                out.push_back(std::move(element.value));
            }
            value = DynamicValue{std::move(out)};
        }
        else if (PyDict_Check(src.ptr())) {
            DynamicValue::Object out;
            for (auto [k, v] : borrow<dict>(src)) {
                make_caster<std::string> key;
                type_caster element;
                if (!key.from_python(k, flags, cleanup) || !element.from_python(v, flags, cleanup)) {
                    return false;
                }
                out.emplace(std::move(key.value), std::move(element.value));
            }
            value = DynamicValue{std::move(out)};
        }
        else {
            return false;
        }
        return true;
    }

    static handle from_cpp(const DynamicValue &value, rv_policy policy, cleanup_list *cleanup) noexcept
    {
        return value.visit([&](const auto &payload) -> handle {
            using V = std::decay_t<decltype(payload)>;
            if constexpr (std::is_same_v<V, std::monostate>) {
                return none().release();
            }
            else if constexpr (std::is_same_v<V, DynamicValue::Array>) {
                PyObject *out = PyList_New(static_cast<Py_ssize_t>(payload.size()));
                for (std::size_t i = 0; i < payload.size(); ++i) {
                    handle item = from_cpp(payload[i], policy, cleanup);
                    if (!item.is_valid()) {
                        Py_DECREF(out);
                        return handle();
                    }
                    PyList_SetItem(out, static_cast<Py_ssize_t>(i), item.ptr());
                }
                return out;
            }
            else if constexpr (std::is_same_v<V, DynamicValue::Object>) {
                PyObject *out = PyDict_New();
                for (const auto &[key, child] : payload) {
                    object k = steal(make_caster<std::string>::from_cpp(key, policy, cleanup));
                    object v = steal(from_cpp(child, policy, cleanup));
                    if (!k.is_valid() || !v.is_valid()) {
                        Py_DECREF(out);
                        return handle();
                    }
                    PyDict_SetItem(out, k.ptr(), v.ptr());
                }
                return out;
            }
            else {
                return make_caster<V>::from_cpp(payload, policy, cleanup);
            }
        });
    }
};

template <>
struct type_caster<bedrock::protocol::CompoundTagData> {
    using CompoundTag = bedrock::protocol::CompoundTag;
    using CompoundTagData = bedrock::protocol::CompoundTagData;

    NB_TYPE_CASTER(CompoundTagData, const_name("bedrock_protocol.nbt.CompoundTag"))

    bool from_python(handle src, uint8_t flags, cleanup_list *cleanup) noexcept
    {
        make_caster<CompoundTag> caster;
        if (!caster.from_python(src, flags, cleanup)) {
            return false;
        }
        value = CompoundTagData{caster.operator cast_t<CompoundTag>()};
        return true;
    }

    static handle from_cpp(const CompoundTagData &value, rv_policy, cleanup_list *cleanup) noexcept
    {
        return make_caster<CompoundTag>::from_cpp(static_cast<const CompoundTag &>(value), rv_policy::copy, cleanup);
    }
};

template <>
struct type_caster<bedrock::protocol::Tag> {
    NB_TYPE_CASTER(bedrock::protocol::Tag, io_name("bedrock_protocol.nbt.Tag", "bedrock_protocol.nbt.Tag | None"))

    bool from_python(handle src, uint8_t flags, cleanup_list *cleanup) noexcept
    {
        return try_as<bedrock::protocol::ByteTag, bedrock::protocol::ShortTag, bedrock::protocol::IntTag,
                      bedrock::protocol::Int64Tag, bedrock::protocol::FloatTag, bedrock::protocol::DoubleTag,
                      bedrock::protocol::ByteArrayTag, bedrock::protocol::StringTag, bedrock::protocol::ListTag,
                      bedrock::protocol::CompoundTag, bedrock::protocol::IntArrayTag>(src, flags, cleanup);
    }

    static handle from_cpp(const bedrock::protocol::Tag &value, rv_policy, cleanup_list *cleanup) noexcept
    {
        return value.visit([&](const auto &payload) -> handle {
            using V = std::decay_t<decltype(payload)>;
            if constexpr (std::is_same_v<V, std::monostate>) {
                return none().release();
            }
            else {
                return make_caster<V>::from_cpp(payload, rv_policy::copy, cleanup);
            }
        });
    }

private:
    template <typename... T>
    bool try_as(handle src, uint8_t flags, cleanup_list *cleanup) noexcept
    {
        if (src.is_none()) {
            value = bedrock::protocol::Tag{};
            return true;
        }
        return (try_one<T>(src, flags, cleanup) || ...);
    }

    template <typename T>
    bool try_one(handle src, uint8_t flags, cleanup_list *cleanup) noexcept
    {
        make_caster<T> caster;
        if (!caster.from_python(src, flags & ~static_cast<uint8_t>(cast_flags::convert), cleanup)) {
            return false;
        }
        value = bedrock::protocol::Tag{caster.operator cast_t<T>()};
        return true;
    }
};

NAMESPACE_END(detail)
NAMESPACE_END(NB_NAMESPACE)
