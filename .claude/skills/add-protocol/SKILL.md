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
  **"Run it" and "dry run it" both mean all four**, every time - a partial pass is not a
  smaller version of this workflow, it is a wrong answer with a confident shape. Reporting
  three categories and calling the fourth "not yet walked" is the failure, not a caveat.
- **DO** fan out rather than defer when the four do not fit one pass. One agent per category,
  each given the interval, the four sources and the schema to check against, is the intended
  shape - the categories are independent by construction, so they parallelise exactly.
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

### 2168 is the template

Whichever direction you are going, the shape the schema already models at 2168 is the
baseline and the version you are adding is a delta against it. You are never modelling a
packet from scratch.

- **DO** start from the declaration in `protocol/*.py` and establish only what the target
  version does *differently*. Forward, that delta lands on top of it; a back-port peels one
  off it, as `until=` or as an earlier redeclaration tiling under the same id.
- **DO** keep 2168's names, field order and type vocabulary except where the evidence names
  a change - see **Naming**.
- **DO NOT** re-derive a whole packet body from gophertunnel because the target is
  pre-cereal. The `Marshal` walk answers what differed *then*, not what the packet is.
- **DO NOT** let the template stand in for evidence. It is where you start reading and the
  spine the names hang on, never a claim about the older wire.

## Sources

**There are exactly two sources of truth, and everything else is a pointer.**

| | source of truth |
| --- | --- |
| cerealised at that version | `github.com/EndstoneMC/protocol-docs`, the era's branch |
| hand-written at that version | **`<Packet>::write` decompiled in that era's IDA database** |

| pointer - tells you *where to look*, never what is true | |
| --- | --- |
| `github.com/Sandertv/gophertunnel` | which bytes moved, and golden generation |
| `github.com/CloudburstMC/Protocol`, `Nukkit-MOT` | per-version dating |
| `Mojang/bedrock-protocol-docs`, `legacy_changelogs/` | which step inside a cycle |
| **bedrock-headers**, the era's branch | names, C++ types, member order - see **Naming** |

- **DO** finish a pre-cereal reading in the binary. The IDA databases are already built, one per
  build, under `bedrock-symbols/<platform>/<build>/`; `<Packet>::write` decompiles in seconds
  and BDS labels every field itself, because each write carries its own name string.
- **DO NOT** take a *type* from gophertunnel any more than a name. It is a Go codec's
  modelling, not BDS's, and it will merge or split members freely.
- **DO NOT** read one write call as one field. **The binary settles the bytes; the header
  settles how many members produced them.** BDS packs adjacent members into a single call:
  `BossEventPacket::write` at 975 emits one `writeUnsignedShort` labelled `"Darken Screen"`,
  and the header at `android/r26_u2` declares `byte mDarkenScreen` **and** `byte
  mCreateWorldFog` - two members, little-endian, one call. Reading the writer alone concludes
  one `uint16` and loses a field BDS really has; reading the header alone never sees that they
  ship in one call. Use both, every time.
- **DO NOT** conclude a field is wrong because the era you are back-porting to lacks it. It may
  be right at the *other* era, which makes it two models rather than a fix - the pair above
  exists at 975 and is gone from the cereal form at 1001, so `until=1001` carries it and
  `since=1001` does not.

Commands below assume you have each repo cloned locally; substitute your own paths. If one
is missing, **clone it** rather than working around its absence - CloudburstMC needs only
`--depth 1`, since every version's codec directory lives at HEAD.

`bedrock-headers` is access-restricted. Read it, cite the branch you read, and paste none
of it anywhere - see **Naming**.

### Naming

**bedrock-headers** is the naming authority, per `CLAUDE.md`'s sources table, and it earns
no `# TODO`. It is branched per release and read without a checkout -
`git show origin/android/r26_u4:<path>` - from `android/r21_u4` (~786) up to
`android/r26_u4` (1.26.40, 2168). Read `origin/<branch>`: a local branch goes stale, and a
stale header does not read as stale, it reads as a finding.

