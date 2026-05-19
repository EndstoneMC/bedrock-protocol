from protocol._dsl import packet

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
    """Lists the armour-trim patterns and materials a server has registered,
    sent to a client as it joins."""

    trim_pattern_list: list[TrimPattern]
    trim_material_list: list[TrimMaterial]
