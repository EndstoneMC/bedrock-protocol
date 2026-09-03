---
name: add-protocol
description: Add a protocol version to the bedrock-protocol schema - a new version at or above 2168 (all-cereal, modelled from the protocol-docs dumps), a back-port below 2168 (mixed hand-written/cereal, modelled from gophertunnel and CloudburstMC history), or a renumber when a newer preview supersedes the one already modelled. Use when asked to "add protocol N", "support 1.26.x", "model the new network version", "follow 1.26.50.x to protocol N", "back-port 944", "support an older protocol", or when a new protocol-docs branch lands.
---

# Add a protocol version to the schema

`CLAUDE.md` is the law for *how* to spell a declaration. This is the workflow. Where they
disagree, CLAUDE.md wins.

## The rule of four

A protocol version changes exactly four things. Every one **MUST** be accounted for before
the work is done - not *should*, not *may*. A change you did not look for is a silent wire
break.

1. **Packet change** - a packet added or removed.
2. **Type change** - a field added, removed, renamed or moved, in a type *or in a packet*,
   and a type itself added, removed or renamed.
3. **Wire change** - the same field, encoded differently.
4. **Enum change** - a value added, removed, renamed, shifted, or a sentinel moved.

- **DO** walk all four explicitly and report what you found in each, including "nothing".
- **DO** treat a change to a packet the schema does **not** model as a finding, not a
  no-op. It is the most expensive miss there is: an unmodelled `CameraPresetsPacket` whose
  preset grew two fields relayed a short body and desynchronised a client mid-list, and a
  union case appended to an unmodelled `ServerboundPackSettingChangePacket` had nothing to
  be appended to. Model the packet.
- **DO NOT** stop at the first category with hits. They are independent, and 3 and 4 are
  the two a name-level reading cannot see.

## The 2168 rule

**Below 2168** BDS wrote packets through a *mixture* of hand-written
`write(BinaryStream&)` and the cereal auto-codec, and a packet could move between the two
at any release. Hand-written code branches on a type field, picks its own union tag widths,
and encodes a *shared* type differently per call site.

**At and above 2168** everything is cereal: every field flat, in declaration order,
unconditional.

That decides both the shape of the DSL and where the rule of four is discovered.

| | forward (>= 2168) | back-port (< 2168) |
| --- | --- | --- |
| evidence | the protocol-docs dump, complete | the dump for the cerealised half only, gophertunnel/Cloudburst for the rest |
| DSL body | bare `name: Type` lines | `when=`, unions, `Literal[True]`, `field(type=)` |
| section | §3 | §4 |

- **DO** treat annotation clutter in a `>=2168` body as a bug: you are modelling the
  pre-cereal shape.
- **DO NOT** assume a packet's pre-2168 shape from its cerealised one, or the reverse.

## Sources

| what it settles | source |
| --- | --- |
| wire type, order, prefix, presence | `github.com/EndstoneMC/protocol-docs` - one branch per update line |
| golden bytes, pre-2168 wire | `github.com/Sandertv/gophertunnel` |
| per-version dating | `github.com/CloudburstMC/Protocol`, `github.com/MemoriesOfTime/Nukkit-MOT` |
| names | the schema itself, then the dump - see **Naming** |
| the arbiter, when refs disagree | the BDS binary |

Commands below assume you have each repo cloned locally; substitute your own paths.

BDS headers are **not** a source here. They are access-restricted, and no header exists for
a preview build in the first place - which is exactly what a new protocol is. Do not plan
around having one.

### Naming

- **DO** keep the name already in the DSL when the dump labels the same field differently.
  The dump's labels are cereal display strings, not member names, and they drift. Renaming
  to chase a label churns every consumer for nothing.
- **DO** convert a genuinely new label into `snake_case` that reads like its neighbours -
  `"Bypass Listener Range Check"` becomes `bypass_listener_range_check`, `"FurnaceType"`
  becomes `furnace_type`. Enum members take the same treatment in `UPPER_CASE`.
- **DO** follow the module's existing vocabulary where the label is awkward. A name that
  matches the surrounding declarations beats a literal transcription.
- **DO NOT** take a name from gophertunnel or CloudburstMC. They date and shape symbols;
  they do not name them, and they carry known-wrong names.
- **DO NOT** rename an existing field as a side effect of a version bump. If a label change
  turns out to be a real BDS rename, that is category 2 and lands as a redeclaration on its
  own evidence, not because the dump's wording moved.

