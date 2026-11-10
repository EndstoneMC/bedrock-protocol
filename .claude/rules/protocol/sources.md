---
paths:
  - "protocol/**"
  - "tests/**"
---

# Sources

## Authorities
An era is one modelled protocol and the BDS build that reports it.

| Aspect | Authority |
| --- | --- |
| names, nesting, C++ types, member order | EndstoneMC/bedrock-headers at the era's `android/rNN_uN` branch, never head |
| wire of a cerealised packet (type, order, prefix, presence) | the dump: EndstoneMC/protocol-docs at the era's branch |
| wire of a hand-written packet | the era's `<Packet>::write`, decompiled in that build's IDA database |
| golden bytes | what Sandertv/gophertunnel marshals (`.claude/rules/tests.md`) |
| dating | MemoriesOfTime/Nukkit-MOT and CloudburstMC/Protocol (`versions.md`) |
| the step inside a cycle | Mojang/bedrock-protocol-docs `legacy_changelogs/` (`versions.md`) |

- Treat every source outside the table as a pointer to where to look, never as what is true; confirm against a second source before acting.
- Use Mojang/bedrock-protocol-docs for wire facts only as a last resort, and mark anything resting on it `# TODO: confirm against BDS`.
- Never infer wire shape from a header, and never complete a type by copying members out of one.
- Never read a bedrock-headers `.cpp` as a wire source; those files hold declarations only.
- Never read one write call as one field; the binary settles the bytes and the header settles how many members produced them.
- Finish every pre-cereal reading in the binary; each write call carries its own field-name string.
- Never take a `<Packet>::write` symbol as proof a packet is hand-written; only its body answers.

## Reading
- Read protocol-docs and bedrock-headers with `git show origin/<branch>:<path>`, never from a local branch or after a checkout; a stale checkout looks like a finding.
- Read each branch's commit subject before diffing; the same `rNN_uN` does not name the same release in bedrock-headers and protocol-docs.
- Grep bedrock-headers, the dump and the schema case-insensitively; BDS spells `Serverbound` with a lowercase b.
- Transcribe an enum with `[A-Za-z0-9_]+`, never `[A-Z0-9_]+`, and check the member count against the header before believing a gap.
- Never paste EndstoneMC/bedrock-headers source (access-restricted) into the schema, a commit or any file; read it and cite the branch.
- Clone a missing reference repository rather than working around it.

## Weighing evidence
- Never take silence in a reference, or agreement between two community codecs, as evidence; the codecs copy each other.
- Where a community codec disagrees with BDS, the codec is wrong until proven otherwise.
- Lean on a codec only for packets its consumer exercises (GeyserMC/Geyser for CloudburstMC/Protocol, df-mc/dragonfly for gophertunnel), after checking that a codec and a test exist.
- Read a codec's Reader as well as its Writer; read-side tolerance, such as a case-insensitive compare or accepting an absent field, is evidence of live traffic.
- Never take a width from a codec's byte, since 0..127 encodes the same as `uint8` and as a varint; only BDS and protocol-docs answer width, while a codec's field order, presence and wide fixed prefixes stay usable.
- Check a CloudburstMC shared helper against gophertunnel's per-field method.
- Re-check a reference's known error at the era you model; `ref X is wrong about Y` always carries an era.
- Trust a capture over a string literal where they disagree.
- Decompile the writer in the era's IDA database where the header and the dump disagree, or gophertunnel and CloudburstMC do; the binary is the arbiter.
- Settle a disagreement between a golden and the dump in the header, then in the binary; never side with the dump by default.
- Where symbols are absent, count the functions that reference a cereal field-name string literal to learn how many times a member is bound.
- Never decide wire presence from a cereal `bind`, which says only what is bound; decompile `write` and count what it emits.
- Never decide cerealisation by grepping the binary for cereal display strings.

## The dump
- A packet missing from the dump is not cerealised at that version, and the dump cannot describe it.
- Check dump presence first: a packet present at both eras is settled by the dump outright; where it is absent at either era, a dump hunk is only a pointer and an empty dump diff is no finding.
- A shared type's dump entry covers only the packets the dump also lists; a hand-written call site may encode it differently, and the dump shows no sign of it.
- An unchanged dump is no proof of an unchanged wire; compile-time TypeSchema specialisations are invisible to it.
- Suspect a TypeSchema specialisation flip when a packet grows by a multiple of a fixed array's outer extent; confirm statically from the RTTI name, then the vtable, then the read virtual's error strings.
- Before modelling a dumped `optional: true`, check whether the binding is dynamic; an older dump hides its always-true marker, so confirm against a codec's read or the binary.
- Read a dumped enum value name as BDS's own spelling, not the wire's (`wire.md`).
- Before diffing two dumps, probe that one dumper generation made both (varint, `_be`, `uint32` repeats, string-typed enum fields); a generation gap is rendering noise, and whatever survives is settled in bedrock-headers at both branches or in the binary, with a control.

## Is a packet live
- Never take an id-enum entry as evidence that a packet exists; BDS keeps ids long after the class is gone.
- Take a packet as live when bedrock-headers has its `<Name>Packet.h`, after dropping any `_DEPRECATED`, `_deprecated` or `_Deprecated` suffix from the id name.
- Run known-live packets through any presence probe as controls, in the same command.
- Never use `make_packet` instantiations as the packet list, since they cover one construction path.
- Never treat a `getId` symbol as present for every packet in a stripped build.

## prototype
- Never merge or rebase across the `prototype` branch, an unrelated history; port its ideas rather than its code, and re-verify every wire detail it holds.
