# Protocol modeling: naming, docstrings, DSL conventions, version-gating

Which file a type belongs in, how to name symbols, where docstrings come from, how to
spell the DSL, how to date each wire change against the reference implementations, and
when to stop and raise instead of editing.

**Enforced by review.**

## Which file a type belongs in

Types are grouped by BDS subsystem into `protocol/<group>.py` files (`actor.py`,
`camera.py`, `inventory.py`, `command.py`, `biome.py`, and so on). To decide where a
new type goes, use these hints in order:

1. **Its path in bedrock-headers.** The subsystem directory the type sits under in
   the BDS headers is the strongest signal -- a type whose header lives under an
   actor / entity path belongs in `actor.py`, one under a camera path in `camera.py`.
2. **Its own name.** When the header path is unavailable or ambiguous, the type name
   usually names its group: a `Camera*` type goes in `camera.py`, a `Biome*` type in
   `biome.py`, an `Attribute*` type in `attributes.py`.

Keep a packet and the component types only it references in the same file. A type
shared across groups stays in its owning subsystem's file (or `common.py` for truly
cross-cutting primitives) and is imported where needed, the way `protocol/common.py`
and the existing cross-module imports already work.

## Names mirror BDS

The generated headers should read like the BDS binary's own headers wherever we can
verify them: class names, type definitions, nested-structure names, and member names
all come from BDS. Resolve every name through this hierarchy, in order, and stop at
the first source that has it:

1. **bedrock-headers** -- the BDS-extracted C++ headers. The authoritative source. A
   name lifted from here needs no TODO: it is the BDS name by construction. Carry it
   into the project's conventions (`PascalCase` for types, `snake_case` for fields)
   without paraphrasing or shortening.
2. **EndstoneMC/protocol-docs** -- fall back here only when bedrock-headers does not
   cover the symbol. Leave a `# TODO: confirm against BDS` next to the name.
3. **Mojang/bedrock-protocol-docs `.dot` files** -- last resort, when neither of the
   above has the symbol. Always leave a `# TODO: confirm against BDS`. The DOT files
   are upstream naming but not BDS-verified.

Never lift a name from gophertunnel or CloudburstMC. Those references date and shape
symbols, they do not name them. If no source names a symbol, raise it rather than
inventing or paraphrasing one (see Stop and raise below).

**Strip Mojang-internal marker prefixes.** A few BDS names carry markers like
`INTERNAL_` (server-internal disconnect reasons such as
`INTERNAL_UserLeaveGameAttempted`, `INTERNAL_NoFailOccurred`,
`INTERNAL_RequestServerShutdown`) or `TESTONLY_` (test-only entries such as
`TESTONLY_CantConnect`). These mean nothing to the plugin developers who are the
audience here. Drop the prefix in the DSL (`USER_LEAVE_GAME_ATTEMPTED`,
`CANT_CONNECT`, `NO_FAIL_OCCURRED`, `REQUEST_SERVER_SHUTDOWN`). The wire value is
unchanged, only the name is cleaned up. This is the one allowed paraphrase of a
bedrock-headers name -- no `# TODO: confirm against BDS` needed, since the value is
still BDS-anchored. Similarly, a `_Deprecated` suffix or `DEPRECATED_` prefix is
metadata: drop it from the name and model the deprecation through the DSL's
`value(deprecated=...)` / `field(deprecated=...)` instead.

**Names only -- not wire shape.** This rule governs what to call a symbol, nothing
else. The DSL declares wire fields, not in-memory members: BDS headers show every
member of a class, but only a subset is serialized, and the on-wire shape (which
fields, in what order, with what prefix, type, and gating) is invisible from a header
alone. Learn the wire shape from the protocol references instead (see Sources of
truth below). Do not infer wire fields from bedrock-headers. In particular, a type
whose body is empty in the schema (e.g. `class ShapedRecipe: pass`) should not be
"completed" by copying members out of the BDS header -- if the wire references show
no fields, the body stays empty.

