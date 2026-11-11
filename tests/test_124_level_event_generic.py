import pytest

from bedrock_protocol import v1001, v2168, v2225

nbt = v2225.nbt

# TODO: pending BDS golden: gophertunnel cannot marshal the raw SerialisedEventData, so bedrock-dumper has to write it
# LevelEventGenericPacket{event_id: 9801, data: {ableToSleep: 1, overworldPlayerCount: 1, sleepingPlayerCount: 0}}
SLEEP_STATE = bytes.fromhex(
    "929901030b61626c65546f536c6565700203146f766572776f726c64506c61796572436f756e74020313736c656570696e67506c61796572436f756e740000"
)

NAMED_ROOT = bytes.fromhex(
    "d41f0a0005076f726967696e5800804a4305076f726967696e590000824205076f726967696e5a00001942030473697a652400"
)

SLEEP_STATE_PACKET = v2225.LevelEventGenericPacket(
    event_id=9801,
    data=nbt.CompoundTag(
        {
            "ableToSleep": nbt.IntTag(1),
            "overworldPlayerCount": nbt.IntTag(1),
            "sleepingPlayerCount": nbt.IntTag(0),
        }
    ),
)


@pytest.mark.parametrize("version", [v1001, v2168, v2225], ids=lambda version: version.__name__.rpartition(".")[2])
def test_level_event_generic_is_packet_124(version):
    assert version.PACKETS[124] is version.LevelEventGenericPacket


def test_a_generic_level_event_encodes_its_compound_without_a_root_tag():
    assert bytes(SLEEP_STATE_PACKET) == SLEEP_STATE


def test_a_generic_level_event_decodes_its_compound_without_a_root_tag():
    assert v2225.LevelEventGenericPacket.from_bytes(SLEEP_STATE) == SLEEP_STATE_PACKET


def test_every_version_reads_the_compound_without_a_root_tag(protocol):
    assert protocol.LevelEventGenericPacket.from_bytes(SLEEP_STATE) == protocol.LevelEventGenericPacket(
        event_id=9801, data=SLEEP_STATE_PACKET.data
    )


def test_every_version_writes_the_compound_without_a_root_tag(protocol):
    assert bytes(protocol.LevelEventGenericPacket.from_bytes(SLEEP_STATE)) == SLEEP_STATE


def test_every_version_rejects_a_compound_with_a_root_tag(protocol):
    with pytest.raises(ValueError, match="at byte"):
        protocol.LevelEventGenericPacket.from_bytes(NAMED_ROOT)


def test_an_empty_compound_is_the_event_id_and_one_tag_byte():
    assert len(bytes(v2225.LevelEventGenericPacket(event_id=-1))) == 2


def test_an_empty_compound_round_trips():
    packet = v2225.LevelEventGenericPacket(event_id=-1)
    assert v2225.LevelEventGenericPacket.from_bytes(bytes(packet)) == packet


def test_a_generic_level_event_rejects_a_compound_missing_its_tag_end():
    with pytest.raises(ValueError, match="at byte"):
        v2225.LevelEventGenericPacket.from_bytes(SLEEP_STATE[:-1])