## 1. Establish the number

Each protocol-docs branch is named `r<minor>_u<patch/10>` by the dumper, and its README
names the Minecraft build, the channel and the network version. Branches run back past 898.

- **DO** read the network version out of the dump itself, which is where the dumper got it:
  `packets/RequestNetworkSettingsPacket.json`, `fields[0].constraints.minimum`.
- **DO** pin the SHA you diff and quote it in the commit message. A branch is a moving head
  that reruns against the newest BDS on its update line, so its README number changes under
  you.
- **DO** record the *build*, not just the number - 1.26.43 and 1.26.44 both say 2168 and
  disagree on the wire.
- **DO** gate at the **first** protocol number of the cycle. A release often bumps twice,
  beta then release, with one wire shape, and the community codecs carry only the second:
  1.21.130 shipped 897 then 898, and the schema gates `since=897`.
  `AnimateSerializer_v898.java` is a codec-dir name, not a `since=` value.
- **DO** cross-check the number against
  `raw.githubusercontent.com/EndstoneMC/bedrock-server-data/v2/versions.json` and
  minecraft.wiki's *Protocol version* page.
- **DO NOT** model a number that appears in none of them - stop and ask.

### When the new number supersedes a modelled preview

**One protocol per update line.** The preview channel renumbers repeatedly inside one
update - 2181, then 2187, then 2192 for 1.26.50 - and nobody runs a superseded preview. A
newer number on the same update line *replaces* the older one; it never becomes a second
snapshot beside it.

- **DO** renumber every gate the superseded preview carried, then model the new dump's
  delta on top. Both halves are one commit.

```shell
sed -i 's/\b<old>\b/<new>/g' protocol/*.py
sed -i 's/\b<old>\b/<new>/g; s/v<old>/v<new>/g; s/V<old>/V<new>/g' tests/*.cpp
grep -rn "<old>" protocol/ tests/ README.md      # must come back empty
```

- **DO** hand-edit `__version__` in `protocol/__init__.py` and README's "Modelled today"
  line; the sed does not reach them meaningfully.
- **DO NOT** trust `\b<old>\b` to catch `v<old>` - there is no word boundary after a
  letter, so namespace spellings survive. Grep for the bare number *and* `v<number>`.
- **DO NOT** keep the superseded number as a snapshot of its own. It buys nothing and costs
  a namespace in every versioned type.

## 2. Snapshots

There is no version registry. `_snapshot_points` in
`src/bedrock_protocol/compiler/descriptor_pool.py` takes `{0}` plus every change point
every versioned type declares, unioned transitively across imports. The first `since=` /
`until=` you write materializes the version: `base` (the floor, claiming validity from 0),
then one `vNNNN` namespace per change point.

- **DO** diff a packet's whole transitive type closure before modelling it. A new branch is
  not evidence of change - one landed whose network version had moved while packet 122's
  entire closure stayed byte-identical.
- **DO** accept transitive versioning as the price: one field on
  `ItemUseInventoryTransaction` re-emits `TransactionData`, `InventoryTransactionPacket`,
  `PackedItemUseLegacyInventoryTransaction` and `PlayerAuthInputPacket` at the new snapshot.
- **DO NOT** materialize a snapshot the evidence does not force.
- **DO NOT** fold a real change into an existing snapshot to avoid the transitive cost.

## 3. Forward: at or above 2168

The dump is complete here, so **the diff between two protocol-docs branches is the whole
rule of four**. Read it on GitHub -
`github.com/EndstoneMC/protocol-docs/compare/<old>..<new>` - or locally:

```shell
git fetch origin
git diff --name-status -M origin/<old> origin/<new>
git diff -U1 -M origin/<old> origin/<new>
```

- **DO** use the two-dot form `<old>..<new>`. The branches are generated independently and
  share no merge base, so the three-dot compare GitHub defaults to is meaningless.
- **DO** pass `-M`. Without it a renamed declaration reads as an unrelated delete plus add,
  and `--diff-filter=AD` misses it entirely.

The dump's shape: `packets/*.json` is `{id, name, fields[]}`, `types/*.json` is
`{name, fields[]}`, `enums/*.json` is `{name, values[{name, value}]}`. A field is
`{name, type}` plus any of `enum`, `repeat`, `optional`, `value`, `constraints`.

