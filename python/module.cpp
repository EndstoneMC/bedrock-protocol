#include "module.hpp"

#include <nanobind/nanobind.h>
#include <nanobind/stl/array.h>

#include "versions.hpp"

namespace bedrock::protocol::python {

std::vector<std::pair<nb::handle, nb::dict (*)()>> &annotators()
{
    static std::vector<std::pair<nb::handle, nb::dict (*)()>> list;
    return list;
}

}  // namespace bedrock::protocol::python

NB_MODULE(_core, m)
{
    namespace nb = nanobind;
    namespace bpy = bedrock::protocol::python;
    m.attr("VERSIONS") = nb::tuple(nb::cast(bpy::versions));
    auto package = nb::module_::import_("bedrock_protocol");
    bpy::init_nbt(package);
    bpy::init_versions(package);
}
