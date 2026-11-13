---
paths:
  - "protocol/**"
  - "tests/**"
  - "include/**"
---

# Wire facts

## cereal

- 2168 is the cereal floor: from it every packet has a cereal schema; below it BDS wrote each packet by hand or through cereal, and a packet could switch at any release.
- BDS writes a packet through cereal at `SerializationMode` 3 to 5 and through its hand-written writer at 0 to 2, read from the packet's constructor in the binary.
- What cereal writes is flat, in declaration order, unconditional.
- cereal writes a nested struct inline with no framing, so a composed type adds no bytes of its own. The DSL still keeps BDS's type boundaries (`naming.md`).
- A variant's selector is a `uvarint32` index over its alternatives, never the tag. The tag member is serialized inside its alternative.
- A name-coded enum goes on the wire folded to lower case. The string literal at the bind site never reaches the wire.
- A cereal-bound constant folds like an enum value: the wire carries the value's folded name, never the member's own name.
- A one-byte enum is one byte on the wire, whatever cereal Compression trait the member carries.
- cereal prefixes a dynamic member with an always-true member-present byte (`dsl.md`). It is a BDS bug.

## Text

- A `mce::UUID` on the wire as text is `mce::UUID::asString`'s lower-case 8-4-4-4-12; BDS reads 36 hyphenated or 32 bare hex digits, either case, and any other text as the nil UUID.

## The frame

- The packet header is one `uvarint32`, `id | recipient << 10 | sender << 12`, with sub-client ids 0..3. gophertunnel swaps the two.

## Packets

- Model `PlayerAuthInputPacket.input_data` as a length-prefixed list of `InputData` from 2168 and a bitset before it; the header's `std::bitset` is the in-memory member.
- Before 2168, `PackedItemUseLegacyInventoryTransaction` writes its slots only when `id < -1 and (id & 1) == 0`.
- Before 2168, the chemistry recipe writers do not write the unlocking requirement; the other four recipe writers do.
- Never unify `ContainerID`: it is `uvarint32` in packet 49 and, from 975, `uint8` in packet 50; they part at `NONE = -1`.
- `TextPacket`'s twelve constant strings are on the wire, folded, over `[898, 924)`.
- Spell packet 124's event data `CompoundTagData`: a compound's entries plus `TAG_End`, no root tag, at every version.