A `constraints` block (`min_length`, `max_length`, `enum_values`, `minimum`, `maximum`,
`description`) is **not wire** and comes and goes in sweeps between builds; the sole
exception is `RequestNetworkSettingsPacket`'s, which is the version.

- **DO** classify hunk by hunk, and let each land in exactly one of the four categories.
- **DO NOT** write a diff off as constraint churn in bulk. One version was landed on
  exactly that reading and the sub-chunk height map's `repeat` change went with it - which
  is the byte a 1.26.50 client stops on.

### (1) Packet change

**Each `packets/*.json`'s own `id` field is the authority.** `enums/MinecraftPacketIds.json`
is a convenience index and Mojang routinely forgets to bind values in it - r26_u6 ships
`ServerboundStonecutterSetRecipePacket` (354) and `ClientboundStonecutterSetRecipePacket`
(355) as dumped packets with no entry in that enum at all.

- **DO** take the id from the packet file. A packet added arrives as a new `packets/*.json`
  carrying its id; a packet removed takes its file with it.
- **DO** diff `MinecraftPacketIds.json` too, as a second view - it names ids the dump has no
  file for, which are packets that are not cerealised.
- **DO** reconcile the two as a **union**, never an intersection. Either source can miss a
  packet, and each miss is a packet on the wire that nothing decodes.
- **DO** treat an id that *moved* as a break for the packet that took it, not a rename.
- **DO** model the body in the same commit as the id. `MinecraftPacketIds` in
  `protocol/network.py` lists ids the schema does not model, which is a standing backlog -
  but an id *you* gate `since=<new>` with no `@packet` body puts that id on the wire with
  nothing able to decode it.
- **DO NOT** treat the id enum as the packet list. It is the source that silently omits.

### (2) Type change

Field entries appearing or vanishing in a `fields[]` array, and whole files arriving,
leaving or being renamed.

- **DO** compare fields as an **ordered** sequence. Cereal is positional, so a field
  inserted mid-struct moves everything after it - `TextDataPayload` gained `LineGapHeight`
  in front of `DepthTest`, not at the end.
- **DO** read a delete-plus-add at the same position with the same type as a **rename**,
  and model it as a class redeclaration; field gates cannot restate a field under a new
  name. `DimensionDefinition` renamed `Height Maximum`/`Height Minimum` to
  `Minimum Y`/`Height Range`, which also inverted what the numbers mean - a rename can
  carry a semantic change the wire types hide.
- **DO** read a vanishing `{"type": "bool", "value": true}` entry as BDS **fixing a cereal
  always-true marker**. Gate that one `Literal[True]` field `until=<new>`; nothing else in
  the type moves. They go in waves - one version dropped twelve across
  `PlayerAuthInputPacket`, `InventoryTransactionPacket`, `InventorySource`,
  `InventoryTransaction`, `ItemStackResponseInfo`, `ItemStackResponseSlotInfo` and
  `PackedItemUseLegacyInventoryTransaction`.
- **DO** follow a renamed type into every file that references it. BDS versions some type
  namespaces, so `SharedTypes::v1_21_90::CameraPreset` became
  `SharedTypes::v1_26_50::CameraPreset` - a file rename *and* a type-string change in
  `CameraPresets.json`, which surfaces under category 3.
- **DO NOT** read a field's disappearance as a removal without checking the same file for a
  matching addition.

### (3) Wire change

The field's `name` is unchanged and everything else about it moved. **This is the category
a name-level reading cannot see** - compare the whole field object.

- **DO** read `repeat` exactly: an **integer** is a fixed count (`array[T, N]`), a
  **string** is that length prefix (`list[T]`). `"repeat": 16` becoming
  `"repeat": "uvarint32"` turned `SubChunkPacketPayload::HeightmapData`'s fixed rows into
  length-prefixed lists.
- **DO** treat a union's `cases` array gaining or losing an entry as a wire change - the
  `uvarint32` discriminator indexes that list in order, so appending is safe and inserting
  renumbers every case after it. `ServerboundPackSettingChangePacket`'s `PackSettingValue`
  gained a fourth case.
- **DO** treat a change of the `type` string, `optional`, or `enum` binding as a wire
  change even when the field name is untouched.
- **DO NOT** ignore a nested `type` object. The change can be one level down, inside the
  element type of a repeat.

### (4) Enum change

Five signatures in `enums/*.json`, each needing different DSL:

