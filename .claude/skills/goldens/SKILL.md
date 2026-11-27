---
name: goldens
description: Runs BDS over the golden cases in tests/goldens through a local, modified bedrock-dumper, so BDS reads each case's bytes, writes its own and prints its own JSON, then compares both with the case and measures which codec branches the cases reach. Use when adding, changing or freezing a case, when BDS refuses, rewrites or crashes on a case, when a case file needs the dump's enum bindings, items or blocks, or when asked which branches no case reaches yet.
---

# Goldens handbook

`.claude/rules/protocol/goldens.md` decides what a case holds and when it freezes. This skill produces the BDS evidence it asks for. Run every step from the repository root: the comparison with `compare.py` beside this file, every other step as an inline command. Save no other script anywhere, the scratchpad included.

`<protocol>` names the case folder `tests/goldens/v<protocol>`, `<version>` is the BDS build that goldens.md says checks it, and `<channel>` is that build's channel, `stable` or `preview`.

## Never

- Push the clone, give it a remote, or copy its code into this repository. bedrock-dumper is closed source: name it, never link it, and describe its code in words.
- Run any BDS but your own, or more than one at a time. Kill only the pid you started.
- Hardcode an address. Find a function by RTTI, or by a byte signature behind a version gate.
- Loosen the comparison until a case passes, or retry values until BDS accepts one.

## A newer protocol's folder

1. List the packets whose class differs from the modelled protocol before it: `[i for i, cls in v<protocol>.packets.items() if v<previous>.packets.get(i) is not cls or _core.encodings[<previous>].get(cls) != _core.encodings[<protocol>][cls]]`.
2. Copy each one's file from the nearest folder toward `v2168/` that holds it, change only the fields whose encoding changed, and write it as `layout(cases)` with bytes from the library. Give a new packet cases of its own from the dump.
3. Delete every file left byte-identical to the one it was copied from.
4. Pick a BDS build at `<protocol>` the runner builds, a stable one unless only a preview reports `<protocol>`, add its `Check` line to goldens.md, then build, run, compare and measure the figure.

## An older protocol's folder

1. List the packets whose class differs from the next modelled protocol toward 2168: `[i for i, cls in v<protocol>.packets.items() if v<next>.packets.get(i) is not cls or _core.encodings[<next>].get(cls) != _core.encodings[<protocol>][cls]]`.
2. Seed each one's file and delete the byte-identical ones as a newer folder does, from the nearest folder toward `v2168/` that holds it.
3. Model each packet in the encoding its build sends by default (dsl.md): a seed from `v2168/` holds cereal shapes, and each record's `serialization_mode` says which encoding BDS sent.
4. Where BDS prints no JSON for a packet, judge the case by its `bds_trace`. Where a script cannot walk the trace against the value, have an agent compare them leaf by leaf and give a verdict per case. A confirmed case freezes, and nothing reruns it.
5. Where the build cannot run a packet's read or write, such as a read that skips to the end of the buffer, a write that ignores what was read, a read that fails `undefined schema` because the build binds the packet's cereal schema into no packet context, or `crashed no factory builds this packet id` for an id the build declares, leave the packet out (goldens.md) and have `bds-reverse-engineer` read the sides the build has against the DSL.
6. Have `bds-reverse-engineer` date each schema fix across every build on disk from the folder's protocol back to 776, one address per build, and gate the fix only where a build changes.
7. Pick a BDS build at `<protocol>` the runner builds, a stable one unless only a preview reports `<protocol>`, add its `Check` line to goldens.md, then build, run, compare and measure the figure.

## The runner

```
git clone <bedrock-dumper checkout> build/bedrock-dumper && git -C build/bedrock-dumper remote remove origin
git -C build/bedrock-dumper log --oneline --grep golden
```

If the log shows no golden mode, add it to the clone and commit it there:

