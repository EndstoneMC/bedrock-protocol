from enum import IntEnum

from protocol import field, int32, packet, uint8
from protocol.actor import ActorUniqueID
from protocol.common import Vec2, Vec3

package = "bedrock.protocol"


class Scheme(IntEnum, uint8):
    LOCKED_PLAYER_RELATIVE_STRAFE = 0
    CAMERA_RELATIVE = 1
    CAMERA_RELATIVE_STRAFE = 2
    PLAYER_RELATIVE = 3
    PLAYER_RELATIVE_STRAFE = 4


class TargetMode(IntEnum, uint8):
    ANGLE = 0
    DISTANCE = 1


class CameraAimAssistCommandPresetDefinition:
    preset_id: str | None
    target_mode: TargetMode | None
    angle: Vec2 | None
    distance: float | None


class CameraPreset:
    class AudioListener(IntEnum, uint8):
        CAMERA = 0
        PLAYER = 1

    name: str
    inherit_from: str
    pos_x: float | None
    pos_y: float | None
    pos_z: float | None
    rot_x: float | None
    rot_y: float | None
    camera_rotation_speed: float | None
    snap_to_target: bool | None
    horizontal_rotation_limit: Vec2 | None
    vertical_rotation_limit: Vec2 | None
    continue_targeting: bool | None
    tracking_radius: float | None
    view_offset: Vec2 | None
    entity_offset: Vec3 | None
    radius: float | None
    yaw_limit_min: float | None
    yaw_limit_max: float | None
    listener: AudioListener | None
    player_effects: bool | None
    aim_assist: CameraAimAssistCommandPresetDefinition | None
    control_scheme: Scheme | None
    apply_inherited_starting_rotation: bool = field(since=2192)
    starting_rotation: Vec2 | None = field(since=2192)


class CameraPresets:
    presets: list[CameraPreset]


@packet(id=198)
class CameraPresetsPacket:
    """The camera presets the level defines, sent during the join sequence."""

    camera_presets: CameraPresets


@packet(id=73, since=2168)
class CameraPacket:
    camera_id: ActorUniqueID
    target_player_id: ActorUniqueID


class CameraShakeType(IntEnum, uint8):
    POSITIONAL = 0
    ROTATIONAL = 1


class CameraShakeAction(IntEnum, uint8):
    ADD = 0
    STOP = 1


@packet(id=159, since=2168)
class CameraShakePacket:
    intensity: float
    seconds: float
    shake_type: CameraShakeType
    shake_action: CameraShakeAction


class CameraAimAssistActorPriority:
    class PriorityData:
        preset_index: int32
        category_index: int32
        actor_index: int32
        priority_value: int32


@packet(id=339, since=2168)
class CameraAimAssistActorPriorityPacket:
    camera_aim_assist_actor_priority_list: list[CameraAimAssistActorPriority.PriorityData]
