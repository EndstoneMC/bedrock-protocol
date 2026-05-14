cmake_minimum_required(VERSION 3.20)
project(bedrock-protocol VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    option(BUILD_TESTING "Build the test suite" ON)
else()
    option(BUILD_TESTING "Build the test suite" OFF)
endif()

add_subdirectory(third_party)

# Header-only library
add_library(bedrock_protocol INTERFACE)
add_library(bedrock::protocol ALIAS bedrock_protocol)
target_include_directories(bedrock_protocol INTERFACE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_BINARY_DIR}/include)
target_link_libraries(bedrock_protocol INTERFACE tl::expected)

# Protocol generator
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
include(BedrockProtocol)
file(GLOB BEDROCK_PROTOCOL_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/protocol/*.py")
list(FILTER BEDROCK_PROTOCOL_SOURCES EXCLUDE REGEX "/_[^/]*\\.py$")
bedrock_protocol_generate(
    TARGET         bedrock_protocol
    INPUTS         ${BEDROCK_PROTOCOL_SOURCES}
    IMPORT_DIRS    ${CMAKE_CURRENT_SOURCE_DIR}
    COMPILER_OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"
    OUT_VAR        BEDROCK_PROTOCOL_GENERATED
)
target_include_directories(bedrock_protocol INTERFACE "$<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}/generated>")

# Umbrella header (`<bedrock/protocol.hpp>` `#include`s this) — emitted by
# bpc itself via the --umbrella mode so the index is consistent with bpc's
# per-input naming.
set(_umbrella "${CMAKE_CURRENT_BINARY_DIR}/generated/protocol/all.hpp")
add_custom_command(
    OUTPUT  "${_umbrella}"
    COMMAND "$<TARGET_FILE:bedrock::protocol_compiler>"
            --umbrella "${_umbrella}" ${BEDROCK_PROTOCOL_SOURCES}
    DEPENDS ${BEDROCK_PROTOCOL_SOURCES} bedrock::protocol_compiler
    COMMENT "bpc: generating protocol/all.hpp"
    VERBATIM
)
add_custom_target(bedrock_protocol_umbrella DEPENDS "${_umbrella}")
add_dependencies(bedrock_protocol bedrock_protocol_umbrella)

# Tests
if(BUILD_TESTING)
    enable_testing()
    add_subdirectory(tests)
endif()
