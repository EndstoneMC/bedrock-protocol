#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

using InputData = bp::PlayerAuthInputPacket::InputData;
using IUT = bp::ItemUseInventoryTransaction;

namespace {

// Air = `NetworkItemStackDescriptor{.id = 0}`; on the wire that's a single 0x00
// byte because the body is guarded on `id != 0`.
bp::NetworkItemStackDescriptor air()
{
    bp::NetworkItemStackDescriptor s;
    s.id = 0;
    return s;
}

// Baseline IUT used by every PerformItemInteraction test below: holds an
// air item, Place + Unknown trigger, predicted Failure + cooldown Off.
bp::PackedItemUseLegacyInventoryTransaction baseIUT()
{
    bp::PackedItemUseLegacyInventoryTransaction iut;
    iut.id.id = 0;
    iut.transaction.action_type = IUT::ActionType::Place;
    iut.transaction.trigger_type = IUT::TriggerType::Unknown;
    iut.transaction.pos = bp::BlockPos{1, 64, 2};
    iut.transaction.face = 1;
    iut.transaction.slot = 0;
    iut.transaction.item = air();
    iut.transaction.from_pos = bp::Vec3{3.5f, 64.5f, 2.5f};
    iut.transaction.click_pos = bp::Vec3{0.5f, 0.5f, 0.5f};
    iut.transaction.target_block_id = 100;
    iut.transaction.client_predicted_result = IUT::PredictedResult::Failure;
    iut.transaction.client_cooldown_state = IUT::ClientCooldownState::Off;
    return iut;
}

// Wraps an IUT into a full v766+ PAIP with PerformItemInteraction set and all
// other gated fields off, so we can vary just the IUT across tests.
bp::PlayerAuthInputPacket withItemUse(bp::PackedItemUseLegacyInventoryTransaction iut)
{
    std::bitset<65> flags;
    flags.set(static_cast<std::size_t>(InputData::PerformItemInteraction));
    return bp::PlayerAuthInputPacket{
        bp::Vec2{0.5f, 1.5f},                 // rot
        bp::Vec3{2.0f, 65.0f, -3.5f},         // pos
        bp::Vec2{0.25f, -0.25f},              // move
        1.25f,                                // y_head_rot
        flags,
        bp::InputMode::Mouse,
        bp::ClientPlayMode::Normal,
        bp::NewInteractionModel::Classic,
        bp::Vec2{0.5f, 1.5f},                 // interact_rotation
        static_cast<bp::PlayerInputTick>(7),  // client_tick
        bp::Vec3{0.0f, -0.5f, 0.0f},          // pos_delta
        std::move(iut),                       // item_use_transaction
        bp::ItemStackRequestData{},           // item_stack_request (gated off)
        bp::PlayerBlockActions{},             // player_block_actions (gated off)
        bp::Vec2{},                           // vehicle_rot (gated off)
        static_cast<bp::ActorUniqueID>(0),    // client_predicted_vehicle (gated off)
        bp::Vec2{0.5f, 0.5f},                 // analog_move_vector
        bp::Vec3{0.0f, 0.0f, 1.0f},           // camera_orientation
        bp::Vec2{1.0f, -1.0f},                // raw_move_vector
    };
}

// Mirror of withItemUse for PerformItemStackRequest. The two helpers are
// distinct because PAIP's two gates are independent: each test only ever
// sets one of them.
bp::PlayerAuthInputPacket withItemStackRequest(bp::ItemStackRequestData req)
{
    std::bitset<65> flags;
    flags.set(static_cast<std::size_t>(InputData::PerformItemStackRequest));
    return bp::PlayerAuthInputPacket{
        bp::Vec2{0.5f, 1.5f},                 // rot
        bp::Vec3{2.0f, 65.0f, -3.5f},         // pos
        bp::Vec2{0.25f, -0.25f},              // move
        1.25f,                                // y_head_rot
        flags,
        bp::InputMode::Mouse,
        bp::ClientPlayMode::Normal,
        bp::NewInteractionModel::Classic,
        bp::Vec2{0.5f, 1.5f},                 // interact_rotation
        static_cast<bp::PlayerInputTick>(7),  // client_tick
        bp::Vec3{0.0f, -0.5f, 0.0f},          // pos_delta
        bp::PackedItemUseLegacyInventoryTransaction{},  // item_use_transaction (gated off)
        std::move(req),                       // item_stack_request
        bp::PlayerBlockActions{},             // player_block_actions (gated off)
        bp::Vec2{},                           // vehicle_rot (gated off)
        static_cast<bp::ActorUniqueID>(0),    // client_predicted_vehicle (gated off)
        bp::Vec2{0.5f, 0.5f},                 // analog_move_vector
        bp::Vec3{0.0f, 0.0f, 1.0f},           // camera_orientation
        bp::Vec2{1.0f, -1.0f},                // raw_move_vector
    };
}

}  // namespace

