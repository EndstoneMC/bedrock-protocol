"""Emit JSON values that hit every path of a packet at a protocol version, and round-trip them through the binding."""

import argparse
import base64
import dataclasses
import functools
import importlib
import json
import re
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from bedrock_protocol_compiler.builder import build
from bedrock_protocol_compiler.descriptor import (
    AliasRef,
    Array,
    Binary,
    Bitset,
    BuiltinRef,
    EnumName,
    EnumRef,
    Expression,
    Field,
    FieldRef,
    Int,
    Len,
    List,
    Literal,
    Map,
    MemberRef,
    Not,
    Optional,
    Primitive,
    Struct,
    StructRef,
    Test,
    Type,
    Variant,
)
from bedrock_protocol_compiler.schema import EnumShape, Schema, StructShape

Json = Any
Point = tuple[str, str]

PROTOCOL_DIR = Path(__file__).resolve().parents[2] / "protocol"
MAX_DEPTH = 6
INTEGER_BITS = {
    "int8": (8, True),
    "int16": (16, True),
    "int32": (32, True),
    "int64": (64, True),
    "uint8": (8, False),
    "uint16": (16, False),
    "uint32": (32, False),
    "uint64": (64, False),
    "varint32": (32, True),
    "varint64": (64, True),
    "uvarint32": (32, False),
    "uvarint64": (64, False),
}
ALTERNATIVE_BY_PRIMITIVE = {"bool": "bool", "float": "float", "double": "float", "str": "str", "bytes": "bytes"}
NBT_TAGS = {
    "b": {"ByteTag": 7},
    "bytes": {"ByteArrayTag": [1, 254, 3]},
    "d": {"DoubleTag": 2.5},
    "f": {"FloatTag": 1.5},
    "i": {"IntTag": 70000},
    "ints": {"IntArrayTag": [4, -5, 6]},
    "l": {"Int64Tag": 5000000000},
    "list": {"ListTag": {"type": 3, "tags": [{"IntTag": 1}, {"IntTag": 2}]}},
    "nested": {"CompoundTag": {"k": {"StringTag": "v"}}},
    "s": {"ShortTag": 300},
    "str": {"StringTag": "text"},
}
NBT_TYPES = {
    "ByteTag": 1,
    "ShortTag": 2,
    "IntTag": 3,
    "Int64Tag": 4,
    "FloatTag": 5,
    "DoubleTag": 6,
    "ByteArrayTag": 7,
    "StringTag": 8,
    "ListTag": 9,
    "CompoundTag": 10,
    "IntArrayTag": 11,
}
SAME_MEMBER = {
    "PlayerVideoCapturePacket.stop_video_capture": "start_video_capture",
    "ClientboundUpdateSoundDataPacket.set_volume": "stop",
    "ClientboundUpdateSoundDataPacket.set_pitch": "stop",
    "ClientboundUpdateSoundDataPacket.fade": "stop",
    "ClientboundUpdateSoundDataPacket.seek_to": "stop",
    "ClientboundUpdateSoundDataPacket.pause": "stop",
    "ClientboundUpdateSoundDataPacket.resume": "stop",
    "CylinderDataPayload.radius_z": "radius_x",
}
PRESENT_WHEN: dict[str, tuple[str, ...] | Expression] = {
    "ItemStackResponseInfo.containers": ("result", "SUCCESS"),
    "MapItemTrackedActor.UniqueId.key_entity_id": ("type", "ENTITY"),
    "MapItemTrackedActor.UniqueId.key_block_pos": ("type", "BLOCK_ENTITY"),
    "InventorySource.container_id": ("type", "CONTAINER_INVENTORY", "NON_IMPLEMENTED_FEATURE_TODO"),
    "InventorySource.flags": ("type", "WORLD_INTERACTION"),
    "PlayerAuthInputPacket.item_use_transaction": ("input_data", "PERFORM_ITEM_INTERACTION"),
    "PlayerAuthInputPacket.item_stack_request": ("input_data", "PERFORM_ITEM_STACK_REQUEST"),
    "PlayerAuthInputPacket.player_block_actions": ("input_data", "PERFORM_BLOCK_ACTIONS"),
    "PlayerAuthInputPacket.vehicle_rot": ("input_data", "IS_IN_CLIENT_PREDICTED_VEHICLE"),
    "PlayerAuthInputPacket.client_predicted_vehicle": ("input_data", "IS_IN_CLIENT_PREDICTED_VEHICLE"),
    "ItemStackResponseSlotInfo.item_stack_net_id": Binary("!=", FieldRef("amount"), Int(0)),
    "InventoryTransactionPacket.legacy_set_item_slots": Binary(
        "and",
        Binary("<", FieldRef("legacy_request_id.raw_id"), Int(-1)),
        Binary("==", Binary("&", FieldRef("legacy_request_id.raw_id"), Int(1)), Int(0)),
    ),
    "PackedItemUseLegacyInventoryTransaction.slots": Binary(
        "and",
        Binary("<", FieldRef("id.raw_id"), Int(-1)),
        Binary("==", Binary("&", FieldRef("id.raw_id"), Int(1)), Int(0)),
    ),
}
LEVEL_GAME_RULES = (
    ("commandBlockOutput", {"bool": True}),
    ("doDayLightCycle", {"bool": True}),
    ("doEntityDrops", {"bool": True}),
    ("doFireTick", {"bool": True}),
    ("recipesUnlock", {"bool": True}),
    ("doLimitedCrafting", {"bool": False}),
    ("doMobLoot", {"bool": True}),
    ("doMobSpawning", {"bool": True}),
    ("doTileDrops", {"bool": True}),
    ("doWeatherCycle", {"bool": True}),
    ("drowningDamage", {"bool": True}),
    ("fallDamage", {"bool": True}),
    ("fireDamage", {"bool": True}),
    ("keepInventory", {"bool": False}),
    ("mobGriefing", {"bool": True}),
    ("pvp", {"bool": True}),
    ("showCoordinates", {"bool": False}),
    ("playerWaypoints", {"int": 1}),
    ("locatorbar", {"bool": True}),
    ("showDaysPlayed", {"bool": False}),
    ("naturalRegeneration", {"bool": True}),
    ("tntExplodes", {"bool": True}),
    ("sendCommandFeedback", {"bool": True}),
    ("maxCommandChainLength", {"int": 65535}),
    ("doInsomnia", {"bool": True}),
    ("commandBlocksEnabled", {"bool": True}),
    ("randomTickSpeed", {"int": 1}),
    ("doImmediateRespawn", {"bool": False}),
    ("showDeathMessages", {"bool": True}),
    ("functionCommandLimit", {"int": 10000}),
    ("spawnRadius", {"int": 10}),
    ("showTags", {"bool": True}),
    ("freezeDamage", {"bool": True}),
    ("respawnBlocksExplode", {"bool": True}),
    ("showBorderEffect", {"bool": True}),
    ("showRecipeMessages", {"bool": True}),
    ("playersSleepingPercentage", {"int": 100}),
    ("projectilesCanBreakBlocks", {"bool": True}),
    ("tntExplosionDropDecay", {"bool": False}),
)
IDENTITY_KEY = (
    "MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEGnLhvg+WqN8j3xJnLCZK/PoGAUwz7OjIA9p+jOYoJMhr80BZVXxHSItC/jzAZ+PVaM/Z"
    "Aulb1nqVerFL2+gkoZiekpbWsnmevndov/3yGeZbxnvSNYksW3qhRKZ7eUbD"
)
GEOMETRY = (
    '{"format_version":"1.12.0","minecraft:geometry":[{"bones":[{"name":"body","pivot":[0.0,24.0,0.0]}],'
    '"description":{"identifier":"geometry.golden","texture_height":32,"texture_width":64}}]}\n'
)
PIXELS = bytes(range(256)) * 32
PLAYER_CLIENT_DATA: dict[str, Json] = {
    "AnimatedImageData": [
        {
            "AnimationExpression": 1,
            "Frames": 2.0,
            "Image": base64.b64encode(PIXELS).decode(),
            "ImageHeight": 64,
            "ImageWidth": 32,
            "Type": 1,
        }
    ],
    "ArmSize": "wide",
    "CapeData": "",
    "CapeId": "",
    "CapeImageHeight": 0,
    "CapeImageWidth": 0,
    "CapeOnClassicSkin": False,
    "ClientRandomId": 1234567890123,
    "CompatibleWithClientSideChunkGen": False,
    "CurrentInputMode": 1,
    "DefaultInputMode": 1,
    "DeviceId": "0123456789abcdef0123456789abcdef",
    "DeviceModel": "Golden Desktop",
    "DeviceOS": 8,
    "GameVersion": "1.26.40",
    "GuiScale": 0,
    "LanguageCode": "en_US",
    "PersonaPieces": [
        {
            "IsDefault": True,
            "PackId": "11111111-2222-4333-8444-555555555555",
            "PieceId": "66666666-7777-4888-9999-aaaaaaaaaaaa",
            "PieceType": "persona_body",
            "ProductId": "",
        }
    ],
    "PersonaSkin": False,
    "PieceTintColors": [{"Colors": ["#ff1a1a1a", "#ff2b2b2b", "#ff3c3c3c", "#0"], "PieceType": "persona_eyes"}],
    "PlatformOfflineId": "",
    "PlatformOnlineId": "",
    "PlayFabId": "abcdef0123456789",
    "PremiumSkin": False,
    "SelfSignedId": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
    "ServerAddress": "127.0.0.1:19132",
    "SkinAnimationData": "",
    "SkinColor": "#0",
    "SkinData": base64.b64encode(PIXELS).decode(),
    "SkinGeometryData": base64.b64encode(GEOMETRY.encode()).decode(),
    "SkinGeometryDataEngineVersion": base64.b64encode(b"1.21.0").decode(),
    "SkinId": "c18e65aa-7b21-4637-9b63-8ad63622ef01.Custom",
    "SkinImageHeight": 32,
    "SkinImageWidth": 64,
    "SkinResourcePatch": base64.b64encode(b'{"geometry":{"default":"geometry.golden"}}').decode(),
    "ThirdPartyName": "GoldenPlayer",
    "TrustedSkin": True,
}
GUEST_CLIENT_DATA = PLAYER_CLIENT_DATA | {
    "AnimatedImageData": [],
    "ArmSize": "slim",
    "ClientRandomId": 2345678901234,
    "CurrentInputMode": 2,
    "DefaultInputMode": 2,
    "DeviceId": "fedcba9876543210fedcba9876543210",
    "DeviceModel": "Golden Console",
    "DeviceOS": 13,
    "PersonaPieces": [],
    "PieceTintColors": [],
    "PlayFabId": "9876543210fedcba",
    "SelfSignedId": "bbbbbbbb-cccc-4ddd-8eee-ffffffffffff",
    "SkinData": base64.b64encode(PIXELS * 2).decode(),
    "SkinId": "d29f76bb-8c32-4748-8c74-9be74733f012.Custom",
    "SkinImageHeight": 64,
    "ThirdPartyName": "GoldenGuest",
}


