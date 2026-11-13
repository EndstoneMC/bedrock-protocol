find_package(Python 3.12 REQUIRED COMPONENTS Interpreter Development.Module Development.SABIModule)
find_package(nanobind CONFIG REQUIRED)

set(_sources _core.cpp nbt.cpp versions.cpp)
set(_declarations "")
set(_calls "")
foreach (_module IN LISTS BEDROCK_PROTOCOL_MODULES)
    configure_file(module_types.cpp.in "bind/${_module}.cpp" @ONLY)
    list(APPEND _sources "${CMAKE_CURRENT_BINARY_DIR}/bind/${_module}.cpp")
    string(APPEND _declarations "void init_${_module}_types(std::span<const Version> bound);\n")
    string(APPEND _calls "    init_${_module}_types(bound);\n")
endforeach ()
configure_file(all_types.cpp.in bind/all_types.cpp @ONLY)
list(APPEND _sources "${CMAKE_CURRENT_BINARY_DIR}/bind/all_types.cpp")

nanobind_add_module(_core STABLE_ABI ${_sources})
target_include_directories(_core PRIVATE .)
target_link_libraries(_core PRIVATE bedrock::protocol)
set_target_properties(bedrock_protocol PROPERTIES POSITION_INDEPENDENT_CODE ON CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN ON)

file(STRINGS "${BEDROCK_PROTOCOL_HEADER_DIR}/version.hpp" _versions REGEX "^inline constexpr std::array versions")
string(REGEX MATCHALL "[0-9]+" _versions "${_versions}")
set(_stubs __init__.pyi _core.pyi nbt.pyi py.typed)
foreach (_version IN LISTS _versions)
    list(APPEND _stubs "v${_version}/__init__.pyi" "v${_version}/pre_cereal.pyi")
endforeach ()
list(TRANSFORM _stubs PREPEND "${CMAKE_CURRENT_BINARY_DIR}/stubs/")
add_custom_command(
        OUTPUT ${_stubs}
        COMMAND "${CMAKE_COMMAND}" -E make_directory stage/bedrock_protocol
        COMMAND "${CMAKE_COMMAND}" -E copy "$<TARGET_FILE:_core>"
                "${CMAKE_CURRENT_SOURCE_DIR}/bedrock_protocol/__init__.py" stage/bedrock_protocol
        COMMAND "${CMAKE_COMMAND}" -E rm -rf stubs
        COMMAND "${Python_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/stubgen.py" stage stubs
                "${CMAKE_CURRENT_SOURCE_DIR}/stubgen.pat"
        WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
        DEPENDS _core "${CMAKE_CURRENT_SOURCE_DIR}/bedrock_protocol/__init__.py"
                "${CMAKE_CURRENT_SOURCE_DIR}/stubgen.py" "${CMAKE_CURRENT_SOURCE_DIR}/stubgen.pat"
        VERBATIM)
add_custom_target(stubs ALL DEPENDS ${_stubs})

install(TARGETS _core DESTINATION bedrock_protocol)
install(DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/stubs/" DESTINATION bedrock_protocol)