TEST_CASE("PlayerAuthInputPacket: id + round-trip of the v766+ field set")
{
    STATIC_REQUIRE(bp::PlayerAuthInputPacket::Id == 144);

    bp::PlayerAuthInputPacket pkt{
        bp::Vec2{0.5f, 1.5f},          // rot: pitch, yaw
        bp::Vec3{2.0f, 65.0f, -3.5f},  // pos
        bp::Vec2{0.25f, -0.25f},       // move
        1.25f,                         // y_head_rot
        std::bitset<65>{},             // input_data: no flags set
        bp::InputMode::Mouse,
        bp::ClientPlayMode::Normal,
        bp::NewInteractionModel::Classic,
        bp::Vec2{0.5f, 1.5f},                 // interact_rotation
        static_cast<bp::PlayerInputTick>(7),  // client_tick
        bp::Vec3{0.0f, -0.5f, 0.0f},          // pos_delta
        bp::PackedItemUseLegacyInventoryTransaction{},  // item_use_transaction (gated off)
        bp::ItemStackRequestData{},                     // item_stack_request (gated off)
        bp::PlayerBlockActions{},             // player_block_actions (gated off)
        bp::Vec2{},                           // vehicle_rot (gated off)
        static_cast<bp::ActorUniqueID>(0),    // client_predicted_vehicle (gated off)
        bp::Vec2{0.5f, 0.5f},                 // analog_move_vector
        bp::Vec3{0.0f, 0.0f, 1.0f},           // camera_orientation
        bp::Vec2{1.0f, -1.0f},                // raw_move_vector
    };

    // generated by gophertunnel:
    // packet.PlayerAuthInput{Pitch: 0.5, Yaw: 1.5, Position: mgl32.Vec3{2, 65, -3.5},
    //   MoveVector: mgl32.Vec2{0.25, -0.25}, HeadYaw: 1.25,
    //   InputData: protocol.NewBitset(packet.PlayerAuthInputBitsetSize),
    //   InputMode: 1, PlayMode: 0, InteractionModel: 2,
    //   InteractPitch: 0.5, InteractYaw: 1.5, Tick: 7,
    //   Delta: mgl32.Vec3{0, -0.5, 0}, AnalogueMoveVector: mgl32.Vec2{0.5, 0.5},
    //   CameraOrientation: mgl32.Vec3{0, 0, 1}, RawMoveVector: mgl32.Vec2{1, -1}}
    const std::vector<std::uint8_t> golden{
        0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x82, 0x42, 0x00,
        0x00, 0x60, 0xC0, 0x00, 0x00, 0x80, 0x3E, 0x00, 0x00, 0x80, 0xBE, 0x00, 0x00, 0xA0, 0x3F, 0x00, 0x01,
        0x00, 0x02, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0xBF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0xBF,
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::PlayerAuthInputPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->pos.y == 65.0f);
    REQUIRE(rt->client_tick == 7);
    REQUIRE(rt->raw_move_vector.x == 1.0f);
}

TEST_CASE("PlayerAuthInputPacket: 388 floor writes vr_gaze_direction in Reality play mode")
{
    bp::PlayerAuthInputPacket_<388> pkt{
        bp::Vec2{0.5f, 1.5f},
        bp::Vec3{2.0f, 65.0f, -3.5f},
        bp::Vec2{0.25f, -0.25f},
        1.25f,
        std::bitset<37>{},
        bp::InputMode_<388>::Mouse,
        bp::ClientPlayMode_<388>::Reality,
        bp::Vec3{0.0f, 1.0f, 0.0f},  // vr_gaze_direction
    };

    // generated by gophertunnel @7b618f9c (post-Pitch/Yaw fix, pre-v419 tick/delta):
    // packet.PlayerAuthInput{Pitch: 0.5, Yaw: 1.5, Position: mgl32.Vec3{2, 65, -3.5},
    //   MoveVector: mgl32.Vec2{0.25, -0.25}, HeadYaw: 1.25, InputData: 0,
    //   InputMode: 1, PlayMode: 4 /* Reality */,
    //   GazeDirection: mgl32.Vec3{0, 1, 0}}
    const std::vector<std::uint8_t> golden{
        0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x82, 0x42,
        0x00, 0x00, 0x60, 0xC0, 0x00, 0x00, 0x80, 0x3E, 0x00, 0x00, 0x80, 0xBE, 0x00, 0x00, 0xA0, 0x3F,
        0x00, 0x01, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x00, 0x00,
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::PlayerAuthInputPacket_<388>>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->play_mode == bp::ClientPlayMode_<388>::Reality);
    REQUIRE(rt->vr_gaze_direction.y == 1.0f);
}

TEST_CASE("PlayerAuthInputPacket: 388 floor predates tick/delta and interaction_model")
{
    bp::PlayerAuthInputPacket_<388> pkt{
        bp::Vec2{0.0f, 0.0f},       bp::Vec3{0.0f, 0.0f, 0.0f},       bp::Vec2{0.0f, 0.0f}, 0.0f, std::bitset<37>{},
        bp::InputMode_<388>::Touch, bp::ClientPlayMode_<388>::Normal,
    };

    // generated by gophertunnel @7b618f9c:
    // packet.PlayerAuthInput{InputMode: 2 /* Touch */, PlayMode: 0 /* Normal */}
    // (all other fields zero; the v388 marshaller stops after PlayMode since
    // PlayMode != Reality, so the wire is rot+pos+move+y_head_rot then the
    // varuint64 input_data + the two enum varuints)
    const std::vector<std::uint8_t> golden{
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00,
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::PlayerAuthInputPacket_<388>>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->input_mode == bp::InputMode_<388>::Touch);
    REQUIRE(rt->play_mode == bp::ClientPlayMode_<388>::Normal);
}