def web_token(claims: dict[str, Json], signature: bytes) -> str:
    """Join an ES384 header naming IDENTITY_KEY, the claims and a signature into a compact JWT."""
    header = {"alg": "ES384", "x5u": IDENTITY_KEY}
    segments = [json.dumps(each, separators=(",", ":")).encode() for each in (header, claims)] + [signature]
    return ".".join(base64.urlsafe_b64encode(each).rstrip(b"=").decode() for each in segments)


def connection_request(authentication: int, token: str, client: dict[str, Json], signature: bytes) -> str:
    """Frame the authentication JSON as BDS writes it and a client-data JWT, each behind its uint32-LE length."""
    parts = [json.dumps({"AuthenticationType": authentication, "Token": token}, separators=(",", ":")) + "\n"]
    parts.append(web_token(client, signature))
    return b"".join(len(each).to_bytes(4, "little") + each.encode() for each in parts).hex()


GAME_TOKEN = web_token(
    {"cpk": IDENTITY_KEY, "exp": 1767225600, "iat": 1767222000, "xid": "2535428000000000", "xname": "GoldenPlayer"},
    bytes(range(96)),
)
ITEM_STACKS = ("SerializedNetworkItemStackDescriptor", "SerializedNetworkItemInstanceDescriptor")
ITEMS: dict[int, dict[int, int | None]] = {2168: {462: None, 855: None, -593: 0}}
MEMBERS_SINCE: dict[int, dict[str, tuple[str, ...]]] = {
    898: {"CommandOriginData.type": ("PLAYER", "DEV_CONSOLE", "TEST", "AUTOMATION_PLAYER")},
    924: {
        "TextPacket.MessageOnly.type": (
            "RAW",
            "TIP",
            "SYSTEM_MESSAGE",
            "TEXT_OBJECT_WHISPER",
            "TEXT_OBJECT",
            "TEXT_OBJECT_ANNOUNCEMENT",
        ),
        "TextPacket.AuthorAndMessage.type": ("CHAT", "WHISPER", "ANNOUNCEMENT"),
        "TextPacket.MessageAndParams.type": ("TRANSLATE", "POPUP", "JUKEBOX_POPUP"),
    },
    2168: {"PlayerListPacket.RemoveEntry.action": ("REMOVE",), "PlayerListPacket.AddEntry.action": ("ADD",)},
}
FIXED_AT: dict[int, dict[str, Json]] = {
    2168: {
        "SerializedRecipeIngredient.descriptor": {"name": "minecraft:apple"},
        "ItemStackRequestCereal.NetworkItemInstanceDescriptorData.item_descriptor": {
            "ItemNameDescriptorData": {"full_name": "minecraft:stick", "aux_value": 7}
        },
    },
}
KEPT_FORMS: dict[str, tuple[str, ...]] = {
    "AddVolumeEntityPacket.min_engine_version": ("1.21.0-beta.1+build.5", "1.21.0"),
    "SerializedSkinRef.geometry_data_min_engine_version": ("1.21.0-beta.1+build.5", "1.21.0"),
    "ResourcePackStackPacket.base_game_version": ("*", "1.21.0"),
    "LevelSettings.base_game_version": ("*", "1.21.0"),
}
FIXED: dict[str, Json] = {
    "SerializedNetworkItemStackDescriptor.stack_size": 3,
    "SerializedNetworkItemInstanceDescriptor.stack_size": 4,
    "ItemStackRequestCereal.NetworkItemInstanceDescriptorData.stack_size": 5,
    "SerializedRecipeIngredient.stack_size": 2,
    "SerializedRecipeIngredient.aux_value": 6,
    "ItemStackRequestCereal.ItemNameDescriptorData.aux_value": 7,
    "ItemStackRequestCereal.TakeActionData.amount": 2,
    "ItemStackRequestCereal.PlaceActionData.amount": 2,
    "ItemStackRequestCereal.DropActionData.amount": 2,
    "ItemStackRequestCereal.DestroyActionData.amount": 2,
    "ItemStackRequestCereal.ConsumeActionData.amount": 2,
    "ItemStackRequestCereal.BeaconPaymentActionData.primary_effect_id": 1,
    "ItemStackRequestCereal.BeaconPaymentActionData.secondary_effect_id": 10,
    "ItemStackRequestCereal.CraftRepairAndDisenchantActionData.repair_cost": 5,
    "LevelChunkPacket.sub_chunks_count": 4,
    "LevelChunkPacket.client_request_sub_chunk_limit?": 8,
    "CameraAimAssistPacket.distance": 8.0,
    "CameraAimAssistCategoryPriorities.entities{v}": 10,
    "CameraAimAssistCategoryPriorities.blocks{v}": 20,
    "CameraAimAssistCategoryPriorities.block_tags{v}": 30,
    "CameraAimAssistCategoryPriorities.entity_type_families{v}": 40,
    "CameraAimAssistCategoryPriorities.entity_default?": 50,
    "CameraAimAssistCategoryPriorities.block_default?": 60,
    "CameraSplineProgressKeyFrame.alpha": 0.5,
    "SkinImage.width": 64,
    "SkinImage.height": 32,
    "ItemStackRequestId.raw_id": -5,
    "CameraAimAssistPacket.view_angle": {"x": 45.5, "y": 30.25},
    "CameraSplineDefinition.name": "test:spline",
    "CameraSplineDefinition.spline_type": "linear",
    "ServerToClientHandshakePacket.token": web_token(
        {"salt": base64.b64encode(bytes(range(16))).decode()}, bytes(range(48, 144))
    ),
    "ModalFormRequestPacket.form_json": (
        '{"type":"form","title":"Golden","content":"Pick one",'
        '"buttons":[{"text":"Yes"},{"text":"No","image":{"type":"path","data":"textures/ui/cancel"}}]}'
    ),
    "ModalFormResponsePacket.json_response?": '[true,"Steve",3,2.50,-1.0]\n',
    "ServerSettingsResponsePacket.form_json": (
        '{"type":"custom_form","title":"Golden settings","content":['
        '{"type":"toggle","text":"Particles","default":true},'
        '{"type":"slider","text":"Volume","min":0,"max":10,"step":1,"default":5}]}'
    ),
    "AddBehaviorTreePacket.json_input": (
        '{"format_version":"1.10.0","minecraft:behavior_tree":{"description":{"identifier":"golden:tree"},'
        '"root":{"sequence":[{"move_to":{"position":[1,2,3]}},{"wait":{"duration":1.5}}]}}}'
    ),
    "FeatureRegistry.FeatureBinaryJsonFormat.binary_json_output": (
        '{"format_version":"1.13.0","minecraft:single_block_feature":{"description":{"identifier":"golden:stone"},'
        '"places_block":"minecraft:stone","enforce_placement_rules":false,"enforce_survivability_rules":false}}'
    ),
    "SerializedSkinRef.geometry_data": GEOMETRY,
    "NpcDialoguePacket.action_json": (
        '[{"button_name":"Greet","data":[{"cmd_line":"say hi","cmd_ver":42}],"mode":0,"text":"say hi","type":1},'
        '{"button_name":"Docs","data":null,"mode":0,"text":"https://minecraft.net","type":0}]'
    ),
    "AvailableActorIdentifiersPacket.identifier_list": {
        "idlist": {
            "ListTag": {
                "type": 10,
                "tags": [
                    {
                        "CompoundTag": {
                            "bid": {"StringTag": "minecraft:"},
                            "hasspawnegg": {"ByteTag": 1},
                            "id": {"StringTag": "minecraft:pig"},
                            "rid": {"IntTag": 1},
                            "summonable": {"ByteTag": 1},
                        }
                    }
                ],
            }
        }
    },
    "SpawnParticleEffectPacket.molang_variables?": (
        '[{"name":"variable.size","value":{"type":"float","value":1.50}},'
        '{"name":"variable.direction","value":{"type":"member_array","value":['
        '{"name":".x","value":{"type":"float","value":0.50}},{"name":".y","value":{"type":"float","value":-1.0}},'
        '{"name":".z","value":{"type":"float","value":2.0}}]}}]\n'
    ),
    "SemVersion.version": "1.2.3",
    "PackInstanceId.version": "2.3.4",
    "ExperimentToggle.name": "gametest",
    "ExperimentToggle.enabled": True,
    "Experiments.experiments_ever_toggled": True,
    "LoginPacket.connection_request": connection_request(0, GAME_TOKEN, PLAYER_CLIENT_DATA, bytes(range(96, 192))),
    "SubClientLoginPacket.connection_request": connection_request(1, "", GUEST_CLIENT_DATA, bytes(range(160, 256))),
    "AgentActionEventPacket.response": (
        '{"action":"move","direction":[1,-2],"result":{"block":"minecraft:stone","distance":2.50,'
        '"position":[0.10,-1.0,1000.0]},"success":true,"tick":12345678901234,"tool":null,"user":"Agent \u00e9/"}\n'
    ),
    "Color255RGBA.r": 16,
    "Color255RGBA.g": 32,
    "Color255RGBA.b": 64,
    "Color255RGBA.a": 128,
    "SerializableCells.x_size": 8,
    "SerializableCells.y_size": 2,
    "SerializableCells.z_size": 3,
    "SerializableCells.storage": [1, 2, 3, 4, 5, 6],
    "EffectDuration.value": 600,
    "NetworkStackLatencyPacket.create_time": 0,
    "ServerboundLoadingScreenPacket.serverbound_loading_screen_packet_type": "START_LOADING_SCREEN",
    "LevelSettings.game_rules": {
        "rules": [{"name": name, "can_be_modified_by_player": True, "value": value} for name, value in LEVEL_GAME_RULES]
    },
}


