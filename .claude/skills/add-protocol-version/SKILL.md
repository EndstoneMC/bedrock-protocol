---
name: add-protocol-version
description: Adds a new Minecraft Bedrock protocol version to the DSL. Use when bumping `protocol/__init__.py`'s `__version__` to a newer protocol, or when reconciling fields added, removed, or reshaped by Mojang in a specific release. DSL-only edits; raise if the change needs compiler work.
---

# Add a new Bedrock protocol version

A protocol bump is a pure DSL edit. The compiler under
`src/bedrock_protocol/` is **out of scope** for this workflow. If a
change demands new DSL primitives, new compiler features, or a new IR
node, **stop and raise it** instead of editing the compiler in passing.

The output of running this skill is a single coherent commit: every
field, enum value, and packet that changed between the previous
`__version__` and the new one is gated through `since=` / `until=` /
`deprecated=`, every new packet is added with `@packet(..., since=N)`
and a gophertunnel-generated golden test, and the final line of the
diff bumps `__version__` in `protocol/__init__.py`.

## Sources of truth -- read in this order

The community references disagree on wire shape and none of them
enumerate the full change set, so resolve every edit by walking these
sources in order and stopping at the first that confirms the change
against a second.

### Enumeration -- the WHAT (use first if available)

0. **The per-protocol-version changelog** -- a one-line-per-version list
   of what changed (packet / enum / field / component), one entry per
   integer protocol bump. When you have one for the cycle, it is the
   strongest **completeness** check: the sources below tell you *how*
   each change is shaped on the wire, but only the changelog tells you
   the *full set*, so it catches changes a `protocol-docs` two-dot diff
   misses (a still-hand-serialized packet is absent from the dump
   entirely). It does **not** resolve wire shape -- every entry still has
   to be confirmed against the sources below. The verbatim 975->1001
   changelog and its audited verdicts are recorded at the end of this
   file as a worked example.

   **Source / how to refresh for the next cycle:** _TODO -- confirm with
   the maintainer where these entries come from (BDS strings, an
   internal Mojang changelog, a community tracker, ...) and record the
   exact fetch step here, so the next bump can obtain its own
   changelog._

   **Using it during a bump.** Treat the changelog as a checklist: for
   every entry between the old and new `__version__`, find the DSL
   symbol and assign a verdict -- **COVERED-CORRECT** (present, gated at
   the right boundary), **MISSING** (a wire change not yet modelled ->
   gate it, or stop-and-raise if blocked), **N-A-WIRE-INVARIANT**,
   **N-A-NOT-WIRE**, or **PARTIAL** (modelled but simplified; confirm
   against BDS). A clean bump ends with every entry COVERED-CORRECT or
   N-A, and every MISSING/PARTIAL fixed or explicitly raised.

   **Read each entry as a change-kind.** The changelog is not just enum
   notes -- it tells you which packets were re-serialized, which fields
   moved, and which packets are new. Most entries are real wire changes:

   - **"... Converted to Cereal"** -- the packet was migrated to Mojang's
     `cereal` serializer. This is the **highest-value signal in the
     changelog**: it names exactly which packets to re-derive, and it
     flags a **likely binary/wire-format change** -- field reorder,
     prefix-width swap (`uint32` -> `uvarint32`), dropped field, or a
     discriminated union collapsing to a flat layout. When the entry
     adds "broke binary compatibility," the wire definitely changed.
     Never assume the wire is unchanged: diff the post-cereal shape
     against the production refs and gate `since=<release>`. A
     reordering rewrite can exceed what the redeclaration resolver
     expresses and must be marked `COMPILER_EXTENSION_NEEDED` (as
     BossEvent / SubChunkRequest were). Pair with the "A new file in the
     dump is a cerealisation" section below.
   - **Packet field added / removed / reshaped** -- e.g. "Added
     richPresenceId to PresenceConfiguration", "now includes hit
     position", "mSoundEvent changed from LevelSoundEvent to
     SoundEventIdentifier". A real wire change: gate the field with
     `since=`/`until=`, or redeclare it for a type/shape change
     (section 3 of "What the DSL diff looks like").
   - **New packet** -- e.g. "Added ClientboundUpdateSoundDataPacket". Add
     `@packet(id=..., since=<release>)` + a gophertunnel golden test.
   - **Enum member added** -- **N-A-WIRE-INVARIANT** *when the carrying
     field is a raw integer*. If the DSL models the field as a raw alias
     (`type LevelSoundEvent = uvarint32`) or a bare `varint32`, adding
     members (`SlimeLanding`, `Equipping`, `GEYSER_BOOST`, ...) does not
     change the wire -- nothing to gate. Only model the add if the DSL
     has that enum as a named `IntEnum` whose surface you keep complete.
     Doubly moot if the field also becomes a string at the release
     (LevelSoundEvent -> string at 1001).
   - **Behavior-pack / component / world-gen data** --
     **N-A-NOT-WIRE**. Entries naming components or generation data
     (`BlockGeometryComponent`, `BiomeNoiseGradient...surfaceData`) are
     NBT/JSON behavior-pack or chunk-gen data, not network packets --
     don't chase them.

   **Cross-cutting boundary rule -- intra-cycle version numbers collapse
   to the shipped release.** The integers between two shipped releases
   (e.g. 976-1000) are internal / beta increments -- no client ever
   shipped on them. The DSL only carries gates at **shipped release**
   protocols (verify: the only gates in the recent range are `...924, 944,
   975, 1001`, never an intermediate value). So gate every change in the
   cycle at `since=<release>` (e.g. `since=1001`), **not** at its raw
   changelog number -- a change dated 980 or 998 is still `since=1001`.
   This applies to all the kinds above. (The DSL gates at the first
   protocol of a cycle.)

