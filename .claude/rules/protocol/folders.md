---
paths:
  - "protocol/**"
---

# Folders

The bedrock-headers folders each schema module draws from. Paths are under `src/common/`, except `SharedTypes/` and `VoxelShapes/` under `src-deps/`, `Core/` under `src/base/` and `PackInfrastructure/` under `src/engine/`.

| Module | Folders |
|---|---|
| ability | `world/actor/player/` (`Abilities.h`), `network/packet/types/world/actor/` (`SerializedAbilitiesData.h`), `world/level/storage/` (`LevelData.h`) |
| actor | `world/actor/`, `network/packet/types/world/actor/` |
| attribute | `world/attribute/`, `world/eas/`, `world/eas/attributes/` |
| biome | `world/level/biome/serialization/` |
| block | `world/level/block/`, `world/level/block/definition/`, `world/level/block/actor/` |
| boss | `world/actor/boss/`, `network/packet/types/world/actor/ai/util/` (`BossEventData.h`) |
| camera | `world/level/camera/`, `world/level/controlscheme/` |
| chunk | `world/level/chunk/` |
| command | `server/commands/` |
| common | `SharedTypes/versionless/`, `Core/Math/`, and `world/level/block/` for `BlockRuntimeId` |
| crafting | `world/item/crafting/`, `world/item/alchemy/` |
| datastore | `scripting/data_sync/` |
| diagnostics | `profile/`, `debug/` |
| dimension | `world/level/dimension/` |
| editor | `network/packet/` (`EditorNetworkPacket.h`), `network/` (`ServerEditorConnectionPolicy.h`), `world/level/` (`EditorLevelMigrationVersion.h`), and `EditorWorldType.h` at the root |
| edu | `codebuilder/`, `world/actor/agent/` |
| effect | `world/effect/` |
| enchanting | `world/item/enchanting/` |
| game | `world/level/`, for StartGame and the packets that change level settings |
| graphics | `network/packet/` only |
| input | `input/` |
| inventory | `world/containers/`, `world/inventory/` |
| item | `world/item/`, `world/item/registry/` |
| item_stack | `world/inventory/network/` |
| level | `world/level/`, `world/level/clock/`, `world/level/storage/`, `options/` |
| map | `world/level/saveddata/maps/`, `world/level/saveddata/photos/` |
| molang | `util/molang/`, `SharedTypes/versionless/Molang/` |
| movement | `network/packet/` only |
| nbt | none; hand-written in `include/bedrock/protocol/nbt.hpp` |
| network | `network/` |
| pack | `Core/Resource/`, `PackInfrastructure/` |
| player | `world/actor/player/` |
| presence | `network/packet/` only |
| scoreboard | `world/scores/` |
| script | `scripting/` |
| skin | `world/actor/player/` (`SerializedSkinRef.h`), `persona/`, `resources/persona/` |
| sound | `sound/`, `world/level/` (`LevelSoundEvent.h`) |
| store | `store/` |
| structure | `world/level/levelgen/structure/`, `gametest/` |
| telemetry | `Events/` |
| text | `textobject/`, `safety/` |
| transaction | `world/inventory/transaction/` |
| ui | `dataDrivenUI/`, `world/` (`Waypoint*.h`), `util/` (`HudElementsEnum.h`) |
| voxelshape | `world/level/voxelshape/`, `VoxelShapes/` |
