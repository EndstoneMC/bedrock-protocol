from protocol import packet, varint32
from protocol.common import BlockPos
from protocol.structure import Rotation

package = "bedrock.protocol"


@packet(id=195, since=2168)
class GameTestResultsPacket:
    succeeded: bool
    error: str
    test_name: str


@packet(id=194, since=2168)
class GameTestRequestPacket:
    max_tests_per_batch: varint32
    repeat_count: varint32
    rotation: Rotation
    stop_on_failure: bool
    test_pos: BlockPos
    tests_per_row: varint32
    test_name: str