- **Appended values** - `value(N, since=<new>)`, with a trailing `COUNT = auto()` following
  on its own.
- **A removed value, tail shifting down** - `value(N, until=<new>)` on the one that went
  and `auto()` for every member after it. The pool re-resolves `auto()` per snapshot, so
  the shift falls out of the single gate. One version dropped
  `Memory::MemoryCategory::Persona_Textures` and shifted fifty-odd members by one.
- **A rename at the same value** - wire-invisible for an int-coded enum, a **wire change**
  for a name-coded one (`field(type=str)`) where the folded member name *is* the bytes.
  `BuildPlatform`'s `Nx` became `Nintendo` at 12. Check the encoding, then take the new
  spelling at **every** era rather than versioning the enum: a gate propagates through
  every referencing type for a rename, and a name-keyed mapping then fails to match across
  the boundary and falls back to a sentinel.
- **A value gaining a name** - not a shift, and not a new enumerator. The test is internal:
  if no other member moved, the value was already there and merely unbound, so the dump's
  *binding* changed rather than BDS. `persona::AnimatedTextureType` gained `None = 0` while
  `Face`, `Body32x32` and `Body128x128` kept 1, 2 and 3. Add it ungated - gating it would
  claim the value did not exist before. **Settle it in bedrock-headers, not the dump**: the
  header lists every enumerator whether cereal binds it or not, so
  `git show origin/android/r26_u3:<path>` against `r26_u4` says outright whether the value
  is new. `persona::PieceType` gained `Unknown = 0` *and* `Unsupported = 28` between u3 and
  u4, which reads like a renumber at both ends - but `PersonaTypes.h` at u3 already carried
  the identical 29-value enum through `Count = 29`, so both were merely unbound and both are
  ungated. Carry the sentinel over with them; it is the arithmetic that proves nothing moved.
- **A sentinel that disagrees with the members** - check both arithmetics every time:
  `Δsentinel` must equal `added − removed`, **and** the sentinel must equal the last named
  member + 1. `CurrentCmdVersion`'s `Count` went 51 → 53 and `Latest` 50 → 52 with the last
  named member still at 44 and no new names in the diff. The absolute check is the one that
  mattered - six had already been unnamed for a version before anyone noticed.
- **An unbound alias is noise; a bound sentinel on a name-coded enum is a gap.** Both look
  like "a value the dump has and the DSL does not", and they are not the same finding. Sort
  them by how the referencing field encodes. `MolangVersion`'s `Latest` and `HardcodedMolang`
  are bound at every era but alias 13, and `item_stack.py` writes the enum
  `field(type=int16)` - numeric, so carrying them changes nothing and they stay out.
  `CurrentCmdVersion`'s `Latest` is bound at every era too, but `command.py` writes that enum
  `field(type=str)`, so the folded name *is* the bytes: BDS puts `"latest"` on the wire and a
  schema without the member cannot decode it. It is deliberately still absent, because its
  value is era-dependent (49 at u3, 50 at u4, 53 at u6) while its name is not, and modelling
  it means writing a number that is right for one era only. Revisit when a header branch above
  1.26.40 lands. Until then: **a name-coded enum missing a bound member is a decode hole, and
  worth saying out loud rather than leaving to a later reader to rediscover.**

- **DO** give a real member an explicit numeric value.
- **DO** reserve `auto()` for a count sentinel (`Count`, `Latest`, `MAX_X`, `NumX`) and for
  a run shifting behind a gate. `auto()` means *the previous member's value* + 1 -- not the
  maximum, and not the member count -- so what it needs is the line immediately above it
  holding the right value, which is weaker than the whole run being dense. `Rotation` is the
  case: `NONE`..`ROTATE_270` then the `CLOCKWISE_*` aliases repeat 1, 2, 3, so the run is not
  dense, yet `TOTAL = auto()` still lands on 4 because `COUNTER_CLOCKWISE_90 = 3` precedes it.
  Check the neighbour, not the histogram.
- **DO** pin a sentinel with an explicit `value(N, since=)` and note the gap where the
  arithmetic says BDS ships enumerators the dump does not bind. Nothing available to you
  will name them, and `auto()` would silently lie about where the sentinel sits.
- **DO NOT** assume the dump lists every enumerator. It lists the bound ones; a sentinel is
  the only witness to the rest.
- **DO NOT** redeclare an enum unless a wholesale renumbering gives one member two explicit
  values.
