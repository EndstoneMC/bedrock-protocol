---
paths:
  - "tests/goldens/**"
  - "tests/test_goldens.py"
  - ".claude/skills/goldens/**"
---

# Goldens

A golden is a case BDS agrees with; the `goldens` skill runs BDS over the cases.

## Case files

- Keep a packet's cases in `tests/goldens/v<protocol>/<id:03>_<snake_name>.json`, `<snake_name>` being the class the folder's module binds at `<id>` without its trailing `Packet`, in snake case: a JSON array of `{"value", "bytes"}`.
- Hold every packet live at 2168 in `v2168/`, checked by BDS 1.26.40.8; another protocol's folder holds a packet only when its class differs from the neighbour's toward 2168.
- Write `value` exactly as `to_json` returns it, key order included, and `bytes` as the lowercase hex of the library's encoding of `value`; never type `bytes` by hand.
- Write a case file as `json.dumps(cases, indent=1)` plus a newline, regenerated from the library after every edit.
- Commit a case only once BDS writes the same bytes and the JSON BDS prints matches `value` in its tree and leaf values; keys are not compared.
- Never change a committed case's `bytes`; change its `value` only for a rename or a library type fix.

## Writing cases

- Cover every branch of the packet's generated encode and decode code that a valid packet reaches, with as few cases as a unit test would use; read what is left from the coverage report.
- Add a case only when it reaches a branch no other case does, and drop one whose branches the others reach.
- Count a packet's branches in its generated codec; a runtime header's branch, such as a multi-byte varint, counts across the suite, so never grow a list or string to reach one.
- Change a case's leaves without changing its branch identity: each optional stays present or absent, each variant arm and gating bool stays, and an empty list stays empty.
- Give a leaf a value other than its type's zero unless its branch needs zero, so a skipped field changes the bytes.
- Keep a list to one element and a string to a few characters unless a branch needs more.
- Give every leaf data BDS accepts (below); when BDS rewrites or refuses a value, fix the schema or add the missing line here with its evidence in the commit body, never retry other values until one passes.
- Never run BDS from a test.
- Run every step as an inline command; save no script, not even in a scratchpad or `build/`.

## Valid data at 2168

- Read enum bindings, limits, items and blocks from the dump of the build that checks the folder, never from another build's protocol-docs.
- Pick an enum member the field's dump binds, never a `sentinel()` or `deprecated=True` member, and keep a value inside the field's dump limits: `minimum`, `maximum`, `max_length`, `max_items`, `pattern` and `enum_values`.
- Name an item by an id the build's own item dump lists, with an aux of 0 for a block item and 0..32767 otherwise, and a stack size of 1..64; name a block by a runtime id its block palette lists.
- Give a recipe ingredient's descriptor only `name`, `tags` or `item_tag`, and an `item_tag` only a registered item carries.
- Fill `AvailableActorIdentifiersPacket`'s tag with an `idlist` ListTag of actor entries.
- Sort a `CompoundTag`'s keys, as BDS's `std::map` holds them.
- Write a `SemVersion` as `X.Y.Z`; a min engine version as `X.Y.Z` with optional pre-release and build suffixes, never four parts or `*`; a base game version as `X.Y.Z` or `*`, without a pre-release suffix or a fourth part.
- Write JSON BDS parses as jsoncpp's FastWriter prints it: keys sorted, no spaces, a trailing newline, numbers in its form (`1000.0` for `1e3`); `form_json` and `json_input` stay as written.
- Make `NpcDialoguePacket.action_json` an array of actions BDS accepts.
- Keep a colour channel in 0..255, an effect duration at 0 or above, and a voxel shape's cell storage at one bit per cell.
- Set an optional BDS derives from an earlier field exactly when BDS writes it: `InventorySource`'s container id for `CONTAINER_INVENTORY` and `NON_IMPLEMENTED_FEATURE_TODO` and its flags for `WORLD_INTERACTION`; the legacy set item slots when `raw_id < -1 and raw_id & 1 == 0`; a response slot's item stack net id when its amount is not 0; `PlayerAuthInputPacket`'s optionals from their `input_data` bits; `ItemStackResponseInfo`'s containers only on `SUCCESS`; `MapItemTrackedActor`'s entity id only for `ENTITY` and block position only for `BLOCK_ENTITY`.
- Send `NetworkStackLatencyPacket.create_time` as 0; BDS reads it in milliseconds and writes it in nanoseconds.

## Login and handshake

- Set `LoginPacket.client_network_version` to 2168: BDS parses the connection request only at its own protocol, and writing back an unparsed one crashes it.
- Frame a connection request as two parts, each behind a `uint32` little-endian length: the authentication JSON `{"AuthenticationType":N,"Token":"..."}` plus a newline, with no `Certificate`, then the client data JWT.
- Keep a `LoginPacket` connection request well-formed: `AuthenticationType` 0 or 2, a known `DeviceOS`, skin sizes up to 0xFFF, a `DeviceId` under 45 characters, a `ThirdPartyName` up to 48, an `AnimatedImageData` `Type` of 1 to 3, and known `PieceType` names.
- Write a JWT as three base64url segments: the header `{"alg":"ES384","x5u":<key>}`, the claims and a signature; the server-to-client handshake's claims are `{"salt":<base64 of 16 bytes>}`.
