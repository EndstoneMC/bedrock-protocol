"""The legacy inventory transaction family: world/inventory/transaction/ --
sources, actions, and the four transaction shapes.
Not container state -- world/containers/, in inventory.py."""

from enum import IntEnum
from typing import Literal

from protocol import field, packet, type, uint8, uint32, uvarint32, varint32
from protocol.actor import ActorRuntimeID
from protocol.common import BlockPos, Vec3
from protocol.inventory import ContainerEnumName, ContainerID, HandSlot
from protocol.item import NetworkItemStackDescriptor, SerializedNetworkItemStackDescriptor

package = "bedrock.protocol"


class InventorySourceType(IntEnum, uint32):
    INVALID_INVENTORY = -1
    CONTAINER_INVENTORY = 0
    GLOBAL_INVENTORY = 1
    WORLD_INTERACTION = 2
    CREATIVE_INVENTORY = 3
    NON_IMPLEMENTED_FEATURE_TODO = 99999


class LegacySetSlot:
    container_enum: ContainerEnumName
    slots: bytes


@type(until=1001)
class InventorySource:
    class InventorySourceFlags(IntEnum, uint32):
        NO_FLAG = 0
        WORLD_INTERACTION_RANDOM = 1

    type: InventorySourceType
    container_id: ContainerID = field(
        type=varint32,
        when=lambda s: (
            s.type in {InventorySourceType.CONTAINER_INVENTORY, InventorySourceType.NON_IMPLEMENTED_FEATURE_TODO}
        ),
    )
    flags: InventorySourceFlags = field(when=lambda s: s.type == InventorySourceType.WORLD_INTERACTION)


@type(since=1001)
class InventorySource:
    class InventorySourceFlags(IntEnum, uint32):
        NO_FLAG = 0
        WORLD_INTERACTION_RANDOM = 1

    type: InventorySourceType
    _true_1: Literal[True] = field(until=2192)
    container_id: ContainerID | None
    _true_2: Literal[True] = field(until=2192)
    flags: InventorySourceFlags | None


@type(until=1001)
class InventoryAction:
    source: InventorySource
    slot: uvarint32
    from_item_descriptor: NetworkItemStackDescriptor
    to_item_descriptor: NetworkItemStackDescriptor


@type(since=1001)
class InventoryAction:
    source: InventorySource
    slot: uvarint32
    from_item_descriptor: SerializedNetworkItemStackDescriptor
    to_item_descriptor: SerializedNetworkItemStackDescriptor


class InventoryTransaction:
    _true: Literal[True] = field(since=1001, until=2192)
    actions: list[InventoryAction]


class NormalTransactionData:
    transaction: InventoryTransaction


class InventoryMismatchData:
    transaction: InventoryTransaction


@type(until=1001)
class ItemUseInventoryTransaction:
    class ActionType(IntEnum):
        PLACE = 0
        USE = 1
        DESTROY = 2
        USE_AS_ATTACK = 3

    class TriggerType(IntEnum, uint8):
        UNKNOWN = 0
        PLAYER_INPUT = 1
        SIMULATION_TICK = 2

    class PredictedResult(IntEnum, uint8):
        FAILURE = 0
        SUCCESS = 1

    class ClientCooldownState(IntEnum, uint8):
        OFF = 0
        ON = 1

    transaction: InventoryTransaction
    action_type: ActionType = field(type=uvarint32)
    trigger_type: TriggerType
    pos: BlockPos
    face: varint32
    slot: varint32
    item: NetworkItemStackDescriptor
    from_pos: Vec3
    click_pos: Vec3
    target_block_id: uvarint32
    client_predicted_result: PredictedResult = field(type=uvarint32)
    client_cooldown_state: ClientCooldownState


@type(since=1001)
class ItemUseInventoryTransaction:
    class ActionType(IntEnum):
        PLACE = 0
        USE = 1
        DESTROY = 2
        USE_AS_ATTACK = 3

    class TriggerType(IntEnum, uint8):
        UNKNOWN = 0
        PLAYER_INPUT = 1
        SIMULATION_TICK = 2

    class PredictedResult(IntEnum, uint8):
        FAILURE = 0
        SUCCESS = 1

    class ClientCooldownState(IntEnum, uint8):
        OFF = 0
        ON = 1

    transaction: InventoryTransaction
    action_type: ActionType
    trigger_type: TriggerType
    pos: BlockPos
    face: uint8
    slot: varint32
    hand: HandSlot = field(since=2192)
    item: SerializedNetworkItemStackDescriptor
    from_pos: Vec3
    click_pos: Vec3
    target_block_id: uvarint32
    client_predicted_result: PredictedResult
    client_cooldown_state: ClientCooldownState