**Header coverage stops at 2168**, which is exactly where the forward work starts. So a
back-port is named from the header, and a forward version is named heuristically for
whatever is new above it.

- **DO** settle a back-port name on the era's branch - a type's shape differs across them -
  and say which branch you read in the commit message.
- **DO** treat a `uN` as one update line with one wire shape. The same `uN` names different
  builds in different repos - bedrock-headers' `android/r26_u3` is 1.26.32, protocol-docs'
  `r26_u3` is 1.26.36.1 - and they still agree on the wire, so the era's branch and the
  era's binary are valid arbiters for each other.
- **DO** reach for the newest branch on forward work too. It cannot describe a field added
  after 2168, but it settles anything that already existed at it: an enum carries its full
  member list there whether or not cereal binds it.
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
- **DO NOT** paste bedrock-headers source into the schema, a commit message or this file.
  Reading it to settle a name is the authorized use; reproducing it is not. Cite the branch
  instead.

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

### An id with no packet behind it

BDS keeps an id in `MinecraftPacketIds` long after the class is gone, so an entry there is
not evidence a packet exists. Ask the question directly before modelling one - and before
concluding a packet is missing from the schema.

- **DO** answer it from **bedrock-headers**: a live packet has a `<Name>Packet.h`, and the
  name in the id enum drops its `_DEPRECATED` / `_deprecated` / `_Deprecated` suffix to give
  it. Of the 22 ids the schema left unmodelled at 924, **all 22** had no class header at any
  branch from `r21_u4` to `r26_u4`, and the binaries agreed.
- **DO** run live packets through the same probe as controls in the same command. A probe
  that quietly matches nothing looks identical to a true negative, and the controls are what
  tell the two apart - `DebugDrawer`, `Text`, `Login`, `StartGame`, `PlayerSkin` all resolve.
- **DO NOT** use `??$make_packet@V<Name>Packet@@` as the packet list. It is instantiated for
  one construction path only - 178 of 240 ids at 924 - and omits `LoginPacket`,
  `TextPacket` and `StartGamePacket` among others, so reading absence there as "removed"
  invents dozens of false deprecations.
- **DO NOT** read `?getId@<Name>Packet@@` as universal either. It resolves for
  `DebugDrawerPacket` and not for `TextPacket` in the same stripped 924 build.
- **DO NOT** date the removal from the enum name. `ScriptCustomEvent` (117) carries no
  deprecation suffix and has had no class for the entire range these sources cover.

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
  **`auto()` absorbs an insertion and a removal in the same span, and they can cancel.**
  Between 944 and 975 that same enum gains `Rendering_RenderRegistry = 60` *and* loses
  `VR = 68`: everything from `Rendering_Library` to `Textures` shifts up one, and
  `WeatherRenderer` lands on 69 at **both** eras. Written as two gates -
  `value(60, since=975)` on the arrival, `value(until=975)` on the departure - with every
  member between them `auto()`, both eras fall out and nothing else is touched. Reach for a
  whole-enum redeclaration only when that fails.
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
- **DO** let a `std::bitset<N>` instantiation in the binary date the enum that sizes it. A
  `bitset[E.COUNT]` field means `E`'s sentinel *is* a wire width, so the writer's
  `?_Xoflo@?$bitset@$0HP@@std@@` (`$0HP@` = 0x7F) pins `ActorFlags::Count` at **127** for 944 -
  which is how the changelog was caught over-reporting four additions at 126..129 when 126
  already existed. The binary outranks the changelog on arithmetic.
- **DO NOT** assume a bound value is the *right* value. The dump can bind a wrong one, not
  merely omit: at r26_u2 `EAS::FloatAttributeOperation` binds `MINIMUM` and `MAXIMUM` both to
  4, colliding with `MULTIPLY`, while the header carries 5 and 6 **byte-identically at both
  eras**. That reads exactly like a renumber and is a dumper bug. Settle a value in the
  header before gating anything.