### Primary (drives the diff)

1. **`EndstoneMC/protocol-docs`** -- the dumped JSON / HTML schema.
   The most accurate and complete picture of the **current** wire
   layout for the snapshot it was dumped from. Compare branches with
   a two-dot git diff:
   `git diff <old-branch>..<new-branch> -- serialized/`
   This is where the bulk of additions and shape changes surface
   field-by-field.

### Cross-validation (don't trust either source alone)

2. **`CloudburstMC/Nukkit`** -- a protocol-tracking reference. Its
   gameplay server is barely maintained, but the protocol layer stays
   current (it tracked v1001 / 1.26.30 within a day of release), and
   the commit messages on each wire change are often clearer than the
   dump. Two cautions: it is a *server*, so client-to-server and many
   server-to-client packets have stubbed `decode()`/`encode()` or no
   class at all -- a missing or flat-placeholder packet here is
   silence, not evidence -- and it only models gameplay packets, so the
   test / debug / editor long tail is absent.

3. **`CloudburstMC/Protocol`** -- the standalone protocol library.
   Has per-protocol-version serializers
   (`bedrock-codec/.../bedrock/codec/vNNN/serializer/<Packet>Serializer_vNNN.java`).
   Useful for confirming when a field first appeared, but the library
   is **not used in production** for any active server, so its codecs
   for the newest versions can lag, drift, or be incorrect.

4. **`Sandertv/gophertunnel`** -- Go protocol library used in
   production proxies. Generally safer because real traffic exercises
   it, but the project's update cadence is slower: the latest
   protocol bumps land here last and the diff between current schema
   and the snapshot we're targeting is often incomplete.

5. **`MemoriesOfTime/Nukkit-MOT`** -- an actively maintained,
   production-used multi-version server (a separate Nukkit fork from
   CloudburstMC/Nukkit). It carries many protocol versions in one tree
   behind `if (protocol >= NNN)` branches, so those branches *date* a
   wire change precisely, and it is usually among the first to track a
   new BDS release (it had v1001 / 1.26.30 the day after release). That
   makes it the strongest cross-check exactly where Protocol and
   gophertunnel are weakest -- the freshest versions. Same two cautions
   as CloudburstMC/Nukkit: server-side stubs, and gameplay packets only.
   Never a naming source (see `.claude/rules/protocol.md`) -- Nukkit naming is
   community, not BDS.

### Watch for in-progress work

Both Cloudburst and gophertunnel often land a new protocol on a
feature branch or open PR before merging to default:

- `git ls-remote --heads https://github.com/CloudburstMC/Protocol | grep -iE "v?<NEW>|bds-<NEW>|<release>"`
- `gh pr list --repo Sandertv/gophertunnel --state open --search "<NEW>"`
- Same for `CloudburstMC/Nukkit`, `EndstoneMC/protocol-docs`.

If `master`/`main` looks empty for the version you're bumping to,
look for a branch or PR before concluding the change isn't modelled
yet. WIP material counts as a source, but flag in commit messages
that it came from a branch and may shift before merge.

