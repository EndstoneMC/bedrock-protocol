cmake_minimum_required(VERSION 3.20 LANGUAGE CXX)
project(bedrock-protocol CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
include(BedrockProtocol)

# Bundled third-party dependencies
add_subdirectory(third_party)

# The single consumable library. Downstream:
#     add_subdirectory(third_party/bedrock-protocol)
#     target_link_libraries(my_app PRIVATE bedrock::protocol)
# brings in both the runtime headers and the codegen-emitted packet types.
add_library(bedrock_protocol STATIC)
add_library(bedrock::protocol ALIAS bedrock_protocol)

target_include_directories(bedrock_protocol PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include)

target_link_libraries(bedrock_protocol PUBLIC tl::expected)

# Collect every packet definition under protocol/. CONFIGURE_DEPENDS makes
# CMake re-glob on rebuilds so adding a new packet file picks up automatically.
file(GLOB BEDROCK_PROTOCOL_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/protocol/*.py")
bedrock_protocol_generate(
    TARGET      bedrock_protocol
    INPUTS      ${BEDROCK_PROTOCOL_SOURCES}
    IMPORT_DIRS ${CMAKE_CURRENT_SOURCE_DIR}/protocol)
