cmake_minimum_required(VERSION 3.20)
project(bedrock-protocol CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_subdirectory(third_party)

# Header-only library
add_library(bedrock_protocol INTERFACE)
add_library(bedrock::protocol ALIAS bedrock_protocol)
target_include_directories(bedrock_protocol INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(bedrock_protocol INTERFACE tl::expected)

# Protocol generator
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
include(BedrockProtocol)
file(GLOB BEDROCK_PROTOCOL_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/protocol/*.py")
bedrock_protocol_generate(
    TARGET      bedrock_protocol
    INPUTS      ${BEDROCK_PROTOCOL_SOURCES}
    IMPORT_DIRS ${CMAKE_CURRENT_SOURCE_DIR}/protocol)