### Disagreement is a stop sign, not a vote

When the sources disagree about a field's name, type, presence,
or wire position, do not pick one. Pause and surface the discrepancy
to the user. This rule is identical to `.claude/rules/protocol.md`: the
protocol-docs JSON is mechanically dumped and is sometimes wrong, but
silently overriding it with gophertunnel or CloudburstMC just buries
the conflict.

Lean toward protocol-docs for the current shape. It is dumped from the
live server and reflects the current wire layout, while gophertunnel and
CloudburstMC land new bumps last and lag behind, so when protocol-docs
shows a shape the community libs do not, the usual cause is that they are
stale, not that protocol-docs is wrong. Never silently model a community
lib's shape as the current one, and never write "protocol-docs says X but
we model gophertunnel's Y" -- gate the change at the version protocol-docs
introduced it, or raise it. (EditorNetworkPacket reshaped its body from a
CompoundTag to two strings at the v1001 cycle, which gophertunnel and
CloudburstMC still lag.)

### A new file in the dump is a cerealisation, not a freebie

`EndstoneMC/protocol-docs` only emits packets that go through Mojang's
`cereal` reflective serializer. A still-hand-written packet
(`read()` / `write()`) is **absent from the dump entirely**, so when
Mojang migrates a packet to cereal it shows up as a *new file* at that
version -- and that migration frequently **rewrites the wire format**:
field reorder, prefix-width swaps (fixed `uint32` -> `uvarint32`),
optional handling, dropped fields, or a discriminated union collapsing
to a flat layout.

So an added file in the `old..new` diff is not "the dumper finally
noticed an unchanged packet" -- it is the **highest-risk** kind of
change. Never assume the wire is unchanged just because the dump entry
is new, and never trust the dump's flattened view of what used to be a
union -- it cannot represent per-case gating, so it lists every variant
field as if always present and silently drops some. For every
newly-appearing packet the DSL already models, diff the dump's
post-cereal shape against the DSL's existing shape and **date the delta
against the production references** (gophertunnel, CloudburstMC/Protocol,
Nukkit-MOT), then gate it with `since=N`. v1001 alone flattened
`BossEventPacket` (dropping `darken_screen`), reordered
`SubChunkRequestPacket` and swapped its offset prefix to `uvarint32`,
and interleaved `ClientCacheBlobStatusPacket`'s two lists -- every one
of them an added file in the dump, every one a real wire change.

### Reference width is byte-aliased -- never read a discriminator's width off a community lib

BDS `cereal` writes a `std::variant` discriminator, and most small
scoped enums, as a **`uvarint32`**. gophertunnel, CloudburstMC, and
Nukkit-MOT routinely model the same field as a `uint8` (a single fixed
byte). For any value that fits in 7 bits (0-127) -- which covers nearly
every variant index and small enum -- `uvarint32` and `uint8` encode to
the **identical byte**, so the community libs are byte-indistinguishable
from the truth and **carry no information about the width**. A
serializer calling `io.Uint8(&x)` is not evidence the field is one byte
wide, and a "narrowing from `uvarint32` to `uint8`" reported across
versions is almost always an artifact of this aliasing, not a real
Mojang change. (v1001's `BossEventPacket` flattened from a union to a
flat layout and dropped `darken_screen` -- both real and observable --
but the refs *also* showed its `event_type`/`colour`/`overlay` as
`uint8`; those are aliased and stay `uvarint32`.)

Consequences:
- Default a variant discriminator and a small enum to `uvarint32`. In
  the DSL a bare `A | B` union already does this -- never write
  `tag=uint8`, and do not "correct" a width down to `uint8` because a
  reference shows a byte.
- The aliasing only hides **single-byte-range** differences. A
  multi-byte gap is still observable and the references are reliable
  there: a fixed `uint32` length prefix (4 bytes) versus a `uvarint32`
  one (1 byte for small counts) genuinely differ on the wire, so a
  `uint32` -> `uvarint32` prefix change IS a real, ref-confirmable
  change. Keep the two straight -- distrust the refs on
  discriminator / enum *width*, trust them on field order, presence,
  and wide fixed-width prefixes.
- When a discriminator or enum width actually matters, the only
  authority is BDS: confirm the enum's underlying type / the
  `std::variant` against `bedrock-headers`, or disassemble the cereal
  serializer. The community libs cannot answer the question -- they are
  byte-aliased by construction.

