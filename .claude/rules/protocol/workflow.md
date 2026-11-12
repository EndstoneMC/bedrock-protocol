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
- Diff a packet's whole transitive type closure across EndstoneMC/protocol-docs branches before modelling it; a new branch is not evidence of change.

## Forward

- Read the dump as primary evidence with known blind spots (`sources.md`).
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

- A cerealisation is the highest-risk change: one changelog line can reorder fields, retype counts and reshape nested types.
- Below 2168 a packet file new between branches is a cerealisation candidate (`sources.md`). From 2168 model every packet from the dump, and where BDS writes it by hand (`SerializationMode` 0 to 2 in its constructor), check the hand-written writer against the dump in the binary before trusting the dump's shape.
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

- Land a schema change with its golden or structural test in the same commit; it is not done until the suite runs (`.claude/rules/tests.md`).
- Write a version commit as `feat(protocol): follow <build> to protocol <new>`, with a body that reports all four categories.

## Consumers

- A schema change reaches EndstoneMC/endweave only through a bedrock-protocol release it pins; a renamed generated name or a renumbered version is a breaking change there.
- A renumber also renames every endweave `protocols/` directory that carries the old number.
- A version endweave lacks is endweave transform work, not a bedrock-protocol limitation.
- Diff the generated public type set before and after any gate change; consumers bind to that set, not to the schema.
