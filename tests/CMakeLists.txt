add_executable(bedrock_protocol_tests)
file(GLOB _test_sources CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/test_*.cpp")
target_sources(bedrock_protocol_tests PRIVATE fixture.hpp ${_test_sources})
target_link_libraries(bedrock_protocol_tests PRIVATE bedrock::protocol Catch2::Catch2WithMain)

include(Catch)
catch_discover_tests(bedrock_protocol_tests)
