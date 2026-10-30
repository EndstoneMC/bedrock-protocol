// Adapted from bedrock-bot (Apache-2.0); owned construction and provenance added.
#include "views.h"

namespace bedrock::protocol::python {
namespace {
constexpr const char *names[] = {"end",    "byte",       "short",  "int",  "int64",    "float",
                                 "double", "byte_array", "string", "list", "compound", "int_array"};
bp::nbt::Type type(const NbtView &view)
{
    return view.compound ? bp::nbt::Type::Compound : view.tag->type();
}
template <class F>
decltype(auto) visit(const NbtView &view, F &&function)
{
    if (view.compound) {
        return function(*view.compound);
    }
    return view.tag->visit(std::forward<F>(function));
}
template <class T>
NbtView nested(const NbtView &parent, const T &tag)
{
    return {parent.owner, &tag, nullptr, parent.protocol};
}
nb::object scalar(const NbtView &view)
{
    return visit(view, [](const auto &payload) -> nb::object {
        using T = std::decay_t<decltype(payload)>;
        if constexpr (std::is_same_v<T, std::monostate>) {
            return nb::none();
        }
        else if constexpr (requires { payload.value(); }) {
            return nb::cast(payload.value());
        }
        else {
            throw nb::type_error("container and array tags have no scalar value");
        }
    });
}
std::size_t length(const NbtView &view)
{
    return visit(view, [](const auto &payload) -> std::size_t {
        if constexpr (requires { payload.size(); }) {
            return payload.size();
        }
        else {
            throw nb::type_error("scalar tags have no length");
        }
    });
}
nb::object getItem(const NbtView &view, nb::handle key)
{
    return visit(view, [&](const auto &payload) -> nb::object {
        using T = std::decay_t<decltype(payload)>;
        if constexpr (std::is_same_v<T, bp::CompoundTag>) {
            const auto name = nb::cast<std::string>(key);
            const auto found = payload.find(name);
            if (found == payload.end()) {
                PyErr_SetObject(PyExc_KeyError, key.ptr());
                throw nb::python_error();
            }
            return nb::cast(nested(view, found->second), nb::rv_policy::move);
        }
        else if constexpr (std::is_same_v<T, bp::ListTag>) {
            return nb::cast(nested(view, payload[index(nb::cast<Py_ssize_t>(key), payload.size())]),
                            nb::rv_policy::move);
        }
        else if constexpr (std::is_same_v<T, bp::ByteArrayTag> || std::is_same_v<T, bp::IntArrayTag>) {
            return nb::int_(payload[index(nb::cast<Py_ssize_t>(key), payload.size())]);
        }
        else {
            throw nb::type_error("scalar tags cannot be indexed");
        }
    });
}
BinaryView byteArray(const NbtView &view)
{
    if (!view.tag) {
        throw nb::type_error("only byte arrays export a buffer");
    }
    const auto *array = view.tag->get_if<bp::ByteArrayTag>();
    if (!array) {
        throw nb::type_error("only byte arrays export a buffer");
    }
    return {view.owner, reinterpret_cast<const char *>(array->data()), array->size()};
}
template <class T>
int getBuffer(PyObject *self, Py_buffer *view, int flags) noexcept
{
    try {
        if (!nb::inst_ready(self)) {
            PyErr_SetString(PyExc_BufferError, "buffer exporter is not initialized");
            return -1;
        }
        BinaryView bytes{nullptr, nullptr, 0};
        const char *format;
        if constexpr (std::is_same_v<T, BinaryView>) {
            bytes = *nb::inst_ptr<BinaryView>(self);
            format = "B";
        }
        else {
            bytes = byteArray(*nb::inst_ptr<NbtView>(self));
            format = "b";
        }
        if (bytes.size > static_cast<std::size_t>(PY_SSIZE_T_MAX)) {
            PyErr_SetString(PyExc_OverflowError, "buffer exceeds Python size limits");
            return -1;
        }
        static const char empty = 0;
        const char *data = bytes.size ? bytes.data : &empty;
        if (PyBuffer_FillInfo(view, self, const_cast<char *>(data), static_cast<Py_ssize_t>(bytes.size), 1, flags) <
            0) {
            return -1;
        }
        view->format = (flags & PyBUF_FORMAT) ? const_cast<char *>(format) : nullptr;
        return 0;
    }
    catch (nb::python_error &error) {
        error.restore();
    }
    catch (const nb::builtin_exception &error) {
        PyErr_SetString(PyExc_TypeError, error.what());
    }
    catch (const std::bad_alloc &) {
        PyErr_NoMemory();
    }
    catch (const std::exception &error) {
        PyErr_SetString(PyExc_RuntimeError, error.what());
    }
    catch (...) {
        PyErr_SetString(PyExc_RuntimeError, "buffer export failed");
    }
    return -1;
}
PyType_Slot binarySlots[] = {{Py_bf_getbuffer, reinterpret_cast<void *>(getBuffer<BinaryView>)}, {0, nullptr}};
PyType_Slot nbtSlots[] = {{Py_bf_getbuffer, reinterpret_cast<void *>(getBuffer<NbtView>)}, {0, nullptr}};
struct NbtIterator {
    NbtView view;
    std::size_t offset = 0;
    bp::CompoundTag::const_iterator current;
};
}  // namespace

nb::dict nbtDict(const NbtView &view)
{
    nb::dict result;
    result["type"] = names[static_cast<unsigned>(type(view))];
    result["value"] = visit(view, [&](const auto &payload) -> nb::object {
        using T = std::decay_t<decltype(payload)>;
        if constexpr (std::is_same_v<T, bp::CompoundTag>) {
            nb::dict values;
            for (const auto &[key, value] : payload) {
                values[nb::str(key.data(), key.size())] = nbtDict(nested(view, value));
            }
            return values;
        }
        else if constexpr (std::is_same_v<T, bp::ListTag>) {
            nb::list values;
            result["element_type"] = names[static_cast<unsigned>(payload.type())];
            for (const auto &value : payload) {
                values.append(nbtDict(nested(view, value)));
            }
            return values;
        }
        else if constexpr (std::is_same_v<T, bp::ByteArrayTag>) {
            return nb::bytes(reinterpret_cast<const char *>(payload.data()), payload.size());
        }
        else if constexpr (std::is_same_v<T, bp::IntArrayTag>) {
            nb::list values;
            for (auto value : payload) {
                values.append(value);
            }
            return values;
        }
        else {
            return scalar(view);
        }
    });
    return result;
}

bp::Tag nbtTag(nb::handle object)
{
    const auto &view = nb::cast<const NbtView &>(object);
    return view.compound ? bp::Tag{*view.compound} : *view.tag;
}

namespace {
bp::Tag makeTag(bp::nbt::Type type, nb::handle value, nb::handle element_type)
{
    if (type != bp::nbt::Type::List && !element_type.is_none()) {
        throw nb::type_error("element_type is only valid for list tags");
    }
    switch (type) {
    case bp::nbt::Type::End:
        if (!value.is_none()) {
            throw nb::type_error("End requires None");
        }
        return {};
    case bp::nbt::Type::Byte:
        return bp::ByteTag{nb::cast<std::int8_t>(value)};
    case bp::nbt::Type::Short:
        return bp::ShortTag{nb::cast<std::int16_t>(value)};
    case bp::nbt::Type::Int:
        return bp::IntTag{nb::cast<std::int32_t>(value)};
    case bp::nbt::Type::Int64:
        return bp::Int64Tag{nb::cast<std::int64_t>(value)};
    case bp::nbt::Type::Float:
        return bp::FloatTag{nb::cast<float>(value)};
    case bp::nbt::Type::Double:
        return bp::DoubleTag{nb::cast<double>(value)};
    case bp::nbt::Type::String:
        return bp::StringTag{Text::load(value)};
    case bp::nbt::Type::ByteArray: {
        bp::ByteArrayTag result;
        if (PyObject_CheckBuffer(value.ptr())) {
            auto bytes = snapshotBuffer(value);
            result.reserve(bytes.size());
            for (char byte : bytes) {
                result.push_back(static_cast<std::int8_t>(byte));
            }
        }
        else {
            for (auto item : nb::borrow<nb::object>(value)) {
                result.push_back(nb::cast<std::int8_t>(item));
            }
        }
        return result;
    }
    case bp::nbt::Type::IntArray: {
        bp::IntArrayTag result;
        for (auto item : nb::borrow<nb::object>(value)) {
            result.push_back(nb::cast<std::int32_t>(item));
        }
        return result;
    }
    case bp::nbt::Type::List: {
        if (element_type.is_none()) {
            throw nb::type_error("list tags require element_type, including empty lists");
        }
        bp::ListTag result(nb::cast<bp::nbt::Type>(element_type));
        for (auto item : nb::borrow<nb::object>(value)) {
            if (result.type() == bp::nbt::Type::End) {
                throw nb::value_error("nonempty list cannot have End element type");
            }
            result.push_back(nbtTag(item));
        }
        return result;
    }
    case bp::nbt::Type::Compound: {
        bp::CompoundTag result;
        for (auto entry : nb::borrow<nb::object>(value).attr("items")()) {
            auto pair = mappingPair(entry);
            auto tag = nbtTag(nb::handle(PyTuple_GET_ITEM(pair.ptr(), 1)));
            if (tag.type() == bp::nbt::Type::End) {
                throw nb::value_error("compound entries cannot be End tags");
            }
            result.emplace(Text::load(nb::handle(PyTuple_GET_ITEM(pair.ptr(), 0))), std::move(tag));
        }
        return result;
    }
    }
    throw nb::value_error("invalid NBT type");
}
}  // namespace

void bindNbt(nb::module_ &module)
{
    nb::enum_<bp::nbt::Type>(module, "NbtType")
        .value("END", bp::nbt::Type::End)
        .value("BYTE", bp::nbt::Type::Byte)
        .value("SHORT", bp::nbt::Type::Short)
        .value("INT", bp::nbt::Type::Int)
        .value("INT64", bp::nbt::Type::Int64)
        .value("FLOAT", bp::nbt::Type::Float)
        .value("DOUBLE", bp::nbt::Type::Double)
        .value("BYTE_ARRAY", bp::nbt::Type::ByteArray)
        .value("STRING", bp::nbt::Type::String)
        .value("LIST", bp::nbt::Type::List)
        .value("COMPOUND", bp::nbt::Type::Compound)
        .value("INT_ARRAY", bp::nbt::Type::IntArray);
    nb::class_<BinaryView, Value>(module, "BinaryView", nb::type_slots(binarySlots))
        .def_prop_ro("protocol", [](const BinaryView &self) { return provenance(self.protocol); })
        .def("__len__", [](const BinaryView &self) { return self.size; })
        .def("__getitem__",
             [](const BinaryView &self, Py_ssize_t offset) {
                 return static_cast<unsigned char>(self.data[index(offset, self.size)]);
             })
        .def("to_bytes", [](const BinaryView &self) { return nb::bytes(self.data, self.size); })
        .def("copy", [](const BinaryView &self) {
            auto owner = std::make_shared<const std::string>(self.data, self.size);
            return BinaryView{owner, owner->data(), owner->size(), self.protocol};
        });
    nb::class_<NbtIterator>(module, "_NbtIterator")
        .def(
            "__iter__", [](NbtIterator &self) -> NbtIterator & { return self; }, nb::rv_policy::reference)
        .def("__next__", [](NbtIterator &self) -> nb::object {
            if (self.offset >= length(self.view)) {
                throw nb::stop_iteration();
            }
            if (type(self.view) == bp::nbt::Type::Compound) {
                ++self.offset;
                const auto &name = (self.current++)->first;
                return nb::str(name.data(), name.size());
            }
            return getItem(self.view, nb::int_(self.offset++));
        });
    nb::class_<NbtView, Value>(module, "Nbt", nb::type_slots(nbtSlots))
        .def(nb::new_([](bp::nbt::Type type, nb::handle value, nb::object element_type) {
                 auto owner = std::make_shared<const bp::Tag>(makeTag(type, value, element_type));
                 return NbtView{owner, owner.get(), nullptr};
             }),
             nb::arg("type"), nb::arg("value").none(), nb::kw_only(), nb::arg("element_type") = nb::none())
        .def_prop_ro("protocol", [](const NbtView &self) { return provenance(self.protocol); })
        .def_prop_ro("type", &type)
        .def_prop_ro("value", &scalar)
        .def_prop_ro("element_type",
                     [](const NbtView &self) -> nb::object {
                         if (self.tag) {
                             if (const auto *list = self.tag->get_if<bp::ListTag>()) {
                                 return nb::cast(list->type());
                             }
                         }
                         return nb::none();
                     })
        .def("__len__", &length)
        .def("__getitem__", &getItem)
        .def("__iter__",
             [](const NbtView &self) {
                 length(self);
                 NbtIterator it{self};
                 if (type(self) == bp::nbt::Type::Compound) {
                     it.current = self.compound ? self.compound->begin() : self.tag->get<bp::CompoundTag>().begin();
                 }
                 return it;
             })
        .def("to_dict", &nbtDict)
        .def("copy",
             [](const NbtView &self) {
                 if (self.compound) {
                     auto owner = std::make_shared<const bp::CompoundTag>(*self.compound);
                     return NbtView{owner, nullptr, owner.get(), self.protocol};
                 }
                 auto owner = std::make_shared<const bp::Tag>(*self.tag);
                 return NbtView{owner, owner.get(), nullptr, self.protocol};
             })
        .def("to_bytes",
             [](const NbtView &self) {
                 const auto bytes = byteArray(self);
                 return nb::bytes(bytes.data, bytes.size);
             })
        .def("wire_bytes", [](const NbtView &self) {
            std::string bytes;
            bp::BinaryWriter writer(bytes);
            if (self.compound) {
                bp::serialize(writer, *self.compound);
            }
            else {
                bp::nbt::writeNamedTag(writer, {}, *self.tag);
            }
            return nb::bytes(bytes.data(), bytes.size());
        });
}
}  // namespace bedrock::protocol::python