- `DUMPER_GOLDEN` names a JSON array of `{id, stem, index, bytes}`. When it is set, the first-tick work runs golden mode instead of the dump and writes `results.json` beside that file.
- Get the packet reflection ctx from the level's packet sender: take `LoopbackPacketSender`'s network, then its server network system, then call `getPacketReflectionCtx`. Make golden mode a friend of both mirrors. The level's own cereal ctx holds no packets.
- Build each packet with `MinecraftPackets::createPacket`, found by a byte signature over its id switch behind a version gate. When it returns null, default-construct the entt meta type whose `[cereal:packet]` property holds the id, and mark the record `"factory":"meta"`. Check the built packet's `getId` against the case's id, and record `crash` as `the factory built packet id N` when they differ.
- Mirror `Packet`'s virtuals in declaration order from that build's headers. Check the slots of `getId`, `read(stream, ctx)`, `write(stream, ctx)` and `getSerializationMode` against a concrete packet's vtable.
- Mirror `ReadOnlyBinaryStream` and `BinaryStream`, and have their constructors adopt BDS's own vtables, because BDS's readers and writers call the stream's virtuals.
- Find each vtable by RTTI. On a build without RTTI, take each stream's vtable from the vptr `lea` in one of its constructors, found by a byte signature behind a version gate, and check `BinaryStream`'s against the vptr of `NetworkSystem::mSendStream`; check `Packet`'s slots on the vtable of a packet `createPacket` built.
- Mirror `Bedrock::Result<void>` with its `ErrorInfo` and `CallStack`, so a failed read gives its category, code, message and frames. Before 1.20.60, `CallStack::Frame` holds its filename as a `const char *`, not a `std::string_view`.
- Fork for each case. The child reads the case's bytes with `read(stream, ctx)` and records `read_ok`, `consumed` (the read pointer), `error` and `serialization_mode`. After a successful read, it writes with `write(stream, ctx)` into `bds_bytes` and prints the packet it read into `bds_json`. It sends each piece over a pipe as soon as it has it, then calls `_exit`.
- Print `bds_json` with the packet's own `toString`. `toString` binds the packet into a fresh reflection ctx, where a type bound twice, such as Vec3, takes whichever binder runs first; so detour `cereal::BasicSaver::saveImpl`, found by a byte signature, and for the packet being printed alone pass the original a handle over the same packet in the server's packet reflection ctx. A detour that never sees the packet records `bds_json_error`.
- Send `bds_json` as one JSON string of BDS's text, each byte outside valid UTF-8 written as `\udcXX`; BDS's text is not always JSON, so the reader parses it.
- On a build from 1.21.60 to before 1.26.40, gate a writer trace on the build's version: a `BinaryStream` subclass that overrides every writer and documented-write helper, records each call's method, value, label, notes, offset, size and depth, and opens a scope for each array, conditional and branching write. When the packet has no reflected type or its `toString` prints nothing, write the packet into it and send `bds_trace` with `bds_trace_bytes_equal`.
- Before 1.21.60, `BinaryStream`'s writers are not virtual, and from 1.21.40 only `writeIf` and `writeConditional` are, so golden mode sends no `bds_trace`; `read` and `write` take no ctx before 1.21.100.
- `saveImpl` takes a `const SaverConfig &` after the schema before 1.26.30; gate it in the detour's declaration, definition and forwarded calls.
- Give the parent a 30 s deadline, then SIGKILL. It records `crash` as the signal name, `exit N` or `timeout`, and the run goes on.
- Append and flush each record. At the end, log `golden: N cases written to <path>`.
- Before forking, flush only stdout and stderr. BDS's console thread holds stdin's lock.
- Leave the server running afterwards. Only the console `stop` shuts BDS down cleanly.

## Build

```
(cd build/bedrock-dumper && cmake --preset clang-relwithdebinfo -B build/<channel>-<version> -DBEDROCK_SERVER_VERSION=<version> -DBEDROCK_SERVER_CHANNEL=<channel> && cmake --build build/<channel>-<version>)
```

