---
paths:
  - "protocol/**"
---

# Adding a protocol version

## Scope

- This file covers a forward version (at or above the cereal floor, `wire.md`), a back-port below it, and a renumber when a newer preview replaces the modelled one.
- How a declaration is spelled lives in `dsl.md`, `enums.md`, `gating.md` and `naming.md` beside this file; on spelling those files win.

## The rule of four

- A version is done only when four categories are accounted for and each is reported, `nothing` included:
  - packet: added, removed, id moved;
  - type: a field added, removed, renamed or moved; a type added, removed or renamed;
  - wire: the same field, encoded differently;
  - enum: a value added, removed, renamed or shifted; a sentinel moved.
- When the four do not fit one pass, fan out one `version-delta` agent per category, each given the interval, the sources and the schema.
- Treat a change to a packet the schema does not model as a finding, and model the packet.
- Never stop at the first category with hits; a name-level read cannot see wire and enum changes.

## Start from the declaration

- Model only the target's delta against the existing declaration: forward work lands on top of it, a back-port peels off it as `until=` or an earlier redeclaration.
- Never take the existing declaration as evidence about an older wire.
- Never assume a packet's pre-floor shape from its cerealised one, or the reverse.
- Never re-derive a whole pre-cereal body from Sandertv/gophertunnel; its Marshal history says only what differed at the time.
- First ask whether a back-port is only a gate edit.
- Never re-baseline, and never fold a drive-by correction into a version bump; land it separately.
- A packet is dirty when a member, a member's type or any type in its nesting changed, never because a protocol-docs branch is new; before modelling, list the dirty packets between two branches with `uv run --no-project scripts/dirty_packets.py <protocol-docs clone> origin/<old> origin/<new>`.

## Forward

- Add a version in five steps:
  - list the packets added, removed, moved and dirty with `scripts/dirty_packets.py`, a read of the dump below;
  - update the DSL from the new dump alone;
  - compare the library's dirty set, the classes of `v<new>.packets` that `v<old>.packets` lacks, with the dump's, where `<old>` is the modelled neighbour toward 2168; any other difference is a DSL defect;
  - run `scripts/goldens/values.py`, then `scripts/goldens/bds.py` on the new version's BDS, release or preview, and fix every difference as a DSL defect before its case freezes into `tests/goldens/<new>/`;
  - land the version with its complete folder.
- Diff both ways from the base: `tests/goldens/2168/` holds every packet, a version above it diffs against the version below, and a version below it against the version above.
- Run the new build over the cases of every clean packet's nearest folder toward 2168 that holds it too; a difference means the DSL missed a dirty packet.
- When a version's bedrock-headers land after its DSL was written, study the version against them and fix the DSL.
- Take a new version's wire from its protocol-docs dump, primary evidence with known blind spots (`sources.md`); names follow `naming.md`.
- Take the four categories from two fetched `origin/` protocol-docs branches: `git diff --name-status -M origin/<old> origin/<new>`, then `git diff -U1 -M origin/<old> origin/<new>`.
- Compare two-dot, because the branches share no merge base; always pass `-M`, or a rename reads as a delete plus an add.
- A `constraints` block is not wire, except `RequestNetworkSettingsPacket`'s, which carries the version.
- Classify every hunk into exactly one category; never write a diff off as constraint churn in bulk.
- Take a packet's id from its own `packets/*.json`; `enums/MinecraftPacketIds.json` is an index that leaves ids out.
- Diff `MinecraftPacketIds.json` as a second view and merge the two lists as a union, never an intersection.
- Compare fields as an ordered sequence, because cereal is positional, and compare the whole field object, not only its name.
- A change to a field's type string, `optional` or `enum` binding is a wire change; follow nested type objects, a repeat's element type included.
- Read `repeat` exactly: an integer means `array[T, N]`; a string is a `list[T]`'s length prefix.
- Before reading a vanished field as removed, check the same file for a matching addition.
- Follow a renamed type into every file that references it, including a BDS-versioned namespace (`SharedTypes::v1_X_Y`).
- Grep every era's dump for `"value": true` when modelling a dynamic member.

## Cerealisation

- In a cerealisation, check every field's order, every count's type and every nested type's shape.
- Below 2168 a packet file new between branches is a cerealisation candidate (`sources.md`); from 2168, where BDS writes a packet by hand, the BDS run checks its hand-written writer against the library (`wire.md`).
- Confirm a candidate against Mojang/bedrock-protocol-docs' `legacy_changelogs/` and the era's gophertunnel Marshal; a new dump file can also mean the dumper's coverage grew.
- Never use size to prove or disprove a reorder; a cerealisation can leave the size unchanged.
- Take the pre-cereal delta from gophertunnel's Marshal history or CloudburstMC/Protocol's older serializer.

## Back-port

- Go one step down: diff the target against the nearest modelled snapshot above it, never skipping one.
- Bound a gophertunnel window by the two commits that set each era's `CurrentProtocol`, and diff the whole `minecraft/protocol` tree between them.
- Classify every commit in the window (the bump, a retro-fix to the older era, non-wire churn) before attributing any of it; the interval diff is only a candidate set.
- At HEAD, read CloudburstMC/Protocol's `codec/v<new>/` listing as the packet-level changelog, and compare `Bedrock_v<new>.java` against `v<old>` for ids.
- Compare CloudburstMC against gophertunnel's whole `minecraft/protocol` tree, never `packet/` alone.
- Never find changes with `git log -S<field>`; it misses wire changes.

## Land it

- Land a schema change with its complete `tests/goldens/<new>/` folder, every path of every dirty packet frozen once BDS agrees (`.claude/rules/tests.md`), in the same commit; it is not done until the suite runs.
- Write a version commit as `feat(protocol): follow <build> to protocol <new>`, with a body that reports all four categories.

## Consumers

- A schema change reaches EndstoneMC/endweave only through a bedrock-protocol release it pins; a renamed generated name or a renumbered version is a breaking change there.
- A renumber also renames every endweave `protocols/` directory that carries the old number.
- A version endweave lacks is endweave transform work, not a bedrock-protocol limitation.
- Diff the generated public type set before and after any gate change; consumers bind to that set, not to the schema.