## What the DSL diff looks like

The DSL surface admits exactly five kinds of edit. Anything that
doesn't fit one of these is a stop-and-raise.

### 1. New field on an existing struct

A field that appears at version N on a struct that already existed:

```python
class FooPacket:
    existing: varint32
    new_thing: uint8 = field(since=NEW)
```

Optional and `T | None` forms work the same way; the `since=` goes on
the `field(...)` call.

### 2. Removed field on an existing struct

A field present until version N-1 and absent from N onward gets
`until=NEW`:

```python
class FooPacket:
    going_away: str = field(until=NEW)
    still_here: int32
```

The half-open convention means `until=NEW` reads "present in
[..., NEW)", absent at NEW and later.

### 3. Field whose shape changed at version N

Re-declare the field with adjacent ranges. The pair below models a
field that was a `uint32` until NEW and a length-prefixed string from
NEW onward:

```python
class FooPacket:
    icon: uint32 = field(until=NEW)
    icon: str = field(since=NEW)
```

A pure type change works the same way; a rename is **not** the same
thing -- a name change with the same wire shape is just a rename,
not a versioned redeclaration.

### 4. New enum member

Most new enum members are non-trailing. Use `value(N, since=NEW)`
where `N` is the explicit wire number (auto-numbering won't survive
later edits to siblings; see `.claude/rules/protocol.md`):

```python
class DisconnectFailReason(IntEnum):
    UNKNOWN = 0
    ...
    NEW_REASON = value(207, since=NEW)
```

If a member is removed, mirror it with `value(N, until=NEW)`. If
Mojang annotated it deprecated rather than removed, use
`value(N, deprecated=NEW)` -- the value stays on the wire but C++
flags new uses with `-Wdeprecated-declarations`.

### 5. New packet

A wholly new packet:

```python
@packet(id=<id>, since=NEW)
class NewThingPacket:
    """<Description from Mojang/bedrock-protocol-docs verbatim>"""

    field_a: varint32
    field_b: str
```

Every new packet needs a golden round-trip test (`tests/test_<group>.cpp`)
generated by gophertunnel. The golden-tests rule (`.claude/rules/tests.md`) is non-negotiable:

- Never hand-compute the golden bytes.
- Precede with `// generated by gophertunnel:` plus the marshalled
  `packet.NewThing{...}` literal.
- If gophertunnel doesn't model the packet yet -- which is likely on
  the freshest protocols -- **stop and raise**. Do not invent a
  golden, even by reading `Marshal`.

### Stop and raise -- do not edit silently

Pause for the user when:

- A packet is **removed** at version NEW. The DSL today can't gate a
  packet definition with a lone `until=` (see the `ExplodePacket`
  note in `protocol/level.py`). A packet that bedrock-headers marks
  `_DEPRECATED` with no body in any reference is a different case: omit
  it from the DSL entirely, do not keep a `pass` stub
  (see `.claude/rules/protocol.md`).
- A struct is **renamed**, or a field rename collides with another
  field's history. The DSL has no rename primitive.
- A new field uses a wire shape the DSL doesn't model (a packed
  bitfield that isn't a `bitset[N]`, a non-prefixed list whose count
  doesn't reduce to a `count=lambda` expression over earlier fields,
  a discriminator type the union machinery can't express).
- Sources disagree about the change in a way two of the four can't
  resolve.
- gophertunnel doesn't model a new packet, so its golden can't be
  generated. Don't invent the bytes.
- A change clearly needs new compiler IR, a new template, or a new
  primitive. The compiler is off-limits for this skill.

In every "raise" case, surface the conflict or limitation and the
specific blocking material (file path, field, references checked).
Don't pre-decide for the user; the spec lists "Ask first about" for
exactly this reason.

## Workflow

### A. Lock in the scope

1. Read the previous `__version__` from
   [protocol/__init__.py](protocol/__init__.py).
2. Decide the new version N. Verify N is not below 292 (the v291 floor
   in `.claude/rules/protocol.md`) -- the floor doesn't apply to new bumps in practice,
   but a typo that lands you at 291 or below should be caught.
3. Note that the bump should be the **last** edit in the diff. Do
   not bump `__version__` until every gated change is in place.

### B. Survey the diff at the source

