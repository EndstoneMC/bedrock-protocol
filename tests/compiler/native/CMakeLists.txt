cmake_minimum_required(VERSION 3.29)
project(nanobind_regressions LANGUAGES CXX)

find_package(Python 3.12 COMPONENTS Interpreter Development.Module REQUIRED)
execute_process(COMMAND "${Python_EXECUTABLE}" -m nanobind --cmake_dir
    OUTPUT_VARIABLE nanobind_DIR OUTPUT_STRIP_TRAILING_WHITESPACE
    COMMAND_ERROR_IS_FATAL ANY)
find_package(nanobind 3.1.0 EXACT CONFIG REQUIRED)

nanobind_add_module(_native NB_STATIC NOMINSIZE PROTECT_STACK
    module.cpp
    "${BPC_SOURCE_DIR}/src/python/views.cpp"
    "${BPC_SOURCE_DIR}/src/python/nbt.cpp"
    "${FIXTURE_WORK_DIR}/generated/native/schema.cpp"
    "${FIXTURE_WORK_DIR}/generated/native/bindings.cpp"
    "${FIXTURE_WORK_DIR}/generated/include/bedrock/protocol/schema.cpp")
target_compile_features(_native PRIVATE cxx_std_23)
target_include_directories(_native PRIVATE
    "${BPC_SOURCE_DIR}/src/python"
    "${BPC_SOURCE_DIR}/include"
    "${FIXTURE_WORK_DIR}/generated/include")
set_target_properties(_native PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${FIXTURE_WORK_DIR}/package/bedrock_protocol"
    RUNTIME_OUTPUT_DIRECTORY "${FIXTURE_WORK_DIR}/package/bedrock_protocol")
