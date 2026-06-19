from enum import IntEnum

from protocol import field, int32, int64, packet, uint8, uint32
from protocol.actor import ActorUniqueID
from protocol.common import Vec2, Vec3
from protocol.nbt import CompoundTag

package = "bedrock.protocol"


@packet(id=73)
class CameraPacket:
    """Used only in EDU through the tripod camera item or the TakePictureCommand. Sends the camera actor id and the
    target player id from the server."""

    camera_id: ActorUniqueID
    target_player_id: ActorUniqueID


@packet(id=316, since=729)
class CameraAimAssistPacket:
    class Action(IntEnum):
        SET = 0
        CLEAR = 1

    class TargetMode(IntEnum):
        ANGLE = 0
        DISTANCE = 1

    preset_id: str = field(since=766)
    view_angle: Vec2
    distance: float
    target_mode: TargetMode = field(type=uint8)
    action: Action = field(type=uint8)
    show_debug_render: bool = field(since=827)


class PriorityData:
    """A single entry in the CameraAimAssistActorPriorityServerComponent.mActorPriorities map,
    flattened for the wire."""

    preset_idx: int32
    category_idx: int32
    actor_idx: int32
    priority: int32


@packet(id=339, since=924)
class CameraAimAssistActorPriorityPacket:
    """Sent by the server to clients for updating the actor priority for client aim-assist
    systems."""

    priorities: list[PriorityData]


class ClientCameraAimAssistPacketAction(IntEnum):
    SET_FROM_CAMERA_PRESET = 0
    CLEAR = 1


@packet(id=321, since=776)
class ClientCameraAimAssistPacket:
    camera_preset_id: str
    action: ClientCameraAimAssistPacketAction = field(type=uint8)
    allow_aim_assist: bool


class CameraAimAssistPresetsPacketOperation(IntEnum):
    SET = 0
    ADD_TO_EXISTING = 1


class CameraAimAssistCategoryDefinition:
    name: str
    entity_priorities: dict[str, int32]
    block_priorities: dict[str, int32]
    block_tag_priorities: dict[str, int32] = field(since=898)
    entity_type_families_priorities: dict[str, int32] = field(since=924)
    entity_default: int32 | None
    block_default: int32 | None


# SharedTypes::v1_21_120::CameraAimAssistPresetDefinition. The wire form
# spreads the BDS-side mExclusionSettings sub-struct across the preset's top
# level. Pre-v776 the wire prefix also carried a category-reference string;
# pre-v898 the exclusion list was a single combined list rather than split
# into block/entity/block-tag.
class CameraAimAssistPresetDefinition:
    identifier: str
    # COMPILER_EXTENSION_NEEDED: v766..v776 prepended a `categories` string here
    # that was removed at v776, and v766..v898 wrote a single `exclusion_list`
    # instead of the v898 split into block/entity/block_tag/entity_type_families
    # exclusion lists (and v924 added the entity_type_families list). Three
    # distinct preset layouts in this window cannot share one field list -- the
    # DSL has no way to redeclare a variable-arity field block across version
    # intervals. The v975 form is modelled below.
    block_exclusion_list: list[str] = field(since=898)
    entity_exclusion_list: list[str] = field(since=898)
    block_tag_exclusion_list: list[str] = field(since=898)
    entity_type_families_exclusion_list: list[str] = field(since=924)
    liquid_targeting_list: list[str]
    item_settings: dict[str, str]
    default_item_settings: str | None
    hand_settings: str | None


@packet(id=320, since=766)
class CameraAimAssistPresetsPacket:
    """Sent by the server to clients for initializing and updating the client aim-assist registry. AddToExisting
    operations are sent by the server when new presets/categories are added to the registry through creator facing
    APIs."""

    # v766..v800 wrote a `CameraAimAssistCategories` wrapper (an identifier +
    # nested list of categories) BEFORE the presets. At v800 the outer shape
    # flattened: the packet writes a flat list of CameraAimAssistCategoryDefinition
    # followed by the presets, then the one-byte operation. The pre-v800 wrapper
    # has no useful in-memory analogue and is left as a compiler-extension TODO.
    categories: list[CameraAimAssistCategoryDefinition] = field(since=800)
    presets: list[CameraAimAssistPresetDefinition]
    operation: CameraAimAssistPresetsPacketOperation = field(type=uint8, since=776)


