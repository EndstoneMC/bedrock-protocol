cmake_minimum_required(VERSION 3.20)
project(bedrock-protocol-package-test LANGUAGES CXX)

find_package(bedrock-protocol CONFIG REQUIRED)

add_executable(package_test main.cpp)
target_link_libraries(package_test PRIVATE bedrock::protocol)
