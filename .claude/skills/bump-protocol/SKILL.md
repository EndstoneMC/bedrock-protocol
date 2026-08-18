---
name: bump-protocol
description: Model a new rolling preview network version in the schema - establish the number, diff the protocol-docs dumps, renumber the superseded preview's gates onto it, and model the wire changes it added. Use when a new BDS preview dump lands or the schema should follow it ("add 2192 support", "bump the protocol to the latest preview", "follow 1.26.50.x to protocol N", "model the new network version").
---

# Model a new preview protocol version

The preview channel renumbers the network version repeatedly inside one update:
r26_u5 went 2171 → 2177 → 2181 → 2187 → 2192 before the release shipped.

**One protocol per update line.** A newer preview *replaces* the older number;
it never becomes a second snapshot beside it. Nobody runs a superseded preview,
so a roll is a wholesale renumber of that era's gates plus the wire changes the
new dump added.

`~/endweave` consumes this schema. After landing here, roll it too - its
`add-protocol` skill covers that half and is the other end of this
one.

---

## 1. Establish the number, and never take it on trust

A number in the request may not exist. Check before modelling anything:

```shell
git -C ~/protocol-docs ls-remote --heads origin        # which update branches exist
git -C ~/protocol-docs fetch origin
git -C ~/protocol-docs show origin/<branch>:README.md  # build + network version
git -C ~/protocol-docs log --oneline origin/<branch>   # one commit per dump
```

The branch README names the **Minecraft build** and the **network version** its
dump came from. Cross-check against
`https://raw.githubusercontent.com/EndstoneMC/bedrock-server-data/v2/versions.json`
(per-channel latest) and minecraft.wiki's *Protocol version* page. A number that
appears in none of them does not exist - stop and ask which version is meant
rather than modelling a guess.

Record the *build*, not just the number: a protocol number does not identify a
wire format (1.26.43 and 1.26.44 both say 2168 and disagree on the wire).

## 2. Diff the dumps - that is the whole evidence

```shell
git -C ~/protocol-docs diff --stat <old-dump-sha> <new-dump-sha>
git -C ~/protocol-docs diff <old-dump-sha> <new-dump-sha>
```

Read `origin/<branch>` shas, never a local checkout - a stale branch reads as a
real finding. Classify every hunk:

- **A field added, removed or moved** - a wire change. Model it.
- **A `constraints` block appearing or vanishing** (`min_length`, `enum_values`,
  `minimum`/`maximum`, `description`) - **not wire**. Whole sweeps of these come
  and go between builds; ignore them.
- **An enum gaining members** - suspect first. Check `~/bedrock-headers` on the
  newest branch that carries the type: if the header already has the members,
  the dump's *binding* changed rather than BDS, and gating them at the new
  version would be wrong. `SharedTypes::persona::PieceType` is the standing case
  - `Unknown` and `Unsupported` appeared in the 2192 dump and had been in the
  r26_u4 header all along (still an open gap in the schema).
- **A new enum or type** - take its C++ spelling from bedrock-headers
  (`HandSlot` is in `world/item/EquipmentSlot.h`), not from the dump's casing.

The dump only describes cerealised packets, so a packet missing from it is not
"removed" - check the id list before concluding anything.

## 3. Renumber, then model

```shell
sed -i 's/\b<old>\b/<new>/g' protocol/*.py
sed -i 's/\b<old>\b/<new>/g; s/V<old>/V<new>/g; s/v<old>/v<new>/g' tests/*.cpp
```

Then, by hand:

- `protocol/__init__.py` - `__version__ = <new>`. It is the latest-alias source
  for every generated header, and nothing else sets the version.
- Model the new deltas. Pick the tool by the *kind* of change: `field(since=)` /
  `field(until=)` for a field simply added or dropped; a whole-class
  redeclaration (`@packet(id=N, until=X)` + `@packet(id=N, since=X)`, same for
  `@type`) for any change to a field's *type*. See CLAUDE.md.
- A gate must land on a modelled snapshot - the new number, never a changelog
  one.
- A new module-scope enum goes in the module that uses it, `UPPER_CASE` members,
  `COUNT = auto()` where BDS has a count sentinel.
- `README.md` - the "Modelled today" line.

Sanity-check the renumber: `grep -rn "<old>" protocol/ tests/ README.md` must
come back empty.

## 4. Tests

Add a case per wire change to the file that owns the packet
(`tests/test_{id:03}_{name}.cpp`), never a new file.

gophertunnel stops at 2168, so **there is no golden above it**. Assert
structurally against the previous era instead:

```cpp
// No golden -- gophertunnel stops at 2168 -- so the <prev> body is the reference.
REQUIRE(encode(newer).size() == encode(older).size() + 1);
REQUIRE(decode<Newer>(encode(newer)).new_field == ...);
```

Where the delta against the previous era mixes several changes at once, say so
in the comment and pin the new field a second way - two bodies differing only in
that field must differ in exactly one byte.

```shell
cmake --build build-libcxx -j8 && ctest --test-dir build-libcxx
```

The suite needs libc++ (configure once with `-DCMAKE_CXX_FLAGS=-stdlib=libc++
-DCMAKE_EXE_LINKER_FLAGS=-stdlib=libc++`). Compiler tests:
`uv run python -m unittest discover -s tests/compiler -t tests/compiler` - it
carries pre-existing failures, so compare against a clean
`git worktree add /tmp/bp-head HEAD` run before blaming the roll.

## 5. Land it

`git fetch` and check `git rev-list --left-right --count origin/main...HEAD`
before pushing - other agents share this branch. Stage your own paths, never
`git add -A` (`build-libcxx/` is untracked and stays that way). Author is
`Vincent <magicdroidx@gmail.com>`; no `Co-Authored-By` line.

Message shape - what the update did, not what you edited:

```
feat(protocol): follow <build> to protocol <new>

<old> is preview .NN's number and .MM supersedes it, so every gate it carried is
renumbered rather than kept beside a new one.

<the wire changes, and where the evidence for each came from>
```

Then roll `~/endweave` - a rename here is a compile error there.

## Gotchas

- **Bumping `__version__` alone regenerates nothing** unless
  `protocol/__init__.py` is in the codegen `DEPENDENCIES` in `CMakeLists.txt` -
  the `/_*.py` filter keeps it out of `INPUTS`. Wired up 2026-08-18; if a roll's
  latest aliases look stale, check that first.
- **`\b<old>\b` does not match inside `v<old>`** (no word boundary after a
  letter), so namespace spellings survive a naive sed. Grep for the bare number
  *and* `v<number>`.
- **A new field versions its containers transitively.** One field on
  `ItemUseInventoryTransaction` re-emitted `TransactionData`,
  `InventoryTransactionPacket`, `PackedItemUseLegacyInventoryTransaction` and
  `PlayerAuthInputPacket` at the new snapshot. That is the cost endweave then
  pays in transforms; it is not a reason to fold the change into an existing
  snapshot.
