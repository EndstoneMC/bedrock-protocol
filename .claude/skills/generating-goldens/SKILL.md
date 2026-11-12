---
name: generating-goldens
description: Produces a frozen golden for a bedrock-protocol test by having the era's official BDS read library-encoded bytes and write its own bytes and JSON. Use whenever a test needs expected bytes, when adding, back-porting or renumbering a protocol version, when a packet is dirty at a version, or when a golden and the schema disagree.
---

# Generating goldens

Where a golden goes and how it is labelled is `.claude/rules/tests.md`; this is the procedure.

## Steps

1. List the dirty packets of the version (`.claude/rules/protocol/workflow.md`); each gets goldens for all its paths.
2. Fetch the build's official Linux BDS zip into its own new directory, never over another build: `https://www.minecraft.net/bedrockdedicatedserver/bin-linux/bedrock-server-<build>.zip` for a release, `https://www.minecraft.net/bedrockdedicatedserver/bin-linux-preview/bedrock-server-<build>.zip` for a preview, with `<build>` in full (`1.26.36.1`, `1.26.70.24`).
3. Generate the values of every path of each dirty packet with `scripts/goldens/values.py` (each variant alternative, optional present and absent, each gated or `when=` branch) and encode them with the library at HEAD into a cases file, a JSON array of `{"packet": <id>, "id": "<case>", "value": <value>, "bytes": "<hex>"}`; `value` uses schema field names, `{"<Alternative>": ...}` for a variant and the bound enum member's `.name`.
4. Run `python3 scripts/goldens/bds.py --server <dir> <cases.json>` with the python3 that lldb's module was built for (`--lldb lldb-22` for a versioned lldb). It moves the server's ports off 19132 and 19133 and turns LAN visibility off in its `server.properties`, starts that `bedrock_server` under lldb with its terminal logged to `<dir>/bds.log`, builds each packet, reads the seed with BDS's own reader, prints BDS's JSON, writes with the packet's default writer (its `SerializationMode`, `.claude/rules/protocol/wire.md`) and, below `SerializationMode` 5 (`CerealOnly`, which has no other writer), with the other writer, kills its own pid, and prints one JSON report.
5. A case whose `difference` is `null` agrees: freeze it by writing the case `{id, writer, value, bytes}`, plus `other_writer_bytes` where the other writer differs, into `tests/goldens/<protocol>/<id:03>_<name>.json`, record the build in `tests/goldens/builds.json`, and never regenerate it.
6. Fix every other case in the schema (`.claude/rules/protocol/sources.md` weighs the evidence) and repeat from step 3.

## When it goes wrong

- `no build in BUILDS has sha256` -> add the build to `BUILDS`, every address read from that binary: `create_packet` by its byte signature (the id switch behind `cmp esi, <highest id>`); each vtable by its RTTI name; `server_network_system` as the constructor that stores `ServerNetworkSystem`'s vtable, and `reflection_ctx` as where its `NetworkSystem` base keeps the `make_unique<cereal::ReflectionCtx>()` result; `stream` and `result_ok` from what slot 9 reads; the slots from `Packet.h` at the era's bedrock-headers branch, checked on one packet's vtable.
- `--lldb: no lldb-server beside` -> pass `--lldb` an lldb installed with its `lldb-server`.
- `no 'Server started.'` or `before 'Server started.'` -> read `<dir>/bds.log`.
- `createPacket builds nothing for this id` -> add the packet's entt default constructor (it stores the packet's vtable into a fresh allocation) to `default_constructors`.
- `read:` with error code 74 -> BDS stopped short of the seed's end or ran past it; `offset` is where it stopped; fix the schema.
- `bytes:` or `json:` -> BDS reads the seed but means something else by it; `json:` names the key path, in `value` or in BDS's JSON past the end of `value`, of the first scalar BDS shows differently; fix the schema, or the value where it is not what the library holds; never loosen `bds.py`'s comparison.
- `bytes` and `other_writer_bytes` disagree -> model the writer BDS uses and record the disagreement in the commit body (`.claude/rules/protocol/sources.md`).
