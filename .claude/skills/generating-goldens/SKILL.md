---
name: generating-goldens
description: Produces a frozen golden for a bedrock-protocol test by having the era's official BDS read library-encoded bytes and write its own bytes and JSON. Use whenever a test needs expected bytes, when adding, back-porting or renumbering a protocol version, when a packet is dirty at a version, or when a golden and the schema disagree.
---

# Generating goldens

Where a golden goes and how it is labelled is `.claude/rules/tests.md`; this is the procedure.

## Steps

1. List the dirty packets of the version (`.claude/rules/protocol/workflow.md`); each gets goldens for all its paths.
2. Fetch the build's official Linux BDS zip into its own new directory, never over another build: `https://www.minecraft.net/bedrockdedicatedserver/bin-linux/bedrock-server-<build>.zip` for a release, `https://www.minecraft.net/bedrockdedicatedserver/bin-linux-preview/bedrock-server-<build>.zip` for a preview, with `<build>` in full (`1.26.36.1`, `1.26.70.24`).
3. Run that `bedrock_server` under lldb with `server-port` and `server-portv6` set off the defaults; kill only the pid you started.
4. Encode every path of each dirty packet with the library at HEAD: each variant alternative, optional present and absent, each gated or `when=` branch.
5. Let BDS read the bytes, write its default write (the packet's own `SerializationMode`, `.claude/rules/protocol/wire.md`), and print its JSON where the build has one.
6. Compare BDS's bytes and JSON with the library's, and the default write with the other writer.
7. On any difference, or a read BDS rejects, fix the schema (`.claude/rules/protocol/sources.md` weighs the evidence) and repeat from step 4.
8. On agreement, freeze: paste the BDS bytes into the test as `tests.md` says; never regenerate them.

## When it goes wrong

- BDS rejects trailing bytes or fails a read -> the library encodes a shape BDS does not; fix the schema.
- BDS's default write and its other writer disagree -> model the writer BDS uses and record the disagreement in the commit body (`.claude/rules/protocol/sources.md`).
