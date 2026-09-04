# CLAUDE.md

## Sources of truth

Each aspect of a type has one authority. Walk them per aspect, not as a ranking,
and confirm against a second source before acting:

| aspect | source |
| --- | --- |
| field/class name, C++ type | **bedrock-headers** (`~/bedrock-headers`) — authoritative, no TODO needed. Branched per release (`android/rNN_uN`); a type's shape can differ from head, so read the era's branch. BossEvent's enums were `: int` through r26_u2, `: uint8_t` at r26_u3 |
| wire type, order, prefix | **EndstoneMC/protocol-docs**, on the release branch (`r26_u3`) |
| golden bytes | **gophertunnel** (see Tests) |
| dating, cross-validation | **Nukkit-MOT**, **CloudburstMC/Protocol** |

Never take a *name* from gophertunnel or CloudburstMC — they date and shape
symbols, they do not name them. Mojang/bedrock-protocol-docs is a last resort and
always earns a `# TODO: confirm against BDS`. **Do not trust `prototype`**: it has real
bugs (its StartGame `game_type` is `uvarint32` where the wire is `varint32`).

**A ref is only as good as its consumer's coverage.** CloudburstMC/Protocol is
exercised by Geyser, gophertunnel by Dragonfly — a packet neither runs has an
effectively untested codec. Agreement is evidence only where the consumer actually
exercises the packet; silence is never evidence. Check whether a codec and a test
exist before leaning on a ref. gophertunnel's `MemoryCategory` list is the standing
proof: it carries a `VR` entry BDS does not, so every constant after `Textures` is
off by one and nothing caught it.

**Read `origin/<branch>`, never the local one.** protocol-docs' local branches go
stale, and a stale dump is not merely old — it is *wrong in the direction that
looks like a real finding*. A sweep that read the working tree's `r26_u3` (four
commits behind) concluded BossEvent and MobEquipment narrowed `uvarint32` to
`uint8` between 1001 and 2168; `origin/r26_u3` says `uint8` at both, and the
whole "disagreement" was the stale checkout. Same for bedrock-headers eras: use
`git show origin/android/r26_u3:<path>`, and never `git checkout` in either repo.

**BDS is the faithful source; a community codec is not, ever.** Where a ref
disagrees with BDS, the ref is wrong until proven otherwise, and it has been
wrong repeatedly: gophertunnel writes the unlocking requirement for chemistry
recipes (BDS does not), calls `mNumIngredients` "TimesCrafted", and carries the
phantom `MemoryCategory` VR entry; CloudburstMC reads a second plain string for
`RedactableString` where BDS has `optional<string>`. Agreement between two refs
is not evidence — they copy each other.

**When the header and the dump disagree, read the binary.** That is the only
arbiter, and it is cheap: the IDA databases under `~/bedrock-symbols` are already
built. Two methods that worked. Decompile the writer directly, which settled the
chemistry recipes (`serialize<ShapedChemistryRecipe>::write` ends at Assume
Symmetry). Or, where symbols are absent, count code owners of a cereal field-name
string literal — `"Radius X"` and `"Radius Z"` are registered back to back in the
shape cerealizer, proving `CylinderDataPayload`'s single `Vec2 mRadii` is bound
twice and two Vec2s reach the wire.

**Dating shortcuts:** Nukkit-MOT annotates members `@since vNNN`. A CloudburstMC
`Serializer_v1001` that extends `Serializer_v975` and appends a field dates that
field to 1001.

**A protocol-docs branch is a network version**, not a release ordering — check its
README (`r26_u3` = 1001, `r26_u4` = **2168**). A packet missing from the dump is not
cerealised at that version, so the dump cannot describe it at all.

## Settled — do not re-open without new evidence

Each of these was argued from the binary or the headers and closed. Re-deriving
them from a community codec will reach the wrong answer, because in every case a
codec is what disagreed.