- **DO NOT** treat the C++ enumerator's spelling as cosmetic. The reflected name table is that
  spelling lowercased with **no separator**, and for a name-coded enum that table *is* the
  wire - `RebeccaPurple` folds to `rebeccapurple` where `REBECCA_PURPLE` folded to
  `rebecca_purple`, and BDS writes the former (`test_077`'s golden matches `automationplayer`).
  So changing how the enumerator is derived is a wire change, and `enum_cast` folds case but
  not underscores.
- **DO NOT** read a wholesale respelling as a rename. `SharedTypes::Legacy::LevelSoundEvent`
  respells all ~563 members between two branches (`ItemUseOn` becomes `item.use.on`) because
  the *dumper* switched to emitting the bound `SoundEventIdentifier` strings; the header keeps
  the CamelCase spellings at both eras. The answer was a packet redeclaration for the field
  that went int-coded to name-coded, not a versioned enum.
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

The dump exists here but covers only the cerealised half, so the four are discovered from
three partial diffs instead of one - see **Discovering the four**. Which half a packet sits
in decides which of those diffs can see it, and presence in the dump at that version is the
test:

| in the dump | cerealised - the dump is the wire, and a variant tag is **always `uvarint32`** over cases in declaration order |
| --- | --- |
| **absent** | hand-written - the dump cannot describe it and gives no hint. Go to the Marshal history |
| **new file between two branches** | usually that packet *cerealised* there - the highest-risk change in the repo - but confirm it, see below |

**A new dump file is not proof of a cerealisation.** It can equally be the *dumper's*
coverage expanding. Mojang's `legacy_changelogs` names six conversions in the 976..1001
window - `SubChunkRequest` 979, `BossEvent` 984, `InventoryTransaction` 985,
`MobArmorEquipment` 988, `ClientCacheBlobStatus` 996, `InventoryContent` 1001 - while the dump
gained **ten** packet files there. The four extras (`ResourcePackStack` 7, `UpdateAttributes`
29, `CommandBlockUpdate` 78, `UpdateAbilities` 187) have no changelog entry at any version.

- **DO** cross the dump's file-appearance against the changelog before calling something a
  cerealisation, and settle a disagreement by reading the era's `Marshal` field-by-field
  against the newer dump. For those four it comes out byte-identical either way, so the
  question is academic *there* - but the inference is not sound in general.
- **DO NOT** try to settle it by grepping the binary for the cereal display strings. They are
  present at both eras for packets the changelog says converted in between, so the probe
  measures string presence, not cerealisation.

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

### Discovering the four

§3 gets all four categories out of one diff. Here no single diff sees everything, so you
run three - and you hold on to what each one can and cannot witness.

**One step down, never a skip.** The two eras are the target and the nearest snapshot the
schema *already models above it* - for 1001 that is 2168, never 975. A back-port is a delta
peeled off the step above, so the interval always runs from the target up to its nearest
modelled neighbour.

**gophertunnel, between the two eras' commits.** Date each era by its `CurrentProtocol`
bump, then diff the whole protocol tree between those commits, not just the packet you came
for.

```shell
git log -S'CurrentProtocol = <old>' --oneline -- minecraft/protocol/info.go
git log -S'CurrentProtocol = <new>' --oneline -- minecraft/protocol/info.go
git diff <old-sha>..<new-sha> -- minecraft/protocol/
```

`-S` returns **two** commits per number, the one that introduced the constant and the one
that removed it. Take the **introducing** commit from each pair.

That diff carries all four - the id list is category 1, a `Marshal` body 2 and 3, the
constant tables 4 - but it is the *candidate set*, not the changelog. The window holds three
kinds of commit and only one of them dates to the new version:

- **the bump itself** - the real delta.
- **a retro-fix to the OLDER era** - a codec correction landing after the old bump, which
  describes what the old version always did. `ServerboundDataDrivenScreenClosedPacket` took
  two inside the 1001..2168 window - `CloseReason` retyped, `FormID` made non-optional - and
  CloudburstMC re-declares no serializer for it at 2168 because nothing changed at 2168.
  Dating these by the interval gates a 1001 correction at 2168.
- **non-wire churn** - allocation and codec-performance refactors, transport plumbing, doc
  fixes. They touch `writer.go` and read like wire changes.

- **DO** classify every commit in the window before attributing any of it. In 1001..2168
  that is 15 commits: one bump, ~5 retro-fixes, 5 non-wire, 2 doc-only.
- **DO NOT** read the interval diff as the changelog.

**CloudburstMC, between the two codec directories.** A serializer is re-declared under
`codec/v<new>/` only when it changed - it otherwise just inherits `..._v<old>` - so the
listing of that directory *is* the packet-level changelog, and `Bedrock_v<new>.java` against
`Bedrock_v<old>.java` gives the id registrations. It is a directory comparison at HEAD, not a
history walk.

Cross-check that listing against gophertunnel's, and mind how you compare:

- **DO** compare it against gophertunnel's **whole `minecraft/protocol/` tree**, never
  `packet/` alone. A Cloudburst serializer inlines the closure where gophertunnel splits it
  into `minecraft/protocol/*.go`, so a `packet/`-only comparison manufactures phantom
  disagreements at exactly the packets whose *closure* moved - `CreativeContent`,
  `ItemStackResponse` and `DimensionData` all read as Cloudburst-only until `creative.go`,
  `item_stack.go` and `world.go` are in the set.
- **DO** normalise the names before diffing the two lists. **The refs do not spell packets
  the same way**, and a literal comparison reports correct code as missing:
  - case - gophertunnel writes `ClientBoundMapItemData` and `ServerBoundDiagnostics`,
    Cloudburst writes `Clientbound` and `Serverbound`.
  - vocabulary - Cloudburst says **Entity** where BDS says **Actor**, so its
    `MoveEntityDeltaPacket` is `MoveActorDeltaPacket`; gophertunnel spells `MobArmourEquipment`
    where BDS spells `MobArmorEquipment`.
  Resolve every name to the **BDS** spelling before comparing anything - to either ref's list,
  or to the schema. A raw set difference manufactures phantom "not modelled" findings.

**protocol-docs, as a hint - never as the diff.** The dump describes only what is fully
cerealised at that version. A change inside a type BDS still writes by hand is not in it,
so an empty dump diff is not a finding and a dump hunk is not a measurement.

- **DO** check dump presence *first*, per packet. A packet present at **both** eras is
  cerealised at both, so the dump **is** the wire for it and settles the question outright -
  no ref adjudication needed. `InventoryContent`, `InventorySlot`, `MobEquipment` and
  `MobArmorEquipment` are all in the dump at 1001 and 2168, and the dump names the one real
  change between them where reading two refs against each other only raised a suspicion.
- **DO** spend a dump hunk as a *pointer* where the packet is absent at either era: it says
  which type is worth reading, and the reading then happens in bedrock-headers at the era's
  branch and in the `Marshal` history.
- **DO NOT** promote a dump hunk into a finding below 2168, and do not read dump silence as
  "unchanged". They are the same laziness in opposite directions.

**Mojang's own changelog, as a second hint.** `Mojang/bedrock-protocol-docs` carries
`legacy_changelogs/changelog_<protocol>_<MM_DD_YY>.md`, one file per cycle from 407 to 2168.
It is the only source **keyed by protocol number**, and its entries are numbered by the
*intermediate* step, so it says which number inside the cycle a change actually landed on -
`984: BossEventPacket : Converted to Cereal, broke binary compatibility` dates that
cerealisation to 984, not to 1001. It also names renames in BDS member spelling:
`993: LevelSoundEventPacket : mSoundEvent changed from LevelSoundEvent to SoundEventIdentifier`.

**Only the step-numbered half dates anything.** A changelog file holds two things: a list
whose lines open with an intermediate protocol number, and a bare `Added X` / `Removed X`
summary. The step list is tight and barely overlaps its neighbours - 893 covers steps
860..897, 924 covers 894..924, 944 covers 925..944 - and it is the dating authority. The
bare summary is **cumulative**: it re-lists what earlier cycles already shipped, so an entry
appearing in it dates nothing at all. 156 of `changelog_944`'s 178 bare entries (**88%**)
appear verbatim in `changelog_924`, and `changelog_893` has 159 fewer of them than `924`
because it carries **none** - it is step list only.

That one mechanism explains both standing over-reports. `Added Lunge (41)` and
`Added ROTATION_LOCKED_TO_VEHICLE (126)` sit in the bare summary of *both* the 924 and the
944 files, yet `changelog_893`'s step list already dates them: `863: Added enchantment
"Lunge"` and `865: Added ActorFlags::ROTATION_LOCKED_TO_VEHICLE`. Both predate the whole
1.26 line, and the binaries agree - `LungeEnchant` is in the 898 build and the 924 build
alike.

- **DO** read the step-numbered lines to find cerealisations stated outright rather than
  inferred from a dump file appearing, and to date a change to its step - which is what "the
  changelog dates it to N" means under **Then model it**, where the gate still lands on the
  next materialized snapshot at or after N.
- **DO** check the step range at the top of the file before trusting any line in it, and
  read the *previous* cycle's file when a step number falls below that range.
- **DO NOT** date anything by the bare `Added`/`Removed` summary, and do not read a name's
  presence there as an arrival. Diff it against the previous file first: what survives the
  diff is a candidate, not a finding, and the header or the binary still settles it.
- **DO NOT** treat it as complete. It carries no wire types, does not list removals, and
  omits silently: the 1001 changelog never mentions `SendPartyDestinationCookiePacket` or
  `PartyDestinationCookieResponsePacket`, and the dump proves both arrived at 1001.
- **DO NOT** let it outrank the dump or the binary. `CLAUDE.md` puts Mojang's docs last, and
  a claim resting on this file alone earns a `# TODO: confirm against BDS`.

**When gophertunnel and CloudburstMC disagree, read the binary.** They are independent
codecs of the same bytes and should agree; a disagreement means one of them is wrong, and
only the BDS build for that version settles which. A packet BDS has not fully cerealised
keeps its own manual writer, so `<Packet>::write` is there to decompile in that version's
IDA database - decompile it rather than reasoning from the refs.

- **DO NOT** read the *presence* of `<Packet>::write` as proof a packet is hand-written.
  Nearly every packet overrides it - 223 of them in the 1.26.32 PDB - because the cereal path
  is driven from inside that override. Only the body answers the question.

### Where the gate lands

A delta lands in exactly one of three places, and **the packet declaration is only one of
them**:

- a **packet redeclaration** - `@packet(id=N, until=X)` / `@packet(id=N, since=X)` tiling one
  id. Earned when the shape shifted, and earned again when the id *changed owner*: a version
  can hand id N to a different packet, which is two classes tiling one id, not a rename.
- a gate on a **closure type** - `@type(until=X)` / `@type(since=X)` on something the packet
  contains. `ItemStackResponsePacket`, `CreativeContentPacket` and
  `StructureBlockUpdatePacket` are each ungated at 2168 while `ItemStackResponseInfo`,
  `CreativeGroupInfoPayload` and `StructureEditorData` carry the gate.
- an **inline field gate** - `damage: int32 = field(type=uint8, until=2168)`.

- **DO** read all three before calling a packet unhandled. An ungated `@packet` line is the
  normal, correct outcome when the top-level field list did not move and the delta sits
  lower in the closure.
- **DO NOT** audit coverage by grepping the `@packet` line. It reports correct code as
  broken, and the repair it invites - splitting a packet that should stay whole - is a real
  wire break.

### Gate a packet at the version it was introduced

An ungated `@packet` claims the packet existed at protocol 0. That is false for anything BDS
added after the floor, and it is the mirror of the over-gating above: the sweep that lowers
gates will happily lower one past its own introduction.

**The header's packet-id enum dates every id, and `EndId` is the fast read.** Across
`android/r21_u13` / `r26_u0` / `r26_u1` / `r26_u2` the last real id runs 332 / 339 / 345 / 347,
so ids 340..345 arrive at 944 and 346..347 at 975 - which Mojang's changelog confirms as
"960: Added ServerStoreInfoPacket and ServerPresenceInfoPacket".

- **DO** gate the body **and** the `MinecraftPacketIds` member at the same version. An id
  ungated below its body puts an undecodable id on the wire; a body ungated below its id
  claims a packet BDS did not have.
- **DO** exclude the sentinel when parsing that enum. `EndId = 346` matches a naive
  `NAME = <int>,` pattern and reads as a packet at id 346, which places two ids an era early.
- **DO** accept that an introduction gate can materialize a new snapshot - 346/347 forced 975
  into existence - and that this is the evidence doing its job, not a cost to avoid.

### Lowering a gate is a back-port

The cheapest back-port is **not modelling at all**. Where a declaration's shape is already
right at the target, the whole change is its gate: `since=2168` becomes `since=<target>`, and
nothing is re-modelled. Ask this before writing anything.

**`since=2168` is a floor the schema was bootstrapped on, not a finding.** The schema was
built at 2168 and everything landed there by default, so a back-port is mostly a sweep of
that population rather than a hunt for deltas. Measured against the 1001 dump, of the **173**
packets declared only from 2168, **169** are byte-identical at 1001, **4** differ
(`MapInfoRequest` 68, `PhotoTransfer` 99, `RequestAbility` 184, `CameraAimAssist` 316) and
**none** is absent. The back-port is a gate edit for all but four.

- **DO** run that sweep first: list every packet whose only declaration is `since=2168`, then
  diff each one's `packets/*.json` between the target's dump branch and 2168's. It costs one
  loop and it scopes the whole job before any modelling starts.
- **DO NOT** stop at the packet's own JSON. Byte-identity there does not clear the closure -
  a referenced type can still differ, which is the standing rule to diff the whole transitive
  closure. The sweep produces *candidates*, and the closure diff confirms them.
- **DO NOT** forget that lowering a gate can **delete the type's versioned alias**. The backend
  emits `X_<V>` only for a type that actually varies by version; a packet that becomes valid
  everywhere is emitted as a plain `struct X` and both `bp::X_<2168>` **and** the qualified
  `bp::v2168::X` stop compiling - sweep for the namespace form too, it is the one that hides.
  Lowering 171 gates cost 161 aliases and 1073 references across 162 test files, and `endweave` consumes the
  same headers. Regenerate and diff the emitted `using X_ =` set before and after - that set,
  not the schema, is what consumers bind to.

**The same bootstrap leaves enums under-gated, which is the worse half.** A packet inherited
the floor as `since=2168`, too high; an enum inherited it as *no gate at all*, so `base`
carries 2168's member set and its sentinel and claims both were true from protocol 0. Sweep
that too, and separately - the two look nothing alike:

| | symptom | failure |
| --- | --- | --- |
| packet | `since=2168` too high | loud - nothing decodes the id |
| enum | no gate at all | silent - decodes a value BDS never had, and `Count` lies |

- **DO** check every ungated enum's sentinel arithmetic *at the target*, not just at head.
  Three were wrong at 975 **and already wrong at 1001**: `CurrentCmdVersion` (`COUNT` reads 51
  where the header says 47 at 975 and 50 at 1001), `MinecraftEventing::AchievementIds`, and
  `Connection::DisconnectFailReason` (`MAX` reads the 2168 value at `base`).
- **DO** price the follow-out before gating: the gate versions the enum, so a consumer
  spelling `bp::base::E::MEMBER` stops compiling while the `bp::E_<N>::` alias form survives.

The test is byte-identity of the declared shape across the two eras, and for a packet
cerealised at or below the target the **dump settles it outright** - identical JSON at both
eras means lower the gate and stop. Six packets sit in exactly that state at 1001:
`SendPartyDestinationCookie` (349) and `PartyDestinationCookieResponse` (350), new at 1001
and modelled `since=2168`; and `CommandBlockUpdate` (78), `ResourcePackStack` (7),
`UpdateAbilities` (187) and `UpdateAttributes` (29), cerealised at 1001 and modelled from
2168. Every one has a body identical at 1001 and 2168.

- **DO** check that a packet's **id gate and body gate agree**. `MinecraftPacketIds` gates
  349 and 350 `since=1001` while both bodies start at 2168, which puts an id on the wire at
  1001 with nothing able to decode it. An id gated below its body is always a defect.
- **DO NOT** read "the packet is modelled" as "the packet is supported at this version". It
  is modelled *from some version*, and the gate is the claim being audited.
- **DO NOT** lower a gate past what the evidence covers. Below the cerealisation the packet
  was hand-written and the cereal shape says nothing about it - that half is real modelling,
  not a gate edit.

### The hand-written half

gophertunnel and CloudburstMC are the main reference here, and **they do not decompose a
packet the way BDS does**. They flatten a BDS struct into the packet, split one in two,
inline a shared type, and name the pieces themselves. Take what they are good for - which
bytes, in what order, at which version - and take the shape from elsewhere.

- **DO** hold the type boundaries and names the 2168 declaration and the era's header
  already give you, and land the ref's finding as a change *inside* that shape.
- **DO NOT** introduce a type because a ref has one, or dissolve one because a ref does not.
  A ref's struct boundary is an implementation detail of that codec - not wire, not
  evidence, and adopting it renames types the schema already exports.

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
- **DO** collapse a ref's *shared-helper swap* to the one type it actually describes. A
  helper swapped at a version rewrites every call site at once and reads as an N-packet wire
  change: gophertunnel moved `InventoryContent`, `InventorySlot`, `MobEquipment` and
  `MobArmorEquipment` from `ItemInstanceNew` to `ItemInstance` at 2168, and the whole of it is
  one field on one shared type - `Net Id Variant` going from a tagged variant to a plain
  `varint32` - which gates once on that type and leaves all four packets ungated.
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
- **DO NOT** carry a ref's known-wrong reputation across eras. gophertunnel's
  `MemoryCategory` `VR` entry is the standing example of a phantom constant - and the header
  says `VR = 68` is **real at 944**, removed at 975. gophertunnel is right at the older era
  and stale at the newer one. "Ref X is wrong about Y" is always dated; re-check it at the
  era you are modelling.
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
- **DO NOT** reach for `field(type=X, until=N)` to switch a width at N. It means "this field
  exists **until** N, encoded as X" - it *removes* the field at the gate. `AnvilDamagePacket`'s
  `damage: int32 = field(type=uint8, until=2168)` is correct precisely because BDS deletes
  Damage Amount at 2168. A field that lives at both eras with different widths is a
  **redeclaration pair**, and the generated serializer is where you catch getting it wrong -
  the field simply vanishes from the later namespace.
- **DO NOT** declare the same field twice over disjoint gates to switch its *type*
  (`pos: NetworkBlockPosition = field(until=944)` then `pos: BlockPos = field(since=944)`).
  It is the obvious shape, the `prototype` branch uses it, and **this compiler drops it
  silently**: `importer.py`'s `_unshadow_repeated_members` rewrites only `ast.Assign` - enum
  members - so a repeated `ast.AnnAssign` struct field stays one key in griffe's member dict
  and the second annotation overwrites the first with no error. Redeclare the owning class
  instead. `NetworkBlockPosition` -> `BlockPos` at 944 is the standing case: 21 owners, each
  a tiling pair, and five of them already tiled at 1001 or 2168 so they became three-tile
  chains.
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
- **DO** re-read every `bp::base::` in the suite after materializing a snapshot. `base` stops
  meaning what it meant: a case that builds a payload from `bp::base::` types and asserts it
  against a *newer* era's golden was only ever right because the two shared a shape. Splitting
  944 from 975 caught `test_122` and `test_328` encoding the 944 shape against a 975 golden -
  they compiled and passed before, and the snapshot is what exposed them.
- **DO NOT** attribute a red C++ suite to your change before checking it built at `HEAD`. It
  can be dark for many commits: a backend change that renamed every emitted enumerator updated
  `tests/compiler/` and left all 214 `tests/test_NNN_*.cpp` behind, so 844 references across
  120 files had been stale for as long as that - and the rot hid two real regressions, a member
  the schema had since renamed and a changed wire fold, behind what looked like spelling drift.
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