- **DO NOT** gate an enum member without following it out. The gate versions the enum, so
  every test and consumer naming a member must then spell the snapshot it exercises
  (`bp::ContainerType_<2168>::...`) or stop compiling.

### Then model it

- **DO** use inline `field(since=N)` / `field(until=N)` / `field(type=)` when a *minority*
  of a type's fields moved.
- **DO** redeclare the whole class over adjacent ranges when the shape shifted - a field's
  type changed, fields reordered or were renamed, or nearly all moved. Redeclarations tile:
  same id, each `until` meets the next `since`, only the last left open. The tiling is
  enforced - a mismatched id, a gap, or an earlier declaration left open is an error, so a
  bad tiling fails loudly rather than silently emitting one shape.
- **DO** land every gate on a materialized snapshot: a field the changelog dates to 2177
  gates at the next snapshot at or after it.
- **DO** update `__version__` in `protocol/__init__.py` and the "Modelled today" line in
  `README.md`.
- **DO** place a declaration by its BDS domain. `head -qn 4 protocol/*.py` is the index,
  `grep -n "^Not " protocol/*.py` the exclusions; a packet added to a module whose docstring
  excludes it changes that docstring in the same commit.
- **DO NOT** gate a field inside a redeclared class - the resolver rejects it, and merges
  every redeclaration onto the *latest* field order, so a reorder cannot be expressed by
  field gates at all. Collapse them into one exact `when=`.
- **DO NOT** spell `field(type=)` on a plain enum field. Width, signedness and compression
  follow the underlying type and already match the dump. It is earned only by `str`
  (name-coded), a fixed primitive against a wider underlying, or `endian="big"`.

## 4. Back-port: below 2168

The dump exists here but covers only the cerealised half, so the rule of four has two
discovery paths and you run both. Presence in the dump at that version is the test:

| in the dump | cerealised - the dump is the wire, and a variant tag is **always `uvarint32`** over cases in declaration order |
| --- | --- |
| **absent** | hand-written - the dump cannot describe it and gives no hint. Go to the Marshal history |
| **new file between two branches** | that packet *cerealised* there - the highest-risk change in the repo |

979 cerealising `SubChunkRequestPacket` moved `center_pos` behind the offsets, swapped the
offset count from fixed `uint32` to `uvarint32`, and reshaped `SubChunkPos` from `varint32`
to fixed `int32` - three wire breaks in one changelog line.

A cerealisation can also be **size-identical**. 996 moved each of
`ClientCacheBlobStatusPacket`'s counts next to its own elements; both forms are the same 26
bytes for the same content, and an empty packet is `0x00 0x00` either way. Size proves
nothing about a reorder - see §5.

- **DO** check whether the two eras actually differ before splitting anything. A
  cerealisation usually leaves most of the closure producing identical bytes:
  `InventoryTransactionPacket`'s pre-cereal form writes the transaction type and action
  list itself, which lands as the same variant tag and leading `InventoryTransaction` the
  cerealised form emits, so both eras share one `TransactionData` and only four types
  needed redeclaring.
- **DO NOT** gate a type that merely became *reachable*. Gate what BDS version-stamped:
  `SharedTypes::v1_26_30::NoiseDescriptor` is new and gates, while
  `SharedTypes::versionless::FloatRange` only started being referenced and stays ungated.

### The hand-written half

```shell
git log -p -- minecraft/protocol/packet/<name>.go     # in a gophertunnel clone
```

- **DO** read every commit's diff *inside the `Marshal` body*, and take that commit's
  `CurrentProtocol` from `minecraft/protocol/info.go` as the gate. That covers categories 2
  and 3 for a hand-written packet; category 1 is the packet id list, and 4 the enum tables
  in the same tree.
- **DO** cross-check CloudburstMC's
  `bedrock-codec/.../codec/vNNN/serializer/<Packet>Serializer_vNNN.java`. A
  `Serializer_v1001` extending `Serializer_v975` and appending a field dates that field to
  1001; Nukkit-MOT annotates members `@since vNNN`.
- **DO** verify any Cloudburst *shared helper* against gophertunnel's per-field method.
  Cloudburst's single `writeBlockPosition`, overridden at 944, made it look like every
  block-pos field switched; gophertunnel's distinct `Writer.BlockPos` vs `Writer.UBlockPos`
  showed `SynchedActorData`'s POS was all-signed at every version.