def integer_range(name: str, wire: str | None) -> tuple[int, int]:
    narrower = wire if wire in INTEGER_BITS and INTEGER_BITS[wire][0] < INTEGER_BITS[name][0] else name
    bits, signed = INTEGER_BITS[narrower]
    return (-(1 << (bits - 1)), (1 << (bits - 1)) - 1) if signed else (0, (1 << bits) - 1)


def tag_printed(tag: Json, path: str) -> list[list[Json]]:
    """List the scalars BDS's JSON prints for an NBT tag's payload in order, each as [key path, scalar]."""
    ((name, value),) = tag.items()
    match name:
        case "ByteArrayTag" | "IntArrayTag":
            return [[path, len(value)], *([f"{path}[{index}]", each] for index, each in enumerate(value))]
        case "ListTag":
            tags = [item for index, each in enumerate(value["tags"]) for item in tag_printed(each, f"{path}[{index}]")]
            return [[path, value["type"]], [path, len(value["tags"])], *tags]
        case "CompoundTag":
            found: list[list[Json]] = []
            for key in sorted(value):
                ((child, _),) = value[key].items()
                found += [[f"{path}.{key}", NBT_TYPES[child]], [f"{path}.{key}", key]]
                found += tag_printed(value[key], f"{path}.{key}")
            return [*found, [path, 0]]
    return [[path, value]]