## Docstrings come from Mojang/bedrock-protocol-docs

The docstring of a `@packet` or `@type` is the Description that
`Mojang/bedrock-protocol-docs` gives for it -- the single source of truth for
docstring prose.

- A packet with a text page under `docs/` carries its Description in
  `<div class="description">` blocks. There may be more than one, and a leading short
  name like `Interact` or `Animate Actor` is a title, not part of the description.
- A packet that appears only as a tree under `html/` -- an embedded SVG with no prose
  -- has no Description.
- Carry the Description across faithfully: decode HTML entities, fix obvious
  rendering typos, and adjust only for the ASCII / no-semicolon-splice rule (see
  `style.md`).
- Write each docstring as a single line. Hand-wrap only the ones `ruff check` flags
  as over-length (E501), since `ruff format` does not reflow docstring prose.
- Do not invent prose, paraphrase a description from gophertunnel or CloudburstMC, or
  restate version history that `since` / `until` already encode. If
  `Mojang/bedrock-protocol-docs` gives no Description, leave the type undocumented
  rather than writing one.

## DSL spelling

**Single-field gates use inline `field(when=...)`, not a `with` block.** When only
one field is guarded by a predicate, write it inline as
`name: T = field(when=lambda p: ...)`. Reserve `with field(when=...):` for groups of
two or more fields that share the same gate, or for the optional / union case the
inline form does not support (see the `when` docstring in `protocol/__init__.py`). A
solo field inside a `with` block is just noise.

**Enum member values: `value(N, ...)` for explicit, `auto()` for the rest.** Three
forms, picked by what the member needs:

- A bare integer literal (`HARD = 3`) when the wire number is itself meaningful and
  worth reading: the first member of a run that anchors the numbering (often the `0`
  baseline), or a wire-deliberate value (e.g. `UNDEFINED = -1`).
- `value(N, since=, until=, deprecated=)` when the member needs version gating or
  deprecation marking. The positional `N` is mandatory here: a member present only in
  a version window has to pin its wire number explicitly, since auto-numbering would
  shift if a sibling were added earlier in the run.
- `auto()` (from `enum.auto`) for everything else, including count or bitset-width
  sentinels like `COUNT = auto()` at the end of an enum. Auto-number is
  `previous_member + 1`, mirroring gophertunnel's `iota` blocks. Do not spell an
  auto-numbered member as `value()` -- prefer the shorter, Python-idiomatic `auto()`
  unless you also need a version kwarg.

**Discriminator and small-enum width default to `uvarint32`.** A bare `A | B` union
already encodes this. Never write `tag=uint8`. A community library showing a single
byte is not evidence of a one-byte field -- see Reference width is byte-aliased below.

## How to version-gate

Use the protocol (network) version number. Gate the type itself at the version it
first appears -- `@packet(since=N)` for a packet, `@type(since=N)` for an enum or
non-packet struct -- so the generated type is absent from earlier snapshots. Fields
and members present from that introduction need no `since` of their own. Only later
additions take `field(since=)` / `value(since=)`. Removals take `until=`. A reshaped
field is redeclared with adjacent ranges. A type or field that no reference models is
left ungated.

EndstoneMC/protocol-docs describes only the latest schema, so it never reveals when a
field appeared or was removed. Date every change against the references below.

## Redeclaring a class versus patching a field

When a type's wire shape changes across versions, prefer **redeclaring the whole class
or `@packet`** over gating each field inline. Declare the type twice with adjacent
`until=` / `since=` ranges (on `@type` or `@packet`), each copy holding the plain field
types for its era. Two clean bodies read as a before / after, whereas the inline
`field(type=OldT, until=N)` form is denser and, repeated across fields or sibling
types, turns into noise fast. F811 (redefinition) is disabled in the ruff config, so a
redeclaration needs no `# noqa`.