TEST_CASE("PlayerAuthInputPacket: bitset input_data round-trip across the 64-bit boundary")
{
    // Three flag bits spanning low, mid, and bit 64 -- the last forces a
    // 10-byte LEB128 encoding that wouldn't fit in a varuint64.
    std::bitset<65> flags;
    flags.set(6);   // Jumping
    flags.set(21);  // AscendBlock
    flags.set(64);  // SneakCurrentRaw

    bp::PlayerAuthInputPacket pkt{
        bp::Vec2{},
        bp::Vec3{},
        bp::Vec2{},
        0.0f,
        flags,
        bp::InputMode::Mouse,
        bp::ClientPlayMode::Normal,
        bp::NewInteractionModel::Touch,
        bp::Vec2{},
        static_cast<bp::PlayerInputTick>(0),
        bp::Vec3{},
        bp::PackedItemUseLegacyInventoryTransaction{},
        bp::ItemStackRequestData{},
        bp::PlayerBlockActions{},
        bp::Vec2{},
        static_cast<bp::ActorUniqueID>(0),
        bp::Vec2{},
        bp::Vec3{},
        bp::Vec2{},
    };

    // generated by gophertunnel:
    // packet.PlayerAuthInput{InputMode: 1, PlayMode: 0, InteractionModel: 0,
    //   InputData: NewBitset(65) with bits 6, 21, 64 set} -- all other fields
    //   zero. The 10-byte LEB128 run at offset 32 is the bitset; everything
    //   after offset 42 is zero-encoded for the remaining fixed-shape fields.
    const std::vector<std::uint8_t> golden{
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0xC0, 0x80, 0x80, 0x81, 0x80, 0x80, 0x80, 0x80, 0x80, 0x02, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::PlayerAuthInputPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->input_data.test(6));
    REQUIRE(rt->input_data.test(21));
    REQUIRE(rt->input_data.test(64));
    REQUIRE(rt->input_data.count() == 3);
}

TEST_CASE("PlayerAuthInputPacket: ClientPredictedVehicle bit gates the vehicle payload")
{
    std::bitset<65> flags;
    flags.set(static_cast<std::size_t>(InputData::IsInClientPredictedVehicle));

    bp::PlayerAuthInputPacket pkt{
        bp::Vec2{0.5f, 1.5f},
        bp::Vec3{2.0f, 65.0f, -3.5f},
        bp::Vec2{0.25f, -0.25f},
        1.25f,
        flags,
        bp::InputMode::Mouse,
        bp::ClientPlayMode::Normal,
        bp::NewInteractionModel::Classic,
        bp::Vec2{0.5f, 1.5f},
        static_cast<bp::PlayerInputTick>(7),
        bp::Vec3{0.0f, -0.5f, 0.0f},
        bp::PackedItemUseLegacyInventoryTransaction{},  // item_use_transaction (gated off)
        bp::ItemStackRequestData{},                     // item_stack_request (gated off)
        bp::PlayerBlockActions{},                       // player_block_actions (gated off)
        bp::Vec2{45.0f, 90.0f},                         // vehicle_rot
        static_cast<bp::ActorUniqueID>(-7),  // client_predicted_vehicle
        bp::Vec2{0.5f, 0.5f},
        bp::Vec3{0.0f, 0.0f, 1.0f},
        bp::Vec2{1.0f, -1.0f},
    };

    // generated by gophertunnel:
    // same packet.PlayerAuthInput literal as the v766+ test, but with
    // InputData.Set(packet.InputFlagClientPredictedVehicle),
    // VehicleRotation: mgl32.Vec2{45, 90}, ClientPredictedVehicle: -7
    const std::vector<std::uint8_t> golden{
        0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x82, 0x42, 0x00,
        0x00, 0x60, 0xC0, 0x00, 0x00, 0x80, 0x3E, 0x00, 0x00, 0x80, 0xBE, 0x00, 0x00, 0xA0, 0x3F, 0x80, 0x80,
        0x80, 0x80, 0x80, 0x80, 0x08, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F, 0x07,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xBF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x34, 0x42, 0x00,
        0x00, 0xB4, 0x42, 0x0D, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0xBF,
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::PlayerAuthInputPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->input_data.test(static_cast<std::size_t>(InputData::IsInClientPredictedVehicle)));
    REQUIRE(rt->vehicle_rot.x == 45.0f);
    REQUIRE(rt->client_predicted_vehicle == static_cast<bp::ActorUniqueID>(-7));
}

