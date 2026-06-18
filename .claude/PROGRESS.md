# Protocol coverage progress

Generated 2026-06-18 from `protocol/*.py` at `__version__ = 1001`. Built mechanically from the DSL parser (type-reference graph) plus the `tests/` golden map. The end state is every packet **complete** with a **ready** golden and zero `#` comments left in the DSL.

## What the columns mean

- **Status** tracks the DSL source. A packet is **complete** only when neither it nor any type in its reference closure carries a review `#` comment. Any explanatory comment, `TODO`, or `BDS:` note means **review** (the target is a comment-free DSL). **blocked** means a `COMPILER_EXTENSION_NEEDED` comment -- the real wire shape cannot be expressed until the compiler grows a feature. Mechanical pragmas (`# noqa: F811` on a version redeclaration, etc.) do not count -- they are required by the redeclaration pattern, not review debt.
- **Golden** tracks the gophertunnel round-trip test (CLAUDE.md rule 8). `ready` = a `golden` byte-vector test exists, `rt-only` = a test exists but only self-round-trips, `MISSING` = no test file yet, `n/a` = empty-body packet (nothing to serialize).

## Summary

- **Packets modeled:** 228
  - complete: **166**
  - needs review: **46**
  - blocked on compiler: **16**
- **Golden tests:** ready 136 / rt-only 1 / missing 84 / n/a 7
- **Fully done** (complete DSL + golden settled): **110 / 228**
  - of which DSL-complete but golden still MISSING/rt-only (test work only): 56
- **Coverage gaps** (ids with no `@packet`): **14** -- see below
- Mechanical pragmas present (not review debt): 5

## Packets by id

