# CLAUDE.md

## Sources of truth

Each aspect of a type has exactly one authority. Walk them per aspect, not as a
general ranking, and confirm a change against a second source before acting:

- **Field name, field type** — bedrock-headers (`~/bedrock-headers`), the
  BDS-extracted C++ headers. Authoritative: a name taken from here needs no
  TODO. Carry it into the project's conventions (`PascalCase` types,
  `snake_case` fields) without paraphrasing or shortening — `mTotalHighCostNS`
  becomes `total_high_cost_ns`.
- **Wire type, wire shape** — [EndstoneMC/protocol-docs](https://github.com/EndstoneMC/protocol-docs),
  the dumped schema, on the branch for the release (`r26_u3`). It records each
  field's encoding, prefix and order.
- **Golden bytes** — [gophertunnel](https://github.com/sandertv/gophertunnel)
  (see Tests below).
- **Cross validation** — [CloudburstMC/Nukkit](https://github.com/CloudburstMC/Nukkit).
- **Second validation only** — [CloudburstMC/Protocol](https://github.com/CloudburstMC/Protocol).

Never take a name from gophertunnel or CloudburstMC. Those references date and
shape symbols, they do not name them. Mojang/bedrock-protocol-docs is a last
resort for a symbol none of the above carries, and always earns a
`# TODO: confirm against BDS`.

## A community ref is only as good as its consumer's coverage

The ordering above is about testing depth, not taste. Each community reference is
only exercised as far as its downstream consumer goes, so a codec nobody runs can
be wrong indefinitely with nothing to surface it.

- **CloudburstMC/Protocol** is only trivially tested: Nukkit does not use it, and
  its real exercise is Geyser, which touches a subset of packets. A codec error in
  a packet Geyser never sends or receives simply never appears. Second validation
  only, never a tiebreaker.
- **gophertunnel** is slightly better — Dragonfly runs it in production — but has
  the same shape of problem: a packet Dragonfly does not exercise carries an
  effectively untested codec.

So agreement from a ref is strong evidence only for packets its consumer actually
exercises, and silence is never evidence. Rate a packet's coverage before leaning
on a ref for it, rather than assuming either way — check whether a codec and a test
actually exist. For `ServerboundDiagnosticsPacket`, CloudburstMC/Nukkit carries only
the id constant (silence, no codec), while Nukkit-MOT both models the packet and
covers it in its regression tests, which made it the strongest cross-check here
despite ranking below gophertunnel in general.

gophertunnel's `MemoryCategory` list is the standing proof that coverage gaps bite:
it carries a `VR` entry BDS 1001 does not, so every constant after `Textures` is off
by one and nothing caught it. When a ref is uncorroborated, take only the generic
encoding conventions from it (`Float32` = fixed LE, `Slice` = varuint32 count,
`String` = varuint32 + bytes), which every packet shares, and confirm field order,
presence and type against protocol-docs.

Nukkit-MOT is also the cheapest dating source when it covers a packet: it annotates
members with `@since vNNN` directly (`whiskerScopes @since v1001`). CloudburstMC's
per-version serializers date the same way structurally — a `Serializer_v1001`
extending `Serializer_v975` and appending one field dates that field to 1001.

## Names mirror BDS

Class names and nesting match BDS exactly, so the generated C++ reads like the
BDS headers. Never fold an enclosing namespace into the class name:
`Bedrock::Profile::Whisker::Diagnostics::ScopeDataSummary` is `ScopeDataSummary`,
not `WhiskerScopeDataSummary`. A BDS `Outer::Inner` stays a nested `class Inner`
inside `class Outer`, never a flattened `OuterInner`. A `FooPacketPayload` maps
onto the `@packet FooPacket` itself, dropping the `Payload` suffix.

Search bedrock-headers case-insensitively. BDS spells these `Serverbound` /
`Clientbound` with a lowercase `b`, so a `ServerBound` grep misses the header
outright and wrongly concludes BDS does not carry the type.

## Enum members are PEP 8, and emitted verbatim

Enum members follow PEP 8 in the DSL — `UPPER_CASE` — and the compiler applies no
transform, so the generated C++ inherits that one consistent style rather than
BDS's per-enum mix (`BoolAttributeOperation` is screaming snake, `SoundDataEvent`
CamelCase, `MemoryCategory` mixed case and underscores). Convert a BDS name into
PEP 8 when adding it: `Invalid_SizeUnknown` becomes `INVALID_SIZE_UNKNOWN`,
`JsonUI_ControlTree_PopulateTTS` becomes `JSON_UI_CONTROL_TREE_POPULATE_TTS`. This
is the enum member exception to Names mirror BDS above — class names still match
BDS exactly; only members are restyled.

**Name-coded enums are PEP 8 too.** When a field is `field(type=str)` the member
name is also the string on the wire, but BDS lowercases that string before the enum
lookup, so the casing is not load-bearing — `STOP` and `Stop` both resolve. Spell
the member PEP 8 and let the wire carry it. The generated reader lowercases both its
keys and the incoming string, so a peer's own spelling still reads back; `test_348`
pins that with a case-insensitive read of gophertunnel's `"Stop"` bytes.

Where this makes our bytes differ from a reference, patch the golden and say so in
its comment — `test_348` writes `"STOP"` where gophertunnel spells the constant
`"Stop"`, and `test_345` writes BDS-verbatim `"OVERRIDE"` where CloudburstMC has an
unvalidated lowercase. Casing is the one name-code aspect a reference cannot settle;
the member's identity still has to be the BDS one.

`ProtocolVersion` (`protocol/version.py`) is compiler-owned rather than BDS and
spells its members `V975` / `V1001`.

## An enum's underlying type is a second base

Spell an enum's C++ underlying type as a second base, taken from bedrock-headers:
BDS `enum class MemoryCategory : uint8_t` becomes
`class MemoryCategory(IntEnum, uint8)` and generates
`enum class MemoryCategory : std::uint8_t`. Both `IntEnum` and the dotted
`enum.IntEnum` spelling are accepted. Omitting the base generates `: int`, which
is the C++ default and what a BDS enum declaring no underlying type resolves to —
so omit it only after confirming BDS declares none, never by default.

The underlying type also gives an enum-typed field its **default wire encoding**, so
`category: MemoryCategory` needs no `field(type=...)`. That default is ours, not
cereal's. cereal defaults a scoped enum to a name-coded **string**, writing a value
only when `EnumAsValue` is set — protocol-dumper's `serialization_type`
(`src/visitor.cpp`) takes the `string` branch whenever the trait is absent. The DSL
inverts that and defaults to underlying type + `EnumAsValue` + `Compression`, purely
because that is the commoner shape: the frequent case costs nothing to write, and
cereal's real default becomes the explicit `field(type=str)`. The derivation:

| underlying | default wire | |
| --- | --- | --- |
| `int8` / `uint8` | `int8` / `uint8` | a single byte has nothing to compress, so it goes as-is |
| `int16` / `int32` / `int` / `uint16` / `uint32` | `varint32` / `uvarint32` | |
| `int64` / `uint64` | `varint64` / `uvarint64` | |

Signedness follows the underlying type. Everything else is spelled out:

- **Name-coded** — `field(type=str)`. cereal's own default, and the one case no
  underlying type can reveal, since it turns on the *absence* of `EnumAsValue`.
- **Uncompressed** — `field(type=int64)`, where BDS writes the fixed width instead.
- **Big-endian** — `field(type=int64, endian="big")`.

An enum with no underlying base and no `field(type=)` is a compile error, not a
guess — the compiler never invents a width. Beware that a wrong choice here is
easily byte-aliased: `uint8` and `uvarint32` agree for 0..127, so a golden will not
catch it. Take the encoding from protocol-docs, which records it per field.

## Enum members are int literals or `auto()`

Spell a member's wire number as a plain int literal, or `auto()` (previous + 1) where
the number is derived rather than chosen — a trailing count sentinel is the usual
case: BDS's `MemoryCategory_count = 92` is `COUNT = auto()`, which stays correct as
members are added. Anything else is a compile error; the compiler never skips a
member it cannot read.

## Placeholder an enum with stub enumerators, never with its primitive

When BDS gives a field an enum you are not ready to transcribe in full, never fall
back to the raw primitive (`category: uint8`). That throws away the type: the field
stops saying what it is, every call site loses the enum, and nothing marks the gap.

Declare the enum with its real name and real underlying type, name only the members
you have, and type the field as the enum with its own wire primitive:

```python
# TODO: enumerator stub -- BDS declares 92 members (Unknown=0 .. MemoryCategory_count=92).
class MemoryCategory(IntEnum, uint8):
    UNKNOWN = 0


class MemoryCategoryCounter:
    category: MemoryCategory = field(type=uint8)
```

The generated C++ then carries `enum class MemoryCategory : std::uint8_t` and a
`MemoryCategory category` field from the start, so filling the members in later is
additive and no call site changes. A `# TODO: enumerator stub` records what is
missing. The enum's underlying type and the field's `field(type=)` stay independent
— fill the stub in without touching the wire.

## Headers name, they don't shape

A BDS header lists every member of a class, but only a subset is serialized, and
a header shows no order, prefix or gating. `ProfilerLiteTelemetry` declares
twelve floats of which nine reach the wire. cereal also writes a nested payload
struct inline, so a composed BDS type — `ServerboundDiagnosticsPacketPayload`
holding `ProfilerLiteTelemetry` + `EntitySystemDiagnosticSummary` + the whisker
vector — lands on the wire flat, and the DSL models it flat. Take the wire shape
from protocol-docs and gophertunnel; never infer it from a header, and never
"complete" a type by copying members out of one.

## Reference width is byte-aliased

cereal writes a variant discriminator and most small scoped enums as
`uvarint32`; gophertunnel and CloudburstMC routinely model the same field as
`uint8`. For 0..127 the two encode to the identical byte, so a community lib
showing a byte carries no width information and is never the justification for a
width. Only BDS answers width. Field order, presence and wide fixed-width
prefixes are still trustworthy in those refs.

An enum that cannot be pinned down — `Memory::MemoryCategory`, 90+ entries that
shift across versions — is modelled as its underlying primitive with a
`# TODO: confirm against BDS`, not silently retyped.

## Version gating

`since=` / `until=` must align to a declared `ProtocolVersion` snapshot
(`protocol/version.py`), never a raw changelog number. Gate a change at the
next snapshot at or after it: a packet or field the changelog dates to 977
gates `since=1001`, not `since=977`. Only 975 and 1001 are materialized, so an
off-snapshot boundary buys nothing — keep every `requires (V >= N)` on a real
snapshot.

## Tests

Name per-packet test files `test_{packet_id:03}_{name}.cpp` — the packet's
wire id zero-padded to three digits, then a descriptive name (e.g.
`test_348_update_sound_data.cpp`).

Golden bytes come from [gophertunnel](https://github.com/sandertv/gophertunnel)
(`minecraft/protocol/packet`), not hand-derivation: read the packet's `Marshal`
and encode each field as its `protocol.IO` call dictates (`Uint64` = fixed LE,
`String` = varuint32 length + bytes, etc.). Cite the source packet/method in a
comment above the golden. Where gophertunnel and BDS disagree, verify against
the BDS binary and note the deviation (as the attribute-layer name-code casing
does).