TEST_CASE("PlayerAuthInputPacket: PerformBlockActions bit gates the action list")
{
    std::bitset<65> flags;
    flags.set(static_cast<std::size_t>(InputData::PerformBlockActions));

    bp::PlayerAuthInputPacket pkt{
        bp::Vec2{0.5f, 1.5f},
        bp::Vec3{2.0f, 65.0f, -3.5f},
        bp::Vec2{0.25f, -0.25f},
        1.25f,
        flags,
        bp::InputMode::Mouse,
        bp::ClientPlayMode::Normal,
        bp::NewInteractionModel::Classic,
        bp::Vec2{0.5f, 1.5f},
        static_cast<bp::PlayerInputTick>(7),
        bp::Vec3{0.0f, -0.5f, 0.0f},
        bp::PackedItemUseLegacyInventoryTransaction{},  // item_use_transaction (gated off)
        bp::ItemStackRequestData{},                     // item_stack_request (gated off)
        bp::PlayerBlockActions{{
            // StartDestroyBlock carries pos + face
            {bp::PlayerActionType::StartDestroyBlock, bp::BlockPos{10, 70, -3}, 1},
            // StopDestroyBlock writes only the action tag
            {bp::PlayerActionType::StopDestroyBlock, bp::BlockPos{}, 0},
        }},
        bp::Vec2{},  // vehicle_rot (gated off)
        static_cast<bp::ActorUniqueID>(0),
        bp::Vec2{0.5f, 0.5f},
        bp::Vec3{0.0f, 0.0f, 1.0f},
        bp::Vec2{1.0f, -1.0f},
    };

    // generated by gophertunnel:
    // same packet.PlayerAuthInput literal as the v766+ test, but with
    // InputData.Set(packet.InputFlagPerformBlockActions),
    // BlockActions: []protocol.PlayerBlockAction{
    //     {Action: protocol.PlayerActionStartBreak, BlockPos: protocol.BlockPos{10, 70, -3}, Face: 1},
    //     {Action: protocol.PlayerActionStopBreak},
    // }
    const std::vector<std::uint8_t> golden{
        0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x82, 0x42, 0x00,
        0x00, 0x60, 0xC0, 0x00, 0x00, 0x80, 0x3E, 0x00, 0x00, 0x80, 0xBE, 0x00, 0x00, 0xA0, 0x3F, 0x80, 0x80,
        0x80, 0x80, 0x80, 0x01, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F, 0x07, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xBF, 0x00, 0x00, 0x00, 0x00, 0x04, 0x00, 0x14, 0x8C, 0x01, 0x05,
        0x02, 0x04, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0xBF,
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::PlayerAuthInputPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->player_block_actions.actions.size() == 2);
    REQUIRE(rt->player_block_actions.actions[0].player_action_type == bp::PlayerActionType::StartDestroyBlock);
    REQUIRE(rt->player_block_actions.actions[0].pos.y == 70);
    REQUIRE(rt->player_block_actions.actions[0].facing == 1);
    REQUIRE(rt->player_block_actions.actions[1].player_action_type == bp::PlayerActionType::StopDestroyBlock);
}

// All nine PerformItemInteraction goldens share the v766+ PAIP envelope built
// by withItemUse(); each gophertunnel literal below diffs against the same
// baseline `protocol.UseItemTransactionData` baseIUT() emits, with only the
// noted fields changed. Tests assume current gophertunnel master / v1.56.2.

TEST_CASE("PlayerAuthInputPacket: ItemUseTransaction Place baseline")
{
    auto pkt = withItemUse(baseIUT());

    // generated by gophertunnel:
    // packet.PlayerAuthInput{... PerformItemInteraction bit set ...
    //   ItemInteractionData: protocol.UseItemTransactionData{
    //     ActionType: 0 /* Place */, TriggerType: 0 /* Unknown */,
    //     BlockPosition: protocol.BlockPos{1, 64, 2}, BlockFace: 1, HotBarSlot: 0,
    //     HeldItem: protocol.ItemInstance{}, Position: mgl32.Vec3{3.5, 64.5, 2.5},
    //     ClickedPosition: mgl32.Vec3{0.5, 0.5, 0.5}, BlockRuntimeID: 100,
    //     ClientPrediction: 0, ClientCooldownState: 0}}
    const std::vector<std::uint8_t> golden{
        0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x82, 0x42,
        0x00, 0x00, 0x60, 0xC0, 0x00, 0x00, 0x80, 0x3E, 0x00, 0x00, 0x80, 0xBE, 0x00, 0x00, 0xA0, 0x3F,
        0x80, 0x80, 0x80, 0x80, 0x40, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F,
        0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xBF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x02, 0x80, 0x01, 0x04, 0x02, 0x00, 0x00, 0x00, 0x00, 0x60, 0x40, 0x00, 0x00, 0x81, 0x42,
        0x00, 0x00, 0x20, 0x40, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F,
        0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0xBF,
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::PlayerAuthInputPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->item_use_transaction.id.id == 0);
    REQUIRE(rt->item_use_transaction.slots.empty());
    REQUIRE(rt->item_use_transaction.transaction.transaction.actions.empty());
    REQUIRE(rt->item_use_transaction.transaction.action_type == IUT::ActionType::Place);
    REQUIRE(rt->item_use_transaction.transaction.target_block_id == 100);
}

