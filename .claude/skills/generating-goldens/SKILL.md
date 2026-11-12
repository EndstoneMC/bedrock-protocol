---
name: generating-goldens
description: Produces a frozen golden for a bedrock-protocol test by having the era's official BDS read library-encoded bytes and write its own bytes and JSON. Use whenever a test needs expected bytes, when a new protocol version drops, when a packet is dirty at a version, or when a golden and the schema disagree.
---

# Generating goldens

Where a golden goes and how it is labelled is `.claude/rules/tests.md`; this is the procedure. BDS is the only golden source; BDS is never run from a test.

## Steps

1. List the dirty packets of the version (`.claude/rules/protocol/workflow.md`); each gets goldens for all its paths.
2. Fetch the version's official Linux BDS zip, `https://www.minecraft.net/bedrockdedicatedserver/bin-linux/bedrock-server-<version>.zip`, into its own new directory; never unpack over another build.
3. Run that `bedrock_server` under lldb with `server-port` and `server-portv6` set off the defaults; kill only the pid you started.
4. Encode every path of each dirty packet with the library at HEAD: each variant alternative, optional present and absent, each gated or `when=` branch.
5. Let BDS read the bytes, write its default write (the packet's own `SerializationMode`, `wire.md`), and dump its JSON.
6. Compare BDS's bytes and JSON with the library's, and the default write with the other writer.
7. On any difference, or a read BDS rejects, fix the schema (`sources.md` weighs the evidence) and repeat from step 4.
8. On agreement, freeze: paste the BDS bytes into the test as `tests.md` says; never regenerate them.

## When it goes wrong

- BDS rejects trailing bytes or fails a read -> the library encodes a shape BDS does not; fix the schema.
- BDS's default write and its other writer disagree -> model the writer BDS uses and record the disagreement in the commit body (`sources.md`).