4. Pull or refresh local clones of all four reference repos. Also get
   the per-protocol-version changelog for the OLD->N cycle if one exists
   (source 0 under "Sources of truth") -- it is the completeness backstop
   for steps 5-7.
5. Run `git diff` on EndstoneMC/protocol-docs between the branch
   tagged for the old version and the branch for N. Read every
   touched packet file.
6. For each touched packet, cross-check the same packet in:
   - `CloudburstMC/Nukkit` (bedrock-codec or equivalent)
   - `CloudburstMC/Protocol` (`v<N>` serializer if present, else
     latest)
   - `Sandertv/gophertunnel` (`minecraft/protocol/packet/<name>.go`
     and `git log -S<field>` for dating)

   Look at open branches and PRs in each repo before concluding a
   reference is silent.

7. Produce a flat list, one row per change:
   `<packet>::<field> | <kind: add|remove|reshape|enum-add|...> | <sources confirming>`.
   Keep this list in the working notes for the commit; you'll cite
   it in the commit body.
7a. **Coverage pass against the changelog.** If you have the
   per-version changelog, walk every entry between OLD and N and assign
   each a verdict -- COVERED-CORRECT / MISSING / N-A-WIRE-INVARIANT /
   N-A-NOT-WIRE / PARTIAL -- reading each entry as a change-kind
   (cerealization / field change / new packet / enum-add / component)
   and applying the boundary rule, per source 0 under "Sources of
   truth". Cerealization entries are the priority: each is a likely
   binary-format change and names exactly which packet to re-derive. Any
   entry the protocol-docs diff didn't surface but the changelog lists
   is a candidate MISSING. Reconcile the two lists before applying
   edits; an entry that is genuinely N-A is recorded as such, not
   silently dropped.

### C. Apply DSL edits, one file at a time

8. For each affected `protocol/<group>.py`, apply the edits from
   section 4 above. Keep the existing file's idiom -- if siblings
   gate with `field(since=N)` rather than a block, do the same.
9. For nested types, gate on the outermost type that reflects the
   change. A nested struct whose only edit is one added field
   gates the field, not the whole nested type.
10. For new packets, also:
    - Carry the Description from `Mojang/bedrock-protocol-docs`
      verbatim as the docstring (`.claude/rules/protocol.md`). If the upstream
      has no Description, omit the docstring entirely.
    - Resolve every new name through the bedrock-headers /
      protocol-docs / `.dot` files hierarchy (`.claude/rules/protocol.md`).
      Add `# TODO: confirm against BDS` where appropriate.

### D. Write the gophertunnel-driven golden tests

11. For every **new** packet added in step C, write a test under
    `tests/test_<group>.cpp` and register the file in
    `tests/CMakeLists.txt` if it's new.
12. Generate the golden bytes by marshalling the equivalent packet
    in `Sandertv/gophertunnel` (`.claude/rules/tests.md`). If gophertunnel
    doesn't have the packet on `master` or any visible branch/PR,
    stop and raise.
13. For shape changes on existing packets, add or extend a test
    asserting both pre- and post-NEW round-trips against
    gophertunnel goldens.

### E. Bump `__version__` and verify

14. Edit [protocol/__init__.py](protocol/__init__.py): change
    `__version__ = <OLD>` to `__version__ = NEW`. This is the
    last code edit in the change.
15. Rebuild and run the suite:
    ```sh
    cmake --build build
    ctest --test-dir build --output-on-failure
    ```
16. Any new failure is either:
    - a missed gate (a field still emitted at the wrong snapshot),
      or
    - a compiler limitation -- in which case **stop, revert the
      `__version__` bump, and raise**. The compiler stays untouched.

### F. Commit

17. Commit on `main` (per memory: this repo commits to main).
18. Body should cite the per-row change list from step 7 and name
    each upstream source that confirmed each row, so a reviewer can
    audit without re-walking the four repos. No
    `Co-Authored-By: Claude ...` line (`.claude/rules/style.md`).

## Quick reference

| Change | DSL form |
| --- | --- |
| New field | `name: T = field(since=NEW)` |
| Removed field | `name: T = field(until=NEW)` |
| Reshaped field | re-declare twice, `until=NEW` then `since=NEW` |
| New enum value | `MEMBER = value(N, since=NEW)` |
| Removed enum value | `MEMBER = value(N, until=NEW)` |
| Deprecated enum value | `MEMBER = value(N, deprecated=NEW)` |
| New packet | `@packet(id=I, since=NEW)` + golden test |
| Removed packet | **raise** (no lone `@packet(until=)`) |
| Deprecated / unserialized packet | omit entirely (no `pass` stub) |
| Rename | **raise** (no rename primitive) |
| Wire shape DSL can't express | **raise** (no compiler edits) |

