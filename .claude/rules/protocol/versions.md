---
paths:
  - "protocol/**"
---

# Versions

## The number

- Model the protocol number the released build reports, never the preview number in a Mojang changelog title.
- Check every cycle for that split; not every cycle has one.
- Read the number from the dump: the first field of `RequestNetworkSettingsPacket`, `constraints.minimum`.
- Confirm it with CloudburstMC/Protocol's `Bedrock_v<N>.java` `protocolVersion` and `minecraftVersion` pair.
- Cross-check it against EndstoneMC/bedrock-server-data's `versions.json` and minecraft.wiki's Protocol version page.
- Stop and ask before modelling a number that none of them carries.
- A Mojang/bedrock-protocol-docs branch is a network version, not a release order, and it can bump within itself; re-read its README after every fetch.
- Pin the protocol-docs SHA you diffed and quote it in the commit; record the build, not only the number.
- A protocol number does not identify a wire format: Mojang changes the wire within one number, and `since=` cannot express that.
- Name the build you dumped, and diff the releases of one update line through that branch's history, one commit per stable release.

## One protocol per update line

- A newer preview on the same update line replaces the older number; it never becomes a second snapshot beside it.
- Renumber every gate the superseded preview carried, and model the new delta in the same commit.
- After a renumber, grep for the bare number and for `v<number>`; a word-boundary match misses the namespace form.
- With every version, bump `__version__` in `protocol/__init__.py` and add the release to README's Supported protocols table.

## Snapshots

- A snapshot is a protocol number that some declaration gates on.
- Gate on released numbers; a change dated to an intermediate changelog step gates at the first modelled release at or after it.
- A change in a released protocol that nothing gates on yet materializes that snapshot; never fold it into a neighbour to avoid the transitive cost.
- Accept the snapshot that an introduction gate materializes.
- Never materialize a snapshot the evidence does not force.

## Dating

- Date a member with MemoriesOfTime/Nukkit-MOT's `@since vNNN`, or with a CloudburstMC/Protocol `Serializer_vN` that extends `_vM` and appends the member.
- Read every gophertunnel commit's diff inside the Marshal body, and gate at that commit's `CurrentProtocol`.
- Never gate by a gophertunnel bug interval; date by the corrected shape.
- Reduce a reference's shared-helper swap to the one shared type it actually describes.
- Use Mojang/bedrock-protocol-docs' `legacy_changelogs/` for the step a change landed on, for cerealisations it states outright, and for BDS member renames.
- Date only from step-numbered lines; the bare Added/Removed summary is cumulative, and diffing it against the previous file yields only candidates.
- Check a changelog's step range before trusting a line, and read the previous cycle's file for a step below it.
- A step number is not the release that reports that number; only the dump, the header's `EndId` and the binary say which release has a change.
- Never treat Mojang's changelog as complete.
- Date packet ids by diffing bedrock-headers' `MinecraftPacketIds` across its `origin/android/*` branches; `EndId` is the quick read and stays out when parsing the enum.
- Never assume a packet id from memory or from another era; ids change and are reused once a packet is deprecated.
- Never date a packet's removal from its id-enum name.