| ID | Packet | File | Status | Golden | Notes |
|---:|--------|------|--------|--------|-------|
| 1 | LoginPacket | login | complete | ready |  |
| 2 | PlayStatusPacket | login | complete | ready |  |
| 3 | ServerToClientHandshakePacket | login | complete | ready |  |
| 4 | ClientToServerHandshakePacket | login | complete | ready |  |
| 5 | DisconnectPacket | disconnect | complete | ready |  |
| 6 | ResourcePacksInfoPacket | resource_pack | BLOCKED | ready | via PackInfoData, self: from v618 until v748 the wire carried a uvarint32-length- |
| 7 | ResourcePackStackPacket | resource_pack | review | ready | 8 comment(s) on: PackInstanceId, self |
| 8 | ResourcePackClientResponsePacket | resource_pack | complete | ready |  |
| 9 | TextPacket | game | BLOCKED | MISSING | via self: the variant body's three cases differ structurally |
| 10 | SetTimePacket | game | complete | ready |  |
| 11 | StartGamePacket | game | review | ready | 1 comment(s) on: EducationEditionOffer |
| 13 | AddActorPacket | actor | BLOCKED | MISSING | via PropertySyncData, SyncedAttribute, self: SynchedActorData::DataList -- a uvarint32-prefixed list |
| 14 | RemoveActorPacket | actor | complete | ready |  |
| 17 | TakeItemActorPacket | actor | complete | ready |  |
| 18 | MoveActorAbsolutePacket | actor | review | ready | 2 comment(s) on: MoveActorAbsoluteData |
| 19 | MovePlayerPacket | player | review | ready | 2 comment(s) on: self |
| 20 | PassengerJumpPacket | actor | review | MISSING | 4 comment(s) on: self |
| 21 | UpdateBlockPacket | level | complete | ready |  |
| 22 | AddPaintingPacket | actor | complete | ready |  |
| 25 | LevelEventPacket | level | complete | MISSING |  |
| 26 | BlockEventPacket | level | complete | MISSING |  |
| 27 | ActorEventPacket | actor | complete | ready |  |
| 28 | MobEffectPacket | effect | complete | ready |  |
| 29 | UpdateAttributesPacket | attributes | complete | ready |  |
| 31 | MobEquipmentPacket | inventory | complete | ready |  |
| 33 | InteractPacket | actor | complete | ready |  |
| 34 | BlockPickRequestPacket | player | complete | ready |  |
| 35 | ActorPickRequestPacket | actor | review | ready | 1 comment(s) on: self |
| 36 | PlayerActionPacket | input | complete | ready |  |
| 37 | ActorFallPacket | actor | complete | MISSING |  |
| 38 | HurtArmorPacket | actor | review | MISSING | 1 comment(s) on: self |
| 39 | SetActorDataPacket | actor | BLOCKED | MISSING | via PropertySyncData, self: SynchedActorData::DataList -- a uvarint32-prefixed list |
| 40 | SetActorMotionPacket | actor | complete | ready |  |
| 41 | SetActorLinkPacket | actor | complete | ready |  |
| 43 | SetSpawnPositionPacket | level | complete | ready |  |
| 44 | AnimatePacket | actor | complete | ready |  |
| 45 | RespawnPacket | level | complete | ready |  |
| 46 | ContainerOpenPacket | inventory | complete | ready |  |
| 47 | ContainerClosePacket | inventory | complete | ready |  |
| 48 | PlayerHotbarPacket | inventory | complete | MISSING |  |
| 49 | InventoryContentPacket | inventory | review | ready | 6 comment(s) on: self |
| 50 | InventorySlotPacket | inventory | review | ready | 8 comment(s) on: self |
| 51 | ContainerSetDataPacket | inventory | complete | ready |  |
| 52 | CraftingDataPacket | crafting | review | ready | 6 comment(s) on: CraftingDataEntry, ShapedChemistryRecipe, ShapedRecipe, ShapelessChemistryRecipe, UserDataShapelessRecipe |
| 53 | CraftingEventPacket | crafting | complete | MISSING |  |
| 54 | GuiDataPickItemPacket | player | complete | ready |  |
| 55 | AdventureSettingsPacket | game | complete | MISSING |  |
| 56 | BlockActorDataPacket | level | complete | ready |  |
| 57 | PlayerInputPacket | input | review | MISSING | 3 comment(s) on: self |
| 58 | LevelChunkPacket | level | review | MISSING | 4 comment(s) on: self |
| 59 | SetCommandsEnabledPacket | command | complete | ready |  |
| 60 | SetDifficultyPacket | game | complete | ready |  |
| 61 | ChangeDimensionPacket | dimension | complete | MISSING |  |
| 62 | SetPlayerGameTypePacket | game | complete | ready |  |
| 64 | SimpleEventPacket | game | complete | MISSING |  |
| 65 | EventPacket | game | BLOCKED | MISSING | via self: the wire layout is event_type (signed varint), use_player_id |
| 66 | SpawnExperienceOrbPacket | actor | complete | ready |  |
| 67 | ClientboundMapItemDataPacket | map | BLOCKED | MISSING | via MapItemTrackedActorUniqueId, self: the wire `type` discriminator is COMPUTED from |
| 68 | MapInfoRequestPacket | map | complete | MISSING |  |
| 69 | RequestChunkRadiusPacket | level | complete | MISSING |  |
| 70 | ChunkRadiusUpdatedPacket | level | complete | ready |  |
| 71 | ItemFrameDropItemPacket | player | review | MISSING | 3 comment(s) on: self |
| 72 | GameRulesChangedPacket | game | review | MISSING | 3 comment(s) on: self |
| 73 | CameraPacket | camera | complete | ready |  |
| 74 | BossEventPacket | actor | review | ready | 4 comment(s) on: self |
| 75 | ShowCreditsPacket | game | complete | MISSING |  |
| 76 | AvailableCommandsPacket | command | BLOCKED | MISSING | via CommandChainedSubcommandRelationship, CommandData, CommandEnumData, CommandOverloadData, CommandParamData: (until=898): each entry is one element from |
| 77 | CommandRequestPacket | command | review | MISSING | 3 comment(s) on: CommandOriginData |
| 78 | CommandBlockUpdatePacket | command | complete | MISSING |  |
| 79 | CommandOutputPacket | command | BLOCKED | MISSING | via CommandOriginData, CommandOutputMessage, self: v898 reordered this struct from |
| 80 | UpdateTradePacket | actor | review | MISSING | 4 comment(s) on: self |
| 81 | UpdateEquipPacket | actor | complete | ready |  |
| 82 | ResourcePackDataInfoPacket | resource_pack | complete | ready |  |
| 83 | ResourcePackChunkDataPacket | resource_pack | complete | ready |  |
| 84 | ResourcePackChunkRequestPacket | resource_pack | complete | ready |  |
| 85 | TransferPacket | game | complete | MISSING |  |
| 86 | PlaySoundPacket | level | complete | ready |  |
| 87 | StopSoundPacket | level | complete | ready |  |
| 88 | SetTitlePacket | graphics | complete | ready |  |
| 89 | AddBehaviorTreePacket | actor | complete | ready |  |
| 90 | StructureBlockUpdatePacket | structure | review | MISSING | 3 comment(s) on: StructureEditorData |
| 91 | ShowStoreOfferPacket | game | complete | MISSING |  |
| 92 | PurchaseReceiptPacket | game | complete | MISSING |  |
| 94 | SubClientLoginPacket | login | complete | ready |  |
| 95 | AutomationClientConnectPacket | game | complete | MISSING |  |
| 96 | SetLastHurtByPacket | actor | review | ready | 2 comment(s) on: self |
| 97 | BookEditPacket | book | complete | ready |  |
| 98 | NpcRequestPacket | npc | complete | ready |  |
| 99 | PhotoTransferPacket | game | complete | MISSING |  |
| 100 | ModalFormRequestPacket | ui | complete | ready |  |
| 101 | ModalFormResponsePacket | ui | complete | MISSING |  |
| 102 | ServerSettingsRequestPacket | game | complete | n/a |  |
| 103 | ServerSettingsResponsePacket | game | complete | MISSING |  |
| 104 | ShowProfilePacket | game | complete | MISSING |  |
| 105 | SetDefaultGameTypePacket | game | complete | MISSING |  |
| 106 | RemoveObjectivePacket | scoreboard | complete | ready |  |
| 107 | SetDisplayObjectivePacket | scoreboard | complete | ready |  |
| 108 | SetScorePacket | scoreboard | review | MISSING | 7 comment(s) on: self |
| 109 | LabTablePacket | crafting | review | ready | 3 comment(s) on: self |
| 110 | UpdateBlockSyncedPacket | level | review | MISSING | 6 comment(s) on: ActorBlockSyncMessage |
| 111 | MoveActorDeltaPacket | actor | review | ready | 10 comment(s) on: self |
| 112 | SetScoreboardIdentityPacket | scoreboard | review | MISSING | 7 comment(s) on: ScoreboardIdentityUpdateEntry |
| 113 | SetLocalPlayerAsInitializedPacket | login | complete | ready |  |
| 114 | UpdateSoftEnumPacket | command | complete | ready |  |
| 115 | NetworkStackLatencyPacket | network | complete | ready |  |
| 116 | BlockPalettePacket | level | review | n/a | 4 comment(s) on: self |
| 118 | SpawnParticleEffectPacket | graphics | complete | ready |  |
| 119 | AvailableActorIdentifiersPacket | actor | complete | ready |  |
| 121 | NetworkChunkPublisherUpdatePacket | level | complete | MISSING |  |
| 122 | BiomeDefinitionListPacket | biome | BLOCKED | ready | via BiomeClimateData, BiomeDefinitionChunkGenData, BiomeDefinitionData, self: each BiomeDefinitionData nested field is written with |
| 123 | LevelSoundEventPacket | level | review | ready | 4 comment(s) on: self |
| 124 | LevelEventGenericPacket | level | complete | MISSING |  |
| 125 | VideoStreamConnectPacket | graphics | review | n/a | 4 comment(s) on: self |
| 127 | AddEntityPacket | actor | review | ready | 4 comment(s) on: self |
| 128 | RemoveEntityPacket | actor | review | ready | 4 comment(s) on: self |
| 129 | ClientCacheStatusPacket | login | complete | ready |  |
| 130 | OnScreenTextureAnimationPacket | graphics | complete | ready |  |
| 131 | MapCreateLockedCopyPacket | map | complete | ready |  |
| 132 | StructureTemplateDataRequestPacket | structure | review | MISSING | 1 comment(s) on: StructureTemplateRequestOperation |
| 133 | StructureTemplateDataResponsePacket | structure | complete | MISSING |  |
| 134 | UpdateBlockPropertiesPacket | level | complete | MISSING |  |
| 135 | ClientCacheBlobStatusPacket | login | complete | ready |  |
| 136 | ClientCacheMissResponsePacket | login | review | ready | 1 comment(s) on: MissingBlobData |
| 137 | EducationSettingsPacket | edu | complete | MISSING |  |
| 138 | EmotePacket | actor | complete | ready |  |
| 139 | MultiplayerSettingsPacket | game | complete | MISSING |  |
| 140 | SettingsCommandPacket | command | complete | ready |  |
| 141 | AnvilDamagePacket | crafting | complete | ready |  |
| 142 | CompletedUsingItemPacket | actor | complete | ready |  |
| 143 | NetworkSettingsPacket | network | complete | ready |  |
| 144 | PlayerAuthInputPacket | input | review | ready | 2 comment(s) on: ItemStackRequestActionCraftRecipeAuto, self |
| 145 | CreativeContentPacket | inventory | complete | ready |  |
| 146 | PlayerEnchantOptionsPacket | inventory | review | ready | 4 comment(s) on: EnchantmentInstance |
| 147 | ItemStackRequestPacket | player | review | MISSING | 1 comment(s) on: ItemStackRequestActionCraftRecipeAuto |
| 148 | ItemStackResponsePacket | inventory | review | ready | 1 comment(s) on: ItemStackResponseContainerInfo |
| 149 | PlayerArmorDamagePacket | inventory | BLOCKED | MISSING | via self: until=844 the wire is a uint8 bitfield over ArmorSlot |
| 150 | CodeBuilderPacket | script | complete | ready |  |
| 151 | UpdatePlayerGameTypePacket | game | complete | MISSING |  |
| 152 | EmoteListPacket | actor | complete | ready |  |
| 153 | PositionTrackingDBServerBroadcastPacket | structure | complete | MISSING |  |
| 154 | PositionTrackingDBClientRequestPacket | structure | complete | ready |  |
| 155 | DebugInfoPacket | script | complete | ready |  |
| 156 | PacketViolationWarningPacket | network | complete | ready |  |
| 157 | MotionPredictionHintsPacket | actor | complete | ready |  |
| 158 | AnimateEntityPacket | actor | complete | ready |  |
| 159 | CameraShakePacket | camera | complete | ready |  |
| 160 | PlayerFogPacket | graphics | complete | ready |  |
| 161 | CorrectPlayerMovePredictionPacket | player | review | ready | 3 comment(s) on: self |
| 162 | ItemComponentPacket | game | complete | MISSING |  |
| 164 | ClientboundDebugRendererPacket | graphics | review | MISSING | 8 comment(s) on: self |
| 165 | SyncActorPropertyPacket | actor | complete | ready |  |
| 166 | AddVolumeEntityPacket | actor | complete | ready |  |
| 167 | RemoveVolumeEntityPacket | actor | complete | ready |  |
| 168 | SimulationTypePacket | game | complete | MISSING |  |
| 169 | NpcDialoguePacket | npc | complete | rt-only |  |
| 170 | EduUriResourcePacket | edu | complete | ready |  |
| 171 | CreatePhotoPacket | game | complete | MISSING |  |
| 172 | UpdateSubChunkBlocksPacket | level | review | MISSING | 8 comment(s) on: ActorBlockSyncMessage, UpdateSubChunkNetworkBlockInfo |
| 173 | PhotoInfoRequestPacket | game | complete | MISSING |  |
| 175 | SubChunkRequestPacket | level | complete | ready |  |
| 176 | PlayerStartItemCooldownPacket | player | complete | MISSING |  |
| 177 | ScriptMessagePacket | script | complete | ready |  |
| 178 | CodeBuilderSourcePacket | script | review | ready | 1 comment(s) on: self |
| 179 | TickingAreasLoadStatusPacket | game | complete | MISSING |  |
| 180 | DimensionDataPacket | dimension | complete | ready |  |
| 181 | AgentActionEventPacket | agent | complete | ready |  |
| 182 | ChangeMobPropertyPacket | actor | complete | ready |  |
| 183 | LessonProgressPacket | edu | complete | ready |  |
| 184 | RequestAbilityPacket | game | complete | MISSING |  |
| 185 | RequestPermissionsPacket | game | complete | MISSING |  |
| 186 | ToastRequestPacket | ui | complete | ready |  |
| 187 | UpdateAbilitiesPacket | game | complete | MISSING |  |
| 188 | UpdateAdventureSettingsPacket | game | complete | MISSING |  |
| 189 | DeathInfoPacket | game | complete | ready |  |
| 190 | EditorNetworkPacket | script | review | MISSING | 2 comment(s) on: self |
| 191 | FeatureRegistryPacket | game | complete | MISSING |  |
| 192 | ServerStatsPacket | game | complete | MISSING |  |
| 193 | RequestNetworkSettingsPacket | network | complete | ready |  |
| 194 | GameTestRequestPacket | game | review | MISSING | 3 comment(s) on: TestParameters |
| 195 | GameTestResultsPacket | game | complete | MISSING |  |
| 197 | ClientCheatAbilityPacket | game | complete | MISSING |  |
| 198 | CameraPresetsPacket | camera | BLOCKED | MISSING | via CameraPreset, self: the v575 wire form bundled every preset into a |
| 199 | UnlockedRecipesPacket | crafting | BLOCKED | ready | via self: until v589 the wire form was a single `bool` (true == NEWLY_UNLOCKE... |
| 300 | CameraInstructionPacket | camera | BLOCKED | ready | via CameraInstruction, CameraInstructionFov, CameraInstructionSet, CameraInstructionSetEaseOption, CameraRotationOption, SplineInstruction: (until=618): the v575 codec wrapped the entire |
| 302 | TrimDataPacket | trim | complete | ready |  |
| 303 | OpenSignPacket | ui | complete | ready |  |
| 304 | AgentAnimationPacket | agent | complete | ready |  |
| 305 | RefreshEntitlementsPacket | game | complete | n/a |  |
| 306 | PlayerToggleCrafterSlotRequestPacket | actor | complete | ready |  |
| 307 | SetPlayerInventoryOptionsPacket | player | complete | MISSING |  |
| 308 | SetHudPacket | graphics | BLOCKED | ready | via self: each element is a HudElement enum, but list[Enum] cannot carry a `f... |
| 309 | AwardAchievementPacket | game | complete | ready |  |
| 310 | ClientboundCloseFormPacket | ui | complete | n/a |  |
| 311 | ClientboundLoadingScreenPacket | ui | review | n/a | 6 comment(s) on: self |
| 312 | ServerboundLoadingScreenPacket | ui | complete | ready |  |
| 313 | JigsawStructureDataPacket | structure | complete | MISSING |  |
| 314 | CurrentStructureFeaturePacket | structure | complete | ready |  |
| 315 | ServerboundDiagnosticsPacket | player | review | ready | 2 comment(s) on: MemoryCategoryCounter |
| 316 | CameraAimAssistPacket | camera | complete | ready |  |
| 317 | ContainerRegistryCleanupPacket | inventory | complete | ready |  |
| 318 | MovementEffectPacket | effect | complete | ready |  |
| 320 | CameraAimAssistPresetsPacket | camera | BLOCKED | MISSING | via CameraAimAssistPresetDefinition, self: v766..v776 prepended a `categories` string here |
| 321 | ClientCameraAimAssistPacket | camera | complete | ready |  |
| 322 | ClientMovementPredictionSyncPacket | player | complete | ready |  |
| 323 | UpdateClientOptionsPacket | player | complete | ready |  |
| 324 | PlayerVideoCapturePacket | game | complete | MISSING |  |
| 327 | ClientboundControlSchemeSetPacket | player | review | ready | 1 comment(s) on: self |
| 328 | PrimitiveShapesPacket | graphics | BLOCKED | ready | via PrimitiveShapeDataPayload: max_render_distance (mMaxRenderDistance) was inserted |
| 329 | ServerboundPackSettingChangePacket | ui | complete | MISSING |  |
| 331 | GraphicsOverrideParameterPacket | graphics | complete | ready |  |
| 333 | ClientboundDataDrivenUIShowScreenPacket | ui | complete | MISSING |  |
| 334 | ClientboundDataDrivenUICloseScreenPacket | ui | complete | ready |  |
| 335 | ClientboundDataDrivenUIReloadPacket | ui | complete | n/a |  |
| 336 | ClientboundTextureShiftPacket | graphics | complete | ready |  |
| 337 | VoxelShapesPacket | game | complete | MISSING |  |
| 338 | CameraSplinePacket | camera | review | MISSING | 4 comment(s) on: CameraRotationOption |
| 339 | CameraAimAssistActorPriorityPacket | camera | complete | MISSING |  |
| 340 | ResourcePacksReadyForValidationPacket | resource_pack | complete | ready |  |
| 341 | LocatorBarPacket | locator | review | ready | 3 comment(s) on: ServerWaypointPayload |
| 342 | PartyChangedPacket | player | complete | ready |  |
| 343 | ServerboundDataDrivenScreenClosedPacket | ui | complete | MISSING |  |
| 344 | SyncWorldClocksPacket | game | complete | MISSING |  |
| 345 | ClientboundAttributeLayerSyncPacket | attributes | complete | ready |  |
| 346 | ServerStoreInfoPacket | game | complete | ready |  |
| 347 | ServerPresenceInfoPacket | game | complete | ready |  |
| 348 | ClientboundUpdateSoundDataPacket | level | complete | MISSING |  |
| 349 | SendPartyDestinationCookiePacket | player | complete | MISSING |  |
| 350 | PartyDestinationCookieResponsePacket | player | complete | MISSING |  |

## Blocked on compiler features

Each needs a compiler/codegen capability before the real wire shape can be modeled. The full `COMPILER_EXTENSION_NEEDED` rationale is reproduced.

### 6 `ResourcePacksInfoPacket` (resource_pack)
- (via `PackInfoData`) `resource_pack.py:96` BDS: PackInfoData (an element of PacksInfoData::mResourcePacks). mHasExceptions
- (via `PackInfoData`) `resource_pack.py:97` exists in BDS but never appears on the wire.
- `resource_pack.py:121` v291..v729 wrote behavior packs before resource packs; v729 dropped them.
- `resource_pack.py:122` The list is uint16_le-length-prefixed.
- `resource_pack.py:125` COMPILER_EXTENSION_NEEDED: from v618 until v748 the wire carried a uvarint32-length-
- `resource_pack.py:126` prefixed appendix of (pack_id_string + "_" + pack_version_string, cdn_url) pairs
- `resource_pack.py:127` that the codec folded back into each pack's cdn_url. No DSL form models a list
- `resource_pack.py:128` whose elements are derived from another list and merged back into a sibling list.
- `resource_pack.py:129` At v748 the CDN URL moved into the PackInfoData entry itself (modeled above).

### 9 `TextPacket` (game)
- `game.py:969` COMPILER_EXTENSION_NEEDED: the variant body's three cases differ structurally
- `game.py:970` (message_type+message / message_type+player_name+message / message_type+message+list[str])
- `game.py:971` and share no leading uvarint32 case-tag in pre-v898 wire shapes

### 13 `AddActorPacket` (actor)
- (via `PropertySyncData`) `actor.py:248` Two consecutive uvarint32-prefixed lists.
- (via `SyncedAttribute`) `actor.py:263` SyncedAttribute is the spawn-only wire form sent inline in AddActorPacket --
- (via `SyncedAttribute`) `actor.py:264` (name, min, current, max) without modifiers or default bounds.
- `actor.py:276` TODO: gophertunnel keeps Attributes as (name, min, value, max) but CloudburstMC's
- `actor.py:277` v291 attribute serializer reads (name, min, max, value); the BDS header lists
- `actor.py:278` mMinValue / mCurrentValue / mMaxValue with no on-wire order, so the disagreement
- `actor.py:279` cannot be resolved from headers alone.
- `actor.py:288` COMPILER_EXTENSION_NEEDED: SynchedActorData::DataList -- a uvarint32-prefixed list
- `actor.py:289` of (uvarint32 key, uvarint32 type-tag, payload) records where the payload type is
- `actor.py:290` selected by the tag (byte/short/int/uvarint64/float/str/CompoundTag/BlockPos/
- `actor.py:291` varint64/Vec3). The DSL has no element-internal-tag list form.

### 39 `SetActorDataPacket` (actor)
- (via `PropertySyncData`) `actor.py:248` Two consecutive uvarint32-prefixed lists.
- `actor.py:661` COMPILER_EXTENSION_NEEDED: SynchedActorData::DataList -- a uvarint32-prefixed list
- `actor.py:662` of (uvarint32 key, uvarint32 type-tag, payload) records where the payload type is
- `actor.py:663` selected by the tag (byte/short/int/uvarint64/float/str/CompoundTag/BlockPos/
- `actor.py:664` varint64/Vec3). The DSL has no element-internal-tag list form.

### 65 `EventPacket` (game)
- `game.py:520` COMPILER_EXTENSION_NEEDED: the wire layout is event_type (signed varint), use_player_id
- `game.py:521` bool, then variant body. The body shape depends on event_type (see the typed-union
- `game.py:522` alternatives above) but the tag is separated from the body by use_player_id, and the
- `game.py:523` v898 codec writes the tag a second time as a uvarint right before the body. The DSL has
- `game.py:524` no "split-tag" or "tag-prefix duplicated since=N" facility.

### 67 `ClientboundMapItemDataPacket` (map)
- (via `MapItemTrackedActorUniqueId`) `map.py:53` MapItemTrackedActor::UniqueId. CloudburstMC writes the discriminator as a
- (via `MapItemTrackedActorUniqueId`) `map.py:54` 32-bit little-endian int (the underlying BDS enum is `int`) and only one of
- (via `MapItemTrackedActorUniqueId`) `map.py:55` the two payload fields based on its value.
- `map.py:65` BDS: ClientboundMapItemDataPacket::Type bitfield. The wire is a single
- `map.py:66` uvarint32 -- TextureUpdate=2, DecorationUpdate=4, Creation=8 -- OR'd
- `map.py:67` together to gate the four payload blocks below. The DSL surface keeps it as
- `map.py:68` the raw uvarint32 so per-bit `when=` gating can test it without needing an
- `map.py:69` IntFlag spelling.
- `map.py:70` BDS mMapIds[0] / mapId. Wire is varint64.
- `map.py:76` COMPILER_EXTENSION_NEEDED: the wire `type` discriminator is COMPUTED from
- `map.py:77` whether each payload block is populated (CloudburstMC sets bit-3 of `type`
- `map.py:78` iff `trackedEntityIds` is non-empty, etc). The DSL surface treats `type` as
- `map.py:79` a raw uvarint32 the caller pins, so a caller has to mirror which payload
- `map.py:80` blocks they populate manually; the DSL has no spelling for "this enum bit
- `map.py:81` is true iff field X is non-empty" on serialize.
- `map.py:84` FLAG_ALL = 0xE. Scale is present whenever any of TextureUpdate /
- `map.py:85` DecorationUpdate / Creation is set.
- `map.py:88` FLAG_DECORATION_UPDATE = 0x4. Two consecutive uvarint32-prefixed lists:
- `map.py:89` tracked objects (block / entity) then decorations.
- `map.py:97` FLAG_TEXTURE_UPDATE = 0x2. width/height/x_offset/y_offset followed by a
- `map.py:98` uvarint32-prefixed list of packed-int colours (one per pixel).

### 76 `AvailableCommandsPacket` (command)
- (via `CommandChainedSubcommandRelationship`) `command.py:46` Pre-v898 wrote the two indexes as uint16; v898 widened both to uint32. The
- (via `CommandChainedSubcommandRelationship`) `command.py:47` v975 wire form (uint32) is modelled here; older shapes are noted in the
- (via `CommandChainedSubcommandRelationship`) `command.py:48` field-level version gates of CommandData below.
- (via `CommandParamData`) `command.py:70` The `parse_symbol` packs both the parameter kind and an optional index into
- (via `CommandParamData`) `command.py:71` one of the packet's tables; the high bits choose between a primitive parser
- (via `CommandParamData`) `command.py:72` type, an enum (hard or soft), or a postfix string (CloudburstMC's
- (via `CommandParamData`) `command.py:73` writeParameter for the ARG_FLAG_VALID / ARG_FLAG_ENUM / ARG_FLAG_POSTFIX /
- (via `CommandParamData`) `command.py:74` ARG_FLAG_SOFT_ENUM bits 0x100000 / 0x200000 / 0x1000000 / 0x4000000).
- (via `CommandParamData`) `command.py:79` `param_options` is a bitmask over the CommandParamOption enum (CollapseEnum,
- (via `CommandParamData`) `command.py:80` HasSemanticConstraint, EnumAutocompleteExpanded, etc.) -- one byte added in v340.
- (via `CommandOverloadData`) `command.py:84` Pre-v594 carried no `is_chaining` flag.
- (via `CommandData`) `command.py:90` Pre-v594 carried no chained subcommands; v594 added the
- (via `CommandData`) `command.py:91` `chained_subcommand_indexes` table and v898 widened those indexes from
- (via `CommandData`) `command.py:92` uint16 to uint32.
- (via `CommandData`) `command.py:99` v898 changed the wire form to the serialize-name string of the enum, but
- (via `CommandData`) `command.py:100` the codegen doesn't apply field(type=str) overrides to cross-module enums
- (via `CommandData`) `command.py:101` today. Model as a raw string for v898+; the higher layer maps the
- (via `CommandData`) `command.py:102` serialize-name back to the enum.
- (via `CommandEnumData`) `command.py:110` v898 widens the value-index elements to uint32 unconditionally.
- (via `CommandEnumData`) `command.py:113` COMPILER_EXTENSION_NEEDED (until=898): each entry is one element from
- (via `CommandEnumData`) `command.py:114` the packet's `enum_values` string table, but the per-element width is
- (via `CommandEnumData`) `command.py:115` set per-packet, not per-element. CloudburstMC picks u8/u16/u32 based on
- (via `CommandEnumData`) `command.py:116` the total enum-values count. The DSL has no per-packet "list width" knob;
- (via `CommandEnumData`) `command.py:117` `field(prefix=...)` sets the count prefix, not the element size. The
- (via `CommandEnumData`) `command.py:118` `values` field is modelled below as the v898+ form.

### 79 `CommandOutputPacket` (command)
- (via `CommandOriginData`) `command.py:181` Name from bedrock-headers (struct CommandOriginData in server/commands/CommandOriginData.h).
- (via `CommandOriginData`) `command.py:187` Pre-v898 the player_id was a varint64 written only when the origin type was
- (via `CommandOriginData`) `command.py:188` DEV_CONSOLE or TEST; v898 widened it to a bare little-endian int64 always.
- (via `CommandOutputMessage`) `command.py:210` COMPILER_EXTENSION_NEEDED: v898 reordered this struct from
- (via `CommandOutputMessage`) `command.py:211` (success: bool, message_id: str, params: list[str]) to (message_id: str,
- (via `CommandOutputMessage`) `command.py:212` success: bool, params: list[str]); the DSL has no way to gate a per-field
- (via `CommandOutputMessage`) `command.py:213` reorder. The v975 shape (since=898) is modelled below.
- `command.py:229` Until v898 the trailing `data` was a bare string written only when
- `command.py:230` `output_type == DATA_SET`; since v898 it is an optional<string> emitted
- `command.py:231` unconditionally.

### 122 `BiomeDefinitionListPacket` (biome)
- (via `BiomeClimateData`) `biome.py:16` bedrock-headers android/r21_u4 (v786) ClimateAttributes carries mRedSporeDensity,
- (via `BiomeClimateData`) `biome.py:17` mBlueSporeDensity, mAshDensity, mWhiteAshDensity alongside the snow accumulation
- (via `BiomeClimateData`) `biome.py:18` floats; main (v975) BiomeClimateData has dropped them.
- (via `BiomeDefinitionChunkGenData`) `biome.py:31` COMPILER_EXTENSION_NEEDED: bedrock-headers shows many additional optional members
- (via `BiomeDefinitionChunkGenData`) `biome.py:32` (mConsolidatedFeatures, mMountainParams, mSurfaceMaterialAdjustments, mOverworldGenRules,
- (via `BiomeDefinitionChunkGenData`) `biome.py:33` mMultinoiseGenRules, mLegacyWorldGenRules, mReplaceBiomes, mVillageType, mSurfaceBuilderData,
- (via `BiomeDefinitionChunkGenData`) `biome.py:34` mSubsurfaceBuilderData) whose nested fields encode string members as uint16 indices into the
- (via `BiomeDefinitionChunkGenData`) `biome.py:35` packet-level BiomeStringList. The DSL has no "look this index up in a sibling pool".
- (via `BiomeDefinitionData`) `biome.py:48` -1 sentinel means "vanilla, id absent" (writeShortLE branch at v827+)
- (via `BiomeDefinitionData`) `biome.py:51` bedrock-headers android/r21_u4 (v786) ClimateAttributes confirms the four
- (via `BiomeDefinitionData`) `biome.py:52` spore density floats; main (v975) drops them from BiomeDefinitionData.
- `biome.py:77` COMPILER_EXTENSION_NEEDED: each BiomeDefinitionData nested field is written with
- `biome.py:78` uint16 indices into the cumulative `string_list` pool that gets emitted only after
- `biome.py:79` all entries. Codegen needs cross-field state to thread the same string pool
- `biome.py:80` through the nested writes; the map shape itself is expressible as dict[K, V].

### 149 `PlayerArmorDamagePacket` (inventory)
- `inventory.py:735` COMPILER_EXTENSION_NEEDED: until=844 the wire is a uint8 bitfield over ArmorSlot
- `inventory.py:736` followed by N varint32 damages where N = popcount(bitfield) and the i-th damage
- `inventory.py:737` corresponds to the i-th set bit. The max bit index is 3 in v407..v712 (HEAD..FEET)
- `inventory.py:738` and 4 in v712..v844 (adds BODY). Cannot be expressed with field(when=) per-slot
- `inventory.py:739` because the DSL has no popcount nor "the bit at index i is set" predicate over an
- `inventory.py:740` integer-valued bitfield. (At v844 the wire became a regular uvarint32-prefixed
- `inventory.py:741` list[ArmorSlotAndDamagePair], which we could model directly if v844+ were the
- `inventory.py:742` only era to support.)

### 198 `CameraPresetsPacket` (camera)
- (via `CameraPreset`) `camera.py:300` pitch
- (via `CameraPreset`) `camera.py:301` yaw
- `camera.py:324` COMPILER_EXTENSION_NEEDED: the v575 wire form bundled every preset into a
- `camera.py:325` single root CompoundTag (key "presets" -> list of compound presets), where
- `camera.py:326` each preset compound carried optional numeric keys -- pos_x/pos_y/pos_z,
- `camera.py:327` rot_x, rot_y -- only when the in-memory field was non-null. The DSL has
- `camera.py:328` no surface for "the tag's child keys are themselves the optional-field
- `camera.py:329` projection of a struct", so the v575..v618 era is left as a hand-rolled
- `camera.py:330` CompoundTag payload and the modern list-of-CameraPreset is gated since
- `camera.py:331` v618.

### 199 `UnlockedRecipesPacket` (crafting)
- `crafting.py:237` COMPILER_EXTENSION_NEEDED: until v589 the wire form was a single `bool` (true == NEWLY_UNLOCKED_RECIPES, false == INITIALLY_UNLOCKED_RECIPES); since v589 it is a uint32 enum

### 300 `CameraInstructionPacket` (camera)
- (via `CameraInstructionSetEaseOption`) `camera.py:120` BDS namespace CameraInstructionOptions holds the per-instruction option
- (via `CameraInstructionSetEaseOption`) `camera.py:121` structs that CameraInstruction aggregates. Hoisted to top-level here because
- (via `CameraInstructionSetEaseOption`) `camera.py:122` the DSL forbids nested classes whose version-gated declaration leaves the
- (via `CameraInstructionSetEaseOption`) `camera.py:123` enclosing namespace empty on pre-since snapshots.
- (via `CameraInstructionSetEaseOption`) `camera.py:125` COMPILER_EXTENSION_NEEDED (since=944): the easing type is written as the
- (via `CameraInstructionSetEaseOption`) `camera.py:126` serialize-name string on v944+ rather than the EasingType ordinal byte
- (via `CameraInstructionSetEaseOption`) `camera.py:127` used in v618..v944. The v944+ shape is the byte form modelled here.
- (via `CameraInstructionSet`) `camera.py:140` BDS: mDefault; renamed to avoid C++ keyword.
- (via `CameraInstructionFov`) `camera.py:169` COMPILER_EXTENSION_NEEDED (since=944): the ease type switched from a
- (via `CameraInstructionFov`) `camera.py:170` one-byte EasingType ordinal to the serialize-name string of the easing
- (via `CameraInstructionFov`) `camera.py:171` function. Same DSL gap as CameraInstructionSetEaseOption.easing_type
- (via `CameraInstructionFov`) `camera.py:172` above.
- (via `CameraRotationOption`) `camera.py:221` Gophertunnel's CameraRotationOption / CameraProgressOption are written as
- (via `CameraRotationOption`) `camera.py:222` (value, time, easing_type-as-string) triples. The DSL spelling below keeps
- (via `CameraRotationOption`) `camera.py:223` easing_type as a string because v944+ wired it that way; the byte-ordinal
- (via `CameraRotationOption`) `camera.py:224` form before v944 is not modelled.
- (via `SplineInstruction`) `camera.py:237` CameraInstructionPacket.camera_instruction.spline carries the
- (via `SplineInstruction`) `camera.py:238` CameraSplineInstruction shape from gophertunnel (TotalTime + Optional<u8>
- (via `SplineInstruction`) `camera.py:239` spline_type + curve points + per-axis keyframes + identifier + load_from_json).
- (via `CameraInstruction`) `camera.py:251` COMPILER_EXTENSION_NEEDED (until=618): the v575 codec wrapped the entire
- (via `CameraInstruction`) `camera.py:252` packet body in a single CompoundTag (`set`, `clear`, `fade` keys with
- (via `CameraInstruction`) `camera.py:253` nested compounds for ease/pos/rot/color/time). v618 replaced the NBT
- (via `CameraInstruction`) `camera.py:254` wrapper with the inline binary optional layout below. The pre-v618 NBT
- (via `CameraInstruction`) `camera.py:255` form is left modelled only by these notes.

### 308 `SetHudPacket` (graphics)
- `graphics.py:323` COMPILER_EXTENSION_NEEDED: each element is a HudElement enum, but list[Enum] cannot carry a `field(type=<primitive>)` override; the wire encoding switches from uvarint32 (<v786) to varint32 (>=v786)

### 320 `CameraAimAssistPresetsPacket` (camera)
- (via `CameraAimAssistPresetDefinition`) `camera.py:82` SharedTypes::v1_21_120::CameraAimAssistPresetDefinition. The wire form
- (via `CameraAimAssistPresetDefinition`) `camera.py:83` spreads the BDS-side mExclusionSettings sub-struct across the preset's top
- (via `CameraAimAssistPresetDefinition`) `camera.py:84` level. Pre-v776 the wire prefix also carried a category-reference string;
- (via `CameraAimAssistPresetDefinition`) `camera.py:85` pre-v898 the exclusion list was a single combined list rather than split
- (via `CameraAimAssistPresetDefinition`) `camera.py:86` into block/entity/block-tag.
- (via `CameraAimAssistPresetDefinition`) `camera.py:89` COMPILER_EXTENSION_NEEDED: v766..v776 prepended a `categories` string here
- (via `CameraAimAssistPresetDefinition`) `camera.py:90` that was removed at v776, and v766..v898 wrote a single `exclusion_list`
- (via `CameraAimAssistPresetDefinition`) `camera.py:91` instead of the v898 split into block/entity/block_tag/entity_type_families
- (via `CameraAimAssistPresetDefinition`) `camera.py:92` exclusion lists (and v924 added the entity_type_families list). Three
- (via `CameraAimAssistPresetDefinition`) `camera.py:93` distinct preset layouts in this window cannot share one field list -- the
- (via `CameraAimAssistPresetDefinition`) `camera.py:94` DSL has no way to redeclare a variable-arity field block across version
- (via `CameraAimAssistPresetDefinition`) `camera.py:95` intervals. The v975 form is modelled below.
- `camera.py:110` v766..v800 wrote a `CameraAimAssistCategories` wrapper (an identifier +
- `camera.py:111` nested list of categories) BEFORE the presets. At v800 the outer shape
- `camera.py:112` flattened: the packet writes a flat list of CameraAimAssistCategoryDefinition
- `camera.py:113` followed by the presets, then the one-byte operation. The pre-v800 wrapper
- `camera.py:114` has no useful in-memory analogue and is left as a compiler-extension TODO.

### 328 `PrimitiveShapesPacket` (graphics)
- (via `PrimitiveShapeDataPayload`) `graphics.py:169` COMPILER_EXTENSION_NEEDED: max_render_distance (mMaxRenderDistance) was inserted
- (via `PrimitiveShapeDataPayload`) `graphics.py:170` before color in the v975 codec but the BDS payload struct still lists it last. The DSL
- (via `PrimitiveShapeDataPayload`) `graphics.py:171` has no `since` interleaving inside a single struct declaration that reorders fields, so
- (via `PrimitiveShapeDataPayload`) `graphics.py:172` the v975 insertion point needs codegen support.
- (via `PrimitiveShapeDataPayload`) `graphics.py:178` Pre-v859, the variant payload was inlined as a fixed sequence of optionals per shape kind
- (via `PrimitiveShapeDataPayload`) `graphics.py:179` rather than tag-discriminated. The since=859 codec switches to writing a uvarint payload
- (via `PrimitiveShapeDataPayload`) `graphics.py:180` type ahead of the variant body. v1001 grew the discriminant with cylinder, pyramid,
- (via `PrimitiveShapeDataPayload`) `graphics.py:181` ellipsoid, and cone shape payloads.

## Needs review

Every comment below must be resolved (or the field/type cleaned up) for the packet to count as complete. `(via X)` means the comment lives on a referenced type, not the packet itself.

### 7 `ResourcePackStackPacket` (resource_pack)
- `resource_pack.py:82` mTexturePackRequired
- `resource_pack.py:83` v291..v898 wrote the behavior-pack stack ahead of the texture-pack stack; v898
- `resource_pack.py:84` dropped the behavior list entirely.
- `resource_pack.py:87` v313..v419 wrote a lone boolean that stood in for the experiments table that
- `resource_pack.py:88` arrived in v419.
- `resource_pack.py:90` mBaseGameVersion
- (via `PackInstanceId`) `resource_pack.py:69` BDS: PackInstanceId. BDS stores mPackId as PackIdVersion, but the wire flattens
- (via `PackInstanceId`) `resource_pack.py:70` the id and version to two separate strings.

### 11 `StartGamePacket` (game)
- (via `EducationEditionOffer`) `game.py:57` TODO: BDS marks this `China_Deprecated`; confirm the deprecation version

### 18 `MoveActorAbsolutePacket` (actor)
- (via `MoveActorAbsoluteData`) `actor.py:99` header packs four flags: FLAG_ON_GROUND=0x1, FLAG_TELEPORTED=0x2,
- (via `MoveActorAbsoluteData`) `actor.py:100` FLAG_FORCE_MOVE=0x4, FLAG_FORCE_COMPLETION=0x8 (new at v975).

### 19 `MovePlayerPacket` (player)
- `player.py:188` BDS: PlayerPositionModeComponent::PositionMode (uint8 on the wire).
- `player.py:195` BDS: MinecraftEventing::TeleportationCause (int32 on the wire).

### 20 `PassengerJumpPacket` (actor)
- `actor.py:649` PassengerJumpPacket (id=20, until=800) was removed at v800. The DSL requires
- `actor.py:650` a packet redeclaration to use until=, but no shape exists for v975. Drop the
- `actor.py:651` version gate -- the packet lives in the generated surface but BDS no longer
- `actor.py:652` uses it.

### 35 `ActorPickRequestPacket` (actor)
- `actor.py:563` Wire: little-endian int64, not the usual varint actor id.

### 38 `HurtArmorPacket` (actor)
- `actor.py:579` std::bitset<5>; BDS aliases as ArmorBitset.

### 49 `InventoryContentPacket` (inventory)
- `inventory.py:526` BDS mInventoryId (ContainerID)
- `inventory.py:527` v291..v407 wrote items as the legacy NetworkItemInstanceDescriptor; from v407
- `inventory.py:528` the wire encoding switched to NetworkItemStackDescriptor (the "net item" form).
- `inventory.py:531` v712 wrote a bare uvarint32 dynamic_id where BDS keeps the full FullContainerName;
- `inventory.py:532` v729 elevated it to the structured (container_slot + optional uint32) form;
- `inventory.py:533` v748 dropped the trailing dynamic_container_size and appended a storage item.

### 50 `InventorySlotPacket` (inventory)
- `inventory.py:544` BDS mInventoryId (ContainerID)
- `inventory.py:546` v975 wrapped the optional cousins (full container name + storage item) ahead
- `inventory.py:547` of the slot item; earlier versions wrote them inline (or not at all).
- `inventory.py:550` v712 wrote only a bare uvarint32 dynamic_id where v729+ writes the structured
- `inventory.py:551` FullContainerName; v729 added a trailing dynamic_container_size that v748
- `inventory.py:552` replaced with a storage item.
- `inventory.py:557` v291..v407 wrote items as the legacy NetworkItemInstanceDescriptor; from v407
- `inventory.py:558` the wire encoding switched to NetworkItemStackDescriptor.

### 52 `CraftingDataPacket` (crafting)
- (via `CraftingDataEntry`) `crafting.py:127` BDS: CraftingDataEntry. Polymorphic recipe record tagged by CraftingDataEntryType.
- (via `ShapedChemistryRecipe`) `crafting.py:107` BDS: ShapedChemistryRecipe (alias of ShapedRecipe wire form).
- (via `ShapedRecipe`) `crafting.py:91` BDS: ShapedRecipe. Ingredients are an inline width*height array with no
- (via `ShapedRecipe`) `crafting.py:92` length prefix -- the count comes from sibling fields.
- (via `ShapelessChemistryRecipe`) `crafting.py:62` BDS: ShapelessChemistryRecipe (alias of ShapelessRecipe wire form).
- (via `UserDataShapelessRecipe`) `crafting.py:57` BDS: UserDataShapelessRecipe (alias of ShapelessRecipe wire form).

### 57 `PlayerInputPacket` (input)
- `input.py:221` PlayerInputPacket (id=57, until=800) was removed at v800. The DSL requires a
- `input.py:222` packet redeclaration to use until=, and no successor lives at id=57 in v975.
- `input.py:223` Drop the gate -- packet is emitted but BDS no longer uses it.

### 58 `LevelChunkPacket` (level)
- `level.py:76` At v486+ the uvarint32 sub-chunk count carries two sentinel values:
- `level.py:77` 0xFFFFFFFF = "request mode limitless" (no trailer), 0xFFFFFFFE = "request
- `level.py:78` mode limited" followed by a uint16 LE highest-sub-chunk index. The trailer
- `level.py:79` is gated by comparing the raw wire integer against the sentinel.

### 71 `ItemFrameDropItemPacket` (player)
- `player.py:232` ItemFrameDropItemPacket (id=71, until=662) was removed before v975. The DSL
- `player.py:233` requires a packet redeclaration to use until=. No successor exists at id=71
- `player.py:234` in v975, so drop the gate -- packet is emitted but unused at the v975 target.

### 72 `GameRulesChangedPacket` (game)
- `game.py:550` bedrock-headers wraps the list in a GameRulesChangedPacketData (mRuleData) holding
- `game.py:551` std::vector<GameRule> mRules; on the wire this collapses to the same varuint32-prefixed
- `game.py:552` list, modeled directly here.

### 74 `BossEventPacket` (actor)
- `actor.py:466` Pre-776: a single `name` field gated on ADD or UPDATE_NAME. From 776 BDS
- `actor.py:467` adds a parallel `filtered_name` next to it. Modelling only the v776+ form
- `actor.py:468` here -- the pre-776 redeclaration would overlap with the with-block, which
- `actor.py:469` the DSL does not currently support for nested field redeclarations.

### 77 `CommandRequestPacket` (command)
- (via `CommandOriginData`) `command.py:181` Name from bedrock-headers (struct CommandOriginData in server/commands/CommandOriginData.h).
- (via `CommandOriginData`) `command.py:187` Pre-v898 the player_id was a varint64 written only when the origin type was
- (via `CommandOriginData`) `command.py:188` DEV_CONSOLE or TEST; v898 widened it to a bare little-endian int64 always.

### 80 `UpdateTradePacket` (actor)
- `actor.py:747` v291 wrote a merchant-timer varint here (40 when economy trading), v313
- `actor.py:748` wrote it (40 when new-trading-ui) and added trader_tier next. v354 dropped
- `actor.py:749` the legacy timer and moved use_new_trade_screen / using_economy_trade
- `actor.py:750` after display_name. The booleans live on the wire only from v354.

### 90 `StructureBlockUpdatePacket` (structure)
- (via `StructureEditorData`) `structure.py:52` Body still needs wiring: BDS declares StructureEditorData with nested
- (via `StructureEditorData`) `structure.py:53` StructureSettings, StructureBlockType, StructureRedstoneSaveMode. The wire
- (via `StructureEditorData`) `structure.py:54` shape changed at v340/v361/v388/v554/v776.

### 96 `SetLastHurtByPacket` (actor)
- `actor.py:690` TODO: protocol-docs reports the wire as uvarint32 (unsigned); gophertunnel and
- `actor.py:691` CloudburstMC v291 both encode it as varint32 (signed). Reconcile against BDS.

### 108 `SetScorePacket` (scoreboard)
- `scoreboard.py:69` Each entry's body is action-gated -- a CHANGE entry carries the full identity
- `scoreboard.py:70` suffix (player / entity / fake-player name), a REMOVE entry stops after the
- `scoreboard.py:71` leading (scoreboard_id, objective_name, score_value) triple. The DSL has no
- `scoreboard.py:72` spelling for "every list element references the outer packet's discriminator"
- `scoreboard.py:73` so the packet body below splits the wire form into two action-gated lists,
- `scoreboard.py:74` each of which carries its own element type. Exactly one of the two is
- `scoreboard.py:75` populated on a real packet.

### 109 `LabTablePacket` (crafting)
- `crafting.py:217` CloudburstMC's LabTableSerializer writes pos via helper.writeVector3i
- `crafting.py:218` (three signed varints unconditionally), NOT helper.writeBlockPosition,
- `crafting.py:219` so no v944 unsigned-Y to signed-Y switch applies here.

### 110 `UpdateBlockSyncedPacket` (level)
- (via `ActorBlockSyncMessage`) `level.py:264` bedrock-headers declares
- (via `ActorBlockSyncMessage`) `level.py:265` `ActorBlockSyncMessage { ActorUniqueID mEntityUniqueID; MessageId mMessage; }`
- (via `ActorBlockSyncMessage`) `level.py:266` but the wire shape from CloudburstMC and gophertunnel encodes the entity id
- (via `ActorBlockSyncMessage`) `level.py:267` as uvarint64 (ActorRuntimeID), not the zigzag-signed varint64 that
- (via `ActorBlockSyncMessage`) `level.py:268` ActorUniqueID would use. Wire as ActorRuntimeID + uvarint64 MessageId.
- (via `ActorBlockSyncMessage`) `level.py:270` BDS: ActorBlockSyncMessage::MessageId (uint32_t, written as uvarint32).

### 111 `MoveActorDeltaPacket` (actor)
- `actor.py:596` MoveActorDeltaPacket header-bit predicate works in C++ only if `flags & enum`
- `actor.py:597` compiles, which `enum class` does not. The header bits live as plain integer
- `actor.py:598` constants on the wire and the BDS code masks them with raw uint16 values, so
- `actor.py:599` we mirror that by dropping the enum and using integer literals directly.
- `actor.py:602` Header bits (mirror BDS MoveActorDeltaPacket::Flags):
- `actor.py:603` HAS_POSITION_X = 1, HAS_POSITION_Y = 2, HAS_POSITION_Z = 4,
- `actor.py:604` HAS_ROTATION_X = 8, HAS_ROTATION_Y = 16, HAS_ROTATION_Y_HEAD = 32,
- `actor.py:605` IS_ON_GROUND = 64, FORCE_MOVE = 128, FORCE_MOVE_LOCAL_ENTITY = 256,
- `actor.py:606` FORCE_COMPLETION = 512.
- `actor.py:610` v291..v418 wrote positional deltas as varint32, then v419 switched to absolute floats.

### 112 `SetScoreboardIdentityPacket` (scoreboard)
- (via `ScoreboardIdentityUpdateEntry`) `scoreboard.py:92` CloudburstMC v291 wrote the per-entry identity as a UUID; gophertunnel and BDS
- (via `ScoreboardIdentityUpdateEntry`) `scoreboard.py:93` write the player_id as a varint64 (the ActorUniqueID type), present only when
- (via `ScoreboardIdentityUpdateEntry`) `scoreboard.py:94` the outer SetScoreboardIdentityPacket.type == UPDATE. The DSL has no spelling
- (via `ScoreboardIdentityUpdateEntry`) `scoreboard.py:95` for "every list element references the outer packet's type discriminator", so
- (via `ScoreboardIdentityUpdateEntry`) `scoreboard.py:96` the packet body below splits the wire form into two action-gated lists, each
- (via `ScoreboardIdentityUpdateEntry`) `scoreboard.py:97` of which carries its own element type. Exactly one of the two is populated on
- (via `ScoreboardIdentityUpdateEntry`) `scoreboard.py:98` a real packet.

### 116 `BlockPalettePacket` (level)
- `level.py:44` bedrock-headers android/r26_u2 declares this id as BlockPalette_deprecated in
- `level.py:45` MinecraftPacketIds. Neither CloudburstMC, gophertunnel, nor EndstoneMC/protocol-docs
- `level.py:46` carries a body for it -- the id is allocated but the packet is no longer serialized.
- `level.py:47` Empty stub kept so the id is not silently absent from the v975 enum surface.

### 123 `LevelSoundEventPacket` (level)
- `level.py:115` v1001 replaced the uvarint32 enum ordinal with the lower-cased sound-event
- `level.py:116` name as a length-prefixed string (e.g. "item.use.on", "fall.big").
- `level.py:124` BDS names this mActor (ActorUniqueID), but the wire encodes it as a little-endian int64,
- `level.py:125` not the usual varint64.

### 125 `VideoStreamConnectPacket` (graphics)
- `graphics.py:368` bedrock-headers android/r26_u2 declares this id as VideoStreamConnect_DEPRECATED in
- `graphics.py:369` MinecraftPacketIds. Neither CloudburstMC, gophertunnel, nor EndstoneMC/protocol-docs
- `graphics.py:370` carries a body for it -- the id is allocated but the packet is no longer serialized.
- `graphics.py:371` Empty stub kept so the id is not silently absent from the v975 enum surface.

### 127 `AddEntityPacket` (actor)
- `actor.py:254` bedrock-headers android/r26_u2 declares this id as AddEntity_DEPRECATED in
- `actor.py:255` MinecraftPacketIds. Neither CloudburstMC, gophertunnel, nor EndstoneMC/protocol-docs
- `actor.py:256` carries a body for it -- the id is allocated but the packet is no longer serialized.
- `actor.py:257` Empty stub kept so the id is not silently absent from the v975 enum surface.

### 128 `RemoveEntityPacket` (actor)
- `actor.py:629` bedrock-headers android/r26_u2 declares this id as RemoveEntity_DEPRECATED in
- `actor.py:630` MinecraftPacketIds. Neither CloudburstMC, gophertunnel, nor EndstoneMC/protocol-docs
- `actor.py:631` carries a body for it -- the id is allocated but the packet is no longer serialized.
- `actor.py:632` Empty stub kept so the id is not silently absent from the v975 enum surface.

### 132 `StructureTemplateDataRequestPacket` (structure)
- (via `StructureTemplateRequestOperation`) `structure.py:113` TODO: gophertunnel removed this constant at v685 (1.21.20), CloudburstMC marks it `@deprecated since v712`, and bedrock-headers (latest) omits it entirely. Until=685 reflects gophertunnel; confirm against an older BDS...

### 136 `ClientCacheMissResponsePacket` (login)
- (via `MissingBlobData`) `login.py:22` ClientBlobCache::BlobId == uint64_t

### 144 `PlayerAuthInputPacket` (input)
- `input.py:186` TODO: confirm against BDS
- (via `ItemStackRequestActionCraftRecipeAuto`) `inventory.py:408` always set to the same value as num_crafts

### 146 `PlayerEnchantOptionsPacket` (inventory)
- (via `EnchantmentInstance`) `inventory.py:753` TODO: at v975 CloudburstMC switched EnchantData.Type from uint8 to uvarint32,
- (via `EnchantmentInstance`) `inventory.py:754` but gophertunnel still marshals EnchantmentInstance.Type as a plain uint8 on
- (via `EnchantmentInstance`) `inventory.py:755` master. Modelled per CloudburstMC; revisit if gophertunnel catches up the
- (via `EnchantmentInstance`) `inventory.py:756` other way.

### 147 `ItemStackRequestPacket` (player)
- (via `ItemStackRequestActionCraftRecipeAuto`) `inventory.py:408` always set to the same value as num_crafts

### 148 `ItemStackResponsePacket` (inventory)
- (via `ItemStackResponseContainerInfo`) `inventory.py:688` pre-v776, BDS-invisible; trust CloudburstMC

### 161 `CorrectPlayerMovePredictionPacket` (player)
- `player.py:166` Modeling the v827+ wire shape only -- the pre-v827 era reordered
- `player.py:167` prediction_type and the vehicle fields several times. v975 is the target so
- `player.py:168` the simpler post-v827 shape is sufficient.

### 164 `ClientboundDebugRendererPacket` (graphics)
- `graphics.py:43` TODO: three references give three distinct shapes for payload_type:
- `graphics.py:44` CloudburstMC writes a uvarint32 ordinal in [428, 671) and int32-LE
- `graphics.py:45` ordinal in [671, latest]; EndstoneMC protocol-docs and gophertunnel
- `graphics.py:46` both say it is a length-prefixed string ("cleardebugmarkers" /
- `graphics.py:47` "adddebugmarkercube") instead. Modeled here as the v671+ int32-LE
- `graphics.py:48` form because the BDS PayloadType : uint8_t header most directly
- `graphics.py:49` matches a numeric ordinal, but the pre-v671 uvarint32 era and the
- `graphics.py:50` protocol-docs string form both still need a separate codec path.

### 172 `UpdateSubChunkBlocksPacket` (level)
- (via `ActorBlockSyncMessage`) `level.py:264` bedrock-headers declares
- (via `ActorBlockSyncMessage`) `level.py:265` `ActorBlockSyncMessage { ActorUniqueID mEntityUniqueID; MessageId mMessage; }`
- (via `ActorBlockSyncMessage`) `level.py:266` but the wire shape from CloudburstMC and gophertunnel encodes the entity id
- (via `ActorBlockSyncMessage`) `level.py:267` as uvarint64 (ActorRuntimeID), not the zigzag-signed varint64 that
- (via `ActorBlockSyncMessage`) `level.py:268` ActorUniqueID would use. Wire as ActorRuntimeID + uvarint64 MessageId.
- (via `ActorBlockSyncMessage`) `level.py:270` BDS: ActorBlockSyncMessage::MessageId (uint32_t, written as uvarint32).
- (via `UpdateSubChunkNetworkBlockInfo`) `level.py:295` BlockRuntimeId
- (via `UpdateSubChunkNetworkBlockInfo`) `level.py:296` BDS in-memory is `byte mUpdateFlags`; wire is uvarint32

### 178 `CodeBuilderSourcePacket` (script)
- `script.py:46` Removed at v685, field name from CloudburstMC (pre-v776, BDS-invisible).

### 190 `EditorNetworkPacket` (script)
- `script.py:64` TODO: protocol-docs and bedrock-headers say the body is two strings (raw_variant_name + raw_variant_data),
- `script.py:65` but gophertunnel and CloudburstMC marshal a single network-little-endian CompoundTag here. Modelling as the latter.

### 194 `GameTestRequestPacket` (game)
- (via `TestParameters`) `game.py:556` CloudburstMC writes a flat block of TestParameters fields inline; the BDS
- (via `TestParameters`) `game.py:557` header bundles them into gametest::TestParameters but the wire is the
- (via `TestParameters`) `game.py:558` same flat sequence.

### 311 `ClientboundLoadingScreenPacket` (ui)
- `ui.py:49` bedrock-headers android/r26_u2 declares this id as ClientboundLoadingScreenPacket_Deprecated
- `ui.py:50` in MinecraftPacketIds. Neither CloudburstMC, gophertunnel, nor EndstoneMC/protocol-docs
- `ui.py:51` carries a body for it -- the id is allocated but the packet is no longer serialized. The
- `ui.py:52` loading-screen flow is now driven by ServerboundLoadingScreenPacket (id=312) plus the
- `ui.py:53` ChangeDimensionPacket.loading_screen_id field added at v712. Empty stub kept so the id
- `ui.py:54` is not silently absent from the v975 enum surface.

### 315 `ServerboundDiagnosticsPacket` (player)
- (via `MemoryCategoryCounter`) `player.py:91` TODO: confirm against BDS -- MemoryCategory enum has 90+ entries that shift across versions;
- (via `MemoryCategoryCounter`) `player.py:92` modelling as raw uint8 for now until a future pass adds the full enum.

### 327 `ClientboundControlSchemeSetPacket` (player)
- `player.py:151` BDS: ControlScheme::Scheme.

### 338 `CameraSplinePacket` (camera)
- (via `CameraRotationOption`) `camera.py:221` Gophertunnel's CameraRotationOption / CameraProgressOption are written as
- (via `CameraRotationOption`) `camera.py:222` (value, time, easing_type-as-string) triples. The DSL spelling below keeps
- (via `CameraRotationOption`) `camera.py:223` easing_type as a string because v944+ wired it that way; the byte-ordinal
- (via `CameraRotationOption`) `camera.py:224` form before v944 is not modelled.

### 341 `LocatorBarPacket` (locator)
- (via `ServerWaypointPayload`) `locator.py:28` v975 replaced the texture-id ordinal with a texture-path string and added
- (via `ServerWaypointPayload`) `locator.py:29` an icon-size Vec2 alongside it.
- (via `ServerWaypointPayload`) `locator.py:33` ARGB packed mce::Color

## Coverage gaps -- packets with no @packet

These ids carry no `@packet` in the DSL. Most are historical packets removed before v975 that cannot be modeled because a lone `@packet(until=)` is unsupported (the id is either unused on v975 or reused by a successor that is modeled). A few are live on v975 but blocked on a compiler feature.

| ID | Packet | File | Reason |
|---:|--------|------|--------|
| 12 | AddPlayerPacket | actor | compiler: needs NetworkItemStackDescriptor (resolver cycle) |
| 15 | AddItemActorPacket | actor | compiler: needs NetworkItemStackDescriptor (resolver cycle) |
| 16 | AddHangingEntityPacket | actor | removed before v975 (lone until= not expressible) |
| 23 | ExplodePacket | level | removed before v975 (lone until= not expressible) |
| 23 | TickSyncPacket | game | removed before v975 (lone until= not expressible) |
| 24 | LevelSoundEventV1Packet | level | removed before v975 (lone until= not expressible) |
| 32 | MobArmorEquipmentPacket | actor | compiler: needs NetworkItemStackDescriptor (resolver cycle) |
| 117 | ScriptCustomEventPacket | script | removed before v975 (lone until= not expressible) |
| 120 | LevelSoundEventV2Packet | level | removed before v975 (lone until= not expressible) |
| 163 | FilterTextPacket | game | removed before v975 (lone until= not expressible) |
| 174 | SubChunkPacket | level | removed before v975 (lone until= not expressible) |
| 301 | CompressedBiomeDefinitionListPacket | biome | removed before v975 (lone until= not expressible) |
| 330 | ClientboundDataStorePacket | ui | compiler: needs union / data-store value type |
| 332 | ServerboundDataStorePacket | ui | compiler: needs union / data-store value type |

## Free-standing DSL notes

Comments not tied to a modeled packet or a genuine gap -- naming rationale, dating notes, and stale omission notes about ids that are in fact covered. They still count against a comment-free DSL.

- `actor.py:213` ============================================================================ Wave 3a additions: helper types + actor-related packets ==================================...
- `actor.py:339` PlayerPermissionLevel lives in protocol.game. We cannot import it without a circular dependency (game imports ActorRuntimeID from here). Wire form is uint8 for Seriali...
- `actor.py:569` ActorDamageCause is a large enum; wire is a varint of the underlying int.
- `actor.py:723` ContainerID lives in protocol.inventory (signed-char in BDS, SharedTypes::Legacy::ContainerID). protocol.inventory imports protocol.actor, so we cannot import inventor...
- `block.py:4` LecternUpdatePacket (id=124, since=340, until=361) is omitted: lone @packet(until=) is not expressible in the DSL today and the body is fully removed long before v975....
- `common.py:43` Cereal writes SharedTypes::Color255RGBA as a tagged union over a CSS-style hex string or a raw four-int RGBA array; the BDS struct itself is one `mce::Color { float r,...
- `game.py:1047` VideoStreamConnectPacket (id=125, v340..v361) is omitted: removed before v975 and the DSL cannot express a lone @packet(until=) today.
- `inventory.py:21` ContainerID is signed-char in BDS (SharedTypes::Legacy::ContainerID).
- `player.py:141` ============================================================================ Wave 3a additions: helper types + player-related packets =================================...