| question | answer | evidence |
| --- | --- | --- |
| `PlayerAuthInputPacket.input_data` at 2168 | a **length-prefixed list of `InputData`**, not a bitset | the header's `std::bitset<66>` is the in-memory member and does not describe the cerealised wire; protocol-docs and CloudburstMC both read the list and are right. The pre-cereal (`until=2168`) form *is* a bitset — gophertunnel writes `io.Bitset(&pk.InputData, 65)` — so the two eras genuinely differ |
| the pre-cereal legacy slot gate | gophertunnel's: `id < -1 and (id & 1) == 0` | matches the `prototype` branch's modelling; a negative-even id is a legacy request |
| `CylinderDataPayload` | **two** `Vec2`s, not the header's one | 1.26.33 registers `"Radius X"` and `"Radius Z"` back to back in the shape cerealizer; Cone's single `"Radii"` is registered elsewhere in the same function |
| chemistry recipes and the unlocking requirement | they do **not** write it | `serialize<ShapedChemistryRecipe>::write` ends at Assume Symmetry, `serialize<ShapelessChemistryRecipe>::write` at Priority; the four non-chemistry writers do write it |
| `ContainerID` width per call site | packet 49 `uvarint32`, packet 50 `int8` — deliberately different | they part company at `NONE = -1`; unifying corrupts every `NONE` |
| a name-coded enum's casing on the wire | **lowercased**, and the read matches nothing else | `BasicFactory<E>::memberDescriptorFor` runs `tolower` over the bound name into `mName` (+0x30) and keeps the original in `mNameExt` (+0x10); `TypeSchema<E>::doSave` writes `mName`, and the meta_data id hashes it. Confirmed against gophertunnel's lowercase-both-ways `CommandOriginType` table. Reading the *bind site's* string literal is what got this backwards once — that literal is `mNameExt`, which never reaches the wire |

## Names mirror BDS

Class names and nesting match BDS exactly, so the generated C++ reads like the BDS
headers. Never fold an enclosing namespace into a class name:
`Bedrock::Profile::Whisker::Diagnostics::ScopeDataSummary` is `ScopeDataSummary`.
A BDS `Outer::Inner` stays nested, never flattened to `OuterInner`. A
`FooPacketPayload` maps onto `@packet FooPacket`, dropping the `Payload` suffix —
**and its nested types come with it**, into the packet rather than into a scoping
class of their own. `PlayerListPacketPayload` held `AddEntry` and `RemoveEntry`
beside the packet for a while; both now live inside `PlayerListPacket`. No
`…PacketPayload` class should exist in the schema.

**Nesting is a `class` inside a `class`**, enum or struct, and a body references
its own nested names bare (`action_type: ActionType`) — lookup walks outward to
module scope, so `Owner.Inner` reaches one from elsewhere. A redeclared owner
repeats each nested type verbatim in every body; identical repeats collapse to a
single C++ type, and bodies that disagree version it. Where only the nested type
is modelled, declare the owner with no fields: it scopes the name and gets no
`Serializer` (`SubChunkPacket` exists solely to hold `SubChunkPosOffset`).

Grep bedrock-headers **case-insensitively**: BDS spells these `Serverbound` /
`Clientbound` with a lowercase `b`, so a `ServerBound` search wrongly concludes the
type is absent.

**Never transcribe an enum with a case-sensitive pattern.** BDS mixes casing
inside one body, so an `[A-Z0-9_]+` match silently drops members and then reads
as evidence they are absent: `ActorDataIDs` went in two short, missing
`DATA_SPAWN_TIME_deprecated = 96` and `Count = 141`, and the commit message
claimed the header lacked 96 on the strength of it. Match `[A-Za-z0-9_]+`, and
check the count against the header before believing a gap.

A field name colliding with a Python keyword takes a single trailing underscore
(`pass_`), which the compiler strips — BDS's `mPass` keeps its name on the wire and
in C++. The escape fires only on keywords; any other trailing underscore is part of
the name.

## Headers name, they don't shape

A header lists every member, but only a subset is serialized, and it shows no
order, prefix, or gating. `ProfilerLiteTelemetry` declares twelve floats of which
nine reach the wire. cereal also writes a nested payload struct **inline**, so a
composed BDS type lands on the wire flat and the DSL models it flat. Never infer
wire shape from a header, and never "complete" a type by copying members out of one.