- **DO** model a shared type's encoding **per embedding type**. `GameRule` is fixed `int32`
  in the cerealised `GameRulesChangedPacket` at 975, 1001 and 2168 alike, while hand-written
  StartGame put a varint on the wire until 2168. One dump entry, two encodings.
- **DO NOT** use `git log -S<field>`. It finds only a name arriving or leaving and misses
  category 3 entirely - `io.UBlockPos` -> `io.BlockPos` at 944, `io.Bool(&pk.EditorWorld)`
  -> `io.Varint32(&pk.EditorWorldType)` at 618.
- **DO NOT** gate by a gophertunnel bug interval. A "Fix incorrect ..." commit or a revert
  marks one; date by the corrected shape.
- **DO NOT** treat agreement between two refs as evidence - they copy each other - or
  silence as evidence. A packet neither Geyser nor Dragonfly exercises has an untested
  codec.
- **DO NOT** put a single `@type(until=N)` pair over a shared type. It forces both call
  sites to agree and silently mis-encodes the one the dump did not describe.

### Keep the floor intact

A gate below the current floor splits `base` and re-emits that type, and everything that
transitively contains it, at a second namespace.

- **DO** gate only the fields and types the evidence actually separates.
- **DO NOT** re-baseline the schema, and do not fold in "while I'm here" corrections to
  types the version did not touch. Land those separately.

### Pre-cereal shapes

- **DO** turn an old `Marshal` `switch` into `when=` - `field(when=lambda p: p.x == E.A)`
  for one field, `with field(when=...):` for a run. The predicate reads earlier fields only,
  carries no presence byte, and leaves an excluded field default-constructed. Cereal
  flattens the switch away, so the same packet is a flat redeclaration on the other side of
  the boundary.
- **DO** use `when=` for any *implicit* presence rule, not just a type switch. Pre-cereal
  BDS gates fields on a sentinel with nothing on the wire marking them:
  `legacy_set_item_slots` rides on a non-zero `legacy_request_id`, and
  `NetworkItemStackDescriptor` puts everything behind `id != 0`, so air is a lone zero byte
  rather than eight. An optional would add a presence byte BDS never wrote.
- **DO NOT** assume the pre-cereal shape used the same construct as the cerealised one.
  Cereal turns an ad-hoc `bool` + value into an optional or a variant; pre-cereal
  `NetworkItemStackDescriptor` writes a plain bool and a `varint32` net id where the
  cerealised form has a netid variant.
- **DO** lead a union with `None` where BDS numbers its cases from one, so `std::monostate`
  takes index 0.
- **DO** write a declared-type-vs-wire split as `name: <DeclaredType> = field(type=<wire>)`
  - the annotation keeps the semantic type, `field(type=)` switches the encoding. The
  declared type is the dump's `type` string or the alias the schema already uses. Dropping
  to the raw primitive and explaining it in a comment is not the alternative.
- **DO** grep an enum for a negative enumerator before unifying a narrowed width.
  `uvarint32` and a signed byte agree on 0..127 and part company at `-1` (one byte against
  five); eleven enums carry one.
- **DO NOT** read a community lib's `uint8` as width evidence. For 0..127 the encodings are
  identical and no golden will catch a wrong choice - only BDS and the dump answer width. A
  width that narrows between eras is BDS shortening the underlying type: model both eras on
  the narrow one.
- **DO NOT** fold cereal's always-true member-present byte into a `T | None`. It is
  `Literal[True]`, its own field, where the byte falls. An optional conflates BDS's bug with
  real presence and lets the schema encode a `nullopt` BDS never writes.

## 5. Tests

- **DO** add the case to the file that owns the packet,
  `tests/test_{packet_id:03}_{name}.cpp`.
- **DO** generate goldens by running gophertunnel - a small Go program marshalling through
  `protocol.NewWriter` - and paste the bytes under a `// generated by gophertunnel:` comment
  carrying the packet literal.
- **DO** check gophertunnel out at the era's commit for a back-port golden, and generate
  **two** for a cerealisation - one per era, from the commits either side of the migration.
- **DO** give a type with no modelled packet its own test file named for the type. The
  `test_{id}_{name}` convention needs an id, and a type reached only through an unmodelled
  packet has none.
- **DO** assert structurally above 2168, where gophertunnel stops and no golden exists:

