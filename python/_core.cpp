#include "_core.h"

#include <cstddef>
#include <format>
#include <string>
#include <string_view>
#include <variant>
#include <vector>

#include <nanobind/nanobind.h>
#include <nanobind/stl/array.h>
#include <nanobind/stl/optional.h>
#include <nanobind/stl/string_view.h>

#include "bedrock/protocol/serializer.hpp"
#include "bedrock/protocol/version.hpp"

namespace bedrock::protocol::python {

void throw_decode_error(DecodeError error)
{
    std::vector<std::string> names;
    names.reserve(error.path.size());
    nb::list path;
    for (auto &segment : error.path) {
        if (const auto *name = std::get_if<std::string_view>(&segment)) {
            segment = std::string_view(names.emplace_back(python_name(*name)));
            path.append(nb::str(names.back().c_str()));
        }
        else {
            path.append(std::get<std::size_t>(segment));
        }
    }
    nb::object type = nb::module_::import_("bedrock_protocol").attr("DecodeError");
    nb::object exception =
        type(std::format("{}", error), std::format("{}", error.reason), nb::tuple(path), error.offset);
    PyErr_SetObject(type.ptr(), exception.ptr());
    throw nb::python_error();
}

}  // namespace bedrock::protocol::python

NB_MODULE(_core, m)
{
    namespace nb = nanobind;
    namespace bpy = bedrock::protocol::python;
    using bedrock::protocol::ProtocolVersion;
    m.attr("versions") = nb::tuple(nb::cast(bedrock::protocol::versions));
    nb::class_<ProtocolVersion>(m, "ProtocolVersion",
                                "A protocol number a release reported, and the releases that report it.")
        .def_ro("number", &ProtocolVersion::number)
        .def_ro("snapshot", &ProtocolVersion::snapshot, "The `v<N>` that decodes it.")
        .def_ro("name", &ProtocolVersion::name)
        .def_ro("first", &ProtocolVersion::first)
        .def_ro("last", &ProtocolVersion::last)
        .def("__repr__", [](const ProtocolVersion &version) {
            return std::format("ProtocolVersion(number={}, snapshot={}, name='{}', first='{}', last='{}')",
                               version.number, version.snapshot, version.name, version.first, version.last);
        });
    m.attr("releases") = nb::tuple(nb::cast(bedrock::protocol::releases));
    m.def("protocol_version", nb::overload_cast<int>(&bedrock::protocol::protocol_version), nb::arg("number"),
          "The release entry for a protocol number, or None.");
    m.def("protocol_version", nb::overload_cast<std::string_view>(&bedrock::protocol::protocol_version),
          nb::arg("release"), "The release entry whose range holds a three-part release, or None.");
    auto package = nb::module_::import_("bedrock_protocol");
    bpy::init_nbt(package);
    bpy::init_versions(package);
}
