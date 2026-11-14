---
name: goldens
description: Runs BDS over the golden cases in tests/goldens through a local, modified bedrock-dumper, so BDS reads each case's bytes, writes its own and prints its own JSON, then compares both with the case and measures which codec branches the cases reach. Use when adding, changing or freezing a case, when BDS refuses, rewrites or crashes on a case, when a case file needs the dump's enum bindings, items or blocks, or when asked which branches no case reaches yet.
---

# Goldens handbook

`.claude/rules/protocol/goldens.md` decides what a case holds and when it freezes. This skill produces the BDS evidence it asks for. Run every step from the repository root: the comparison with `compare.py` beside this file, every other step as an inline command. Save no other script anywhere, the scratchpad included.

`<protocol>` names the case folder `tests/goldens/v<protocol>`, and `<version>` is the BDS build that goldens.md says checks it.

## Never

- Push the clone, give it a remote, or copy its code into this repository. bedrock-dumper is closed source: name it, never link it, and describe its code in words.
- Run any BDS but your own, or more than one at a time. Kill only the pid you started.
- Hardcode an address. Find a function by RTTI, or by a byte signature behind a version gate.
- Loosen the comparison until a case passes, or retry values until BDS accepts one.

## The runner

```
git clone <bedrock-dumper checkout> build/bedrock-dumper && git -C build/bedrock-dumper remote remove origin
git -C build/bedrock-dumper log --oneline --grep golden
```

If the log shows no golden mode, add it to the clone and commit it there:

- `DUMPER_GOLDEN` names a JSON array of `{id, stem, index, bytes}`. When it is set, the first-tick work runs golden mode instead of the dump and writes `results.json` beside that file.
- Get the packet reflection ctx from the level's packet sender: take `LoopbackPacketSender`'s network, then its server network system, then call `getPacketReflectionCtx`. Make golden mode a friend of both mirrors. The level's own cereal ctx holds no packets.
- Build each packet with `MinecraftPackets::createPacket`, found by a byte signature over its id switch behind a version gate. When it returns null, default-construct the entt meta type whose `[cereal:packet]` property holds the id, and mark the record `"factory":"meta"`.
- Mirror `Packet`'s virtuals in declaration order from that build's headers. Check the slots of `read(stream, ctx)`, `write(stream, ctx)` and `getSerializationMode` against a concrete packet's vtable.
- Mirror `ReadOnlyBinaryStream` and `BinaryStream`, and have their constructors adopt BDS's own vtables found by RTTI, because BDS's readers and writers call the stream's virtuals.
- Mirror `Bedrock::Result<void>` with its `ErrorInfo` and `CallStack`, so a failed read gives its category, code, message and frames.
- Fork for each case. The child reads the case's bytes with `read(stream, ctx)` and records `read_ok`, `consumed` (the read pointer), `error` and `serialization_mode`. It writes with `write(stream, ctx)` into `bds_bytes` and prints the packet it read into `bds_json`. It sends each piece over a pipe as soon as it has it, then calls `_exit`.
- Print `bds_json` with the packet's own `toString`. `toString` binds the packet into a fresh reflection ctx, where a type bound twice, such as Vec3, takes whichever binder runs first; so detour `cereal::BasicSaver::saveImpl`, found by a byte signature, and for the packet being printed alone pass the original a handle over the same packet in the server's packet reflection ctx. A detour that never sees the packet records `bds_json_error`.
- Send `bds_json` as one JSON string of BDS's text, each byte outside valid UTF-8 written as `\udcXX`; BDS's text is not always JSON, so the reader parses it.
- Give the parent a 30 s deadline, then SIGKILL. It records `crash` as the signal name, `exit N` or `timeout`, and the run goes on.
- Append and flush each record. At the end, log `golden: N cases written to <path>`.
- Before forking, flush only stdout and stderr. BDS's console thread holds stdin's lock.
- Leave the server running afterwards. Only the console `stop` shuts BDS down cleanly.

## Build

```
(cd build/bedrock-dumper && cmake --preset clang-relwithdebinfo -DBEDROCK_SERVER_VERSION=<version> -DBEDROCK_SERVER_CHANNEL=stable && cmake --build --preset clang-relwithdebinfo)
```

