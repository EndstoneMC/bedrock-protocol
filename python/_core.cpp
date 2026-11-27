#include "_core.h"

#include <cstddef>
#include <cstdint>
#include <format>
#include <optional>
#include <string>
#include <string_view>
#include <variant>
#include <vector>

#include <nanobind/nanobind.h>
#include <nanobind/stl/string_view.h>

#include "bedrock/protocol/serializer.hpp"
#include "bedrock/protocol/version.hpp"

namespace bedrock::protocol::python {

namespace {

template <typename Error, typename... Extra>
[[noreturn]] void throw_error(const char *name, Error error, Extra... extra)
{
    std::vector<std::string> names;
    names.reserve(error.path.size());
    nb::list path;
    for (auto &segment : error.path) {
        if (const auto *field = std::get_if<std::string_view>(&segment)) {
            segment = std::string_view(names.emplace_back(python_name(*field)));
            path.append(nb::str(names.back().c_str()));
        }
        else {
            path.append(std::get<std::size_t>(segment));
        }
    }
    nb::object type = nb::module_::import_("bedrock_protocol").attr(name);
    nb::object exception = type(std::format("{}", error), std::format("{}", error.reason), nb::tuple(path), extra...);
    PyErr_SetObject(type.ptr(), exception.ptr());
    throw nb::python_error();
}

char *instance(nb::handle self, const StructInfo &info)
{
    if (Py_TYPE(self.ptr()) != info.type || !nb::inst_ready(self)) {
        throw nb::type_error(std::format("{}: incompatible self", info.name).c_str());
    }
    return nb::inst_ptr<char>(self);
}

}  // namespace

void throw_decode_error(const DecodeError &error)
{
    throw_error("DecodeError", error, error.offset);
}

void throw_encode_error(const EncodeError &error)
{
    throw_error("EncodeError", error);
}

void throw_cannot_hold(const Label &label, nb::handle src)
{
    throw nb::type_error(std::format("{}.{}: cannot hold {}", label.type, label.field, nb::repr(src).c_str()).c_str());
}

void *field_address(nb::handle self, const StructInfo &info, std::size_t index)
{
    return instance(self, info) + info.fields[index].offset;
}

void assign_fields(void *value, PyObject **args, const StructInfo &info)
{
    for (std::size_t i = 0; i < info.fields.size(); ++i) {
        if (args[i] != Py_Ellipsis) {
            const Field &field = info.fields[i];
            field.assign(static_cast<char *>(value) + field.offset, args[i], Label{info.name, info.names[i]});
        }
    }
}

PyObject *construct_impl(void *capture, PyObject **args, std::uint8_t *flags, nb::rv_policy,
                         nb::detail::cleanup_list *cleanup)
{
    const auto &info = *static_cast<const StructInfo *>(static_cast<void **>(capture)[0]);
    void *storage = nullptr;
    if (!nb::detail::nb_type_get(info.cpp_type, args[0], flags[0], cleanup, &storage)) {
        return NB_NEXT_OVERLOAD;
    }
    info.construct(storage, args + 1, info);
    return nb::detail::none_ref();
}

nb::object copy_instance(nb::handle self, const StructInfo &info)
{
    instance(self, info);
    nb::object out = nb::inst_alloc(self.type());
    nb::inst_copy(out, self);
    return out;
}

void def_eq(nb::handle cls, const StructInfo &info)
{
    const StructInfo *owner = &info;
    nb::cpp_function_def(
        [owner](nb::handle self, nb::handle other) -> nb::object {
            if (Py_TYPE(self.ptr()) != owner->type || Py_TYPE(other.ptr()) != owner->type || !nb::inst_ready(self) ||
                !nb::inst_ready(other)) {
                return nb::borrow(Py_NotImplemented);
            }
            const char *a = nb::inst_ptr<char>(self);
            const char *b = nb::inst_ptr<char>(other);
            for (const Field &field : owner->fields) {
                if (!field.equal(a + field.offset, b + field.offset)) {
                    return nb::bool_(false);
                }
            }
            return nb::bool_(true);
        },
        nb::scope(cls), nb::name("__eq__"), nb::is_method(), nb::is_operator(), nb::sig(eq_signature));
}

void def_repr(nb::handle cls, const StructInfo &info)
{
    const StructInfo *owner = &info;
    nb::cpp_function_def(
        [owner](nb::handle self) {
            const char *base = instance(self, *owner);
            std::string members;
            for (std::size_t i = 0; i < owner->fields.size(); ++i) {
                const Field &field = owner->fields[i];
                members += std::format("{}{}={}", i ? ", " : "", owner->names[i],
                                       nb::repr(field.value(base + field.offset)).c_str());
            }
            return std::format("{}({})", nb::cast<std::string>(self.type().attr("__qualname__")), members);
        },
        nb::scope(cls), nb::name("__repr__"), nb::is_method());
}

}  // namespace bedrock::protocol::python

NB_MODULE(_core, m)
{
    namespace nb = nanobind;
    namespace bpy = bedrock::protocol::python;
    using bedrock::protocol::ProtocolVersion;
    auto package = nb::module_::import_("bedrock_protocol");
    nb::class_<ProtocolVersion> version(
        package, "ProtocolVersion", nb::is_final(),
        "A supported protocol number, named for the first release of the newest number at or below it.");
    version.def_prop_ro("protocol", &ProtocolVersion::getProtocol)
        .def_prop_ro("name", &ProtocolVersion::getName)
        .def("__repr__",
             [](const ProtocolVersion &each) {
                 return std::format("ProtocolVersion(protocol={}, name='{}')", each.getProtocol(), each.getName());
             })
        .def_prop_ro_static("SUPPORTED_VERSIONS",
                            [](nb::handle) {
                                nb::list supported;
                                for (const ProtocolVersion &each : ProtocolVersion::SUPPORTED_VERSIONS) {
                                    supported.append(nb::cast(&each, nb::rv_policy::reference));
                                }
                                return nb::tuple(supported);
                            })
        .def_prop_ro_static(
            "MINIMUM_VERSION", [](nb::handle) { return &ProtocolVersion::SUPPORTED_VERSIONS.front(); },
            nb::rv_policy::reference)
        .def_prop_ro_static(
            "MAXIMUM_VERSION", [](nb::handle) { return &ProtocolVersion::SUPPORTED_VERSIONS.back(); },
            nb::rv_policy::reference)
        .def_static(
            "get",
            [](int protocol) -> nb::object {
                for (const ProtocolVersion &each : ProtocolVersion::SUPPORTED_VERSIONS) {
                    if (each.getProtocol() == protocol) {
                        return nb::cast(&each, nb::rv_policy::reference);
                    }
                }
                std::optional<ProtocolVersion> found = ProtocolVersion::get(protocol);
                return found ? nb::cast(*found) : nb::none();
            },
            nb::arg("protocol"), nb::sig("def get(protocol: int) -> ProtocolVersion | None"),
            "The supported version a protocol number names.");
    bpy::init_nbt(package);
    bpy::init_versions(m, package);
}