# BDS namespace CameraInstructionOptions holds the per-instruction option
# structs that CameraInstruction aggregates. Hoisted to top-level here because
# the DSL forbids nested classes whose version-gated declaration leaves the
# enclosing namespace empty on pre-since snapshots.
class CameraInstructionSetEaseOption:
    # COMPILER_EXTENSION_NEEDED (since=944): the easing type is written as the
    # serialize-name string on v944+ rather than the EasingType ordinal byte
    # used in v618..v944. The v944+ shape is the byte form modelled here.
    easing_type: uint8
    easing_time: float


class CameraInstructionSet:
    preset_index: uint32
    ease: CameraInstructionSetEaseOption | None
    pos: Vec3 | None
    rot: Vec2 | None
    facing: Vec3 | None
    view_offset: Vec2 | None = field(since=748)
    entity_offset: Vec3 | None = field(since=748)
    default_settings: bool | None  # BDS: mDefault; renamed to avoid C++ keyword.
    remove_ignore_starting_values_component: bool = field(since=818)


class CameraInstructionFadeTimeOption:
    fade_in_time: float
    hold_time: float
    fade_out_time: float


class CameraInstructionFadeColorOption:
    red: float
    green: float
    blue: float


class CameraInstructionFade:
    time: CameraInstructionFadeTimeOption | None
    color: CameraInstructionFadeColorOption | None


class CameraInstructionTarget:
    target_center_offset: Vec3 | None
    target_actor_id: int64


class CameraInstructionFov:
    fov: float
    fov_ease_time: float
    # COMPILER_EXTENSION_NEEDED (since=944): the ease type switched from a
    # one-byte EasingType ordinal to the serialize-name string of the easing
    # function. Same DSL gap as CameraInstructionSetEaseOption.easing_type
    # above.
    fov_ease_type: uint8
    fov_clear: bool


class CameraInstructionAttachToEntity:
    attach_to_entity_id: int64


class SplineType(IntEnum):
    CATMULL_ROM = 0
    LINEAR = 1


class EasingType(IntEnum):
    LINEAR = 0
    SPRING = 1
    IN_QUAD = 2
    OUT_QUAD = 3
    IN_OUT_QUAD = 4
    IN_CUBIC = 5
    OUT_CUBIC = 6
    IN_OUT_CUBIC = 7
    IN_QUART = 8
    OUT_QUART = 9
    IN_OUT_QUART = 10
    IN_QUINT = 11
    OUT_QUINT = 12
    IN_OUT_QUINT = 13
    IN_SINE = 14
    OUT_SINE = 15
    IN_OUT_SINE = 16
    IN_EXPO = 17
    OUT_EXPO = 18
    IN_OUT_EXPO = 19
    IN_CIRC = 20
    OUT_CIRC = 21
    IN_OUT_CIRC = 22
    IN_BOUNCE = 23
    OUT_BOUNCE = 24
    IN_OUT_BOUNCE = 25
    IN_BACK = 26
    OUT_BACK = 27
    IN_OUT_BACK = 28
    IN_ELASTIC = 29
    OUT_ELASTIC = 30
    IN_OUT_ELASTIC = 31


# Gophertunnel's CameraRotationOption / CameraProgressOption are written as
# (value, time, easing_type-as-string) triples. The DSL spelling below keeps
# easing_type as a string because v944+ wired it that way; the byte-ordinal
# form before v944 is not modelled.
class CameraRotationOption:
    value: Vec3
    time_seconds: float
    ease_type: str


class CameraProgressOption:
    value: float
    time_seconds: float
    ease_type: str


# CameraInstructionPacket.camera_instruction.spline carries the
# CameraSplineInstruction shape from gophertunnel (TotalTime + Optional<u8>
# spline_type + curve points + per-axis keyframes + identifier + load_from_json).
class SplineInstruction:
    total_time: float
    spline_type: uint8 | None
    curve: list[Vec3]
    progress_key_frames: list[CameraProgressOption]
    rotation_options: list[CameraRotationOption]
    spline_identifier: str | None
    load_from_json: bool | None