```cpp
// No golden -- gophertunnel stops at 2168 -- so the <prev> body is the reference.
REQUIRE(encode(newer).size() == encode(older).size() + 1);
REQUIRE(decode<Newer>(encode(newer)).new_field == ...);
```

- **DO** pin a new field a second way when the delta mixes changes: two bodies differing
  only in that field must differ in exactly one byte.
- **DO NOT** assert a reorder with a size comparison. A reshape that moves fields without
  changing widths encodes to the same length, so the assertion passes on the wrong shape;
  pin the ordering with a body whose bytes actually move.
- **DO** update the per-snapshot modelled-packet counts in `tests/test_packet.cpp`. A new
  snapshot adds a row, and a newly modelled packet moves every row it exists at.
- **DO** check `grep -c "struct [A-Za-z_0-9]* {};"` over the generated headers reads 0. An
  unresolvable field type is silent: the parser returns `None` and the backend emits a
  one-line empty struct.
- **DO** build with libc++. The default configuration stops earlier on an unrelated
  `std::variant` default-construction in the generated `item_stack.h`, so a green
  `cmake --build build` may never have reached a test:

```shell
cmake -B build-libcxx -G Ninja -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_COMPILER=clang++ \
      -DCMAKE_CXX_FLAGS=-stdlib=libc++ -DCMAKE_EXE_LINKER_FLAGS=-stdlib=libc++
cmake --build build-libcxx -j8 && ctest --test-dir build-libcxx --output-on-failure
```

- **DO** rebuild endweave's `develop` branch - it consumes the generated headers, and a
  rename here is a compile error there.
- **DO NOT** derive golden bytes by hand. An empty `CompoundTag` is three bytes, not four,
  and only an executed golden catches that.
- **DO NOT** fake an old golden by deleting bytes from a newer literal.
- **DO NOT** label a golden's bytes field by field, or add a new test file for a packet that
  already has one.
- **DO NOT** blame compiler-test failures on the change before diffing against a clean
  `git worktree add /tmp/bp-head HEAD` run - the suite
  (`uv run python -m unittest discover -s tests/compiler -t tests/compiler`) carries
  pre-existing failures.

## 6. Land it

- **DO** `git fetch` and check `git rev-list --left-right --count origin/main...HEAD` before
  pushing - the branch is shared.
- **DO** stage your own paths, and write no `Co-Authored-By` line.
- **DO** say what the *update* did and where each change's evidence came from - the build,
  the dump SHA, the gophertunnel commit - and account for all four categories:

```
feat(protocol): follow <build> to protocol <new>

<what changed on the wire, and the evidence for each>
```

- **DO NOT** `git add -A`; the libc++ build tree is untracked and stays that way.
- **DO NOT** leave a `#` in a protocol file for anything but an unresolved blocker - a
  `TODO`, a `confirm against BDS`, an open disagreement. Reasoning, how gophertunnel encodes
  a field, and history that `since=` already states go in the commit message.

## Traps

- `__version__` regenerates nothing unless `protocol/__init__.py` is in the codegen
  `DEPENDENCIES` in `CMakeLists.txt` - the `/_*.py` filter keeps it out of `INPUTS`.
- Grep the dump and the schema case-insensitively - BDS spells these `Serverbound` /
  `Clientbound` with a lowercase `b`, so a `ServerBound` search concludes the type is absent.
- Match an enum body with `[A-Za-z0-9_]+`, never `[A-Z0-9_]+`. BDS mixes casing inside one
  body, and the strict pattern silently drops members, then reads as evidence they are
  absent.
- Import `value` even though the AST parser tolerates its absence - ruff will not. `F811`
  and `F821` are per-file ignored for `protocol/*.py`, so redeclarations need no `# noqa`.
- Keep the import graph acyclic. `descriptor_pool.py` *skips* an import already on the build
  stack instead of reporting it, silently dropping that side's versioned set and snapshot
  points.
- A name-coded enum's `Serializer` is emitted only by a module that name-codes it. Declaring
  `E` in one module and writing `e: E = field(type=str)` in another links against a
  `Serializer<E>` nobody generated.
- A `type X = <primitive>` alias is resolved once at parse time and never re-narrowed per
  snapshot. Give a version-dependent width inline at its use; an alias froze at the wide
  value while the field correctly narrowed, and the pool emitted a `requires ()` with a
  single arm, which does not compile.
- A refactor must be output-identical: regenerate the whole schema before and after and
  diff. Behaviour changes ride in their own commit.
