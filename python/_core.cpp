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
    m.attr("versions") = nb::tuple(nb::cast(bedrock::protocol::versions));
    nb::class_<ProtocolVersion>(m, "ProtocolVersion", nb::is_final(),
                                "A protocol number a release reported, and the releases that report it.")
        .def_ro("number", &ProtocolVersion::number)
        .def_ro("snapshot", &ProtocolVersion::snapshot)
        .def_ro("name", &ProtocolVersion::name)
        .def_ro("first", &ProtocolVersion::first)
        .def_ro("last", &ProtocolVersion::last)
        .def("__repr__", [](const ProtocolVersion &version) {
            return std::format("ProtocolVersion(number={}, snapshot={}, name='{}', first='{}', last='{}')",
                               version.number, version.snapshot, version.name, version.first, version.last);
        });
    m.attr("releases") = nb::tuple(nb::cast(bedrock::protocol::releases));
    m.def("protocol_version", nb::overload_cast<int>(&bedrock::protocol::protocol_version), nb::arg("number"));
    m.def("protocol_version", nb::overload_cast<std::string_view>(&bedrock::protocol::protocol_version),
          nb::arg("release"), "The release entry whose range holds a three-part release.");
    auto package = nb::module_::import_("bedrock_protocol");
    bpy::init_nbt(package);
    bpy::init_versions(m, package);
}
