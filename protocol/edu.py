from protocol import packet

package = "bedrock.protocol"


class EduSharedUriResource:
    button_name: str
    link_uri: str


@packet(id=150, since=2168)
class CodeBuilderPacket:
    url: str
    should_open_code_builder: bool