class Generator:
    def __init__(self, schema: Schema, version: int) -> None:
        self.schema = schema
        self.version = version
        self.fixed = FIXED | FIXED_AT.get(version, {}) | {"LoginPacket.client_network_version": version}
        self.members = {
            key: members for since, table in MEMBERS_SINCE.items() if since <= version for key, members in table.items()
        }
        self.cursors: dict[str, int] = {}
        self.hits: set[Point] = set()
        self.counter = 0

    def label(self, shape: StructShape) -> str:
        names = []
        family: Struct | None = shape.family
        while family is not None:
            names.append(family.name)
            family = family.owner
        return ".".join(reversed(names))

    def shape(self, struct: Any) -> StructShape:
        shape = self.schema.shape_at(struct, self.version)
        if not isinstance(shape, StructShape):
            raise TypeError(f"{struct.name}: not a struct shape")
        return shape

    def numbers(self, enum: Any) -> dict[str, int]:
        shape = self.schema.shape_at(enum, self.version)
        if not isinstance(shape, EnumShape):
            raise TypeError(f"{enum.name}: not an enum shape")
        return shape.numbers

    def named(self, enum: Any) -> dict[int, str]:
        shape = self.schema.shape_at(enum, self.version)
        if not isinstance(shape, EnumShape):
            raise TypeError(f"{enum.name}: not an enum shape")
        names: dict[int, str] = {}
        for member in sorted(shape.members, key=lambda member: not isinstance(member.value, MemberRef | Binary)):
            if member.name in shape.numbers and member.name != "COUNT":
                names.setdefault(shape.numbers[member.name], member.name)
        return names

    def fields(self, shape: StructShape) -> list[Field]:
        label = self.label(shape)
        found: list[Field] = []
        for each in shape.fields:
            gate = PRESENT_WHEN.get(f"{label}.{each.name}")
            if gate is None or not isinstance(each.type, Optional):
                found.append(each)
                continue
            if not isinstance(gate, tuple):
                found.append(dataclasses.replace(each, type=each.type.element, when=gate))
                continue
            name, *members = gate
            declared = next(field.type for field in shape.fields if field.name == name)
            tests: list[Expression]
            match declared:
                case EnumRef(enum=enum) | EnumName(enum=enum):
                    tests = [Binary("==", FieldRef(name), MemberRef(enum, member)) for member in members]
                case List(element=EnumRef(enum=enum) | EnumName(enum=enum)):
                    tests = [Test(name, MemberRef(enum, member)) for member in members]
                case _:
                    raise TypeError(f"{label}.{name}: not an enum or a list of enums")
            when = functools.reduce(lambda left, right: Binary("or", left, right), tests)
            found.append(dataclasses.replace(each, type=each.type.element, when=when))
        return found

    def points(self, shape: StructShape, seen: set[int]) -> Iterator[Point]:
        if id(shape) in seen:
            return
        seen.add(id(shape))
        label = self.label(shape)
        for index in range(len(self.whens(shape))):
            yield (f"{label} when#{index}", "true")
            yield (f"{label} when#{index}", "false")
        for each in self.fields(shape):
            if f"{label}.{each.name}" not in SAME_MEMBER and f"{label}.{each.name}" not in self.fixed:
                yield from self.type_points(each.type, f"{label}.{each.name}", seen)

    def type_points(self, node: Type, key: str, seen: set[int]) -> Iterator[Point]:
        match node:
            case EnumRef() | EnumName() if key in self.members:
                yield from ((key, member) for member in self.members[key])
            case StructRef(struct=struct):
                yield from self.points(self.shape(struct), seen)
            case Optional(element=element):
                yield (key + "?", "present")
                yield (key + "?", "absent")
                yield from self.type_points(element, key + "?", seen)
            case List(element=element) | Array(element=element):
                yield from self.type_points(element, key + "[]", seen)
            case Map(key=map_key, value=value):
                yield from self.type_points(map_key, key + "{k}", seen)
                yield from self.type_points(value, key + "{v}", seen)
            case Variant(cases=cases):
                for index, case in enumerate(cases):
                    yield (key + "|", f"case {index}")
                    if case is not None:
                        yield from self.type_points(case, f"{key}|{index}", seen)

    def whens(self, shape: StructShape) -> list[Expression]:
        found: list[Expression] = []
        for each in self.fields(shape):
            if each.when is not None and each.when not in found:
                found.append(each.when)
        return found

    def pick(self, key: str, states: list[str], record: bool = True) -> int:
        cursor = self.cursors.get(key, 0)
        self.cursors[key] = cursor + 1
        index = cursor % len(states)
        if record:
            self.hits.add((key, states[index]))
        return index

    def next(self) -> int:
        self.counter += 1
        return self.counter

    def integer(self, name: str, wire: str | None) -> int:
        low, high = integer_range(name, wire)
        count = self.next()
        magnitude = (count * 7) % 100 + 1 if high <= 255 else (count * 131) % 30000 + 200
        if low < 0 and count % 3 == 0:
            magnitude = -magnitude
        return min(max(magnitude, low), high)

    def leaf(self, node: Primitive, wire: str | None = None) -> Json:
        if node.name in INTEGER_BITS:
            return self.integer(node.name, wire or node.wire)
        match node.name:
            case "bool":
                return self.next() % 2 == 0
            case "float" | "double":
                return self.next() * 0.5 + 0.25
            case "str":
                return f"s{self.next()}"
            case "bytes":
                return bytes([self.next() % 256, 1, 2]).hex()
        raise TypeError(f"{node.name}: no generator for primitive")

    def default(self, node: Type) -> Json:
        match node:
            case Primitive(name=name):
                return {"bool": False, "float": 0.0, "double": 0.0, "str": "", "bytes": ""}.get(name, 0)
            case AliasRef():
                return 0
            case EnumRef(enum=enum) | EnumName(enum=enum):
                return self.named(enum).get(0, 0)
            case StructRef(struct=struct):
                shape = self.shape(struct)
                return {
                    each.name: self.default(each.type) for each in shape.fields if not isinstance(each.type, Literal)
                }
            case BuiltinRef(builtin=builtin):
                return {"UUID": str(uuid.UUID(int=0)), "DynamicValue": None}.get(builtin.name, {})
            case Optional():
                return None
            case List() | Map():
                return {} if isinstance(node, Map) else []
            case Array(element=element, size=size):
                return [self.default(element) for _ in range(size)]
            case Variant(cases=cases):
                first = cases[0]
                return None if first is None else {self.alternative(first): self.default(first)}
            case Bitset():
                return 0
        raise TypeError(f"{node!r}: no default")

    def alternative(self, node: Type) -> str:
        match node:
            case StructRef(struct=struct):
                return struct.name
            case EnumRef(enum=enum) | EnumName(enum=enum):
                return enum.name
            case Primitive(name=name):
                return ALTERNATIVE_BY_PRIMITIVE.get(name, "int")
            case AliasRef():
                return "int"
            case BuiltinRef(builtin=builtin):
                return builtin.name
            case List() | Array():
                return "list"
        raise TypeError(f"{node!r}: no variant tag")

    def generate(self, node: Type, key: str, depth: int, length: int | None = None) -> Json:
        if key in self.fixed:
            return self.fixed[key]
        if key in KEPT_FORMS:
            return KEPT_FORMS[key][self.pick(key, list(KEPT_FORMS[key]), False)]
        match node:
            case Primitive():
                return self.leaf(node)
            case AliasRef(alias=alias):
                return self.leaf(alias.primitive, node.wire)
            case EnumRef() | EnumName() if key in self.members:
                return self.members[key][self.pick(key, list(self.members[key]))]
            case EnumRef(enum=enum) | EnumName(enum=enum):
                names = self.named(enum)
                if not names:
                    return 0
                ordered = sorted(names)
                return names[ordered[self.next() % len(ordered)]]
            case StructRef(struct=struct):
                return self.struct(self.shape(struct), depth + 1)
            case BuiltinRef(builtin=builtin):
                match builtin.name:
                    case "UUID":
                        return str(uuid.UUID(int=self.next()))
                    case "DynamicValue":
                        return {"k": [1, 2.5, "s", True, None, {"n": 3}]}
                return dict(NBT_TAGS)
            case Optional(element=element):
                if depth > MAX_DEPTH:
                    return None
                if self.pick(key + "?", ["present", "absent"]) == 1:
                    return None
                return self.generate(element, key + "?", depth)
            case List(element=element):
                count = (1 if length is None else length) if depth <= MAX_DEPTH else 0
                return [self.generate(element, key + "[]", depth) for _ in range(count)]
            case Array(element=element, size=size):
                return [self.generate(element, key + "[]", depth) for _ in range(size)]
            case Map(key=map_key, value=value):
                entry = self.generate(map_key, key + "{k}", depth)
                return {entry if isinstance(entry, str) else str(entry): self.generate(value, key + "{v}", depth)}
            case Variant(cases=cases):
                index = self.pick(key + "|", [f"case {each}" for each in range(len(cases))])
                case = cases[index]
                if case is None:
                    return None
                return {self.alternative(case): self.generate(case, f"{key}|{index}", depth)}
            case Bitset(width=width):
                bits = self.numbers(width.enum)[width.name]
                return 1 | (1 << (bits - 1))
        raise TypeError(f"{node!r}: cannot generate")

    def evaluate(self, expression: Expression, env: dict[str, int], bits: set[tuple[str, str]]) -> int:
        match expression:
            case FieldRef(name=name):
                return env.get(name, 0)
            case MemberRef(enum=enum, name=name):
                return self.numbers(enum)[name]
            case Int(value=value):
                return value
            case Test(field=name, member=member):
                return int((name, member.name) in bits)
            case Not(operand=operand):
                return int(not self.evaluate(operand, env, bits))
            case Binary(operator=operator, left=left, right=right):
                a = self.evaluate(left, env, bits)
                b = self.evaluate(right, env, bits)
                match operator:
                    case "==":
                        return int(a == b)
                    case "!=":
                        return int(a != b)
                    case "<":
                        return int(a < b)
                    case ">":
                        return int(a > b)
                    case "<=":
                        return int(a <= b)
                    case ">=":
                        return int(a >= b)
                    case "&":
                        return a & b
                    case "|":
                        return a | b
                    case "and":
                        return int(bool(a) and bool(b))
                    case "or":
                        return int(bool(a) or bool(b))
                raise TypeError(f"{operator}: unknown operator")
        raise TypeError(f"{expression!r}: cannot evaluate")

    def atoms(self, expression: Expression) -> Iterator[Expression]:
        match expression:
            case FieldRef() | Test() | Int() | MemberRef() | Len():
                yield expression
            case Not(operand=operand):
                yield from self.atoms(operand)
            case Binary(left=left, right=right):
                yield from self.atoms(left)
                yield from self.atoms(right)

    def declared(self, shape: StructShape, name: str) -> Type:
        outer, _, inner = name.partition(".")
        found = next(each.type for each in shape.fields if each.name == outer)
        if not inner:
            return found
        if not isinstance(found, StructRef):
            raise TypeError(f"{outer}: not a struct field")
        return next(each.type for each in self.shape(found.struct).fields if each.name == inner)

    def candidates(self, shape: StructShape, name: str, whens: list[Expression]) -> list[int]:
        declared = self.declared(shape, name)
        constants: set[int] = {0, 1}
        for expression in whens:
            for atom in self.atoms(expression):
                if isinstance(atom, Int):
                    constants |= {atom.value - 1, atom.value, atom.value + 1}
                elif isinstance(atom, MemberRef):
                    constants.add(self.numbers(atom.enum)[atom.name])
        if isinstance(declared, EnumRef | EnumName):
            numbers = sorted(self.named(declared.enum))
            chosen = [each for each in numbers if each in constants]
            return chosen + [each for each in numbers if each not in constants][:1]
        if isinstance(declared, Primitive) and declared.name == "bool":
            return [0, 1]
        if isinstance(declared, AliasRef):
            primitive = declared.alias.primitive
            wire = declared.wire or primitive.wire
        elif isinstance(declared, Primitive):
            primitive = declared
            wire = declared.wire
        else:
            raise TypeError(f"{name}: not an integer variable")
        if primitive.name not in INTEGER_BITS:
            raise TypeError(f"{name}: not an integer variable")
        low, high = integer_range(primitive.name, wire)
        return sorted(each for each in constants if low <= each <= high)

    def solve(
        self, shape: StructShape, wanted: list[tuple[Expression, bool]]
    ) -> tuple[dict[str, int], set[tuple[str, str]]]:
        fields = {each.name for each in shape.fields}
        variables: list[tuple[str, str]] = []
        for expression, _ in wanted:
            for atom in self.atoms(expression):
                variable = self.variable(atom)
                if variable is None:
                    continue
                if variable not in variables:
                    variables.append(variable)
        expressions = [each for each, _ in wanted]
        domains = [[0, 1] if kind != "field" else self.candidates(shape, name, expressions) for kind, name in variables]
        for kind, name in variables:
            if kind == "field" and name.partition(".")[0] not in fields:
                raise TypeError(f"{name}: not a field of {shape.family.name}")
        kept: list[tuple[Expression, bool]] = []
        best: tuple[dict[str, int], set[tuple[str, str]]] = ({}, set())
        for each in wanted:
            trial = [*kept, each]
            used = [{self.variable(atom) for atom in self.atoms(expression)} - {None} for expression, _ in trial]
            last = [max((variables.index(v) for v in names if v in variables), default=-1) for names in used]
            found = self.search(variables, domains, trial, last, 0, [])
            if found is not None:
                kept.append(each)
                best = found
        return best

    def variable(self, atom: Expression) -> tuple[str, str] | None:
        if isinstance(atom, FieldRef):
            return ("field", atom.name)
        if isinstance(atom, Test):
            return (atom.field, atom.member.name)
        return None

    def search(
        self,
        variables: list[tuple[str, str]],
        domains: list[list[int]],
        trial: list[tuple[Expression, bool]],
        last: list[int],
        index: int,
        chosen: list[int],
    ) -> tuple[dict[str, int], set[tuple[str, str]]] | None:
        env = {name: value for (kind, name), value in zip(variables, chosen, strict=False) if kind == "field"}
        bits = {
            variable for variable, value in zip(variables, chosen, strict=False) if variable[0] != "field" and value
        }
        for (expression, want), position in zip(trial, last, strict=True):
            if position == index - 1 and bool(self.evaluate(expression, env, bits)) != want:
                return None
        if index == len(variables):
            return env, bits
        for value in domains[index]:
            found = self.search(variables, domains, trial, last, index + 1, [*chosen, value])
            if found is not None:
                return found
        return None

    def length(self, each: Any, values: dict[str, Json], counted: dict[str, int]) -> int | None:
        match each.type:
            case List(count=Len(field=name)):
                return len(values[name])
            case List(count=FieldRef(name=name)):
                return counted[name]
            case List(count=Binary(operator="*", left=FieldRef(name=left), right=FieldRef(name=right))):
                return counted[left] * counted[right]
        return None

    def struct(self, shape: StructShape, depth: int) -> Json:
        label = self.label(shape)
        fields = self.fields(shape)
        whens = self.whens(shape)
        values: dict[str, Json] = {}
        counted: dict[str, int] = {}
        for each in fields:
            match each.type:
                case List(count=FieldRef(name=name)):
                    counted[name] = 1
                case List(count=Binary(operator="*", left=FieldRef(name=left), right=FieldRef(name=right))):
                    counted[left] = 1
                    counted[right] = 2
        for each in fields:
            plain = each.when is None and not isinstance(each.type, Literal | List)
            counts = isinstance(each.type, List) and each.when is None and not isinstance(each.type.count, Len)
            if (
                (plain or counts)
                and f"{label}.{each.name}" not in SAME_MEMBER
                and f"{label}.{each.name}" not in self.fixed
            ):
                values[each.name] = self.generate(
                    each.type, f"{label}.{each.name}", depth, self.length(each, values, counted)
                )
        for each in fields:
            if isinstance(each.type, List) and each.when is None and isinstance(each.type.count, Len):
                values[each.name] = self.generate(
                    each.type, f"{label}.{each.name}", depth, self.length(each, values, counted)
                )
        values.update(counted)
        wanted: list[Any] = []
        for index, expression in enumerate(whens):
            unhit = [state for state in ("true", "false") if (f"{label} when#{index}", state) not in self.hits]
            cycled = self.pick(f"{label} when#{index}", ["true", "false"], False) == 0
            wanted.append((expression, unhit[0] == "true" if unhit else cycled, not unhit))
        wanted = [(expression, want) for expression, want, _ in sorted(wanted, key=lambda each: each[2])]
        env, bits = self.solve(shape, wanted) if wanted else ({}, set())
        for name, number in env.items():
            declared = self.declared(shape, name)
            value: Json = number
            if isinstance(declared, EnumRef | EnumName):
                value = self.named(declared.enum).get(number, number)
            elif isinstance(declared, Primitive) and declared.name == "bool":
                value = bool(number)
            outer, _, inner = name.partition(".")
            values[outer] = {**values[outer], inner: value} if inner else value
        for each in fields:
            if isinstance(each.type, Bitset) and any(field == each.name for field, _ in bits):
                width = self.numbers(each.type.width.enum)
                values[each.name] = sum(1 << width[member] for field, member in bits if field == each.name)
            held = [member for field, member in bits if field == each.name]
            if isinstance(each.type, List) and isinstance(each.type.element, EnumRef | EnumName) and held:
                numbers = self.numbers(each.type.element.enum)
                values[each.name] = sorted(held, key=lambda member: numbers[member])
        final, flags = self.environment(shape, values)
        for index, expression in enumerate(whens):
            state = bool(self.evaluate(expression, final, flags))
            self.hits.add((f"{label} when#{index}", "true" if state else "false"))
        for each in fields:
            if each.when is None:
                continue
            if bool(self.evaluate(each.when, final, flags)):
                values[each.name] = self.generate(
                    each.type, f"{label}.{each.name}", depth, self.length(each, values, counted)
                )
            else:
                values[each.name] = None if f"{label}.{each.name}" in PRESENT_WHEN else self.default(each.type)
        for each in fields:
            if f"{label}.{each.name}" in self.fixed and each.when is None and each.name not in env:
                values[each.name] = self.fixed[f"{label}.{each.name}"]
            if f"{label}.{each.name}" in SAME_MEMBER:
                values[each.name] = values[SAME_MEMBER[f"{label}.{each.name}"]]
        if label in ITEM_STACKS and self.version in ITEMS:
            ids = list(ITEMS[self.version])
            values["id"] = ids[self.pick("item", list(map(str, ids)), False)]
            aux = ITEMS[self.version][values["id"]]
            values["aux_value"] = values["aux_value"] if aux is None else aux
        return {each.name: values[each.name] for each in fields if each.name in values}

    def environment(self, shape: StructShape, values: dict[str, Json]) -> tuple[dict[str, int], set[tuple[str, str]]]:
        env: dict[str, int] = {}
        bits: set[tuple[str, str]] = set()
        for each in shape.fields:
            value = values.get(each.name)
            declared = each.type
            if isinstance(declared, EnumRef | EnumName):
                numbers = self.numbers(declared.enum)
                env[each.name] = numbers[value] if isinstance(value, str) else int(value or 0)
            elif isinstance(declared, Bitset):
                width = self.numbers(declared.width.enum)
                number = int(value or 0)
                bits |= {(each.name, member) for member, index in width.items() if number >> index & 1}
            elif isinstance(declared, List) and isinstance(declared.element, EnumRef | EnumName):
                bits |= {(each.name, member) for member in value or []}
            elif isinstance(declared, StructRef) and isinstance(value, dict):
                env |= {f"{each.name}.{key}": item for key, item in value.items() if type(item) is int}
            elif isinstance(value, bool | int):
                env[each.name] = int(value)
        return env, bits

    def printed(self, node: Type, value: Json, path: str = "") -> list[list[Json]]:
        """List the [key path, scalar] BDS's JSON prints for `value` in order, a third true where one value runs on."""
        found: list[list[Json]] = []
        match node:
            case StructRef(struct=struct):
                for each in self.shape(struct).fields:
                    key = f"{path}.{each.name}" if path else each.name
                    if not isinstance(each.type, Literal):
                        found += self.printed(each.type, value[each.name], key)
                    elif isinstance(each.type.value, MemberRef):
                        found += self.printed(EnumRef(each.type.value.enum), each.type.value.name, key)
                    elif not each.name.startswith("_true"):
                        found.append([key, each.type.value])
                return found
            case Optional(element=element):
                return [] if value is None else self.printed(element, value, path)
            case List(element=Primitive(name="uint8")):
                return [[path, bytes(value).decode(errors="surrogateescape")]]
            case List(element=element) | Array(element=element):
                for index, each in enumerate(value):
                    found += self.printed(element, each, f"{path}[{index}]")
                return found
            case Map(key=key, value=element):
                primitive = key.alias.primitive if isinstance(key, AliasRef) else key
                parse: Any = str
                if isinstance(primitive, Primitive) and primitive.name in INTEGER_BITS:
                    parse = int
                elif isinstance(primitive, Primitive) and primitive.name in ("float", "double"):
                    parse = float
                for entry, each in value.items():
                    inner = f"{path}.{entry}" if path else entry
                    found += [*self.printed(key, parse(entry), inner), *self.printed(element, each, inner)]
                return found
            case Variant(cases=cases):
                if value is None:
                    return [[path, None]]
                ((name, item),) = value.items()
                case = next(each for each in cases if each is not None and self.alternative(each) == name)
                return self.printed(case, item, f"{path}.{name}" if path else name)
            case Primitive() | AliasRef():
                primitive = node if isinstance(node, Primitive) else node.alias.primitive
                wire = node.wire or primitive.wire or primitive.name
                if primitive.name in INTEGER_BITS and wire in INTEGER_BITS:
                    bits, signed = INTEGER_BITS[wire]
                    number = value % (1 << bits)
                    return [[path, number - (1 << bits) if signed and number >> (bits - 1) else number]]
                if primitive.name == "bytes":
                    return [[path, bytes.fromhex(value).decode(errors="surrogateescape")]]
                return [[path, value]]
            case EnumRef(enum=enum) | EnumName(enum=enum):
                shape = self.schema.shape_at(enum, self.version)
                if not isinstance(shape, EnumShape):
                    raise TypeError(f"{enum.name}: not an enum shape")
                if isinstance(node, EnumName):
                    return [[path, next((member.wire_name for member in shape.members if member.name == value), value)]]
                number = shape.numbers[value] if isinstance(value, str) else value
                if shape.underlying.name == "bool":
                    return [[path, bool(number)]]
                return self.printed(Primitive(shape.underlying.name, node.wire or shape.underlying.wire), number, path)
            case Bitset():
                groups = [value >> shift & 0x7F for shift in range(0, max(value.bit_length(), 1), 7)]
                found = [[path, each | (0x80 if index + 1 < len(groups) else 0)] for index, each in enumerate(groups)]
                return [found[0], *([*each, True] for each in found[1:])]
            case BuiltinRef(builtin=builtin, wire="str") if builtin.name == "UUID":
                return [[path, value]]
            case BuiltinRef(builtin=builtin) if builtin.name == "UUID":
                number = uuid.UUID(value).int
                return [[path, number >> 64], [path, number & (1 << 64) - 1]]
            case BuiltinRef(builtin=builtin) if builtin.name == "DynamicValue":
                if isinstance(value, dict):
                    for entry, each in value.items():
                        found += [[f"{path}.{entry}", entry], *self.printed(node, each, f"{path}.{entry}")]
                    return found
                if isinstance(value, list):
                    for index, each in enumerate(value):
                        found += self.printed(node, each, f"{path}[{index}]")
                    return found
                return [[path, value]]
            case BuiltinRef(builtin=builtin) if builtin.name in ("CompoundTag", "CompoundTagData"):
                found = tag_printed({"CompoundTag": value}, path)
                if builtin.name == "CompoundTag":
                    found = [[path, NBT_TYPES["CompoundTag"]], [path, ""], *found]
                return [found[0], *([*each, True] for each in found[1:])]
        raise TypeError(f"{node!r}: no printed form")


