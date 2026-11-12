#include "module.h"

#include <nanobind/nanobind.h>
#include <nanobind/stl/array.h>

#include "bedrock/protocol/version.hpp"

NB_MODULE(_core, m)
{
    namespace nb = nanobind;
    namespace bpy = bedrock::protocol::python;
    m.attr("VERSIONS") = nb::tuple(nb::cast(bedrock::protocol::versions));
    auto package = nb::module_::import_("bedrock_protocol");
    bpy::init_nbt(package);
    bpy::init_versions(package);
}
