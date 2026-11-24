#include "_core.h"

#include <cstddef>
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

}  // namespace

void throw_decode_error(const DecodeError &error)
{
    throw_error("DecodeError", error, error.offset);
}

void throw_encode_error(const EncodeError &error)
{
    throw_error("EncodeError", error);
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
