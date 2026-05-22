add_executable(${PROJECT_NAME}_tests
    test_actor.cpp
    test_book.cpp
    test_crafting.cpp
    test_disconnect.cpp
    test_game.cpp
    test_graphics.cpp
    test_inventory.cpp
    test_level.cpp
    test_login.cpp
    test_network.cpp
    test_player.cpp
    test_resource_pack.cpp
    test_trim.cpp)
target_link_libraries(${PROJECT_NAME}_tests PRIVATE
    bedrock::protocol
    Catch2::Catch2WithMain
)

include(Catch)
catch_discover_tests(${PROJECT_NAME}_tests)