TEST_CASE("PlayerAuthInputPacket: ItemUseTransaction ActionType=Use")
{
    auto iut = baseIUT();
    iut.transaction.action_type = IUT::ActionType::Use;
    auto pkt = withItemUse(std::move(iut));

    // generated by gophertunnel: baseline with ActionType: 1 /* Use */
    const std::vector<std::uint8_t> golden{
        0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x82, 0x42,
        0x00, 0x00, 0x60, 0xC0, 0x00, 0x00, 0x80, 0x3E, 0x00, 0x00, 0x80, 0xBE, 0x00, 0x00, 0xA0, 0x3F,
        0x80, 0x80, 0x80, 0x80, 0x40, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F,
        0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xBF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01,
        0x00, 0x02, 0x80, 0x01, 0x04, 0x02, 0x00, 0x00, 0x00, 0x00, 0x60, 0x40, 0x00, 0x00, 0x81, 0x42,
        0x00, 0x00, 0x20, 0x40, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F,
        0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0xBF,
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::PlayerAuthInputPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->item_use_transaction.transaction.action_type == IUT::ActionType::Use);
}

TEST_CASE("PlayerAuthInputPacket: ItemUseTransaction ActionType=Destroy")
{
    auto iut = baseIUT();
    iut.transaction.action_type = IUT::ActionType::Destroy;
    auto pkt = withItemUse(std::move(iut));

    // generated by gophertunnel: baseline with ActionType: 2 /* Destroy */
    const std::vector<std::uint8_t> golden{
        0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x82, 0x42,
        0x00, 0x00, 0x60, 0xC0, 0x00, 0x00, 0x80, 0x3E, 0x00, 0x00, 0x80, 0xBE, 0x00, 0x00, 0xA0, 0x3F,
        0x80, 0x80, 0x80, 0x80, 0x40, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F,
        0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xBF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02,
        0x00, 0x02, 0x80, 0x01, 0x04, 0x02, 0x00, 0x00, 0x00, 0x00, 0x60, 0x40, 0x00, 0x00, 0x81, 0x42,
        0x00, 0x00, 0x20, 0x40, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F,
        0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0xBF,
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::PlayerAuthInputPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->item_use_transaction.transaction.action_type == IUT::ActionType::Destroy);
}

TEST_CASE("PlayerAuthInputPacket: ItemUseTransaction ActionType=UseAsAttack")
{
    auto iut = baseIUT();
    iut.transaction.action_type = IUT::ActionType::UseAsAttack;
    auto pkt = withItemUse(std::move(iut));

    // generated by gophertunnel: baseline with ActionType: 3 /* UseAsAttack */
    const std::vector<std::uint8_t> golden{
        0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x82, 0x42,
        0x00, 0x00, 0x60, 0xC0, 0x00, 0x00, 0x80, 0x3E, 0x00, 0x00, 0x80, 0xBE, 0x00, 0x00, 0xA0, 0x3F,
        0x80, 0x80, 0x80, 0x80, 0x40, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F,
        0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xBF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03,
        0x00, 0x02, 0x80, 0x01, 0x04, 0x02, 0x00, 0x00, 0x00, 0x00, 0x60, 0x40, 0x00, 0x00, 0x81, 0x42,
        0x00, 0x00, 0x20, 0x40, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F,
        0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0xBF,
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::PlayerAuthInputPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->item_use_transaction.transaction.action_type == IUT::ActionType::UseAsAttack);
}

TEST_CASE("PlayerAuthInputPacket: legacy_request_id<-1 even gates slots")
{
    auto iut = baseIUT();
    iut.id.id = -2;
    bp::LegacySetSlot slot;
    slot.container_enum = bp::ContainerEnumName::HotbarContainer;
    slot.slots = std::string{"\x00\x01", 2};
    iut.slots = {slot};
    auto pkt = withItemUse(std::move(iut));

    // generated by gophertunnel: baseline with LegacyRequestID: -2 and
    // LegacySetSlots: [{ContainerID: 28 /* Hotbar */, Slots: []byte{0x00, 0x01}}]
    const std::vector<std::uint8_t> golden{
        0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x82, 0x42,
        0x00, 0x00, 0x60, 0xC0, 0x00, 0x00, 0x80, 0x3E, 0x00, 0x00, 0x80, 0xBE, 0x00, 0x00, 0xA0, 0x3F,
        0x80, 0x80, 0x80, 0x80, 0x40, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F,
        0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xBF, 0x00, 0x00, 0x00, 0x00, 0x03, 0x01, 0x1C,
        0x02, 0x00, 0x01, 0x00, 0x00, 0x00, 0x02, 0x80, 0x01, 0x04, 0x02, 0x00, 0x00, 0x00, 0x00, 0x60,
        0x40, 0x00, 0x00, 0x81, 0x42, 0x00, 0x00, 0x20, 0x40, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00,
        0x3F, 0x00, 0x00, 0x00, 0x3F, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0x3F,
        0x00, 0x00, 0x80, 0xBF,
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::PlayerAuthInputPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->item_use_transaction.id.id == -2);
    REQUIRE(rt->item_use_transaction.slots.size() == 1);
    REQUIRE(rt->item_use_transaction.slots[0].container_enum == bp::ContainerEnumName::HotbarContainer);
    REQUIRE(rt->item_use_transaction.slots[0].slots.size() == 2);
}

