from enum import IntEnum

from protocol import field, packet, type, uint8, varint32

package = "bedrock.protocol"


class AgentCapabilities:
    can_modify_blocks: bool | None


@packet(id=150, since=407)
class CodeBuilderPacket:
    """Code Builder Packet"""

    url: str
    should_open_code_builder: bool


class CodeBuilderStorageQueryOptions:
    class Operation(IntEnum):
        NONE = 0
        GET = 1
        SET = 2
        RESET = 3

    class Category(IntEnum):
        NONE = 0
        CODE_STATUS = 1
        INSTANTIATION = 2


class CodeBuilderExecutionStateCodeStatus(IntEnum):
    NONE = 0
    NOT_STARTED = 1
    IN_PROGRESS = 2
    PAUSED = 3
    ERROR = 4
    SUCCEEDED = 5


@packet(id=178, since=486)
class CodeBuilderSourcePacket:
    """This is EDU exclusive, used in getInterface() of WebviewSystem."""

    operation: CodeBuilderStorageQueryOptions.Operation = field(type=uint8)
    category: CodeBuilderStorageQueryOptions.Category = field(type=uint8)
    # Removed at v685, field name from CloudburstMC (pre-v776, BDS-invisible).
    value: str = field(until=685)
    code_status: CodeBuilderExecutionStateCodeStatus = field(type=uint8, since=685)


class EduSharedUriResource:
    button_name: str
    link_uri: str


@packet(id=170, since=465)
class EduUriResourcePacket:
    """Transmits Edu Shared Uri Resource settings to all clients."""

    edu_shared_uri_resource: EduSharedUriResource


class ExternalLinkSettings:
    url: str
    display_name: str


class EducationLocalLevelSettings:
    code_builder_override_uri: str | None


class EducationLevelSettings:
    code_builder_default_uri: str
    code_builder_title: str = field(since=407)
    can_resize_code_builder: bool = field(since=407)
    disable_legacy_title_bar: bool = field(since=465)
    post_process_filter: str = field(since=465)
    screenshot_border_resource_path: str = field(since=465)
    agent_capabilities: AgentCapabilities | None = field(since=465)
    local_settings: EducationLocalLevelSettings = field(since=407)
    quiz_attached: bool
    external_link_settings: ExternalLinkSettings | None = field(since=465)


@packet(id=137, since=388)
class EducationSettingsPacket:
    """Transmits EducationLevelSettings to all clients."""

    settings: EducationLevelSettings


@type(since=527)
class LessonAction(IntEnum):
    START = 0
    COMPLETE = 1
    RESTART = 2


@packet(id=183, since=527)
class LessonProgressPacket:
    """Lesson Progress."""

    action: LessonAction = field(type=varint32)
    score: varint32
    activity_id: str
