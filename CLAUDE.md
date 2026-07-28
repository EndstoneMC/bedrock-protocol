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
always earns a `# TODO: confirm against BDS`. **Do not trust `main`**: it has real
bugs (its StartGame `game_type` is `uvarint32` where the wire is `varint32`).

**A ref is only as good as its consumer's coverage.** CloudburstMC/Protocol is
exercised by Geyser, gophertunnel by Dragonfly — a packet neither runs has an
effectively untested codec. Agreement is evidence only where the consumer actually
exercises the packet; silence is never evidence. Check whether a codec and a test
exist before leaning on a ref. gophertunnel's `MemoryCategory` list is the standing
proof: it carries a `VR` entry BDS does not, so every constant after `Textures` is
off by one and nothing caught it.

**Dating shortcuts:** Nukkit-MOT annotates members `@since vNNN`. A CloudburstMC
`Serializer_v1001` that extends `Serializer_v975` and appends a field dates that
field to 1001.

**A protocol-docs branch is a network version**, not a release ordering — check its
README (`r26_u3` = 1001, `r26_u4` = **2168**). A packet missing from the dump is not
cerealised at that version, so the dump cannot describe it at all.

## Names mirror BDS

Class names and nesting match BDS exactly, so the generated C++ reads like the BDS
headers. Never fold an enclosing namespace into a class name:
`Bedrock::Profile::Whisker::Diagnostics::ScopeDataSummary` is `ScopeDataSummary`.
A BDS `Outer::Inner` stays nested, never flattened to `OuterInner`. A
`FooPacketPayload` maps onto `@packet FooPacket`, dropping the `Payload` suffix.

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

## Enums

**Members are PEP 8 (`UPPER_CASE`) and emitted verbatim** — the compiler applies no
transform, so the DSL spelling *is* the C++ spelling. BDS has no single convention
(screaming snake, CamelCase, mixed), so convert when adding:
`JsonUI_ControlTree_PopulateTTS` → `JSON_UI_CONTROL_TREE_POPULATE_TTS`. This is the
one exception to *Names mirror BDS*; class names still match exactly.

Name-coded enums (`field(type=str)`) are PEP 8 too: BDS lowercases before lookup, so
casing is not load-bearing. Patch the golden and say so in its comment.

**Values are int literals or `auto()`** (previous + 1) — use `auto()` where the
number is derived, typically a trailing count sentinel (`COUNT = auto()` for BDS's
`MemoryCategory_count = 92`). Anything else is a compile error.

**The underlying type is a second base**, taken from bedrock-headers:
`enum class MemoryCategory : uint8_t` → `class MemoryCategory(IntEnum, uint8)`.
Omitting it generates `: int` — the C++ default — so omit only after confirming BDS
declares none. BDS really does have `enum class NetherWorldType : bool`.

That underlying type also gives the field its **default wire encoding**, so
`category: MemoryCategory` needs no `field(type=)`: one byte goes as-is, wider
compresses to `[u]varint32` (`[u]varint64` at eight), signedness following the
underlying. Spell `field(type=)` for everything else — `str` (name-coded),
a fixed primitive (uncompressed), or `endian="big"`. An enum with neither an
underlying base nor `field(type=)` is a compile error; the compiler never guesses.

Width and signedness do follow the underlying, so the derived default matches the
wire. **Compression does not** — it is a per-field cereal trait, so two one-byte
enums disagree: `BossEventUpdateType : uint8_t` dumps `uvarint32` where
`PlayerPermissionLevel : int8_t` dumps `int8`. Spell `field(type=)` only where the
dump and the derived default **diverge on a real value** — drop it where the enum's
range keeps them byte-equal, since the annotation then only adds noise.

> **A dump taken before 2026-07-28 stamped every enum field unsigned.**
> protocol-dumper read the sign from entt's `is_signed`, which is
> `std::is_signed_v<Type>` and therefore false for every enum, so `GameType : int`
> dumped `uvarint32` where the wire is `varint32` (fixed in protocol-dumper
> `11a6c46`; every protocol-docs branch regenerated). Treat a `uvarint32` on an enum
> field in an older dump — or a schema comment citing one — as unverified.

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
range: same id, each `until` meeting the next `since`, only the last left open. An
enum cannot be redeclared — gate its members.

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

## A union spells its discriminator

A `A | B | C` field is prefixed by a `uvarint32` index over the cases in declaration
order. Line the cases up with the wire's numbering rather than reaching for
`field(tag=)`; where BDS numbers from one, lead with `None` so `std::monostate`
takes index 0:

```python
# BDS GameRule::Type: INVALID=0, BOOL=1, INT=2, FLOAT=3.
value: None | bool | uvarint32 | float
```

## Version gating

`since=` / `until=` are raw protocol version numbers, but must land on a modelled
snapshot, never an arbitrary changelog number. Gate a change at the next snapshot at
or after it: a field the changelog dates to 977 gates `since=1001`. Only 975 and 1001
are materialized, so an off-snapshot boundary buys nothing.

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
which side has to give -- the same marker a doubted wire type earns in the DSL. One is
open today: gophertunnel writes `BoolAttributeData`'s operation as an optional `int32`
where the r26_u3 dump has a name-coded string. `InventoryAction`'s window id is the
next to check, `int8` in gophertunnel against `varint32` in the dump.

## The compiler mirrors protoc

`src/bedrock_protocol/` follows protoc's architecture, names, and call shapes —
`Importer` / `SourceTree` / `Parser`, `DescriptorPool.build_file`, `FileGenerator` /
`MessageGenerator` / `EnumGenerator` / `FieldGeneratorMap`, `CodeGenerator` +
`GeneratorContext`. When adding to it, find protoc's equivalent first and follow it;
when diverging, say so where it bites (the parser resolves type references eagerly
where protoc defers them to `DescriptorBuilder`, which is why `SymbolTable` exists).

Refactors must be **output-identical**: regenerate the whole schema before and after
and diff. Behaviour changes ride in their own commit.

**`main` is an unrelated history — a reference, never a base.** It has its own root
commit, so nothing merges or rebases between the two. It carries a much fuller
compiler (`MappingType`, `TupleType`, `CondType`, `BitsetType`) and a wider schema,
which makes it the first place to read when adding a feature — but port the *idea*
protoc-faithfully into this architecture rather than lifting the code, and re-verify
any wire detail against the sources of truth above.

The rewrite **deliberately dropped** every path the MVP did not use — `bitset`,
`count=`, `tuple`, `tag=IntEnum`, deprecation. A missing
feature is therefore a deferral, not an oversight: when a packet first needs one,
re-add it as its own reviewable change (as `@builtin`, `dict[K, V]`, `when=`,
`endian=` and nested types were), with a test that exercises it.