bedrock-headers' `.cpp` files are **declaration-only** — `BiomeDefinitionData.cpp`
holds the signatures of `write` / `read` and no bodies. A serializer sitting next to
its header is not a wire source; protocol-docs still is.

## Reference widths are byte-aliased

cereal writes variant discriminators as `uvarint32`, and compresses many small enums
to a varint; gophertunnel and CloudburstMC model the same field as `uint8`. For
0..127 both encode to the identical byte, so a community lib showing a byte carries
**no width information** and no golden will catch a wrong choice. Only BDS and protocol-docs
answer width. Field order, presence, and wide fixed-width prefixes remain
trustworthy in those refs.

**A width that narrows between eras is BDS shortening the enum's underlying type,
not two wire shapes.** Model both eras on the narrow one — the values are
identical on the wire — and do not split the type. `SerializedAbilitiesLayer` is
the pattern: six enumerators against a `std::array<…, 6UL>`, so `uint8` and
`uvarint32` emit the same byte forever.

**Unless the enum carries a negative value, and then they must be two types.**
`uvarint32` and a signed byte agree on 0..127 and part company below zero: `-1`
is one byte as `int8` and five as `uvarint32`. `ContainerID::NONE = -1` is the
live case, which is why packet 49 spells `field(type=uvarint32)` and packet 50
takes the bare `int8` — unifying them would corrupt every `NONE`. Before
unifying a narrowed width, grep the enum for a negative enumerator; eleven of
them carry one.

## Enums

**Members are PEP 8 (`UPPER_CASE`) and emitted verbatim** — the compiler applies no
transform, so the DSL spelling *is* the C++ spelling. BDS has no single convention
(screaming snake, CamelCase, mixed), so convert when adding:
`JsonUI_ControlTree_PopulateTTS` → `JSON_UI_CONTROL_TREE_POPULATE_TTS`. This is the
one exception to *Names mirror BDS*; class names still match exactly.

**The reflected name is lowercased, for every enum** — `enum_name(BossBarColor::PINK)`
is `"pink"`. The table doubles as the wire table for a name-coded enum, where BDS's
own string is the folded one, and one spelling per enum is what lets `enum_cast`
fold its input and be case-insensitive with no predicate to pass. The C++ enumerator
stays `UPPER_CASE`.

Name-coded enums (`field(type=str)`) are PEP 8 too, and **the wire is lowercased,
always** — never patch a golden to a mixed-case spelling. `BasicFactory<E>::memberDescriptorFor`
folds the bound name into `MemberDescriptor::mName` at bind time and keeps the
original in `mNameExt`; the write hands out `mName` and the entt lookup id hashes
it, so `TextPacketType::JukeboxPopup`, bound `"jukeboxPopup"`, goes out
`jukeboxpopup` and BDS's own reader resolves nothing else. gophertunnel's
`commandOriginToString` / `commandOriginFromString` is the end-to-end confirmation:
lowercase both ways, no fallback on the read. The compiler applies the fold, so
the DSL records BDS's spelling and never the wire's.

A **separator** is not free: BDS's `DownloadingFinished` has none to map back to,
so `DOWNLOADING_FINISHED` would fold to `downloading_finished` — one byte longer
than BDS's string, and resolving to nothing. Pair the member with BDS's spelling,
the way `enum` itself spells `MONDAY = 1, "Mon"`:

```python
class ResourcePackResponse(Enum, int8):
    DOWNLOADING_FINISHED = 3, "DownloadingFinished"   # on the wire: downloadingfinished
```

**Pair only the members whose spelling BDS does not already give you.**
Folding never removes an underscore, so a snake_case BDS name is reached by
the PEP 8 member outright: `IN_QUAD` folds to `in_quad`, and pairing it says
nothing. `EasingType` was written with all 32 pairs and every one was redundant.
Pairs are earned by a dropped separator (`FacialHair`) or an added prefix
(`persona_skeleton`).

