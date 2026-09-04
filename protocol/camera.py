"""Cameras: world/level/camera/ -- presets, shake, instructions, splines, aim assist,
and the world/level/controlscheme/ control scheme."""

from enum import IntEnum, auto

from protocol import field, int32, int64, packet, type, uint8, uint32
from protocol.actor import ActorUniqueID
from protocol.common import Vec2, Vec3
from protocol.eas import EasingType

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


@packet(id=73)
class CameraPacket:
    camera_id: ActorUniqueID
    target_player_id: ActorUniqueID


class CameraShakeType(IntEnum, uint8):
    POSITIONAL = 0
    ROTATIONAL = 1


class CameraShakeAction(IntEnum, uint8):
    ADD = 0
    STOP = 1


@packet(id=159)
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


@packet(id=339, since=924)
class CameraAimAssistActorPriorityPacket:
    camera_aim_assist_actor_priority_list: list[CameraAimAssistActorPriority.PriorityData]


class ClientCameraAimAssistPacketAction(IntEnum, uint8):
    SET_FROM_CAMERA_PRESET = 0
    CLEAR = 1
    COUNT = auto()


@packet(id=321)
class ClientCameraAimAssistPacket:
    camera_preset_id: str
    action: ClientCameraAimAssistPacketAction
    allow_aim_assist: bool


@packet(id=316)
class CameraAimAssistPacket:
    class Action(IntEnum, uint8):
        SET = 0
        CLEAR = 1
        COUNT = auto()

    class TargetMode(IntEnum, uint8):
        ANGLE = 0
        DISTANCE = 1
        COUNT = auto()

    preset_id: str
    view_angle: Vec2
    distance: float
    target_mode: TargetMode
    action: Action
    show_debug_render: bool


class CameraAimAssistCategoryPriorities:
    entities: dict[str, int32]
    blocks: dict[str, int32]
    block_tags: dict[str, int32] = field(since=898)
    entity_type_families: dict[str, int32] = field(since=924)
    entity_default: int32 | None
    block_default: int32 | None


class CameraAimAssistCategoryDefinition:
    name: str
    priorities: CameraAimAssistCategoryPriorities


class CameraAimAssistPresetExclusionDefinition:
    block_exclusion_list: list[str]
    actor_exclusion_list: list[str]
    block_tag_exclusion_list: list[str]
    entity_type_family_exclusion_list: list[str] = field(since=924)


class CameraAimAssistPresetDefinition:
    identifier: str
    exclusion_settings: CameraAimAssistPresetExclusionDefinition
    liquid_targeting_list: list[str]
    item_settings: dict[str, str]
    default_item_settings: str | None
    hand_settings: str | None


class CameraAimAssistPresetsPacketOperation(IntEnum, uint8):
    SET = 0
    ADD_TO_EXISTING = 1


@packet(id=320)
class CameraAimAssistPresetsPacket:
    categories: list[CameraAimAssistCategoryDefinition]
    presets: list[CameraAimAssistPresetDefinition]
    operation: CameraAimAssistPresetsPacketOperation


class SplineType(IntEnum, uint8):
    CATMULL_ROM = 0
    LINEAR = 1


class CameraInstructionOptions:
    class SetInstruction:
        class EaseOption:
            easing_type: EasingType = field(type=uint8)
            easing_time: float

        class PosOption:
            pos: Vec3

        class RotOption:
            rot_x: float
            rot_y: float

        class FacingOption:
            facing_pos: Vec3

        class ViewOffsetOption:
            view_offset_x: float
            view_offset_y: float

        class EntityOffsetOption:
            entity_offset_x: float
            entity_offset_y: float
            entity_offset_z: float

        preset_index: uint32
        ease: EaseOption | None
        pos: PosOption | None
        rot: RotOption | None
        facing: FacingOption | None
        view_offset: ViewOffsetOption | None
        entity_offset: EntityOffsetOption | None
        default_: bool | None
        remove_ignore_starting_values_component: bool

    class FadeInstruction:
        class TimeOption:
            fade_in_time: float
            hold_time: float
            fade_out_time: float

        class ColorOption:
            red: float
            green: float
            blue: float

        time: TimeOption | None
        color: ColorOption | None

    class TargetInstruction:
        target_center_offset: Vec3 | None
        target_actor_id: int64

    class FovInstruction:
        fov: float
        fov_ease_time: float
        fov_ease_type: EasingType = field(type=str)
        fov_clear: bool

    class AttachToEntityInstruction:
        attach_to_entity_id: int64

    @type(until=924)
    class SplineInstruction:
        class SplineRotationOption:
            rotation_key_frame_value: Vec3
            rotation_key_frame_time: float

        total_time: float
        curve_type: SplineType
        curve: list[Vec3]
        progress_key_frames: list[Vec2]
        spline_rotation_option: list[SplineRotationOption]

    @type(since=924)
    class SplineInstruction:
        class SplineProgressOption:
            progress_key_frame_value: float
            progress_key_frame_time: float
            progress_key_frames_easing_func: EasingType = field(type=str)

        class SplineRotationOption:
            rotation_key_frame_value: Vec3
            rotation_key_frame_time: float
            rotation_key_frames_easing_func: EasingType = field(type=str)

        total_time: float
        curve_type: SplineType
        curve: list[Vec3]
        progress_key_frames: list[SplineProgressOption]
        spline_rotation_option: list[SplineRotationOption]
        spline_identifier: str = field(since=944)
        load_from_json: bool = field(since=944)


class CameraInstruction:
    set: CameraInstructionOptions.SetInstruction | None
    clear: bool | None
    fade: CameraInstructionOptions.FadeInstruction | None
    target: CameraInstructionOptions.TargetInstruction | None
    remove_target: bool | None
    field_of_view: CameraInstructionOptions.FovInstruction | None
    spline: CameraInstructionOptions.SplineInstruction | None = field(since=859)
    attach_to_entity: CameraInstructionOptions.AttachToEntityInstruction | None = field(since=859)
    detach_from_entity: bool | None = field(since=859)


@packet(id=300)
class CameraInstructionPacket:
    camera_instruction: CameraInstruction


class CameraSplineControlPoint:
    position: Vec3


class CameraSplineProgressKeyFrame:
    alpha: float
    time_seconds: float
    easing_type: EasingType | None = field(type=str)


class CameraSplineRotationKeyFrame:
    rotation: Vec3
    time_seconds: float
    easing_type: EasingType | None = field(type=str)


class CameraSplineDefinition:
    name: str
    total_time: float
    spline_type: str
    spline_control_points: list[CameraSplineControlPoint]
    spline_progress_frames: list[CameraSplineProgressKeyFrame]
    spline_rotation_frames: list[CameraSplineRotationKeyFrame]


@packet(id=338, since=924)
class CameraSplinePacket:
    splines: list[CameraSplineDefinition]


@packet(id=327)
class ClientboundControlSchemeSetPacket:
    control_scheme: Scheme
