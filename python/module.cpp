#include "module.hpp"

#include <nanobind/nanobind.h>
#include <nanobind/stl/array.h>

#include "versions.hpp"

NB_MODULE(_core, m)
{
    namespace nb = nanobind;
    namespace bpy = bedrock::protocol::python;
    m.attr("VERSIONS") = nb::tuple(nb::cast(bpy::versions));
    auto package = nb::module_::import_("bedrock_protocol");
    bpy::init_nbt(package);
    bpy::init_versions(package);
}
