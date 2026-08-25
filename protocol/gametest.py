from protocol import packet

package = "bedrock.protocol"


@packet(id=195, since=2168)
class GameTestResultsPacket:
    succeeded: bool
    error: str
    test_name: str
