---
paths:
  - "protocol/**"
  - "scripts/goldens/**"
  - "tests/**"
---

# BDS semantics

What BDS checks, derives or rewrites in a value whose bytes are well-formed. A golden's value satisfies every line here.

## Checks on read

- BDS refuses a value outside its field's limits in the dump: `minimum`, `maximum`, `max_length`, `max_items`, `pattern`, and `enum_values`, the members of its enum that field accepts.
- BDS refuses an enum member its dump does not bind.
- BDS holds its item registry per thread, set only on the server thread; call anything that reads an item there.
- BDS writes back as id 0 a stack whose item id its registry lacks, rebuilds a block item with aux 0, and refuses an aux above 32767 and a stack size above 64.
- A recipe ingredient's descriptor keeps only `name`, `tags` and `item_tag`, and an `item_tag` only when a registered item carries it.
- At 1.26.40 a craft result names a registered item with a stack size above 0.
- `AvailableActorIdentifiersPacket`'s tag holds an `idlist` ListTag of actor entries.

## Login and handshake

- BDS parses `LoginPacket`'s connection request only when `client_network_version` is its own protocol; any other number leaves it unparsed, and writing the packet back crashes BDS.
- A connection request is two `uint32` little-endian-prefixed parts, the auth JSON and the client data JWT; BDS refuses one it cannot parse and drops the auth JSON's `Certificate` on write.
- The server-to-client handshake token is a three-part JWT: header `{"alg":"ES384","x5u":<key>}`, claims `{"salt":<base64 of 16 bytes>}`.

## Derived at 2168

- BDS computes these presence bytes from an earlier field: `InventorySource`'s container id for `CONTAINER_INVENTORY` and `NON_IMPLEMENTED_FEATURE_TODO` and its flags for `WORLD_INTERACTION`; the legacy set item slots when `raw_id < -1 and raw_id & 1 == 0`; a response slot's item stack net id when its amount is not 0; `PlayerAuthInputPacket`'s optionals from their `input_data` bits; `ItemStackResponseInfo`'s containers only on `SUCCESS`; `MapItemTrackedActor`'s entity id only for `ENTITY` and block position only for `BLOCK_ENTITY`.
- BDS clamps a colour channel to 0..255, writes a negative effect duration as 0, and sizes a voxel shape's cell storage to one bit per cell.

## Text

- JSON BDS parses comes back through jsoncpp's FastWriter: keys sorted, no spaces, a trailing newline, numbers in jsoncpp's form (`1e3` as `1000.0`); JSON held as `std::string` (`form_json`, `json_input`) comes back verbatim.
- `NpcDialoguePacket.action_json` is an array of actions BDS accepts.
- A min engine version keeps `X.Y.Z` with its pre-release and build suffixes, fills `X.Y` to `X.Y.0`, and refuses four parts or `*`.
- A base game version keeps `X.Y.Z` and `*`, fills `X.Y` to `X.Y.0`, drops a pre-release suffix, and writes four parts back empty.

## Bugs

- `NetworkStackLatencyPacket.create_time` is read in milliseconds and written in nanoseconds; send 0.
