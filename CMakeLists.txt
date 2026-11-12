cmake_minimum_required(VERSION 3.20)
file(STRINGS pyproject.toml _version_line REGEX "^version = ")
string(REGEX MATCH "[0-9]+\\.[0-9]+\\.[0-9]+" _version "${_version_line}")
project(bedrock-protocol VERSION ${_version} LANGUAGES CXX)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS pyproject.toml)

if (MSVC)
    add_compile_options(/MP)
endif ()

option(BEDROCK_PROTOCOL_INSTALL "Generate the install target and CMake package" ${PROJECT_IS_TOP_LEVEL})

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/generated/bedrock/protocol/version.hpp")
    set(BEDROCK_PROTOCOL_GENERATED_DIR "${CMAKE_CURRENT_SOURCE_DIR}/generated")
else ()
    set(BEDROCK_PROTOCOL_GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")
    find_package(Python 3.12 REQUIRED COMPONENTS Interpreter)
    file(GLOB BEDROCK_PROTOCOL_SCHEMA_INPUTS CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/protocol/*.py")
    file(GLOB_RECURSE BEDROCK_PROTOCOL_COMPILER_INPUTS CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/compiler/src/*.py")
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
            ${BEDROCK_PROTOCOL_SCHEMA_INPUTS} ${BEDROCK_PROTOCOL_COMPILER_INPUTS})
    execute_process(
            COMMAND "${CMAKE_COMMAND}" -E env "PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}/compiler/src"
                    "${Python_EXECUTABLE}" -B -m bedrock_protocol_compiler
                    "${CMAKE_CURRENT_SOURCE_DIR}/protocol" --out "${BEDROCK_PROTOCOL_GENERATED_DIR}"
            COMMAND_ERROR_IS_FATAL ANY)
endif ()
set(BEDROCK_PROTOCOL_HEADER_DIR "${BEDROCK_PROTOCOL_GENERATED_DIR}/bedrock/protocol")
file(GLOB BEDROCK_PROTOCOL_SOURCES CONFIGURE_DEPENDS "${BEDROCK_PROTOCOL_HEADER_DIR}/*.cpp")

add_library(bedrock_protocol STATIC)
add_library(bedrock::protocol ALIAS bedrock_protocol)
set_target_properties(bedrock_protocol PROPERTIES EXPORT_NAME protocol)
target_compile_features(bedrock_protocol PUBLIC cxx_std_23)
target_include_directories(bedrock_protocol PUBLIC
        "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>"
        "$<BUILD_INTERFACE:${BEDROCK_PROTOCOL_GENERATED_DIR}>"
        "$<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>")

target_sources(bedrock_protocol PRIVATE ${BEDROCK_PROTOCOL_SOURCES})

set(BEDROCK_PROTOCOL_MODULES ${BEDROCK_PROTOCOL_SOURCES})
list(TRANSFORM BEDROCK_PROTOCOL_MODULES REPLACE "^.*/([^/]+)\\.cpp$" "\\1")

if (SKBUILD AND PROJECT_IS_TOP_LEVEL)
    add_subdirectory(python)
elseif (BEDROCK_PROTOCOL_INSTALL)
    install(TARGETS bedrock_protocol EXPORT bedrock-protocol-targets)

    install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/include/"
            DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
            FILES_MATCHING PATTERN "*.hpp")
    install(DIRECTORY "${BEDROCK_PROTOCOL_GENERATED_DIR}/"
            DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
            FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp")

    install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/LICENSE"
            DESTINATION "${CMAKE_INSTALL_DATAROOTDIR}/licenses/${PROJECT_NAME}")

    install(EXPORT bedrock-protocol-targets
            NAMESPACE bedrock::
            DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/bedrock-protocol")

    configure_package_config_file(
            "${CMAKE_CURRENT_SOURCE_DIR}/cmake/bedrock-protocol-config.cmake.in"
            "${CMAKE_CURRENT_BINARY_DIR}/bedrock-protocol-config.cmake"
            INSTALL_DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/bedrock-protocol")
    write_basic_package_version_file(
            "${CMAKE_CURRENT_BINARY_DIR}/bedrock-protocol-config-version.cmake"
            COMPATIBILITY SameMinorVersion)
    install(FILES
            "${CMAKE_CURRENT_BINARY_DIR}/bedrock-protocol-config.cmake"
            "${CMAKE_CURRENT_BINARY_DIR}/bedrock-protocol-config-version.cmake"
            DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/bedrock-protocol")
endif ()
