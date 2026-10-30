find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
execute_process(COMMAND "${Python_EXECUTABLE}" -m nanobind --cmake_dir
    OUTPUT_VARIABLE nanobind_DIR OUTPUT_STRIP_TRAILING_WHITESPACE
    COMMAND_ERROR_IS_FATAL ANY)
find_package(nanobind 3.1.0 EXACT CONFIG REQUIRED)

set(_python_generated "${CMAKE_CURRENT_BINARY_DIR}/generated")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${PROJECT_SOURCE_DIR}/protocol/__init__.py")
execute_process(COMMAND "${Python_EXECUTABLE}" -c
    "import protocol; print(';'.join(map(str, protocol.__supported_versions__)))"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    OUTPUT_VARIABLE _versions OUTPUT_STRIP_TRAILING_WHITESPACE
    COMMAND_ERROR_IS_FATAL ANY)
set(_python_modules)
foreach (_version IN LISTS _versions)
    list(APPEND _python_modules
        "${_python_generated}/bedrock_protocol/v${_version}.py"
        "${_python_generated}/bedrock_protocol/v${_version}.pyi")
endforeach ()
file(GLOB _schema CONFIGURE_DEPENDS "${PROJECT_SOURCE_DIR}/protocol/*.py")
list(FILTER _schema EXCLUDE REGEX "/_[^/]*\\.py$")
file(GLOB_RECURSE _compiler CONFIGURE_DEPENDS "${PROJECT_SOURCE_DIR}/src/bedrock_protocol/*.py")
set(_bindings "${_python_generated}/bindings.cpp")
foreach (_input IN LISTS _schema)
    get_filename_component(_stem "${_input}" NAME_WE)
    list(APPEND _bindings "${_python_generated}/${_stem}.cpp")
endforeach ()
add_custom_command(OUTPUT ${_bindings} ${_python_modules} "${_python_generated}/coverage.json"
    COMMAND "${CMAKE_COMMAND}" -E env "PYTHONPATH=${PROJECT_SOURCE_DIR}/src" "PYTHONUTF8=1"
        "${Python_EXECUTABLE}" -m bedrock_protocol --language nanobind --out "${_python_generated}"
        --import-path "${PROJECT_SOURCE_DIR}" ${_schema}
    DEPENDS ${_schema} ${_compiler} "${PROJECT_SOURCE_DIR}/protocol/__init__.py"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    VERBATIM)
nanobind_add_module(_native NB_STATIC NOMINSIZE PROTECT_STACK
    module.cpp codec.cpp views.cpp nbt.cpp wire.cpp ${_bindings})
target_include_directories(_native PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
target_link_libraries(_native PRIVATE bedrock::protocol bedrock::protocol_wire)
install(TARGETS _native DESTINATION bedrock_protocol COMPONENT bedrock_protocol_wheel)
install(DIRECTORY "${_python_generated}/bedrock_protocol/" DESTINATION bedrock_protocol COMPONENT bedrock_protocol_wheel)