The pair needs a plain **`Enum`** base: `IntEnum` and `StrEnum` coerce a member to
their own type, so a pair is not a value there. Where the base cannot take one, or
the member is also version-gated, `value()` carries the string as its second
positional — `SECOND = value(7, "Second", since=1001)`. Never mangle the member to
match the wire (`DOWNLOADINGFINISHED`); the C++ spelling stays PEP 8.

**Values are int literals or `auto()`** (previous + 1) — use `auto()` where the
number is derived, typically a trailing count sentinel (`COUNT = auto()` for BDS's
`MemoryCategory_count = 92`). Anything else is a compile error.

**The underlying type is a second base**, taken from bedrock-headers:
`enum class MemoryCategory : uint8_t` → `class MemoryCategory(IntEnum, uint8)`.
BDS really does have `enum class NetherWorldType : bool`.

**Spell it even when it is `int`, however redundant that reads.** An enum used as
a field cannot omit it: the compiler has no wire encoding to derive and stops with
"declares no underlying type". Stripping the 38 `(IntEnum, int)` / `(IntEnum, int32)`
bases as noise fails the build outright. Making a bare `IntEnum` default to `int`
would be a one-line change to `_default_enum_wire` and is safe (it only turns a
hard error into a default), but until someone makes it, spell the base.

**A redeclaration cannot carry its own underlying type**, so where BDS narrows one
between eras the DSL has to pick a single spelling. `InputData` is `unsigned int`
at r26_u3 and `int` at r26_u4; it only ever sizes a bitset, so neither reaches the
wire and it stays `uint32` with a comment. If a narrowing ever did reach the wire,
that is the *two types* case above.

That underlying type also gives the field its **default wire encoding**, so
`category: MemoryCategory` needs no `field(type=)`: one byte goes as-is, wider
compresses to `[u]varint32` (`[u]varint64` at eight), signedness following the
underlying. Spell `field(type=)` for everything else — `str` (name-coded),
a fixed primitive (uncompressed), or `endian="big"`. An enum with neither an
underlying base nor `field(type=)` is a compile error; the compiler never guesses.

Width, signedness and compression all follow the underlying, so the derived default
matches the dump and `field(type=)` is noise on a plain enum field. A one-byte enum
reaches the wire as one byte whatever cereal Compression trait the member carries —
`BossEventUpdateType : uint8_t` and `PlayerPermissionLevel : int8_t` both dump their
own width. Spell `field(type=)` only where the encoding is genuinely something else:
`str`, a fixed primitive against a wider underlying, or `endian="big"`.

**Placeholder with stub enumerators, never with the primitive.** A `category: uint8`
throws the type away — the field stops saying what it is and every call site loses
the enum. Declare the enum with its real name and underlying type, name only the
members you have, and leave a `# TODO: enumerator stub`. Filling it in later is
additive and touches no call site.

## A reshaped type is redeclared, not patched

**A reshape is redeclared; `field()` covers a field coming or going.** A
cerealisation is a reshape, and so is any change to a field's *type* -- retyping a
field in place would leave one declaration claiming two shapes. Redeclare the whole
class at the change point instead, and keep `field(since=)` / `field(until=)` for a
field that is simply present over part of the range.

Declare it twice over adjacent ranges, each body holding its era's plain types:

```python
@packet(id=175, until=1001)          @packet(id=175, since=1001)
class SubChunkRequestPacket:         class SubChunkRequestPacket:
    dimension_type: DimensionType        dimension_type: DimensionType
    center_pos: SubChunkPos              sub_chunk_pos_offsets: list[...]
    sub_chunk_pos_offsets: list[...]     center_pos: SubChunkPos
        = field(prefix=uint32)
```

Only this form can express a **reorder**, a **rename**, or a field whose type moved
— each declaration's fields carry its range, so a snapshot narrows to exactly one
shape. `field(since=)` / `field(until=)` adds or drops a field, wherever it sits in
the body; it never restates one under a second type. Redeclarations must tile one
range: same id, each `until` meeting the next `since`, only the last left open.