## Worked example: the v975 -> v1001 changelog (BDS 1.26.20 -> 1.26.30)

Verbatim per-version entries for the cycle, then the audited verdicts
(2026-06-19). All covered changes are gated `since=1001` per rule 1.

```
976: Added support to noise transitions for ClientboundAttributeLayerSyncPacket
977: Added ClientboundUpdateSoundDataPacket
978: Modified ServerBoundDiagnosticsPacket to include whisker profiler scope diagnostic data
979: SubChunkRequestPacket : Converted to Cereal
980: Added richPresenceId to PresenceConfiguration
981: Updated the data contained in BiomeNoiseGradientsurfaceData yet again.
982: ItemUseOnActorInventoryTransaction now includes hit position for an ActionType::Attack action
983: Added SlimeLanding, AbsorbBlock and EjectBlock to LevelSoundEvent enum
984: BossEventPacket : Converted to Cereal, broke binary compatibility
985: InventoryTransactionPacket : Converted to Cereal
986: LegacyTelemetryEventPacket : Added Equipping to the MinecraftEventing::InteractionType enum
987: Added GeyserEruptionStart and GeyserEruptionActive to LevelSoundEvent enum
988: MobArmorEquipmentPacket: Converted to Cereal
989: Added Cylinder, Ellipsoid, Cone and Pyramid payload types to PrimitiveShapesPacket
990: Added PlayerID to GraphicsOverrideParameterPacket for handling Per-Player Graphics Overrides
991: Add RecordBounce LevelSoundEvent.
992: Added BucketFillLandAnimal and BucketEmptyLandAnimal LevelSoundEvents
993: LevelSoundEventPacket : mSoundEvent changed from LevelSoundEvent to SoundEventIdentifier (variant of enum or string)
994: Added n_way_visual_rotation field to BlockGeometryComponent
995: Added isChatLogging to StartGamePacket
996: ClientCacheBlobStatusPacket : Converted to Cereal
997: LevelSettings: Added allowAnonymousBlockDropsInEditorWorlds flag for hybrid editor worlds and fixed the read-order placement of ServerEditorConnectionPolicy to match the write order.
998: Added MovementEffectType::GEYSER_BOOST
999: Updated mExperienceName and mWorldName in PresenceConfiguration to be optional (StartGamePacket and ServerPresenceInfoPacket)
1000: Added GeyserContinuousEruptionStart and GeyserContinuousEruptionActive to LevelSoundEvent enum
1001: InventoryContentPacket : Converted to Cereal
```

**Covered:** 976 (`attributes.py` noise_transition), 977 (`level.py`
ClientboundUpdateSoundDataPacket), 978 (`player.py` whisker_scopes), 979
(SubChunkRequest -- COMPILER_EXTENSION_NEEDED), 980 (`game.py` richPresenceId),
984 (BossEvent -- COMPILER_EXTENSION_NEEDED), 989 (`graphics.py` PrimitiveShapes),
990 (`graphics.py` player_id), 993 (`level.py` -- modelled as `str`; PARTIAL,
confirm no variant discriminator), 996 (`login.py` ClientCacheBlobStatus,
codegens), 998 (`effect.py` GEYSER_BOOST), 999 (`game.py` experience/world
optional).

**N-A wire-invariant (rule 2):** 983, 986, 987, 991, 992, 1000.
**N-A not-wire (rule 3):** 981, 994.

**Open gaps at the audit:**
- **1001 InventoryContentPacket -> Cereal** -- present at `inventory.py`
  `@packet(id=49)` but no `since=1001` redeclaration. Already uses
  `NetworkItemStackDescriptor` (no import cycle), so directly fixable.
- **995 isChatLogging / 997 allowAnonymousBlockDropsInEditorWorlds** -- absent
  from StartGamePacket / LevelSettings.
- **982 / 985 / 988** (ItemUseOnActorInventoryTransaction hit_pos,
  InventoryTransactionPacket, MobArmorEquipmentPacket cereal) -- only in
  `protocol/_drafts/`, blocked on the `NetworkItemStackDescriptor` resolver cycle.