Each build has its own tree, which fetches BDS into `build/bedrock-dumper/build/<channel>-<version>/bedrock-server-<version>` and makes it load the dumper. In that folder's `server.properties`, set `server-port`, and `server-portv6` where the build has one, to ports nothing else uses, and set `enable-lan-visibility=false`. If the build does not compile, or does not dump, on `<version>`, follow bedrock-dumper's own `update` skill.

## Run

```
S=build/bedrock-dumper/build/<channel>-<version>/bedrock-server-<version>
G=$PWD/build/goldens/<version>
mkdir -p $G
```

The stock dump comes first. Case files read their enum bindings, limits, items and blocks from it (goldens.md):

```
rm -f $G/dump.log && mkfifo $G/console
(cd $S && exec ./bedrock_server) <> $G/console > $G/dump.log 2>&1 & P=$!
until grep -qE 'dump (written|failed|crashed)' $G/dump.log || ! kill -0 $P 2>/dev/null; do sleep 5; done
echo stop 1<> $G/console; wait $P; rm $G/console
rm -rf $G/dump && cp -r $S/data $G/dump && rm -f $G/dump/bootstrap.json
```

Golden mode, over the folder's current case files. Narrow `'*.json'` to rerun some of them. Each run overwrites `results.json`:

```
python3 -I -c "import json, pathlib, sys; cases = [{'id': int(p.stem[:3]), 'stem': p.stem, 'index': i, 'bytes': c['bytes']} for p in sorted(pathlib.Path(sys.argv[1]).glob(sys.argv[3])) for i, c in enumerate(json.loads(p.read_text()))]; pathlib.Path(sys.argv[2]).write_text(json.dumps(cases))" tests/goldens/v<protocol> $G/cases.json '*.json'
rm -f $G/golden.log && mkfifo $G/console
(cd $S && DUMPER_GOLDEN=$G/cases.json exec ./bedrock_server) <> $G/console > $G/golden.log 2>&1 & P=$!
until grep -qE 'golden: [0-9]+ cases written|dump failed' $G/golden.log || ! kill -0 $P 2>/dev/null; do sleep 5; done
echo stop 1<> $G/console; wait $P; rm $G/console
```

A clean stop exits 0 and logs `Quit correctly`.

## Compare

`compare.py` beside this file judges every case of a folder against one run, through `CaseForm` and `schema_of` in `tests/conftest.py`. A case `freezes` when BDS read every byte, wrote the case's bytes back unchanged and printed JSON that `CaseForm.matches` accepts for the case's value. Any other case prints each difference: the crash or refusal, the byte where the write-back departs, or the path in the value where BDS's JSON departs, with both values. It ends with the totals and exits 1 unless every case freezes:

```
uv run python .claude/skills/goldens/compare.py tests/goldens/v<protocol> $G
```

`compare.py` has no trace walk. A case with a `bds_trace` freezes when BDS wrote its bytes back unchanged, `bds_trace_bytes_equal` holds and every leaf of the trace matches the case's value in order. A case before 1.21.60 freezes when BDS read every byte and wrote them back unchanged, and every leaf of a static read of that build's writer matches the case's value in order.

Only a `freezes` case can freeze, or a traced or statically read one as above. A difference no rule in goldens.md explains is a finding: fix the schema, the case or `CaseForm`, and never relax the comparison.

## Symptom -> action

