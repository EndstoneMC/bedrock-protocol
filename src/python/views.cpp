// Adapted from bedrock-bot (Apache-2.0); generated schema adapters and immutable construction added.
#include "views.h"

#include <limits>

namespace bedrock::protocol::python {

std::string snapshotBuffer(nb::handle value, std::size_t maximum)
{
    Py_buffer buffer{};
    if (PyObject_GetBuffer(value.ptr(), &buffer, PyBUF_FULL_RO) < 0) {
        throw nb::python_error();
    }
    struct Release {
        Py_buffer *buffer;
        ~Release() { PyBuffer_Release(buffer); }
    } release{&buffer};
    if (buffer.len < 0 || static_cast<std::size_t>(buffer.len) > maximum) {
        throw nb::value_error("input exceeds byte limit");
    }
    std::string copy(static_cast<std::size_t>(buffer.len), '\0');
    if (buffer.len && PyBuffer_ToContiguous(copy.data(), &buffer, buffer.len, 'C') < 0) {
        throw nb::python_error();
    }
    return copy;
}

namespace {
using DynamicArray = Sequence<bp::DynamicValue::Array, Dynamic>;
using DynamicObject = Mapping<Text, Dynamic>;

bp::DynamicValue dynamicLoad(nb::handle object, std::vector<PyObject *> &path)
{
    if (path.size() >= 128) {
        throw nb::value_error("DynamicValue exceeds depth 128");
    }
    if (std::find(path.begin(), path.end(), object.ptr()) != path.end()) {
        throw nb::value_error("cyclic DynamicValue");
    }
    if (Py_EnterRecursiveCall(" while constructing DynamicValue") != 0) {
        throw nb::python_error();
    }
    struct Leave {
        ~Leave() { Py_LeaveRecursiveCall(); }
    } leave;
    const auto &variant = castValue<const Variant &>(object);
    path.push_back(object.ptr());
    struct Pop {
        std::vector<PyObject *> &path;
        ~Pop() { path.pop_back(); }
    } pop{path};
    const auto value = variant.value;
    switch (variant.index) {
    case 0:
        if (!value.is_none()) throw nb::type_error("DynamicValue null requires None");
        return {};
    case 1:
        if (!PyBool_Check(value.ptr())) throw nb::type_error("DynamicValue boolean requires bool");
        return bp::DynamicValue{value.ptr() == Py_True};
    case 2:
        if (!PyLong_Check(value.ptr()) || PyBool_Check(value.ptr())) {
            throw nb::type_error("DynamicValue integer requires int");
        }
        return bp::DynamicValue{castValue<std::int64_t>(value)};
    case 3:
        if (!PyFloat_Check(value.ptr())) throw nb::type_error("DynamicValue number requires float");
        return bp::DynamicValue{castValue<double>(value)};
    case 4:
        return bp::DynamicValue{Text::load(value)};
    case 5: {
        if (!PyList_Check(value.ptr()) && !PyTuple_Check(value.ptr()) &&
            !nb::isinstance<SequenceView<DynamicArray>>(value)) {
            throw nb::type_error("DynamicValue array requires list, tuple, or matching SequenceView");
        }
        bp::DynamicValue::Array result;
        for (auto item : value) result.push_back(dynamicLoad(item, path));
        return bp::DynamicValue{std::move(result)};
    }
    case 6: {
        if (!PyDict_Check(value.ptr()) && !PyObject_TypeCheck(value.ptr(), &PyDictProxy_Type) &&
            !nb::isinstance<MappingView<DynamicObject>>(value)) {
            throw nb::type_error("DynamicValue object requires dict or matching MapView");
        }
        bp::DynamicValue::Object result;
        for (auto key : value) result.insert_or_assign(Text::load(key), dynamicLoad(value[key], path));
        return bp::DynamicValue{std::move(result)};
    }
    default:
        throw nb::value_error("DynamicValue tag must be in 0..6");
    }
}

nb::object freezeImpl(nb::handle value, std::vector<PyObject *> &path)
{
    if (Py_EnterRecursiveCall(" while snapshotting a Variant") != 0) {
        throw nb::python_error();
    }
    struct Leave {
        ~Leave() { Py_LeaveRecursiveCall(); }
    } leave;
    if (value.is_none() || PyLong_Check(value.ptr()) || PyFloat_Check(value.ptr()) || PyUnicode_Check(value.ptr()) ||
        PyBytes_Check(value.ptr())) {
        return nb::borrow<nb::object>(value);
    }
    if (nb::isinstance<Value>(value) || nb::isinstance<Variant>(value)) {
        if (!nb::inst_ready(value.ptr())) {
            throw nb::type_error("cannot reference an uninitialized protocol value");
        }
        return nb::borrow<nb::object>(value);
    }
    if (PyObject_CheckBuffer(value.ptr())) {
        const auto bytes = snapshotBuffer(value);
        return nb::bytes(bytes.data(), bytes.size());
    }
    if (PyList_Check(value.ptr()) || PyTuple_Check(value.ptr())) {
        if (std::find(path.begin(), path.end(), value.ptr()) != path.end()) {
            throw nb::value_error("cyclic Variant value");
        }
        path.push_back(value.ptr());
        nb::list items;
        for (auto item : nb::borrow<nb::object>(value)) {
            items.append(freezeImpl(item, path));
        }
        path.pop_back();
        return nb::tuple(items);
    }
    if (PyDict_Check(value.ptr())) {
        if (std::find(path.begin(), path.end(), value.ptr()) != path.end()) {
            throw nb::value_error("cyclic Variant value");
        }
        path.push_back(value.ptr());
        nb::dict items;
        for (auto [key, item] : nb::borrow<nb::dict>(value)) {
            items[freezeImpl(key, path)] = freezeImpl(item, path);
        }
        path.pop_back();
        return nb::module_::import_("types").attr("MappingProxyType")(items);
    }
    if (nb::isinstance(value, nb::module_::import_("uuid").attr("UUID"))) {
        return nb::borrow<nb::object>(value);
    }
    throw nb::type_error("Variant value must be a protocol value or immutable scalar/container");
}

int variantTraverse(PyObject *self, visitproc visit, void *arg)
{
    Py_VISIT(Py_TYPE(self));
    if (nb::inst_ready(self)) {
        Py_VISIT(nb::inst_ptr<Variant>(self)->value.ptr());
    }
    return 0;
}

int variantClear(PyObject *self)
{
    if (nb::inst_ready(self)) {
        const auto value = nb::inst_ptr<Variant>(self)->value.release();
        Py_XDECREF(value.ptr());
    }
    return 0;
}
PyType_Slot variantSlots[] = {{Py_tp_traverse, reinterpret_cast<void *>(variantTraverse)},
                              {Py_tp_clear, reinterpret_cast<void *>(variantClear)},
                              {0, nullptr}};
}  // namespace

Dynamic::Type Dynamic::load(nb::handle value)
{
    std::vector<PyObject *> path;
    return dynamicLoad(value, path);
}

nb::object Dynamic::get(std::shared_ptr<const Type> value, int protocol)
{
    auto payload = value->visit([&](const auto &item) -> nb::object {
        using T = std::decay_t<decltype(item)>;
        if constexpr (std::is_same_v<T, std::monostate>) return nb::none();
        else if constexpr (std::is_same_v<T, Type::Array>) return DynamicArray::get(child(value, item), protocol);
        else if constexpr (std::is_same_v<T, Type::Object>) return DynamicObject::get(child(value, item), protocol);
        else return Scalar<T>::get(child(value, item), protocol);
    });
    return nb::cast(Variant{static_cast<std::size_t>(value->type()), std::move(payload)});
}

nb::object freeze(nb::handle value)
{
    std::vector<PyObject *> path;
    return freezeImpl(value, path);
}

nb::object materialize(nb::handle object)
{
    if (nb::isinstance<Variant>(object)) {
        const auto &value = nb::cast<const Variant &>(object);
        return nb::cast(Variant{value.index, materialize(value.value)});
    }
    if (nb::hasattr(object, "to_dict")) {
        return object.attr("to_dict")();
    }
    if (nb::hasattr(object, "to_list")) {
        return object.attr("to_list")();
    }
    if (nb::isinstance<BinaryView>(object)) {
        return object.attr("to_bytes")();
    }
    return nb::borrow<nb::object>(object);
}

Uuid::Type Uuid::load(nb::handle value)
{
    auto cls = nb::module_::import_("uuid").attr("UUID");
    if (!nb::isinstance(value, cls)) {
        throw nb::type_error("expected uuid.UUID");
    }
    const auto bytes = nb::cast<nb::bytes>(value.attr("bytes"));
    if (bytes.size() != 16) {
        throw nb::value_error("UUID bytes must have length 16");
    }
    const auto *data = reinterpret_cast<const unsigned char *>(bytes.c_str());
    Type result{};
    for (int i = 0; i < 8; ++i) {
        result.most_significant_bits = (result.most_significant_bits << 8) | data[i];
        result.least_significant_bits = (result.least_significant_bits << 8) | data[i + 8];
    }
    return result;
}

nb::object Uuid::get(std::shared_ptr<const Type> value, int)
{
    std::array<unsigned char, 16> data{};
    for (int i = 0; i < 8; ++i) {
        data[i] = static_cast<unsigned char>(value->most_significant_bits >> ((7 - i) * 8));
        data[i + 8] = static_cast<unsigned char>(value->least_significant_bits >> ((7 - i) * 8));
    }
    return nb::module_::import_("uuid").attr("UUID")(nb::arg("bytes") = nb::bytes(data.data(), data.size()));
}

void bindViews(nb::module_ &module)
{
    nb::class_<Value>(module, "Value");
    nb::class_<Packet, Value>(module, "Packet");
    nb::class_<SequenceBase, Value>(module, "SequenceView").def_static("__class_getitem__", [](nb::handle) {
        return nb::borrow<nb::object>(nb::type<SequenceBase>());
    });
    nb::class_<MapBase, Value>(module, "MapView").def_static("__class_getitem__", [](nb::handle) {
        return nb::borrow<nb::object>(nb::type<MapBase>());
    });
    nb::class_<Variant>(module, "Variant", nb::type_slots(variantSlots))
        .def(nb::new_([](std::size_t index, nb::handle value) { return Variant{index, freeze(value)}; }),
             nb::arg("index"), nb::arg("value").none())
        .def_ro("index", &Variant::index)
        .def_ro("value", &Variant::value)
        .def_static("__class_getitem__", [](nb::handle) { return nb::borrow<nb::object>(nb::type<Variant>()); });
    bindSequence<DynamicArray>(module, "_DynamicArray");
    bindMap<DynamicObject>(module, "_DynamicObject");
}
}  // namespace bedrock::protocol::python