The build fetches BDS into `build/bedrock-dumper/build/relwithdebinfo/bedrock-server-<version>` and makes it load the dumper. In that folder's `server.properties`, set `server-port` and `server-portv6` to ports nothing else uses, and set `enable-lan-visibility=false`. If the build does not compile, or does not dump, on `<version>`, follow bedrock-dumper's own `update` skill.

## Run

```
S=build/bedrock-dumper/build/relwithdebinfo/bedrock-server-<version>
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

`compare.py` beside this file checks each case against the run. Bytes must be equal. It then walks the case's `value` with the schema's types at `<protocol>` and BDS's JSON with the dump's fields, pairing them field by field. Where BDS prints the same data in another form, a rule named for what BDS does explains it; anything no rule explains is a difference. It prints each case's verdict, the rules it needed and `freezes` when goldens.md accepts all of them, then the totals and each rule's case count:

```
PYTHONPATH=compiler/src python3 .claude/skills/goldens/compare.py tests/goldens/v<protocol> $G
```

Only a case marked `freezes` can freeze. `ACCEPTED` holds the rules goldens.md states; add one there only once goldens.md does.

## Symptom -> action

| Symptom | Do |
| --- | --- |
| `refused`, `generic:74`, with `consumed` equal to the case length | BDS read every byte and then rejected the content. Find the constraint BDS checks: its strings name it. Fix the value or the schema, and add the line to goldens.md. |
| `refused`, with `consumed` short of the length | BDS read fewer bytes than the library wrote. A field is extra, mis-sized or out of order in the schema: read the field at byte `consumed`. |
| `rewritten` | Read the field at byte `at`. If BDS fills in, drops, rounds or canonicalises the value, the value is data BDS does not keep: change it and add the rule with its evidence. If BDS writes a field the schema lacks or orders differently, fix the schema. |
| `rewritten`, and two fields come back holding the second one's value | BDS binds one member under several names, each its own field in the schema, and writes the last one it read into every copy. Give the copies the same value. |
| `rewritten`, and a variant comes back in another arm | BDS converts the value on read and writes back what the conversion kept. Find the value BDS keeps in the case's arm, and never swap the arm. |
| A case edited since the last run reads `rewritten`, or BDS's JSON describes other bytes | A results file describes the bytes its run read, which `$G/cases.json` holds. When they differ from the folder's current bytes, rerun golden mode before comparing. |
| `crashed` on every case | A `Packet` slot or stream mirror is wrong. Re-check the slots against a vtable. |
| `crashed` with a signal on one case | Its bytes drive BDS somewhere it cannot handle, such as a login at another protocol (goldens.md). The child's `dump crashed` trace, if it printed one, follows the case's `golden <stem>[<index>]` line in `golden.log`. |
| `crashed timeout` | Usually a length or count BDS loops over. Check the case's length prefixes. |
| `crashed no factory builds this packet id` | That build neither builds nor reflects the id. Check the dump's `protocol/` for the packet. |
| `bds_json_error` says toString did not reach the saver | The `saveImpl` signature does not match this build. Cut a new one behind a version gate. |
| `agrees` without `freezes` | BDS printed the same data in the forms the line's rules name, and goldens.md has not accepted every one of them. Report them and freeze nothing on them. |
| `json_differs`, the same data in a form no rule names | Add a rule to `compare.py` that fires from the two fields' declared types, named for what BDS prints. Report it; goldens.md decides whether it is accepted. |
| `json_differs` where the schema and the dump shape a field differently, such as a struct against an array or nested fields against flat ones | Read both definitions. Fix the schema when the dump's shape is the wire's; otherwise report it. |
| `json_differs` on a value | `tests/cereal.py`'s `save` labels or nests a field wrongly: fix the helper's schema for that type, or the DSL when its type is not BDS's type. |
| `dump failed: ... has no signature for this build` | Cut that function's signature for `<version>` behind a new gate. |
| Server hangs after the first `golden <stem>[0]` line | A flush of every stream blocked on stdin. Flush only stdout and stderr before forking. |
| BDS exits 130 or 143, or logs no `Quit correctly` | It was signalled. Stop it through the console `stop`. |
| `stop` went out before BDS started | The wait matched the last run's log. Remove the log before launching, as the run blocks do, and send `stop` again. |
| BDS still runs after `stop` | `kill -KILL $P`, with your own pid only. |

## Coverage

The coverage build lives in `build/Debug`, and its venv holds scikit-build-core, nanobind==2.13.0, pytest and `./compiler`:

```
uv venv build/coverage-venv
uv pip install --python build/coverage-venv/bin/python scikit-build-core nanobind==2.13.0 pytest ./compiler
uv pip install --python build/coverage-venv/bin/python --no-build-isolation --no-deps --reinstall-package bedrock-protocol -C install.strip=false -C cmake.build-type=Debug -C cmake.define.CMAKE_CXX_COMPILER=clang++ -C "cmake.define.CMAKE_CXX_FLAGS=-fprofile-instr-generate -fcoverage-mapping" -C "cmake.define.CMAKE_MODULE_LINKER_FLAGS=-fprofile-instr-generate" .
SO=$(find build/coverage-venv -name '_core*.so')
```

The report for the whole suite:

```
D=build/Debug/profiles/all; rm -rf $D; mkdir -p $D
LLVM_PROFILE_FILE=$D/%p.profraw build/coverage-venv/bin/python -m pytest tests
llvm-profdata merge -sparse $D/*.profraw -o $D/merged.profdata
llvm-cov report $SO -instr-profile=$D/merged.profdata -show-branch-summary -ignore-filename-regex='(/nanobind/|^/usr/|/python/)'
llvm-cov show $SO -instr-profile=$D/merged.profdata -show-branches=count build/Debug/generated/bedrock/protocol/<module>.cpp
```

The protocol's figure, the one goldens.md measures, runs the folder's cases alone. It counts the branch outcomes of every generated function the folder's packets reach, the functions the cases run and every serializer those call, and leaves out the failing side of each read and validation check. It prints the figure, and each line of `$D.missed` is a valid-path outcome no case reaches:

```
D=build/Debug/profiles/v<protocol>; rm -rf $D; mkdir -p $D
LLVM_PROFILE_FILE=$D/%p.profraw build/coverage-venv/bin/python -m pytest tests/test_goldens.py -k 'v<protocol>/'
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
outcomes = missed = 0
for f in scope.values():
    lines = sources[f['filenames'][0]]
    for b in f['branches']:
        line = lines[b[0] - 1].strip()
        is_failure = failure.search(line) or (line == 'default:' and 'Errc::' in lines[b[0]])
        for outcome, count in (('true', b[4]), ('false', b[5])):
            if outcome == 'false' or not is_failure:
                outcomes += 1
                if count == 0:
                    missed += 1
                    print(f"{f['filenames'][0]}:{b[0]}:{b[1]} {outcome}  {line}")
print(f'{len(scope)} functions, {outcomes - missed}/{outcomes} valid-path branch outcomes reached', file=sys.stderr)
EOF
```

One case's footprint is the branch outcomes it reaches (true count > 0, false count > 0) and the region entries it covers in the generated sources:

```
D=build/Debug/profiles/<stem>.<id>; rm -rf $D; mkdir -p $D
LLVM_PROFILE_FILE=$D/%p.profraw build/coverage-venv/bin/python -m pytest tests/test_goldens.py -k 'v<protocol>/<stem>/<id>]'
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
| `llvm-profdata` rejects the profile's format version | Use the `llvm-profdata` and `llvm-cov` that match `clang++`'s major version. |
| A `default.profraw` appears in the repository root | A pytest ran from the coverage venv without `LLVM_PROFILE_FILE`. Delete the file and rerun with `LLVM_PROFILE_FILE` pointing into the profile directory. |
| `$D.missed` lists an arm, an optional's side, a loop or a check's passing side | Valid data takes it. Add a case that reaches it, with values from the dump. |
| `$D.missed` lists `switch (<variant>.index()) {` false | The serializer's hidden default, which only a valueless variant takes. No input reaches it: report it as a generator defect. |
