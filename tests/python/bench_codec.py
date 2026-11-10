"""Encode+decode throughput of two mid-size packets.

python tests/python/bench_codec.py
"""

import timeit

from bedrock_protocol import v2193 as proto


def player_auth_input():
    flags = proto.PlayerAuthInputPacket.InputData
    return proto.PlayerAuthInputPacket(
        rot=proto.Vec2(x=12.5, y=-90.0),
        pos=proto.Vec3(x=104.5, y=65.62, z=-37.25),
        move=proto.Vec2(x=0.0, y=1.0),
        y_head_rot=12.5,
        input_data=[flags.UP, flags.SPRINTING, flags.SPRINT_DOWN, flags.START_SPRINTING],
        client_tick=123456,
        pos_delta=proto.Vec3(x=0.0, y=-0.0784, z=0.28),
        player_block_actions=[
            proto.PlayerBlockActionData(
                player_action_type=proto.PlayerActionType.CONTINUE_DESTROY_BLOCK,
                pos=proto.BlockPos(x=104, y=64, z=-38),
                facing=1,
            ),
        ],
        analog_move_vector=proto.Vec2(x=0.0, y=1.0),
        camera_orientation=proto.Vec3(x=0.2, y=-0.1, z=0.97),
        raw_move_vector=proto.Vec2(x=0.0, y=1.0),
    )


def inventory_transaction():
    use = proto.ItemUseInventoryTransaction(
        pos=proto.BlockPos(x=104, y=64, z=-38),
        face=1,
        slot=0,
        from_pos=proto.Vec3(x=104.5, y=65.62, z=-37.25),
        click_pos=proto.Vec3(x=0.5, y=1.0, z=0.5),
        target_block_id=7,
    )
    return proto.InventoryTransactionPacket(transaction=use)


def read_all(value):
    for name in getattr(type(value), "__match_args__", ()):
        member = getattr(value, name)
        for item in member if isinstance(member, list) else (member,):
            read_all(item)


def measure(name, packet):
    body = proto.encode(packet)
    assert proto.decode(packet.ID, body) == packet
    for label, call in (
        ("encode", lambda: proto.encode(packet)),
        ("decode", lambda: proto.decode(packet.ID, body)),
        ("encode+decode", lambda: proto.decode(packet.ID, proto.encode(packet))),
        ("decode+read every field", lambda: read_all(proto.decode(packet.ID, body))),
    ):
        timer = timeit.Timer(call)
        number, _ = timer.autorange()
        per_call = min(timer.repeat(repeat=5, number=number)) / number
        print(f"{name} ({len(body)} bytes) {label}: {1 / per_call:,.0f}/s, {per_call * 1e6:.2f} us")


if __name__ == "__main__":
    measure("PlayerAuthInputPacket", player_auth_input())
    measure("InventoryTransactionPacket", inventory_transaction())
