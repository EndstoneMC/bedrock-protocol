cmake_minimum_required(VERSION 3.20)
project(bedrock-protocol-package-test LANGUAGES CXX)

find_package(bedrock-protocol CONFIG REQUIRED)

add_executable(package_test main.cpp)
target_link_libraries(package_test PRIVATE bedrock::protocol)

enable_testing()
add_test(NAME package_test COMMAND package_test)

if (TARGET bedrock::protocol_wire)
    add_executable(package_wire_test wire.cpp)
    target_link_libraries(package_wire_test PRIVATE bedrock::protocol_wire)
    add_test(NAME package_wire_test COMMAND package_wire_test)
endif ()