TEST_CASE("PlayerAuthInputPacket: ItemUseTransaction action with Container source writes window_id")
{
    auto iut = baseIUT();
    bp::InventoryAction action;
    action.source.source_type = bp::InventorySourceType::ContainerInventory;
    action.source.container_id = 0;
    action.slot = 1;
    action.from_item_descriptor = air();
    action.to_item_descriptor = air();
    iut.transaction.transaction.actions = {action};
    auto pkt = withItemUse(std::move(iut));

    // generated by gophertunnel: baseline with Actions:
    //   [{SourceType: 0 /* Container */, WindowID: 0, InventorySlot: 1, OldItem: {}, NewItem: {}}]
    const std::vector<std::uint8_t> golden{
        0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x82, 0x42,
        0x00, 0x00, 0x60, 0xC0, 0x00, 0x00, 0x80, 0x3E, 0x00, 0x00, 0x80, 0xBE, 0x00, 0x00, 0xA0, 0x3F,
        0x80, 0x80, 0x80, 0x80, 0x40, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F,
        0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xBF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00,
        0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x02, 0x80, 0x01, 0x04, 0x02, 0x00, 0x00, 0x00, 0x00, 0x60,
        0x40, 0x00, 0x00, 0x81, 0x42, 0x00, 0x00, 0x20, 0x40, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00,
        0x3F, 0x00, 0x00, 0x00, 0x3F, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0x3F,
        0x00, 0x00, 0x80, 0xBF,
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::PlayerAuthInputPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    const auto &acts = rt->item_use_transaction.transaction.transaction.actions;
    REQUIRE(acts.size() == 1);
    REQUIRE(acts[0].source.source_type == bp::InventorySourceType::ContainerInventory);
    REQUIRE(acts[0].source.container_id == 0);
    REQUIRE(acts[0].slot == 1);
}

TEST_CASE("PlayerAuthInputPacket: ItemUseTransaction action with World source writes flags")
{
    auto iut = baseIUT();
    bp::InventoryAction action;
    action.source.source_type = bp::InventorySourceType::WorldInteraction;
    action.source.flags = 1;  // WorldInteraction_Random
    action.slot = 0;
    action.from_item_descriptor = air();
    action.to_item_descriptor = air();
    iut.transaction.transaction.actions = {action};
    auto pkt = withItemUse(std::move(iut));

    // generated by gophertunnel: baseline with Actions:
    //   [{SourceType: 2 /* World */, SourceFlags: 1, InventorySlot: 0, OldItem: {}, NewItem: {}}]
    const std::vector<std::uint8_t> golden{
        0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x82, 0x42,
        0x00, 0x00, 0x60, 0xC0, 0x00, 0x00, 0x80, 0x3E, 0x00, 0x00, 0x80, 0xBE, 0x00, 0x00, 0xA0, 0x3F,
        0x80, 0x80, 0x80, 0x80, 0x40, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F,
        0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xBF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x02,
        0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x80, 0x01, 0x04, 0x02, 0x00, 0x00, 0x00, 0x00, 0x60,
        0x40, 0x00, 0x00, 0x81, 0x42, 0x00, 0x00, 0x20, 0x40, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00,
        0x3F, 0x00, 0x00, 0x00, 0x3F, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0x3F,
        0x00, 0x00, 0x80, 0xBF,
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::PlayerAuthInputPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    const auto &src = rt->item_use_transaction.transaction.transaction.actions[0].source;
    REQUIRE(src.source_type == bp::InventorySourceType::WorldInteraction);
    REQUIRE(src.flags == 1);
}

TEST_CASE("PlayerAuthInputPacket: ItemUseTransaction action with Creative source has no inner gate")
{
    auto iut = baseIUT();
    bp::InventoryAction action;
    action.source.source_type = bp::InventorySourceType::CreativeInventory;
    action.slot = 0;
    action.from_item_descriptor = air();
    action.to_item_descriptor = air();
    iut.transaction.transaction.actions = {action};
    auto pkt = withItemUse(std::move(iut));

    // generated by gophertunnel: baseline with Actions:
    //   [{SourceType: 3 /* Creative */, InventorySlot: 0, OldItem: {}, NewItem: {}}]
    // (no WindowID, no SourceFlags -- saves one byte over the Container case)
    const std::vector<std::uint8_t> golden{
        0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x82, 0x42,
        0x00, 0x00, 0x60, 0xC0, 0x00, 0x00, 0x80, 0x3E, 0x00, 0x00, 0x80, 0xBE, 0x00, 0x00, 0xA0, 0x3F,
        0x80, 0x80, 0x80, 0x80, 0x40, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F,
        0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xBF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x03,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x80, 0x01, 0x04, 0x02, 0x00, 0x00, 0x00, 0x00, 0x60, 0x40,
        0x00, 0x00, 0x81, 0x42, 0x00, 0x00, 0x20, 0x40, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F,
        0x00, 0x00, 0x00, 0x3F, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0x3F, 0x00,
        0x00, 0x80, 0xBF,
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::PlayerAuthInputPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->item_use_transaction.transaction.transaction.actions[0].source.source_type ==
            bp::InventorySourceType::CreativeInventory);
}

TEST_CASE("PlayerAuthInputPacket: ItemUseTransaction non-zero trigger/prediction/cooldown")
{
    auto iut = baseIUT();
    iut.transaction.action_type = IUT::ActionType::UseAsAttack;
    iut.transaction.trigger_type = IUT::TriggerType::SimulationTick;
    iut.transaction.client_predicted_result = IUT::PredictedResult::Success;
    iut.transaction.client_cooldown_state = IUT::ClientCooldownState::On;
    auto pkt = withItemUse(std::move(iut));

    // generated by gophertunnel: baseline with ActionType: 3, TriggerType: 2,
    //   ClientPrediction: 1, ClientCooldownState: 1
    const std::vector<std::uint8_t> golden{
        0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x82, 0x42,
        0x00, 0x00, 0x60, 0xC0, 0x00, 0x00, 0x80, 0x3E, 0x00, 0x00, 0x80, 0xBE, 0x00, 0x00, 0xA0, 0x3F,
        0x80, 0x80, 0x80, 0x80, 0x40, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F,
        0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xBF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03,
        0x02, 0x02, 0x80, 0x01, 0x04, 0x02, 0x00, 0x00, 0x00, 0x00, 0x60, 0x40, 0x00, 0x00, 0x81, 0x42,
        0x00, 0x00, 0x20, 0x40, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F,
        0x64, 0x01, 0x01, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0xBF,
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::PlayerAuthInputPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->item_use_transaction.transaction.trigger_type == IUT::TriggerType::SimulationTick);
    REQUIRE(rt->item_use_transaction.transaction.client_predicted_result == IUT::PredictedResult::Success);
    REQUIRE(rt->item_use_transaction.transaction.client_cooldown_state == IUT::ClientCooldownState::On);
}

// Phase C envelope goldens. The three tests below share the same v766+ PAIP
// envelope produced by withItemStackRequest(); each diffs against the same
// baseline `protocol.ItemStackRequest{}` gophertunnel emits, varying only the
// envelope contents.

TEST_CASE("PlayerAuthInputPacket: empty ItemStackRequest envelope")
{
    auto pkt = withItemStackRequest(bp::ItemStackRequestData{});

    // generated by gophertunnel:
    // packet.PlayerAuthInput{... PerformItemStackRequest bit set ...
    //   ItemStackRequest: protocol.ItemStackRequest{} /* zero everything */}
    const std::vector<std::uint8_t> golden{
        0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F, 0x00, 0x00, 0x00, 0x40,
        0x00, 0x00, 0x82, 0x42, 0x00, 0x00, 0x60, 0xC0, 0x00, 0x00, 0x80, 0x3E,
        0x00, 0x00, 0x80, 0xBE, 0x00, 0x00, 0xA0, 0x3F, 0x80, 0x80, 0x80, 0x80,
        0x80, 0x02, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0,
        0x3F, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xBF, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x3F, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80,
        0xBF,
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::PlayerAuthInputPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->item_stack_request.client_request_id.id == 0);
    REQUIRE(rt->item_stack_request.actions.empty());
    REQUIRE(rt->item_stack_request.strings_to_filter.empty());
    REQUIRE(rt->item_stack_request.strings_to_filter_origin == bp::TextProcessingEventOrigin::ServerChatPublic);
}

TEST_CASE("PlayerAuthInputPacket: ItemStackRequest with four heterogeneous actions")
{
    bp::ItemStackRequestData req;
    req.client_request_id.id = 7;

    bp::TakeStackRequestAction take;
    take.amount = 2;
    take.src.full_container_name.name = bp::ContainerEnumName::HotbarContainer;
    take.src.full_container_name.dynamic_id = std::nullopt;
    take.src.slot = 0;
    take.src.net_id_variant = 100;
    take.dst.full_container_name.name = bp::ContainerEnumName::InventoryContainer;
    take.dst.full_container_name.dynamic_id = std::nullopt;
    take.dst.slot = 5;
    take.dst.net_id_variant = 0;

    bp::CraftRecipeStackRequestAction recipe;
    recipe.recipe_net_id = 42;
    recipe.num_crafts = 3;

    bp::ScreenLabTableCombineStackRequestAction lab;

    bp::CraftResultsDeprecatedStackRequestAction results;
    results.num_crafts = 2;

    req.actions = {take, recipe, lab, results};
    req.strings_to_filter = {"hello"};
    req.strings_to_filter_origin = bp::TextProcessingEventOrigin::AnvilText;

    auto pkt = withItemStackRequest(std::move(req));

    // generated by gophertunnel:
    // protocol.ItemStackRequest{RequestID: 7, FilterStrings: []string{"hello"},
    //   FilterCause: AnvilText, Actions: [Take{Count:2,Source:Hotbar/0/100,
    //   Destination:Inventory/5/0}, CraftRecipe{Recipe:42, NumberOfCrafts:3},
    //   LabTableCombine{}, CraftResultsDeprecated{TimesCrafted:2}]}
    const std::vector<std::uint8_t> golden{
        0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F, 0x00, 0x00, 0x00, 0x40,
        0x00, 0x00, 0x82, 0x42, 0x00, 0x00, 0x60, 0xC0, 0x00, 0x00, 0x80, 0x3E,
        0x00, 0x00, 0x80, 0xBE, 0x00, 0x00, 0xA0, 0x3F, 0x80, 0x80, 0x80, 0x80,
        0x80, 0x02, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0,
        0x3F, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xBF, 0x00, 0x00,
        0x00, 0x00, 0x0E, 0x04, 0x00, 0x02, 0x1C, 0x00, 0x00, 0xC8, 0x01, 0x1D,
        0x00, 0x05, 0x00, 0x0C, 0x2A, 0x03, 0x09, 0x13, 0x00, 0x02, 0x01, 0x05,
        0x68, 0x65, 0x6C, 0x6C, 0x6F, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x3F, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80,
        0xBF,
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::PlayerAuthInputPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->item_stack_request.actions.size() == 4);
    REQUIRE(rt->item_stack_request.actions[0].index() == 0);   // Take
    REQUIRE(rt->item_stack_request.actions[1].index() == 12);  // CraftRecipe
    REQUIRE(rt->item_stack_request.actions[2].index() == 9);   // LabTableCombine
    REQUIRE(rt->item_stack_request.actions[3].index() == 19);  // CraftResultsDeprecated
    REQUIRE(std::get<bp::TakeStackRequestAction>(rt->item_stack_request.actions[0]).amount == 2);
    REQUIRE(std::get<bp::CraftRecipeStackRequestAction>(rt->item_stack_request.actions[1]).recipe_net_id == 42);
    REQUIRE(rt->item_stack_request.strings_to_filter == std::vector<std::string>{"hello"});
    REQUIRE(rt->item_stack_request.strings_to_filter_origin == bp::TextProcessingEventOrigin::AnvilText);
}

TEST_CASE("PlayerAuthInputPacket: AutoCraftRecipe with all five ItemDescriptor variants")
{
    bp::ItemStackRequestData req{};  // value-init so strings_to_filter_origin defaults to ServerChatPublic
    req.client_request_id.id = 11;

    bp::CraftRecipeAutoStackRequestAction action;
    action.recipe_net_id = 5;
    action.num_crafts = 1;
    action.num_crafts = 1;
    action.ingredients = {
        bp::ItemDescriptorCount{
            bp::InternalItemDescriptor{static_cast<std::int16_t>(7), static_cast<std::int16_t>(0)},
            1,
        },
        bp::ItemDescriptorCount{
            bp::MolangDescriptor{"q.is_baby", 1},
            2,
        },
        bp::ItemDescriptorCount{
            bp::ItemTagDescriptor{"minecraft:planks"},
            3,
        },
        bp::ItemDescriptorCount{
            bp::DeferredDescriptor{"minecraft:stick", static_cast<std::int16_t>(0)},
            4,
        },
        bp::ItemDescriptorCount{
            bp::ComplexAliasDescriptor{"alias"},
            5,
        },
    };

    req.actions = {action};
    auto pkt = withItemStackRequest(std::move(req));

    // generated by gophertunnel:
    // protocol.ItemStackRequest{RequestID: 11, Actions:
    //   [&AutoCraftRecipe{Recipe:5, NumberOfCrafts:1, TimesCrafted:1,
    //     Ingredients: [Default(7), MoLang("q.is_baby", v=1),
    //                   ItemTag("minecraft:planks"),
    //                   Deferred("minecraft:stick", 0), ComplexAlias("alias")]}]}
    const std::vector<std::uint8_t> golden{
        0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0, 0x3F, 0x00, 0x00, 0x00, 0x40,
        0x00, 0x00, 0x82, 0x42, 0x00, 0x00, 0x60, 0xC0, 0x00, 0x00, 0x80, 0x3E,
        0x00, 0x00, 0x80, 0xBE, 0x00, 0x00, 0xA0, 0x3F, 0x80, 0x80, 0x80, 0x80,
        0x80, 0x02, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0xC0,
        0x3F, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xBF, 0x00, 0x00,
        0x00, 0x00, 0x16, 0x01, 0x0D, 0x05, 0x01, 0x01, 0x05, 0x01, 0x07, 0x00,
        0x00, 0x00, 0x02, 0x02, 0x09, 0x71, 0x2E, 0x69, 0x73, 0x5F, 0x62, 0x61,
        0x62, 0x79, 0x01, 0x04, 0x03, 0x10, 0x6D, 0x69, 0x6E, 0x65, 0x63, 0x72,
        0x61, 0x66, 0x74, 0x3A, 0x70, 0x6C, 0x61, 0x6E, 0x6B, 0x73, 0x06, 0x04,
        0x0F, 0x6D, 0x69, 0x6E, 0x65, 0x63, 0x72, 0x61, 0x66, 0x74, 0x3A, 0x73,
        0x74, 0x69, 0x63, 0x6B, 0x00, 0x00, 0x08, 0x05, 0x05, 0x61, 0x6C, 0x69,
        0x61, 0x73, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3F,
        0x00, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x80, 0xBF,
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::PlayerAuthInputPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->item_stack_request.actions.size() == 1);
    const auto &auto_craft = std::get<bp::CraftRecipeAutoStackRequestAction>(rt->item_stack_request.actions[0]);
    REQUIRE(auto_craft.recipe_net_id == 5);
    REQUIRE(auto_craft.ingredients.size() == 5);
    REQUIRE(auto_craft.ingredients[0].descriptor.index() == 1);  // Internal
    REQUIRE(auto_craft.ingredients[1].descriptor.index() == 2);  // Molang
    REQUIRE(auto_craft.ingredients[2].descriptor.index() == 3);  // ItemTag
    REQUIRE(auto_craft.ingredients[3].descriptor.index() == 4);  // Deferred
    REQUIRE(auto_craft.ingredients[4].descriptor.index() == 5);  // ComplexAlias
}
