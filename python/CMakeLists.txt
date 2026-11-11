find_package(Python 3.12 REQUIRED COMPONENTS Interpreter Development.Module Development.SABIModule)
find_package(nanobind CONFIG REQUIRED)

file(STRINGS "${BEDROCK_PROTOCOL_HEADER_DIR}/version.hpp" _latest REGEX "^#define BEDROCK_PROTOCOL_LATEST [0-9]+$")
string(REGEX MATCH "[0-9]+$" _latest "${_latest}")
set(_versions ${BEDROCK_PROTOCOL_PYTHON_VERSIONS} ${_latest})
list(REMOVE_DUPLICATES _versions)

set(_sources module.cpp nbt.cpp)
set(_declarations "")
set(_table "")
foreach (BP_VERSION IN LISTS _versions)
    set(_files "")
    foreach (BP_MODULE IN LISTS BEDROCK_PROTOCOL_MODULES)
        set(_tu "${CMAKE_CURRENT_BINARY_DIR}/bind/${BP_MODULE}_${BP_VERSION}.cpp")
        configure_file(bind_module.cpp.in "${_tu}" @ONLY)
        list(APPEND _sources "${_tu}")
        string(APPEND _declarations "void bind_${BP_MODULE}_${BP_VERSION}(Version &);\n")
        string(APPEND _files "&bind_${BP_MODULE}_${BP_VERSION}, ")
    endforeach ()
    string(APPEND _table "        {${BP_VERSION}, {${_files}}, &check_packets<${BP_VERSION}>},\n")
    configure_file(version.py.in "${CMAKE_CURRENT_BINARY_DIR}/v${BP_VERSION}.py" @ONLY)
    install(FILES "${CMAKE_CURRENT_BINARY_DIR}/v${BP_VERSION}.py" DESTINATION bedrock_protocol)
endforeach ()
file(CONFIGURE OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/bind/versions.cpp" CONTENT "#include <bedrock/protocol.hpp>

#include \"binder.hpp\"
#include \"module.hpp\"

namespace bedrock::protocol::python {

${_declarations}
const std::vector<VersionBinding> &version_bindings()
{
    static const std::vector<VersionBinding> table{
${_table}    };
    return table;
}

}  // namespace bedrock::protocol::python
")
list(APPEND _sources "${CMAKE_CURRENT_BINARY_DIR}/bind/versions.cpp")

nanobind_add_module(_native STABLE_ABI ${_sources})
target_include_directories(_native PRIVATE .)
target_link_libraries(_native PRIVATE bedrock::protocol)
if (MSVC)
    target_compile_options(_native PRIVATE /bigobj)
endif ()

install(TARGETS _native DESTINATION bedrock_protocol)
