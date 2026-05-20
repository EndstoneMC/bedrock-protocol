from protocol import packet

package = "bedrock.protocol"


class TrimPattern:
    item_name: str
    pattern_id: str


class TrimMaterial:
    material_id: str
    color: str
    item_name: str


@packet(id=302, since=582)
class TrimDataPacket:
    trim_patterns: list[TrimPattern]
    trim_materials: list[TrimMaterial]
