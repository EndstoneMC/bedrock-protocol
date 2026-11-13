---
paths:
  - "protocol/**"
  - "README.md"
---

# Versions

## The number

- Model the protocol number the released build reports, never the preview number in a Mojang changelog title.
- Read the number from the dump: `constraints.minimum` on `RequestNetworkSettingsPacket`'s first field.
- Take the list of builds from EndstoneMC/bedrock-server-data's `versions.json`.
- Stop and ask before modelling a number that no build reports.
- An EndstoneMC/protocol-docs branch is a network version, not a release order, and it can bump within itself; re-read its README after every fetch.
- Pin the protocol-docs SHA you diffed and the build you dumped.
- A protocol number does not identify a wire format: Mojang changes the wire within one number, and `since=` cannot express that.
- Diff the releases of one update line through its protocol-docs branch's history, taking one commit per stable release.
- Spell a release with three parts (`1.26.60`) and a preview with four (`1.26.70.21`).

## One protocol per update line

- A newer preview on the same update line replaces the older number; it never becomes a second snapshot beside it.
- Renumber every gate the superseded preview carried, and model the new delta in the same commit.
- After a renumber, grep for the bare number and for `v<number>`; a word-boundary match misses the namespace form.
- With every version, add its number to `versions` in `protocol/__init__.py` in ascending order (a renumber replaces the superseded one) and bump README's pinned examples to the new number.
- README shows one example: the same packet and steps in every language, the library imported as `bp`, a pin naming `v<N>` only for a type that differs between protocols, the packet built empty and each field set in its own statement with its value built whole in place; every block is laid out by ruff format or clang-format.

## Releases

- Record every number a stable client release reports in `releases` beside `versions`, with the releases that report it; a number nothing gates on goes in `releases` only and decodes with the newest snapshot below it.
- Take a range's ends from each stable build's dump, one protocol-docs commit per stable release, and from minecraft.wiki's list; a BDS-only build widens its line's range only when it reports the line's number.
- Spell an entry as a release (`"1.26.45"`) or a range (`"1.26.40-1.26.44"`); only the newest may be its line's wildcard (`"1.26.6x"`).
- A hotfix that keeps an open entry's number changes nothing; when a new number ships, close the open entry to the last release that reported it.
- A mid-line renumber is a closed entry (`2226: "1.26.64"`); a later hotfix that reports its number widens it.
- List each `releases` entry as a row of README's Supported Protocols table, `| <number> | <first> to <last> |`, an open entry with its wildcard.
- A preview stays out of `releases`; its entry lands with the renumber to the shipped number.

## Snapshots

- A snapshot is a protocol number that some declaration gates on.
- Gate on released numbers; a change dated to an intermediate changelog step gates at the first modelled release at or after it.
- A change in a released protocol that nothing gates on yet materializes that snapshot; never fold it into a neighbouring snapshot.
- Accept the snapshot that an introduction gate materializes.
- Never materialize a snapshot the evidence does not force.

## Dating

- Date a member with MemoriesOfTime/Nukkit-MOT's `@since vNNN`, or with a CloudburstMC/Protocol `Serializer_vN` that extends `_vM` and appends the member.
- Read every Sandertv/gophertunnel commit's diff inside the Marshal body, and gate at that commit's `CurrentProtocol`.
- Never gate by a gophertunnel bug interval; date by the corrected shape.
- Reduce a reference's shared-helper swap to the one shared type it actually describes.
- Use Mojang/bedrock-protocol-docs' `legacy_changelogs/` for the step a change landed on, for cerealisations it states outright, and for BDS member renames.
- Date only from step-numbered lines; the bare Added/Removed summary is cumulative, and diffing it against the previous file yields only candidates.
- Check a changelog's step range before trusting a line, and read the previous cycle's file for a step below it.
- A step number is not the release that reports that number; only the dump, `MinecraftPacketIds::EndId` in EndstoneMC/bedrock-headers and the binary say which release has a change.
- Never treat Mojang's changelog as complete.
- Date packet ids by diffing bedrock-headers' `MinecraftPacketIds` across its `origin/android/*` branches; `EndId` is the quick read and stays out when parsing the enum.
- Date a packet's arrival, body and id together, from the first era whose `MinecraftPacketIds` holds the id and whose CloudburstMC/Protocol codec or Mojang/bedrock-protocol-docs commit carries the packet; a class missing from that era's BDS or bedrock-headers build does not delay it.
- Never assume a packet id from memory or from another era; ids change and are reused once a packet is deprecated.
- Never date a packet's removal from its id-enum name.