def packets(schema: Schema, version: int) -> list[Any]:
    found = [
        family
        for family in schema.order
        if getattr(family, "packet_id", None) is not None and (family, version) in schema.live
    ]
    return sorted(found, key=lambda each: each.packet_id)


def values_of(schema: Schema, version: int, family: Any) -> tuple[list[Json], set[Point], set[Point]]:
    generator = Generator(schema, version)
    shape = generator.shape(family)
    wanted = set(generator.points(shape, set()))
    chosen: list[Json] = []
    attempts = 0
    while attempts < 8 + 4 * len(wanted) and (not chosen or wanted - generator.hits):
        before = len(generator.hits & wanted)
        value = generator.struct(shape, 0)
        attempts += 1
        if not chosen or len(generator.hits & wanted) > before:
            chosen.append(value)
    return chosen, generator.hits & wanted, wanted - generator.hits


def differs(expected: Json, actual: Json, path: str = "") -> str | None:
    if isinstance(expected, dict) and isinstance(actual, dict):
        if list(expected) != list(actual):
            return path.lstrip(".")
        for key in expected:
            found = differs(expected[key], actual[key], f"{path}.{key}")
            if found is not None:
                return found
        return None
    if isinstance(expected, list) and isinstance(actual, list) and len(expected) == len(actual):
        for index, (left, right) in enumerate(zip(expected, actual, strict=True)):
            found = differs(left, right, f"{path}[{index}]")
            if found is not None:
                return found
        return None
    return None if expected == actual and type(expected) is type(actual) else path.lstrip(".")