**An enum is redeclared the same way when it is renumbered.** `value(N, since=)` /
`value(N, until=)` covers a member arriving or going, and a member that *moves* may be
declared twice over disjoint ranges (`SKELETON_HORSE = value(2186010, until=924)` then
`= value(2183962, since=924)`) -- the importer unshadows the repeat. Reach for a
redeclaration only when a wholesale renumbering — `Memory::MemoryCategory` at 2168 dropped
one member, added twenty, and shifted most survivors — declares the enum twice over
adjacent ranges, each body holding its era's numbers. Every declaration shares one
underlying type. `@type(since=, until=)` gates the enum itself as it does a struct,
so outside its range the type is absent and a reference from that era needs the
snapshot namespace (`v1001::SoundDataEvent`).

## A cerealisation is the highest-risk change

protocol-docs only dumps cerealised packets, so a migrated packet appears as a
**new file** — never read that as "the dumper finally noticed it". 979 moved
`SubChunkRequestPacket`'s `center_pos` behind the offsets, swapped the offset count
from fixed `uint32` to `uvarint32`, and reshaped `SubChunkPos` from `varint32` to
fixed `int32`: three wire breaks in one changelog line.

The dump cannot show the pre-cereal shape. Take it from gophertunnel's history
(`git log -p` the packet, read the `Marshal` diff) or CloudburstMC's older
per-version serializer, and gate the delta at the snapshot.

**A pre-cereal switch becomes `when=`.** Where the old `Marshal` branched on a type
field (`switch pk.EventType`), gate each arm on it: `field(when=lambda p: p.x ==
E.A)` for a lone field, `with field(when=...):` for a run. The predicate reads
earlier fields only, carries no presence byte, and leaves an excluded field
default-constructed. cereal typically flattens the switch away, so the new snapshot
is a flat redeclaration with every field unconditional — model both, gated at the
boundary (984's BossEvent: eight switch arms at 975, flat at 1001, `darken_screen`
dropped).

**The cerealised form reads clean.** cereal writes every field flat and
unconditional, so the post-migration declaration is bare `name: Type` lines — no
`when=`, no union, no `field(type=)` beyond a genuine wire divergence (an enum
carrying its bedrock-headers underlying needs none; a small enum's byte falls out
either way). Annotation clutter on a cerealised form is a smell that you are
modelling the pre-cereal shape.

**A shared type's wire form is per call site; the dump gives you one of them.**
protocol-docs describes a type once, from its cereal schema, and that describes the
cerealised packets that embed it. A packet *missing* from that branch writes the same
type through its own hand-written code and may encode it differently — the dump
cannot show the second form and gives no hint it exists. So a type being in the dump
licenses only the packets the dump also lists; it says nothing about a call site that
is not there yet.

`GameRule` is the standing case. `GameRulesChangedPacket` is in the dump from 975 on,
and at 1001 its `write(BinaryStream&)` is confirmed to build a `ReflectionCtx`, call
`cerealizer<GameRulesChangedPacket>::bind` and delegate — no legacy path — so the
dump's fixed `int32` integer case is the wire there at 975, 1001 and 2168 alike. But
StartGame was hand-written until 2168 and put the same `GameRule` on the wire through
`std::function<void(BinaryStream&, const GameRule&)>` lambdas living in
`GameRulesChangedPacketData.h`, with a varint integer. One type, two encodings, one
dump entry. At 2168 StartGame cerealised and `LevelSettings` took a
`GameRulesChangedPacketData` member, collapsing the two onto the cereal form — which
is why both gophertunnel and CloudburstMC carried a second game-rule codec
(`GameRuleLegacy`, `writeGameRuleInStartGame`) and deleted it at exactly that version.

Model the encoding **per embedding type**, not on the shared type. A single
`@type(until=N)` / `@type(since=N)` pair over the shared type forces both call sites
to agree and silently mis-encodes whichever one the dump did not describe.

Those two legacy codecs disagree with each other — Cloudburst writes a zigzag
`varint32`, gophertunnel an unsigned `uvarint32`, which differ for every non-zero
value — so anything modelling StartGame's game rules before 2168 earns a
`# TODO: confirm against BDS` until BDS's hand-written path is read directly.

## An always-true marker is `Literal[True]`, never an optional

