add_executable(${PROJECT_NAME}_tests test_disconnect.cpp)
target_link_libraries(${PROJECT_NAME}_tests PRIVATE
    bedrock::protocol
    Catch2::Catch2WithMain
)

include(Catch)
catch_discover_tests(${PROJECT_NAME}_tests)