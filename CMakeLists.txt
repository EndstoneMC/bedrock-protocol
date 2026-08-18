cmake_minimum_required(VERSION 3.20)
project(bedrock-protocol VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if (CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    option(BUILD_TESTING "Build the test suite" ON)
else ()
    option(BUILD_TESTING "Build the test suite" OFF)
endif ()

add_subdirectory(third_party)

# Compiled library: the generated .cpp bodies compile in here once, so a
# consumer TU only sees declarations and links the object code.
add_library(bedrock_protocol STATIC)
add_library(bedrock::protocol ALIAS bedrock_protocol)
target_compile_features(bedrock_protocol PUBLIC cxx_std_23)
# CMake's default Windows flags define WIN32, which collides with BuildPlatform's
# WIN32 enumerator. The enum mirrors BDS, so the macro gives way -- and it gives way
# for consumers too, since the collision is in a header they include.
if (MSVC)
    target_compile_options(bedrock_protocol PUBLIC /UWIN32)
endif ()
target_include_directories(bedrock_protocol PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${CMAKE_CURRENT_BINARY_DIR}/include
        ${CMAKE_CURRENT_BINARY_DIR})

# Protocol generator
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
        COMPILER_OUT_DIR ${CMAKE_CURRENT_BINARY_DIR}
        OUT_VAR BEDROCK_PROTOCOL_GENERATED
)

# Configure the umbrella header (<bedrock/protocol.hpp>) by stamping one
# `#include` line per generated packet header into protocol.hpp.in.
# BEDROCK_PROTOCOL_GENERATED holds every generated file; keep only the headers.
set(BEDROCK_PROTOCOL_INCLUDES "")
set(_includes ${BEDROCK_PROTOCOL_GENERATED})
list(FILTER _includes INCLUDE REGEX "\\.h$")
list(SORT _includes)
foreach (_gen IN LISTS _includes)
    file(RELATIVE_PATH _rel "${CMAKE_CURRENT_BINARY_DIR}" "${_gen}")
    string(APPEND BEDROCK_PROTOCOL_INCLUDES "#include \"${_rel}\"\n")
endforeach ()
configure_file(
        "${CMAKE_CURRENT_SOURCE_DIR}/include/bedrock/protocol.hpp.in"
        "${CMAKE_CURRENT_BINARY_DIR}/include/bedrock/protocol.hpp"
        @ONLY
)

# Tests
if (BUILD_TESTING)
    enable_testing()
    add_subdirectory(tests)
endif ()