cereal prefixes a dynamic member with an always-true member-present byte. That is
a BDS **bug**, not a design, and every one the dump shows is modelled faithfully
as its own `Literal[True]` field sitting exactly where the byte falls, with the
member it precedes left bare:

```python
_true: Literal[True]
transaction: TransactionData
```

**Never fold it into a `T | None`.** The two encode the same bytes while the
member is present, which is why it is easy to reach for and why no golden catches
it, but an optional conflates BDS's spurious byte with genuine member presence.
The marker is expected to go away: when BDS fixes it, a `Literal[True]` field is
removed by gating that one field `until=<version>` and nothing else in the type
moves, whereas a conflated optional has to be reshaped or redeclared. Folding it
also lets the schema encode a `nullopt` BDS never writes.

Grep the dump for `"value": true` when modelling any dynamic member, at every era
— `git grep '"value": true' origin/r26_u4` and the same for `origin/r26_u3`.

## A union spells its discriminator

A `A | B | C` field is prefixed by a `uvarint32` index over the cases in declaration
order. Line the cases up with the wire's numbering rather than reaching for
`field(tag=)`; where BDS numbers from one, lead with `None` so `std::monostate`
takes index 0:

```python
# BDS GameRule::Type: INVALID=0, BOOL=1, INT=2, FLOAT=3.
value: None | bool | uvarint32 | float
```

## A fixed length is a size, not a count

`array[T, N]` is the member BDS declares `std::array<T, N>`: exactly N elements,
nothing on the wire marking the count, and the size sitting in the type where both
sides can read it. `list[T]` is the length-prefixed sequence, and `field(count=)`
covers a length BDS wrote somewhere else — an expression over earlier fields, never
a constant. A constant `count=` and an `array[T, N]` put the same bytes out, but the
count spells `std::vector` in C++ and lets a wrong-sized one reach the wire, where
an array cannot be the wrong size. `SubChunkPacket`'s height maps are the pattern:
`array[array[int8, 16], 16]`, which is `SubChunkPacketPayload::HeightMapArray`
verbatim at every era bedrock-headers covers.

BDS's alias for it is nested (`SubChunkPacketPayload::HeightMapArray`) and the DSL
has only module-scope `type X = Y`, so the array is spelled inline rather than
hoisted out of its owner.

## Version gating

`since=` / `until=` are raw protocol version numbers, but must land on a modelled
snapshot, never an arbitrary changelog number. Gate a change at the next snapshot at
or after it: a field the changelog dates to 977 gates `since=1001`. Only 898, 924, 944,
975, 1001, 2168 and 2192 are materialized, so an off-snapshot boundary buys nothing.

**Diff the type closure across protocol-docs branches before modelling a packet.**
Walk the packet's transitive types on the old and new branch and diff the two dumps:
that settles in one step whether an update touched this packet at all. `r26_u4` is
network version 2168, but packet 122's whole closure is byte-identical to `r26_u3`,
so it needed no gating and no new snapshot. A new branch is not evidence of change.

## DSL comments record blockers only

A `#` in a protocol file is earned by something unresolved: a `TODO`, a
`confirm against BDS`, an open disagreement. Delete everything else — why a
modelling decision went the way it did, how gophertunnel encodes a field, which BDS
namespace a type came from, version history that `since` already states. That
reasoning belongs in the commit message, attached to the change.

## Tests

Name per-packet files `test_{packet_id:03}_{name}.cpp`.

**The suite needs libc++.** The default configuration stops earlier on an
unrelated `std::variant` default-construction in the generated `item_stack.h`, so
a green-looking `cmake --build build` may never have reached a test at all:

```shell
cmake -B build-libcxx -G Ninja -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_COMPILER=clang++ \
      -DCMAKE_CXX_FLAGS=-stdlib=libc++ -DCMAKE_EXE_LINKER_FLAGS=-stdlib=libc++
ctest --test-dir build-libcxx
```

A schema change is not done until those tests run. endweave consumes this schema
directly **on its `develop` branch** — `main` is the pure-Python line and names no
generated header — so rebuild that branch too: a rename here is a compile error there.
The coupling is include lines only; every type it names is namespace-scope
(`bp::LevelSoundEvent_<2168>`), and those spellings do not change.