| Symptom | Do |
| --- | --- |
| `refused`, `generic:74`, with `read` equal to the case length | BDS read every byte and then rejected the content. Find the constraint BDS checks: its strings name it. Fix the value or the schema, and add the line to goldens.md. |
| `refused`, with `read` short of the length | BDS read fewer bytes than the library wrote. A field is extra, mis-sized or out of order in the schema: read the field at the byte `read` names. |
| `rewritten` | Read the field at the byte named. If BDS fills in, drops, rounds or canonicalises the value, the value is data BDS does not keep: change it and add the rule with its evidence. If BDS writes a field the schema lacks or orders differently, fix the schema. |
| `rewritten`, and two fields come back holding the second one's value | BDS writes one member several times, once per name it binds the member under, or once per write in a hand-written encoding. Declare it as one field with `field(duplicate=N)`, and never pick equal values to pass. |
| `rewritten`, and a variant comes back in another arm | BDS converts the value on read and writes back what the conversion kept. Find the value BDS keeps in the case's arm, and never swap the arm. |
| A case edited since the last run reads `rewritten`, or BDS's JSON describes other bytes | A results file describes the bytes its run read, which `$G/cases.json` holds. When they differ from the folder's current bytes, rerun golden mode before comparing. |
| A case before 2168 is `refused` or `rewritten` in a field the case holds in cereal's shape | `serialization_mode` below CerealOnly means BDS sent the hand-written encoding. Model the pre-cereal shape (dsl.md). |
| `JSON differs at <packet>` before 2168, with `serialization_mode` below CerealOnly | BDS printed the cereal shape of a packet it sent by hand. Have an agent match the case's values against BDS's JSON (an older protocol's folder, step 4). |
| `no reflected type for packet id N`, `toString printed nothing` or `this build has no Packet::toString`, on a build before 1.26.40 | Judge the case by its `bds_trace` (an older protocol's folder, step 4). |
| A record before 1.21.60 has no `bds_trace` | That build's writers are not virtual: judge the case by its bytes against the DSL statically (an older protocol's folder, step 5). |
| A record before 1.21.100 has no `serialization_mode` | That era has no cereal packets, so BDS read and wrote the hand-written encoding: judge the case by its `bds_trace`, and before 1.21.60, which has none, by its bytes against the DSL statically (an older protocol's folder, step 5). |
| A trace leaf with no field of its own in the case's value | It is a list's length, an optional's presence bool, a variant's selector, a `field(duplicate=)` copy, an NBT tag's type, name or end byte, or a `raw` run BDS appended without a writer. Match it to the value's shape at that point, never skip it. |
| Before 1.21.130, a crash in `entt::any_cast<int>` on `[cereal:packet]`, or BDS's JSON wrapped in one `mPayload` member | That era reflects a packet as a class holding one `mPayload`, with no int id property. Take the id from the packet's `getId` and print `mPayload` alone. |
| `crashed` on every case | A `Packet` slot or stream mirror is wrong. Re-check the slots against a vtable. |
| `crashed` with a signal on one case | Its bytes drive BDS somewhere it cannot handle, such as a login at another protocol (goldens.md). The child's `dump crashed` trace, if it printed one, follows the case's `golden <stem>[<index>]` line in `golden.log`. |
| `crashed timeout` | Usually a length or count BDS loops over. Check the case's length prefixes. |
| `crashed no factory builds this packet id` | That build neither builds nor reflects the id. Check the dump's `protocol/` for the packet. |
| `crashed the factory built packet id N` | `createPacket`'s signature matched another function, or `getId` left its slot. Re-cut the signature behind a new gate, or re-check `Packet`'s slots against a vtable. |
| `dump failed: BinaryStream's vtable is not NetworkSystem::mSendStream's` | The stream constructor's signature matched another constructor. Re-cut it behind a new gate; if the vptrs still differ, the `NetworkSystem` mirror moved, so follow bedrock-dumper's `update` skill. |
| `serialization_mode` 0 to 2 on a case that freezes | BDS read and wrote the packet by hand (encoding.md). Nothing to fix. |
| `bds_json_error` says toString did not reach the saver | The `saveImpl` signature does not match this build. Cut a new one behind a version gate. |
| `JSON differs at <path>` on a value | The path names the field. Fix the case's value, or the schema when its type is not BDS's type. |
| `JSON differs at <path>` where BDS prints the same data in another form | `CaseForm.matches` has no rule for the form. Report it; add the rule to `CaseForm` and goldens.md only once goldens.md accepts it. |
| `JSON differs at <path>` where the schema and the dump shape a field differently, such as a struct against an array or nested fields against flat ones | Read both definitions. Fix the schema when the dump's shape is the encoding's; otherwise report it. |
| `printed no JSON` | `bds_json_error` says why; a toString that did not reach the saver needs a new `saveImpl` signature behind a version gate. |
| `dump failed: ... has no signature for this build`, or `hooking failed: ... has no signature for this build` at load | Cut that function's signature for `<version>` behind a new gate. |
| Server hangs after the first `golden <stem>[0]` line | A flush of every stream blocked on stdin. Flush only stdout and stderr before forking. |
| BDS exits 130 or 143, or logs no `Quit correctly` | It was signalled. Stop it through the console `stop`. |
| `stop` went out before BDS started | The wait matched the last run's log. Remove the log before launching, as the run blocks do, and send `stop` again. |
| BDS still runs after `stop` | `kill -KILL $P`, with your own pid only. |

## Coverage

The coverage build lives in `build/Debug`, and its venv holds scikit-build-core, nanobind==2.13.0, pytest, nbtlib and `./compiler`:

```
uv venv build/Debug/.venv
uv pip install --python build/Debug/.venv/bin/python scikit-build-core nanobind==2.13.0 pytest nbtlib ./compiler
uv pip install --python build/Debug/.venv/bin/python --no-build-isolation --no-deps --reinstall-package bedrock-protocol -C install.strip=false -C cmake.build-type=Debug -C cmake.define.CMAKE_CXX_COMPILER=clang++ -C "cmake.define.CMAKE_CXX_FLAGS=-fprofile-instr-generate -fcoverage-mapping" -C "cmake.define.CMAKE_MODULE_LINKER_FLAGS=-fprofile-instr-generate" .
SO=$(find build/Debug/.venv -name '_core*.so')
```

The report for the whole suite:

```
D=build/Debug/profiles/all; rm -rf $D; mkdir -p $D
LLVM_PROFILE_FILE=$D/%p.profraw build/Debug/.venv/bin/python -m pytest tests
llvm-profdata merge -sparse $D/*.profraw -o $D/merged.profdata
llvm-cov report $SO -instr-profile=$D/merged.profdata -show-branch-summary -ignore-filename-regex='(/nanobind/|^/usr/|/python/)'
llvm-cov show $SO -instr-profile=$D/merged.profdata -show-branches=count build/Debug/generated/bedrock/protocol/<module>.cpp
```

The protocol's figure, the one goldens.md measures, runs the folder's cases alone. It counts the branch outcomes of every generated function the folder's packets reach at its protocol, the functions the cases run and every serializer those call, whatever their N, and leaves out the failing side of each read and validation check and the no-match side of each variant switch. It prints the figure, and each line of `$D.missed` is a valid-path outcome no case reaches.:

```
D=build/Debug/profiles/v<protocol>; rm -rf $D; mkdir -p $D
LLVM_PROFILE_FILE=$D/%p.profraw build/Debug/.venv/bin/python -m pytest tests/test_goldens.py -k 'v<protocol>/'
llvm-profdata merge -sparse $D/*.profraw -o $D/merged.profdata
llvm-cov export $SO -instr-profile=$D/merged.profdata -skip-expansions -ignore-filename-regex='(/nanobind/|^/usr/|/python/)' > $D/export.json
python3 -I - $D/export.json <<'EOF' | sort > $D.missed
import json, re, sys
functions = [f for f in json.load(open(sys.argv[1]))['data'][0]['functions'] if re.search(r'/generated/.*\.cpp$', f['filenames'][0])]
sources = {path: open(path).read().split('\n') for path in {f['filenames'][0] for f in functions}}
call = re.compile(r'Serializer<(.+?)>::(serialize|deserialize)\(')
by_signature = {call.search(sources[f['filenames'][0]][f['regions'][0][0] - 2])[0]: f for f in functions}
reached = [f for f in functions if f['count'] > 0]
scope = {id(f): f for f in reached}
while reached:
    f = reached.pop()
    for line in sources[f['filenames'][0]][f['regions'][0][0] - 1:f['regions'][0][2]]:
        for callee in filter(None, (by_signature.get(m[0]) for m in call.finditer(line))):
            if id(callee) not in scope:
                scope[id(callee)] = callee
                reached.append(callee)
failure = re.compile(r'if \(!(\w+)\) return (stream\.fail|std::unexpected)\(\1\.error\(\)|Errc::')
no_match = re.compile(r'switch \(.+\.index\(\)\) \{')
owned = list(scope.values())
outcomes = missed = 0
for f in owned:
    lines = sources[f['filenames'][0]]
    for b in f['branches']:
        line = lines[b[0] - 1].strip()
        is_failure = failure.search(line) or (line == 'default:' and 'Errc::' in lines[b[0]])
        excluded = 'true' if is_failure else 'false' if no_match.fullmatch(line) else None
        for outcome, count in (('true', b[4]), ('false', b[5])):
            if outcome != excluded:
                outcomes += 1
                if count == 0:
                    missed += 1
                    print(f"{f['filenames'][0]}:{b[0]}:{b[1]} {outcome}  {line}")
print(f'{len(owned)} functions, {outcomes - missed}/{outcomes} valid-path branch outcomes reached', file=sys.stderr)
EOF
```

One case's footprint is the branch outcomes it reaches (true count > 0, false count > 0) and the region entries it covers in the generated sources:

```
D=build/Debug/profiles/<stem>.<id>; rm -rf $D; mkdir -p $D
LLVM_PROFILE_FILE=$D/%p.profraw build/Debug/.venv/bin/python -m pytest tests/test_goldens.py -k 'v<protocol>/<stem>/<id>]'
llvm-profdata merge -sparse $D/*.profraw -o $D/merged.profdata
llvm-cov export $SO -instr-profile=$D/merged.profdata -skip-expansions -skip-functions -ignore-filename-regex='(/nanobind/|^/usr/|/python/)' > $D/export.json
python3 -I - $D/export.json <<'EOF' | sort -u > $D.fp
import json, sys
for f in json.load(open(sys.argv[1]))['data'][0]['files']:
    for b in f['branches']:
        for outcome, count in (('true', b[4]), ('false', b[5])):
            if count > 0:
                print(f"{f['filename']}:{b[0]}:{b[1]} {outcome}")
    if '/generated/' in f['filename']:
        for s in f['segments']:
            if s[2] > 0 and s[3] and s[4]:
                print(f"{f['filename']}:{s[0]}:{s[1]} region")
EOF
```

A case reaches a new branch when its footprint holds a generated-source entry that no other case of its packet holds, or an `include/bedrock/protocol` entry that no other case in the suite holds. With every case's `.fp` written, these lines print what is new, and empty output means the case reaches nothing new:

```
comm -23 $D.fp <(cat /dev/null $(ls build/Debug/profiles/<stem>.*.fp | grep -vx $D.fp) | sort -u) | grep /generated/
comm -23 $D.fp <(cat /dev/null $(ls build/Debug/profiles/*.fp | grep -vx $D.fp) | sort -u) | grep /include/bedrock/protocol/
```

| Symptom | Do |
| --- | --- |
| `llvm-cov`: `no coverage data found` | The install stripped the coverage mapping. Reinstall with `-C install.strip=false`. |
| The coverage reinstall ships a wheel with no `_core` | A `CMAKE_CXX_COMPILER` spelled unlike the cached one wipes `build/Debug`'s cache, and the reconfigure loses scikit-build-core's settings. Run the install again. |
| `llvm-profdata` or `llvm-cov`: command not found | Put the LLVM tools of `clang++`'s major version first on `PATH`. |
| `llvm-profdata` rejects the profile's format version | Use the `llvm-profdata` and `llvm-cov` that match `clang++`'s major version. |
| A `default.profraw` appears in the repository root | A pytest ran from the coverage venv without `LLVM_PROFILE_FILE`. Delete the file and rerun with `LLVM_PROFILE_FILE` pointing into the profile directory. |
| `$D.missed` lists an arm, an optional's side, a loop or a check's passing side | Valid data takes it. Add a case that reaches it, with values from the dump. |
