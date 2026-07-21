add_executable(bedrock_protocol_tests)
target_sources(bedrock_protocol_tests PRIVATE
        test_011_start_game.cpp
        test_030_inventory_transaction.cpp
        test_032_mob_armor_equipment.cpp
        test_074_boss_event.cpp
        test_122_biome_definition_list.cpp
        test_123_level_sound_event.cpp
        test_175_sub_chunk_request.cpp
        test_315_serverbound_diagnostics.cpp
        test_328_primitive_shapes.cpp
        test_331_graphics_override_parameter.cpp
        test_345_attribute_layer_sync.cpp
        test_347_server_presence_info.cpp
        test_348_update_sound_data.cpp
)
target_link_libraries(bedrock_protocol_tests PRIVATE bedrock::protocol Catch2::Catch2WithMain)

include(Catch)
catch_discover_tests(bedrock_protocol_tests)
