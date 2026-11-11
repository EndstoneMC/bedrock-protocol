#include "module.hpp"

#include <nanobind/nanobind.h>

#include "bedrock/protocol/version.hpp"

namespace bedrock::protocol::python {

std::vector<std::pair<nb::handle, nb::dict (*)()>> &annotators()
{
    static std::vector<std::pair<nb::handle, nb::dict (*)()>> list;
    return list;
}

}  // namespace bedrock::protocol::python

NB_MODULE(_native, m)
{
    namespace bpy = bedrock::protocol::python;
    m.attr("LATEST_PROTOCOL") = bedrock::protocol::latest_version;
    bpy::init_nbt(m);
    bpy::init_versions(m);
}
