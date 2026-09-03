"""Education Edition: codebuilder/, edu level settings, edu URI resources, and the Agent
(world/actor/agent/), which is Education-only."""

from enum import IntEnum
from typing import Literal

from protocol import field, int8, int32, packet, uint8, varint32
from protocol.actor import ActorRuntimeID

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


class AgentCapabilities:
    can_modify_blocks: bool | None


class EducationLocalLevelSettings:
    code_builder_override_uri: str | None


class ExternalLinkSettings:
    url: str
    display_name: str


class EducationLevelSettings:
    code_builder_default_uri: str
    code_builder_title: str
    can_resize_code_builder: bool
    disable_legacy_title_bar: bool
    post_process_filter: str
    screenshot_border_resource_path: str
    agent_capabilities: AgentCapabilities | None
    local_settings: EducationLocalLevelSettings
    _deprecated: Literal[False]
    external_link_settings: ExternalLinkSettings | None


@packet(id=137, since=2168)
class EducationSettingsPacket:
    education_level_settings: EducationLevelSettings


@packet(id=170, since=2168)
class EduUriResourcePacket:
    edu_shared_uri_resource: EduSharedUriResource


class Operation(IntEnum, uint8):
    NONE = 0
    GET = 1
    SET = 2
    RESET = 3


class Category(IntEnum, uint8):
    NONE = 0
    CODE_STATUS = 1
    INSTANTIATION = 2


class CodeStatus(IntEnum, uint8):
    NONE = 0
    NOT_STARTED = 1
    IN_PROGRESS = 2
    PAUSED = 3
    ERROR = 4
    SUCCEEDED = 5


@packet(id=178, since=2168)
class CodeBuilderSourcePacket:
    operation: Operation
    category: Category
    code_status: CodeStatus


class AgentAnimation(IntEnum, uint8):
    ARM_SWING = 0
    SHRUG = 1


@packet(id=304, since=2168)
class AgentAnimationPacket:
    anim: AgentAnimation
    runtime_id: ActorRuntimeID


class AgentActionType(IntEnum):
    ATTACK = 1
    COLLECT = 2
    DESTROY = 3
    DETECT_REDSTONE = 4
    DETECT_OBSTACLE = 5
    DROP = 6
    DROP_ALL = 7
    INSPECT = 8
    INSPECT_DATA = 9
    INSPECT_ITEM_COUNT = 10
    INSPECT_ITEM_DETAIL = 11
    INSPECT_ITEM_SPACE = 12
    INTERACT = 13
    MOVE = 14
    PLACE_BLOCK = 15
    TILL = 16
    TRANSFER_ITEM_TO = 17
    TURN = 18


@packet(id=181, since=2168)
class AgentActionEventPacket:
    request_id: str
    action: AgentActionType = field(type=int32)
    response: str