def round_trip(cls: Any, value: Json) -> tuple[str, str, str, bytes | None]:
    """Return the failing step, its path and error, and the seed bytes when every step held."""
    decode_error = importlib.import_module("bedrock_protocol").DecodeError
    try:
        packet = cls.from_json(value)
    except ValueError as error:
        return "from_json", str(error).split(":")[0].partition(".")[2], str(error), None
    data = bytes(packet)
    try:
        again = cls.from_bytes(data)
    except decode_error as error:
        path = "".join(f"[{each}]" if isinstance(each, int) else f".{each}" for each in error.path)
        return "from_bytes", path.lstrip("."), str(error), None
    back = again.to_json()
    changed = differs(value, back)
    if changed is not None:
        return "to_json", changed, f"differs: {value!r} != {back!r}"[:600], None
    return "", "", "", data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", type=int, help="protocol number; every modelled version when omitted")
    parser.add_argument(
        "packets", nargs="*", help="packet stems (144_player_auth_input), class names or ids; every packet when omitted"
    )
    parser.add_argument(
        "--check", action="store_true", help="round-trip every value through the bedrock_protocol binding"
    )
    parser.add_argument("--disagreements", type=Path, help="write the failures of --check here")
    parser.add_argument("--cases", type=Path, help="write the values that held, with their seed bytes, here")
    arguments = parser.parse_args()
    schema = Schema(build(PROTOCOL_DIR))
    if arguments.version and arguments.version not in schema.versions:
        raise ValueError(f"{arguments.version}: not a modelled protocol version")
    versions = [arguments.version] if arguments.version else list(schema.versions)
    check = arguments.check or bool(arguments.cases or arguments.disagreements)
    matched: set[str] = set()
    failures: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    total = hit = 0
    for version in versions:
        module = importlib.import_module(f"bedrock_protocol.v{version}") if check else None
        for family in packets(schema, version):
            snake = re.sub(
                r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", family.name.removesuffix("Packet")
            ).lower()
            stem = f"{family.packet_id:03}_{snake}"
            names = {stem, family.name, family.name.removesuffix("Packet"), str(family.packet_id)}
            if arguments.packets and not names & set(arguments.packets):
                continue
            matched |= names
            chosen, hits, misses = values_of(schema, version, family)
            total += len(hits) + len(misses)
            hit += len(hits)
            print(f"{version}/{stem}: {len(hits)} of {len(hits) + len(misses)} states hit")
            for key, state in sorted(misses):
                print(f"  missed {key} {state}")
            if module is None:
                continue
            cls = module.packets[family.packet_id]
            for index, value in enumerate(chosen):
                step, path, error, data = round_trip(cls, value)
                if step:
                    failures.append(
                        {
                            "packet": family.name,
                            "version": version,
                            "path": path,
                            "value": value,
                            "step": step,
                            "error": error,
                        }
                    )
                elif data is not None:
                    cases.append(
                        {
                            "packet": family.packet_id,
                            "id": f"v{index}",
                            "version": version,
                            "value": value,
                            "printed": Generator(schema, version).printed(StructRef(family), value),
                            "bytes": data.hex(),
                        }
                    )
    unmatched = [each for each in arguments.packets if each not in matched]
    if unmatched:
        raise ValueError(f"{', '.join(unmatched)}: matches no packet at the chosen versions")
    print(f"{hit} of {total} states hit")
    if check:
        print(f"{len(failures)} failures, {len(cases)} values held")
    if arguments.disagreements:
        arguments.disagreements.parent.mkdir(parents=True, exist_ok=True)
        arguments.disagreements.write_text(json.dumps(failures, indent=1))
    if arguments.cases:
        arguments.cases.write_text(json.dumps(cases))
    if check and failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