**Generate goldens by running gophertunnel; never derive them by hand.** Write a
small Go program that marshals the packet through `protocol.NewWriter`, and paste
the bytes under a `// generated by gophertunnel:` comment carrying the packet
literal that produced them. Hand-derivation silently invents bytes — an empty
`CompoundTag` is three bytes (named root, empty name), not four, and only an
executed golden catches that.

gophertunnel marshals its *current* shape only, so an older version's golden cannot
be generated the same way. Either check gophertunnel out at the matching commit and
re-run, or assert the old form structurally (size delta plus round-trip). Never fake
one by deleting bytes from the newer literal.

**A golden is bare bytes.** The comment above it names the source and the packet
literal, and that is the whole annotation: never label the bytes field by field.
Labelling them is hand-derivation smuggled back in. The labels rot the moment a field
moves, and they invite patching the bytes to match the label. Say what the packet was,
not what each byte means.

**A patch is a TODO, not a fix.** Casing is the one settled patch: a name-coded enum
reaches the wire in whatever case BDS spells, and BDS lowercases before the lookup, so
the golden takes the DSL's spelling and its comment says so. Any other disagreement
means one side is wrong about the wire, and the golden cannot say which. Patch it so
the suite still says what the schema encodes, mark the bytes
`// TODO: patched, confirm against BDS`, and open the comment above with
`// TODO: confirm against BDS` naming what the reference wrote, what the dump says, and
which side has to give -- the same marker a doubted wire type earns in the DSL. None are
open today.

The dump is not the tiebreaker by default; the header is, and a third-party codec breaks
a tie the header cannot. `BoolAttributeData`'s operation closed toward the dump --
gophertunnel wrote an optional `int32` where the dump has a name-coded string, and
`BoolEnvironmentAttribute::mOperation` is a cereal-bound enum, which Cloudburst
ProtocolLib and Nukkit-MOT both write name-coded. `InventorySource`'s container id closed
toward gophertunnel's plain `int8`: `ContainerID` is a `signed char`, and a one-byte member
reaches the wire as one byte whatever Compression trait it carries. The dump reads `int8`
there too, so neither disagreement stands today.

## The compiler mirrors protoc

`src/bedrock_protocol/` follows protoc's architecture, names, and call shapes —
`Importer` / `SourceTree` / `Parser`, `DescriptorPool.build_file`, `FileGenerator` /
`MessageGenerator` / `EnumGenerator` / `FieldGeneratorMap`, `CodeGenerator` +
`GeneratorContext`. When adding to it, find protoc's equivalent first and follow it;
when diverging, say so where it bites (the parser resolves type references eagerly
where protoc defers them to `DescriptorBuilder`, which is why `SymbolTable` exists).

Refactors must be **output-identical**: regenerate the whole schema before and after
and diff. Behaviour changes ride in their own commit.

**`prototype` is an unrelated history — a reference, never a base.** It has its own root
commit, so nothing merges or rebases between the two. It carries a much fuller
compiler (`MappingType`, `TupleType`, `CondType`, `BitsetType`) and a wider schema,
which makes it the first place to read when adding a feature — but port the *idea*
protoc-faithfully into this architecture rather than lifting the code, and re-verify
any wire detail against the sources of truth above.