`BookEditPacket` and its `BookEditAction` action structs are the model. `book_slot`
goes `uint8 -> varint32` at 924, so the packet is declared twice -- `@packet(id=97,
until=924)` then `@packet(id=97, since=924)`. Each action struct whose index field
changes width is likewise declared twice (`@type(until=924)` then `@type(since=924)`),
not given a per-field `field(type=...)` gate. Also redeclare when two or more fields of
a type bump at the same version.

Reach for field-level `field(since=/until=)` only for a single field that changes
inside an otherwise-stable struct large enough that a second full copy would duplicate
far more than it clarifies -- adding or removing one trailing field, for instance. A
lone type change there is `name: NewT = field(type=OldT, until=N)` then
`name: NewT = field(since=N)`. The moment that patch repeats across fields or sibling
types, switch back to redeclaring the class.

## Sources of truth

Walk these in order and confirm each change against a second before acting:

- **EndstoneMC/protocol-docs** -- the dumped schema. The most accurate picture of the
  current layout. Diff branches:
  `git diff <old-branch>..<new-branch> -- serialized/`.
- **CloudburstMC/Protocol** -- per-protocol-version serializers
  (`bedrock-codec/.../bedrock/codec/vNNN/serializer/<Packet>Serializer_vNNN.java`).
  Good for dating: a field first appearing in serializer `vNNN` is `since=NNN`, and
  the oldest `vNNN` that defines the serializer at all is the packet's own `since`
  (subject to the v291 floor below). Not used in production, so its newest-version
  codecs can lag or drift.
- **Sandertv/gophertunnel** -- `minecraft/protocol/packet/<name>.go`. Production-
  exercised, so safer, but the slowest to land new bumps. Walk
  `git log -p -- <file>` and read each `Marshal` body diff: `git log -S<field>`
  catches name add/remove but MISSES type or encoding changes that keep a name
  (`io.UBlockPos -> io.BlockPos`, `io.Bool -> io.Varint32`,
  `io.Bool -> protocol.OptionalFunc`). A surviving name says nothing about wire shape.
  Treat a "Fix incorrect ..." or revert commit as a gophertunnel bug interval, not a
  Mojang change: date the DSL by the corrected shape and leave the buggy interval out
  of the gating.
- **CloudburstMC/Nukkit** and **MemoriesOfTime/Nukkit-MOT** -- production
  multi-version servers. Nukkit-MOT carries many versions behind
  `if (protocol >= NNN)` branches that date a change precisely, and both track fresh
  BDS releases fast, so they are the strongest cross-check exactly where Protocol and
  gophertunnel are weakest. Two cautions: they are servers, so client-to-server and
  many server-to-client packets have stubbed or absent codecs (silence, not
  evidence), and they model gameplay packets only. Never a naming source (see Names
  mirror BDS above).

Before concluding a reference is silent, look for in-progress work. A new protocol
often lands on a feature branch or open PR before merging:
`git ls-remote --heads <repo>` and `gh pr list --repo <repo> --state open`. WIP
material counts as a source, but flag in the commit that it came from a branch and
may shift before merge.

## Disagreement is a stop sign, not a vote

When sources disagree about a field's name, type, id, presence, or wire position, do
not pick one. Raise it (see Stop and raise below). The protocol-docs dump is mechanical
and sometimes wrong, but silently overriding it with gophertunnel or CloudburstMC
just buries the conflict.

## A new file in the dump is a cerealisation, not a freebie

protocol-docs only emits packets that go through Mojang's `cereal` reflective
serializer. A still-hand-written packet (`read()` / `write()`) is absent from the
dump entirely, so when Mojang migrates a packet to cereal it shows up as a NEW file
at that version -- and that migration frequently rewrites the wire format: field
reorder, prefix-width swap (fixed `uint32` -> `uvarint32`), optional handling, dropped
fields, or a discriminated union collapsing to a flat layout.

