---
paths:
  - "tests/goldens/**"
  - "tests/test_goldens.py"
  - ".claude/skills/goldens/**"
---

# Goldens

A golden is a case BDS agrees with; the `goldens` skill runs BDS over the cases.

## Case files

- Keep a packet's cases in `tests/goldens/v<protocol>/<id:03>_<snake_name>.json`, `<snake_name>` being the class the folder's module binds at `<id>` without its trailing `Packet`, in snake case: a JSON array of `{"id", "value", "bytes"}`.
- Name a case's `id` for the state it reaches, in lower_with_under, as the `<state>` of Google's `test_<method_under_test>_<state>` (`every_optional_absent`, `item_use_arm`), unique within its file; a packet's only case names what it holds (`player_spawn`), never `basic`, `default`, `full` or a number.
- Hold every packet live at 2168 in `v2168/`, checked by BDS 1.26.40.8; another protocol's folder holds a packet only when its class differs from the neighbour's toward 2168.
- Write `value` exactly as `to_json` returns it, key order included, and `bytes` as the lowercase hex of the library's encoding of `value`; never type `bytes` by hand.
- Write a case file as `layout(cases)` from `test_goldens.py`, which puts each flat list on one line, regenerated from the library after every edit.
- Land a case on origin only once a BDS run writes its bytes back unchanged.
- Compare a field declared as one type over another wire type (`rot_x: int8 = field(type=uint8)`) through its wire type, as BDS prints it.
- Compare an enum member with the int BDS prints for it through the member's number in our schema.
- Compare an `ActorRuntimeID`, `ActorUniqueID`, `DimensionType`, `PlayerInputTick` or `Color` with the one member BDS wraps it in; unwrap no other type.
- Never change the bytes of a case BDS writes back unchanged; change its value only for a rename or a library type fix.

## Writing cases

- Reach every branch of the generated codec at 2168 that valid data takes, with as few cases as a unit test would use, each a golden BDS writes back unchanged; read and validation failures stay outside the measure, and a valid-path branch no golden reaches is a generator defect.
- Add a case only when it reaches a branch no other case does, and drop one whose branches the others reach.
- Count a packet's branches in its generated codec; a runtime header's branch, such as a multi-byte varint, counts across the suite, so never grow a list or string to reach one.
- Change a case's leaves without changing its branch identity: each optional stays present or absent, each variant arm and gating bool stays, and an empty list stays empty.
- Give a leaf a value other than its type's zero unless its branch needs zero, so a skipped field changes the bytes.
- Keep a list to one element and a string to a few characters unless a branch needs more.
- Give every leaf data BDS accepts (below); when BDS rewrites or refuses a value, fix the schema or add the missing line here with its evidence in the commit body, never retry other values until one passes.
- Never run BDS from a test.
- Compare a BDS run with the `goldens` skill's `compare.py`; run every other step as an inline command and save no other script, not even in a scratchpad or `build/`.

## Valid data at 2168

- Read enum bindings, limits, items and blocks from the dump of the build that checks the folder, never from another build's protocol-docs.
- Pick an enum member the field's dump binds, never a `sentinel()` or `deprecated=True` member, and keep a value inside the field's dump limits: `minimum`, `maximum`, `max_length`, `max_items`, `pattern` and `enum_values`.
- Name an item by an id the build's own item dump lists, with an aux of 0 for a block item and 0..32767 otherwise, and a stack size of 1..64; name a block by a runtime id its block palette lists, written as the uint32 of the same bits when the palette shows it signed.
- Make a `CraftResultsActionData` craft result an `ItemNameDescriptorData` naming a listed item.
- Give a recipe ingredient's descriptor only `name`, `tags` or `item_tag`, and an `item_tag` only a registered item carries.
- Use only `query.any_tag` and `query.all_tags` in the `tag_expression` of a Molang descriptor inside `PlayerAuthInputPacket.item_stack_request`.
- Fill `AvailableActorIdentifiersPacket`'s tag with an `idlist` ListTag of actor entries, each `bid` as `minecraft:` when it has no other id.
- Sort a `CompoundTag`'s keys, as BDS's `std::map` holds them.
- Give a data store compound one key and hold several values in a list: BDS writes the keys of a compound in an order of its own, and a list keeps its order.
- Write a `SemVersion` as `X.Y.Z`; a min engine version, a skin's `geometry_data_min_engine_version` included, as `X.Y.Z` with optional pre-release and build suffixes, never four parts or `*`; a base game version as `X.Y.Z` or `*`, without a pre-release suffix or a fourth part.
- Write JSON BDS parses as jsoncpp's FastWriter prints it: keys sorted, no spaces, a trailing newline (`{}` comes back as `{}\n` in a skin's `geometry_data` and a command output's `data`), numbers in its form (`1000.0` for `1e3`); `form_json` and `json_input` stay as written.
- Give every copy of a member that BDS binds under several names the same value: `PlayerVideoCapturePacket`'s start and stop slots, `CylinderDataPayload`'s `radius_x` and `radius_z`, each slot of `ClientboundUpdateSoundDataPacket`.
- Fill `StartGamePacket`'s game rules with exactly the list BDS writes, in its order.
- Give `StructureSettings.integrity_seed` a value a float holds exactly.
- List an item-use transaction's actions in ascending `InventorySource` type order.
- Keep `RequestAbilityPacket`'s bool member false when its `value_type` is `FLOAT`.
- Make `NpcDialoguePacket.action_json` an array of actions BDS accepts.
- Make `SpawnParticleEffectPacket.molang_variables` a JSON array of `{"name", "value"}` variables, each value `{"type": "float", "value": N}` or `{"type": "member_array", "value": [...]}`, each name lowercase letters, digits and `_` with at most one `.`.
- Keep a colour channel in 0..255, an effect duration at 0 or above, and a voxel shape's cell storage at one bit per cell.
- Set an optional BDS derives from an earlier field exactly when BDS writes it: `InventorySource`'s container id for `CONTAINER_INVENTORY` and `NON_IMPLEMENTED_FEATURE_TODO` and its flags for `WORLD_INTERACTION`; the legacy set item slots when `raw_id < -1 and raw_id & 1 == 0`; a response slot's item stack net id when its amount is not 0; `PlayerAuthInputPacket`'s optionals from their `input_data` bits; `ItemStackResponseInfo`'s containers only on `SUCCESS`; `MapItemTrackedActor`'s entity id only for `ENTITY` and block position only for `BLOCK_ENTITY`.
- Send `NetworkStackLatencyPacket.create_time` as 0; BDS reads it in milliseconds and writes it in nanoseconds.

## Login and handshake

- Set `LoginPacket.client_network_version` to 2168: BDS parses the connection request only at its own protocol, and writing back an unparsed one crashes it.
- Frame a connection request as two parts, each behind a `uint32` little-endian length: the authentication JSON `{"AuthenticationType":N,"Token":"..."}` plus a newline, with no `Certificate`, then the client data JWT.
- Keep a `LoginPacket` connection request well-formed: `AuthenticationType` 0 or 2, a known `DeviceOS`, skin sizes up to 0xFFF, a `DeviceId` under 45 characters, a `ThirdPartyName` up to 48, an `AnimatedImageData` `Type` of 1 to 3, and known `PieceType` names.
- Write a JWT as three base64url segments: the header `{"alg":"ES384","x5u":<key>}`, the claims and a signature; the server-to-client handshake's claims are `{"salt":<base64 of 16 bytes>}`.
