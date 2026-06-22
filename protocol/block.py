from protocol import field, packet, uint8
from protocol.common import BlockPos, NetworkBlockPos

package = "bedrock.protocol"


# COMPILER_EXTENSION_NEEDED: was at id 124 in [340, 361) before moving here at v361;
# the DSL can't express a packet whose id changes by version, so the id-124 lifetime
# is unmodeled.
@packet(id=125, since=361)
class LecternUpdatePacket:
    page: uint8
    total_pages: uint8
    block_pos: NetworkBlockPos = field(until=944)
    block_pos: BlockPos = field(since=944)
    dropping_book: bool = field(until=662)