So an added file in the `old..new` diff is the highest-risk kind of change, not "the
dumper finally noticed an unchanged packet". The dump's flattened view cannot
represent a former union's per-case gating, so it lists every variant field as if
always present and silently drops some. For every newly-appearing packet the DSL
already models, diff the post-cereal shape against the existing DSL shape, date the
delta against the production references, and gate it with `since=N`. v1001 alone
flattened `BossEventPacket` (dropping `darken_screen`), reordered
`SubChunkRequestPacket` and swapped its offset prefix to `uvarint32`, and interleaved
`ClientCacheBlobStatusPacket`'s two lists -- every one an added file in the dump,
every one a real wire change.

## Reference width is byte-aliased

cereal writes a `std::variant` discriminator, and most small scoped enums, as a
`uvarint32`. gophertunnel, CloudburstMC, and Nukkit-MOT routinely model the same field
as a `uint8`. For any value that fits in 7 bits (0..127) -- which covers nearly every
variant index and small enum -- `uvarint32` and `uint8` encode to the identical byte,
so the community libs are byte-indistinguishable from the truth and carry no width
information. A serializer calling `io.Uint8(&x)` is not evidence the field is one byte
wide, and a reported "narrowing from `uvarint32` to `uint8`" across versions is almost
always an artifact of this aliasing, not a real Mojang change. (v1001's
`BossEventPacket` flattened from a union and dropped `darken_screen` -- both real and
observable -- yet the refs also showed its `event_type` / `colour` / `overlay` as
`uint8`, which are aliased and stay `uvarint32`.)

- Default a variant discriminator and a small enum to `uvarint32`. A bare `A | B`
  union already does this. Never write `tag=uint8`, and never "correct" a width down
  to `uint8` because a reference shows a byte.
- The aliasing only hides single-byte-range differences. A multi-byte gap is still
  observable: a fixed `uint32` length prefix (4 bytes) versus a `uvarint32` one (1
  byte for small counts) genuinely differ on the wire, so a `uint32 -> uvarint32`
  prefix change IS a real, ref-confirmable change. Distrust the refs on discriminator
  / enum width, but trust them on field order, presence, and wide fixed-width prefixes.
- When a width actually matters, the only authority is BDS: confirm the enum's
  underlying type or the `std::variant` against bedrock-headers, or disassemble the
  cereal serializer. The community libs cannot answer the question.

## v291 is a floor, not an introduction point

CloudburstMC's codec history begins at protocol 291, so a packet or enum whose oldest
serializer is `v291` cannot be told apart from one that predates the reference window.
Leave it ungated -- no `since=291`. The same applies to any `field(since=)` /
`value(since=)` that would land on 291: drop it. The earliest introduction worth
gating is 292 or later.

## Omit deprecated and no-longer-serialized packets

When bedrock-headers marks a packet id `X_Deprecated` / `X_DEPRECATED` in
MinecraftPacketIds and no reference (protocol-docs, gophertunnel, CloudburstMC)
carries a body for it, the packet is no longer on the wire. Omit it from the DSL
entirely. Do not keep an empty `class X: pass` stub just to hold the id in the
generated enum surface -- a packet that nothing serializes should not appear at all.

## Stop and raise -- do not edit silently

When you hit one of the cases below, pause and surface it to the user together with
the blocking material (file path, field, references checked) instead of guessing. Do
not pre-decide for the user.

- Sources disagree about a change in a way two of the references cannot resolve (a
  field's name, type, id, presence, or wire position).
- A packet is removed at version N. The DSL cannot gate a packet definition with a
  lone `until=` (see the `ExplodePacket` note in `protocol/level.py`).
- A struct is renamed, or a field rename collides with another field's history. The
  DSL has no rename primitive. (A name change with the same wire shape is just a
  rename, not a versioned redeclaration.)
- A new field uses a wire shape the DSL does not model: a packed bitfield that is not
  a `bitset[N]`, a non-prefixed list whose count does not reduce to a `count=lambda`
  over earlier fields, or a discriminator type the union machinery cannot express.
- gophertunnel does not model a new packet, so its golden cannot be generated. Do not
  invent the bytes (see `tests.md`).
- A change needs new compiler IR, a new template, or a new primitive. The compiler is
  off-limits for protocol-bump work.
