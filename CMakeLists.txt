cmake_minimum_required(VERSION 3.20)
project(bedrock-protocol VERSION 0.1.0 LANGUAGES CXX)

if (PROJECT_IS_TOP_LEVEL)
    set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
    set(CMAKE_CXX_STANDARD 23)
    set(CMAKE_CXX_STANDARD_REQUIRED ON)
    set(CMAKE_CXX_EXTENSIONS OFF)
endif ()

if (PROJECT_IS_TOP_LEVEL AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/tests/CMakeLists.txt")
    set(_tests_default ON)
else ()
    set(_tests_default OFF)
endif ()
option(BEDROCK_PROTOCOL_BUILD_TESTS "Build the test suite" ${_tests_default})
option(BEDROCK_PROTOCOL_INSTALL "Generate the install target and CMake package" ${PROJECT_IS_TOP_LEVEL})

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

# A source release ships `generated/` already compiled from the schema, so building
# from one needs neither uv nor the Python compiler. A checkout has no such tree and
# runs bpc during the build instead.
if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/generated/include/bedrock/protocol.hpp")
    set(BEDROCK_PROTOCOL_PREGENERATED ON)
    set(BEDROCK_PROTOCOL_GENERATED_DIR "${CMAKE_CURRENT_SOURCE_DIR}/generated")
else ()
    set(BEDROCK_PROTOCOL_PREGENERATED OFF)
    set(BEDROCK_PROTOCOL_GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")
endif ()
set(BEDROCK_PROTOCOL_HEADER_DIR "${BEDROCK_PROTOCOL_GENERATED_DIR}/include/bedrock/protocol")

add_library(bedrock_protocol STATIC)
add_library(bedrock::protocol ALIAS bedrock_protocol)
set_target_properties(bedrock_protocol PROPERTIES
        EXPORT_NAME protocol
        OUTPUT_NAME bedrock_protocol)
target_compile_features(bedrock_protocol PUBLIC cxx_std_23)
target_include_directories(bedrock_protocol PUBLIC
        "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>"
        "$<BUILD_INTERFACE:${BEDROCK_PROTOCOL_GENERATED_DIR}/include>"
        "$<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>")

if (BEDROCK_PROTOCOL_PREGENERATED)
    file(GLOB BEDROCK_PROTOCOL_GENERATED CONFIGURE_DEPENDS "${BEDROCK_PROTOCOL_HEADER_DIR}/*.cpp")
    target_sources(bedrock_protocol PRIVATE ${BEDROCK_PROTOCOL_GENERATED})
else ()
    # The latest protocol the schema targets, read off the DSL surface so the C++
    # side and the compiler cannot disagree about it.
    file(STRINGS "${CMAKE_CURRENT_SOURCE_DIR}/protocol/__init__.py" _version_line
            REGEX "^__version__[ \t]*=[ \t]*[0-9]+")
    if (NOT _version_line)
        message(FATAL_ERROR "bedrock-protocol: no __version__ in protocol/__init__.py")
    endif ()
    string(REGEX MATCH "[0-9]+" BEDROCK_PROTOCOL_LATEST "${_version_line}")

    list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
    include(BedrockProtocol)
    file(GLOB BEDROCK_PROTOCOL_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/protocol/*.py")
    list(FILTER BEDROCK_PROTOCOL_SOURCES EXCLUDE REGEX "/_[^/]*\\.py$")
    bedrock_protocol_generate(
            TARGET bedrock_protocol
            INPUTS ${BEDROCK_PROTOCOL_SOURCES}
            # The DSL surface is not an input, but every generated file reads __version__ off it.
            DEPENDENCIES ${CMAKE_CURRENT_SOURCE_DIR}/protocol/__init__.py
            IMPORT_DIRS ${CMAKE_CURRENT_SOURCE_DIR}
            COMPILER_OUT_DIR ${BEDROCK_PROTOCOL_HEADER_DIR}
            OUT_VAR BEDROCK_PROTOCOL_GENERATED
    )

    configure_file(
            "${CMAKE_CURRENT_SOURCE_DIR}/include/bedrock/protocol/version.hpp.in"
            "${BEDROCK_PROTOCOL_HEADER_DIR}/version.hpp"
            @ONLY
    )

    # Configure the umbrella header (<bedrock/protocol.hpp>) by stamping one
    # `#include` line per generated packet header into protocol.hpp.in.
    # BEDROCK_PROTOCOL_GENERATED holds every generated file; keep only the headers.
    set(BEDROCK_PROTOCOL_INCLUDES "")
    set(_includes ${BEDROCK_PROTOCOL_GENERATED})
    list(FILTER _includes INCLUDE REGEX "\\.h$")
    list(SORT _includes)
    foreach (_gen IN LISTS _includes)
        file(RELATIVE_PATH _rel "${BEDROCK_PROTOCOL_GENERATED_DIR}/include" "${_gen}")
        string(APPEND BEDROCK_PROTOCOL_INCLUDES "#include <${_rel}>\n")
    endforeach ()
    configure_file(
            "${CMAKE_CURRENT_SOURCE_DIR}/include/bedrock/protocol.hpp.in"
            "${BEDROCK_PROTOCOL_GENERATED_DIR}/include/bedrock/protocol.hpp"
            @ONLY
    )
endif ()

# Tests
if (BEDROCK_PROTOCOL_BUILD_TESTS)
    set(BUILD_TESTING ON)
    enable_testing()
    add_subdirectory(third_party)
    add_subdirectory(tests)
endif ()

if (BEDROCK_PROTOCOL_INSTALL)
    install(TARGETS bedrock_protocol
            EXPORT bedrock-protocol-targets
            ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}"
            LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}"
            RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}")

    install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/include/"
            DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
            FILES_MATCHING PATTERN "*.hpp")
    install(DIRECTORY "${BEDROCK_PROTOCOL_GENERATED_DIR}/include/"
            DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
            FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp")

    install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/LICENSE"
            DESTINATION "${CMAKE_INSTALL_DATAROOTDIR}/licenses/${PROJECT_NAME}")

    install(EXPORT bedrock-protocol-targets
            FILE bedrock-protocol-targets.cmake
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