@type(cereal=False, until=1001)
class ItemUseInventoryTransaction:
    """The shape PlayerAuthInputPacket writes: that packet did not cerealise until
    2168, so its transaction keeps the pre-cereal framing -- the action list carries
    no member-present marker and `face` stays a varint32 -- while its leaves
    cerealise at 1001 with everything else."""

    actions: list[InventoryAction]
    action_type: ItemUseInventoryTransaction.ActionType = field(type=uvarint32)
    trigger_type: ItemUseInventoryTransaction.TriggerType
    pos: BlockPos
    face: varint32
    slot: varint32
    item: NetworkItemStackDescriptor
    from_pos: Vec3
    click_pos: Vec3
    target_block_id: uvarint32
    client_predicted_result: ItemUseInventoryTransaction.PredictedResult = field(type=uvarint32)
    client_cooldown_state: ItemUseInventoryTransaction.ClientCooldownState


@type(cereal=False, since=1001)
class ItemUseInventoryTransaction:
    actions: list[InventoryAction]
    action_type: ItemUseInventoryTransaction.ActionType = field(type=uvarint32)
    trigger_type: ItemUseInventoryTransaction.TriggerType
    pos: BlockPos
    face: varint32
    slot: varint32
    item: SerializedNetworkItemStackDescriptor
    from_pos: Vec3
    click_pos: Vec3
    target_block_id: uvarint32
    client_predicted_result: ItemUseInventoryTransaction.PredictedResult
    client_cooldown_state: ItemUseInventoryTransaction.ClientCooldownState


@type(until=1001)
class ItemUseOnActorInventoryTransaction:
    class ActionType(IntEnum):
        INTERACT = 0
        ATTACK = 1
        ITEM_INTERACT = 2

    transaction: InventoryTransaction
    runtime_id: ActorRuntimeID
    action_type: ActionType = field(type=uvarint32)
    slot: varint32
    item: NetworkItemStackDescriptor
    from_pos: Vec3
    hit_pos: Vec3


@type(since=1001)
class ItemUseOnActorInventoryTransaction:
    class ActionType(IntEnum):
        INTERACT = 0
        ATTACK = 1
        ITEM_INTERACT = 2

    transaction: InventoryTransaction
    runtime_id: ActorRuntimeID
    action_type: ActionType
    slot: varint32
    item: SerializedNetworkItemStackDescriptor
    from_pos: Vec3
    hit_pos: Vec3


@type(until=1001)
class ItemReleaseInventoryTransaction:
    class ActionType(IntEnum):
        RELEASE = 0
        USE = 1

    transaction: InventoryTransaction
    action_type: ActionType = field(type=uvarint32)
    slot: varint32
    item: NetworkItemStackDescriptor
    from_pos: Vec3


@type(since=1001)
class ItemReleaseInventoryTransaction:
    class ActionType(IntEnum):
        RELEASE = 0
        USE = 1

    transaction: InventoryTransaction
    action_type: ActionType
    slot: varint32
    item: SerializedNetworkItemStackDescriptor
    from_pos: Vec3


type TransactionData = (
    NormalTransactionData
    | InventoryMismatchData
    | ItemUseInventoryTransaction
    | ItemUseOnActorInventoryTransaction
    | ItemReleaseInventoryTransaction
)


@packet(id=30, until=1001)
class InventoryTransactionPacket:
    legacy_request_id: varint32
    legacy_set_item_slots: list[LegacySetSlot] = field(when=lambda p: p.legacy_request_id != 0)
    transaction: TransactionData


@packet(id=30, since=1001)
class InventoryTransactionPacket:
    legacy_request_id: varint32
    legacy_set_item_slots: list[LegacySetSlot] | None
    _true: Literal[True] = field(until=2192)
    transaction: TransactionData