The rewrite **deliberately dropped** every path the MVP did not use, and a missing
feature is therefore a deferral, not an oversight: when a packet first needs one,
re-add it as its own reviewable change, with a test that exercises it. `@builtin`,
`dict[K, V]`, `when=`, `endian=`, nested types, `bitset` (`input.py`'s
`bitset[InputData.INPUT_NUM]`), `count=` (`network.py`'s counted blob id lists) and
`array[T, N]` (`chunk.py`'s height maps) have all come back that way. Still gone:
`tuple` and deprecation.

## A module is a BDS domain, and says so in its docstring

Every schema module is named after a folder in the BDS game tree and opens with a
docstring naming what it holds **and what it deliberately excludes**. A placement
argument is settled by grepping those docstrings, not by re-deriving the taxonomy — the
whole index is `head -qn 4 protocol/*.py`, and the exclusions are `grep -n "^Not " protocol/*.py`.
A commit that adds a packet to a module whose docstring excludes it must change the
docstring in the same commit.

To place a new declaration: **find its BDS header and use the module named after that
header's domain folder.** A reusable domain type goes to its domain's module however many
packets reach it (`ItemStackDescriptor` → `item`, `PlayerPermissionLevel` → `command`); a
wire-only type under `network/packet/types/<path>/` goes to the module mirroring `<path>`
(`SerializedAbilitiesData` → `ability`); a payload BDS declares inside the packet's own
header is nested in the `@packet` class. A BDS subdirectory merges into its parent's
module unless it carries enough declarations to stand alone. Where the folder cannot
decide — it appears at two depths, holds >100 headers (`world/level`, `world/item`,
`world/actor`) or fewer than 3 (`editor/`) — fall back in order to the module already
declaring the most types the packet references, then the packet family, then leaving it
where it is. **Size is never a reason to create a module**: a lookup table lives with its
subject, which is why `LevelSoundEvent`'s ~578 members stay in `sound.py`.

Three constraints outrank the taxonomy, and none of them is diagnosed:

- **A name-coded enum's `Serializer` is emitted only by a module that name-codes it**
  (`cpp/file.py`'s `_string_coded_enums` reads the file's own structs). Declaring `E` in
  one module and writing `e: E = field(type=str)` only in another links against a
  `Serializer<E>` nobody generated. Never separate the two — it is why `EasingType` sits
  in `eas.py` and `CommandPermissionLevel` moved in `3f7ac67`.
- **The import graph must stay acyclic.** `descriptor_pool.py` *skips* an import already
  on the build stack instead of reporting it, then silently drops that side's versioned
  set and snapshot points — and which side loses depends on which file `bpc` is emitting.
- **An unresolvable field type is silent**: the parser returns `None` and the backend
  emits a one-line `struct Name {};`. `F821` is per-file-ignored here by design, so
  `grep -c "struct [A-Za-z_0-9]* {};"` over the generated headers is the detector, and it
  must read 0.

## The include tree is `bedrock/protocol/`

`<bedrock/protocol.hpp>` is the umbrella and everything else sits one level down, so
the install tree and the build tree name a header the same way:

- `bedrock/protocol/<family>.h` — emitted, one per schema module, each paired with a
  `.cpp` compiled into the archive.
- `bedrock/protocol/<name>.hpp` — hand-written and header-only: streams, `Serializer`,
  NBT, UUID, `packet_of`, enum reflection, and the configured `version.hpp`.
- `bedrock/protocol/detail/<name>.hpp` — plumbing the emitted code leans on and a
  consumer never includes directly.

The extension is the rule, not decoration: `.h` has a `.cpp` next to it, `.hpp` does
not. That is also what lets `nbt.py`'s emitted `nbt.h` sit beside the hand-written
`nbt.hpp` without a collision.

`INCLUDE_PREFIX` in `compiler/cpp/helpers.py` is the single spelling of that
directory; every emitted `#include` is built from it, and CMake writes the generated
tree into a matching path. Change it in one place or not at all.

**An enumerator that a platform header also defines as a macro is bracketed, not
compiled around.** `MACRO_ENUMERATORS` lists the names (`ERROR`, `TRUE`, `VOID`, …);
a file spelling one wraps its whole namespace in `push_macro`/`#undef`/`pop_macro`,
which keeps the fix inside the header instead of a `/U` flag every consumer inherits.
Renaming away from the macro is better still where BDS's spelling survives as a wire
pair — `WINDOWS = value(8, "Win32")` still goes out as `win32`.

## A release ships the emitted C++

CI packages `generated/` next to `include/` and the top-level `CMakeLists.txt` builds
from it when it finds one, so nothing downstream needs uv or `bpc`. Anything the
build needs at *consume* time therefore has to be inside that archive: a new
`configure_file` template must be stamped during generation, never resolved lazily,
or a source build will look for a `.in` that was never shipped.