class CameraInstruction:
    # COMPILER_EXTENSION_NEEDED (until=618): the v575 codec wrapped the entire
    # packet body in a single CompoundTag (`set`, `clear`, `fade` keys with
    # nested compounds for ease/pos/rot/color/time). v618 replaced the NBT
    # wrapper with the inline binary optional layout below. The pre-v618 NBT
    # form is left modelled only by these notes.
    set: CameraInstructionSet | None
    clear: bool | None
    fade: CameraInstructionFade | None
    target: CameraInstructionTarget | None = field(since=712)
    remove_target: bool | None = field(since=712)
    field_of_view: CameraInstructionFov | None = field(since=827)
    spline: SplineInstruction | None = field(since=859)
    attach_to_entity: CameraInstructionAttachToEntity | None = field(since=859)
    detach_from_entity: bool | None = field(since=859)


@packet(id=300, since=575)
class CameraInstructionPacket:
    """Used to send a CameraInstruction from the server to the specified clients."""

    camera_instruction: CameraInstruction = field(since=618)


class ControlSchemeScheme(IntEnum):
    LOCKED_PLAYER_RELATIVE_STRAFE = 0
    CAMERA_RELATIVE = 1
    CAMERA_RELATIVE_STRAFE = 2
    PLAYER_RELATIVE = 3
    PLAYER_RELATIVE_STRAFE = 4


class CameraAimAssistCommandPresetDefinition:
    preset_id: str | None
    target_mode: int32 | None
    angle: Vec2 | None
    distance: float | None


class CameraPresetAudioListener(IntEnum):
    CAMERA = 0
    PLAYER = 1


class CameraPreset:
    name: str
    inherit_from: str
    pos_x: float | None
    pos_y: float | None
    pos_z: float | None
    rot_x: float | None  # pitch
    rot_y: float | None  # yaw
    rotation_speed: float | None = field(since=729)
    snap_to_target: bool | None = field(since=729)
    horizontal_rotation_limit: Vec2 | None = field(since=748)
    vertical_rotation_limit: Vec2 | None = field(since=748)
    continue_targeting: bool | None = field(since=748)
    block_listening_radius: float | None = field(since=766)
    view_offset: Vec2 | None = field(since=712)
    entity_offset: Vec3 | None = field(since=729)
    radius: float | None = field(since=712)
    yaw_limit_min: float | None = field(since=776)
    yaw_limit_max: float | None = field(since=776)
    listener: CameraPresetAudioListener | None = field(type=uint8)
    player_effects: bool | None
    align_target_and_camera_forward: bool | None = field(since=748, until=818)
    aim_assist: CameraAimAssistCommandPresetDefinition | None = field(since=766)
    control_scheme: ControlSchemeScheme | None = field(type=uint8, since=800)


@packet(id=198, since=575)
class CameraPresetsPacket:
    """Used to sync CameraPresets data from server to clients."""

    # COMPILER_EXTENSION_NEEDED: the v575 wire form bundled every preset into a
    # single root CompoundTag (key "presets" -> list of compound presets), where
    # each preset compound carried optional numeric keys -- pos_x/pos_y/pos_z,
    # rot_x, rot_y -- only when the in-memory field was non-null. The DSL has
    # no surface for "the tag's child keys are themselves the optional-field
    # projection of a struct", so the v575..v618 era is left as a hand-rolled
    # CompoundTag payload and the modern list-of-CameraPreset is gated since
    # v618.
    legacy_definition: CompoundTag = field(since=575, until=618)
    presets: list[CameraPreset] = field(since=618)


class CameraShakeType(IntEnum):
    POSITIONAL = 0
    ROTATIONAL = 1


class CameraShakeAction(IntEnum):
    ADD = 0
    STOP = 1


@packet(id=159, since=419)
class CameraShakePacket:
    """Used to control trigger camera shake movements on the client's player camera. It may be used to queue or stop a
    camera shake."""

    intensity: float
    seconds: float
    shake_type: CameraShakeType = field(type=uint8)
    shake_action: CameraShakeAction = field(type=uint8, since=428)


class CameraSplineControlPoint:
    position: Vec3


class CameraSplineDefinition:
    name: str
    total_time: float
    spline_type: str | None
    spline_control_points: list[CameraSplineControlPoint]
    spline_progress_frames: list[CameraProgressOption]
    spline_rotation_frames: list[CameraRotationOption]


@packet(id=338, since=924)
class CameraSplinePacket:
    """Camera custom spline data sent from server to client."""

    splines: list[CameraSplineDefinition]
