from enum import IntEnum

from protocol import field, int8, packet, varint32

package = "bedrock.protocol"


class EduSharedUriResource:
    button_name: str
    link_uri: str


@packet(id=150, since=2168)
class CodeBuilderPacket:
    url: str
    should_open_code_builder: bool


class LessonAction(IntEnum, int8):
    START = 0
    COMPLETE = 1
    RESTART = 2


@packet(id=183, since=2168)
class LessonProgressPacket:
    action: LessonAction = field(type=varint32)
    score: varint32
    activity_id: str
