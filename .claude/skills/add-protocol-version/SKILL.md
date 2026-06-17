---
name: add-protocol-version
description: Adds a new Minecraft Bedrock protocol version to the DSL. Use when bumping `protocol/__init__.py`'s `__version__` to a newer protocol, or when reconciling fields added, removed, or reshaped by Mojang in a specific release. DSL-only edits; raise if the change needs compiler work.
---

# Add a new Bedrock protocol version

A protocol bump is a pure DSL edit. The compiler under
`src/bedrock_protocol/` is **out of scope** for this workflow. If a
change demands new DSL primitives, new compiler features, or a new IR
node, **stop and raise it** instead of editing the compiler in passing.

The output of running this skill is a single coherent commit: every
field, enum value, and packet that changed between the previous
`__version__` and the new one is gated through `since=` / `until=` /
`deprecated=`, every new packet is added with `@packet(..., since=N)`
and a gophertunnel-generated golden test, and the final line of the
diff bumps `__version__` in `protocol/__init__.py`.

## Sources of truth — read in this order

The skill exists because Mojang publishes no canonical changelog and
the community references disagree. Resolve the wire shape of every
edit by walking these sources in order and stopping at the first that
confirms the change against a second:

### Primary (drives the diff)

1. **`EndstoneMC/protocol-docs`** -- the dumped JSON / HTML schema.
   The most accurate and complete picture of the **current** wire
   layout for the snapshot it was dumped from. Compare branches with
   a two-dot git diff:
   `git diff <old-branch>..<new-branch> -- serialized/`
   This is where the bulk of additions and shape changes surface
   field-by-field.

2. **`CloudburstMC/Nukkit`** -- treat as a protocol-only reference.
   The server itself is effectively dead, but the project is kept
   alive specifically to mirror Mojang's wire changes. The bedrock
   adapter modules show the same updates Endstone's dump captures,
   often with clearer commit messages.

### Cross-validation (don't trust either source alone)

3. **`CloudburstMC/Protocol`** -- the standalone protocol library.
   Has per-protocol-version serializers
   (`bedrock-codec/.../bedrock/codec/vNNN/serializer/<Packet>Serializer_vNNN.java`).
   Useful for confirming when a field first appeared, but the library
   is **not used in production** for any active server, so its codecs
   for the newest versions can lag, drift, or be incorrect.

4. **`Sandertv/gophertunnel`** -- Go protocol library used in
   production proxies. Generally safer because real traffic exercises
   it, but the project's update cadence is slower: the latest
   protocol bumps land here last and the diff between current schema
   and the snapshot we're targeting is often incomplete.

### Watch for in-progress work

Both Cloudburst and gophertunnel often land a new protocol on a
feature branch or open PR before merging to default:

- `git ls-remote --heads https://github.com/CloudburstMC/Protocol | grep -iE "v?<NEW>|bds-<NEW>|<release>"`
- `gh pr list --repo Sandertv/gophertunnel --state open --search "<NEW>"`
- Same for `CloudburstMC/Nukkit`, `EndstoneMC/protocol-docs`.

If `master`/`main` looks empty for the version you're bumping to,
look for a branch or PR before concluding the change isn't modelled
yet. WIP material counts as a source, but flag in commit messages
that it came from a branch and may shift before merge.

### Disagreement is a stop sign, not a vote

When the four sources disagree about a field's name, type, presence,
or wire position, do not pick one. Pause and surface the discrepancy
to the user. This rule is identical to CLAUDE.md rule 7: the
protocol-docs JSON is mechanically dumped and is sometimes wrong, but
silently overriding it with gophertunnel or CloudburstMC just buries
the conflict.

## What the DSL diff looks like

The DSL surface admits exactly five kinds of edit. Anything that
doesn't fit one of these is a stop-and-raise.

### 1. New field on an existing struct

A field that appears at version N on a struct that already existed:

```python
class FooPacket:
    existing: varint32
    new_thing: uint8 = field(since=NEW)
```

Optional and `T | None` forms work the same way; the `since=` goes on
the `field(...)` call.

### 2. Removed field on an existing struct

A field present until version N-1 and absent from N onward gets
`until=NEW`:

```python
class FooPacket:
    going_away: str = field(until=NEW)
    still_here: int32
```

The half-open convention means `until=NEW` reads "present in
[..., NEW)", absent at NEW and later.

### 3. Field whose shape changed at version N

Re-declare the field with adjacent ranges. The pair below models a
field that was a `uint32` until NEW and a length-prefixed string from
NEW onward:

```python
class FooPacket:
    icon: uint32 = field(until=NEW)
    icon: str = field(since=NEW)
```

A pure type change works the same way; a rename is **not** the same
thing -- a name change with the same wire shape is just a rename,
not a versioned redeclaration.

### 4. New enum member

Most new enum members are non-trailing. Use `value(N, since=NEW)`
where `N` is the explicit wire number (auto-numbering won't survive
later edits to siblings; CLAUDE.md rule 13):

```python
class DisconnectFailReason(IntEnum):
    UNKNOWN = 0
    ...
    NEW_REASON = value(207, since=NEW)
```

If a member is removed, mirror it with `value(N, until=NEW)`. If
Mojang annotated it deprecated rather than removed, use
`value(N, deprecated=NEW)` -- the value stays on the wire but C++
flags new uses with `-Wdeprecated-declarations`.

### 5. New packet

A wholly new packet:

```python
@packet(id=<id>, since=NEW)
class NewThingPacket:
    """<Description from Mojang/bedrock-protocol-docs verbatim>"""

    field_a: varint32
    field_b: str
```

Every new packet needs a golden round-trip test (`tests/test_<group>.cpp`)
generated by gophertunnel. CLAUDE.md rule 8 is non-negotiable:

- Never hand-compute the golden bytes.
- Precede with `// generated by gophertunnel:` plus the marshalled
  `packet.NewThing{...}` literal.
- If gophertunnel doesn't model the packet yet -- which is likely on
  the freshest protocols -- **stop and raise**. Do not invent a
  golden, even by reading `Marshal`.

### Stop and raise — do not edit silently

Pause for the user when:

- A packet is **removed** at version NEW. The DSL today can't gate a
  packet definition with a lone `until=` (see the `ExplodePacket`
  note in `protocol/level.py`).
- A struct is **renamed**, or a field rename collides with another
  field's history. The DSL has no rename primitive.
- A new field uses a wire shape the DSL doesn't model (a packed
  bitfield that isn't a `bitset[N]`, a non-prefixed list whose count
  doesn't reduce to a `count=lambda` expression over earlier fields,
  a discriminator type the union machinery can't express).
- Sources disagree about the change in a way two of the four can't
  resolve.
- gophertunnel doesn't model a new packet, so its golden can't be
  generated. Don't invent the bytes.
- A change clearly needs new compiler IR, a new template, or a new
  primitive. The compiler is off-limits for this skill.

In every "raise" case, surface the conflict or limitation and the
specific blocking material (file path, field, references checked).
Don't pre-decide for the user; the spec lists "Ask first about" for
exactly this reason.

## Workflow

### A. Lock in the scope

1. Read the previous `__version__` from
   [protocol/__init__.py](protocol/__init__.py).
2. Decide the new version N. Verify N is not below 292 (CLAUDE.md
   rule 7 floor) -- the floor doesn't apply to new bumps in practice,
   but a typo that lands you at 291 or below should be caught.
3. Note that the bump should be the **last** edit in the diff. Do
   not bump `__version__` until every gated change is in place.

### B. Survey the diff at the source

4. Pull or refresh local clones of all four reference repos.
5. Run `git diff` on EndstoneMC/protocol-docs between the branch
   tagged for the old version and the branch for N. Read every
   touched packet file.
6. For each touched packet, cross-check the same packet in:
   - `CloudburstMC/Nukkit` (bedrock-codec or equivalent)
   - `CloudburstMC/Protocol` (`v<N>` serializer if present, else
     latest)
   - `Sandertv/gophertunnel` (`minecraft/protocol/packet/<name>.go`
     and `git log -S<field>` for dating)

   Look at open branches and PRs in each repo before concluding a
   reference is silent.

7. Produce a flat list, one row per change:
   `<packet>::<field> | <kind: add|remove|reshape|enum-add|...> | <sources confirming>`.
   Keep this list in the working notes for the commit; you'll cite
   it in the commit body.

### C. Apply DSL edits, one file at a time

8. For each affected `protocol/<group>.py`, apply the edits from
   section 4 above. Keep the existing file's idiom -- if siblings
   gate with `field(since=N)` rather than a block, do the same.
9. For nested types, gate on the outermost type that reflects the
   change. A nested struct whose only edit is one added field
   gates the field, not the whole nested type.
10. For new packets, also:
    - Carry the Description from `Mojang/bedrock-protocol-docs`
      verbatim as the docstring (CLAUDE.md rule 11). If the upstream
      has no Description, omit the docstring entirely.
    - Resolve every new name through the bedrock-headers /
      protocol-docs / `.dot` files hierarchy (CLAUDE.md rule 12).
      Add `# TODO: confirm against BDS` where appropriate.

### D. Write the gophertunnel-driven golden tests

11. For every **new** packet added in step C, write a test under
    `tests/test_<group>.cpp` and register the file in
    `tests/CMakeLists.txt` if it's new.
12. Generate the golden bytes by marshalling the equivalent packet
    in `Sandertv/gophertunnel` (CLAUDE.md rule 8). If gophertunnel
    doesn't have the packet on `master` or any visible branch/PR,
    stop and raise.
13. For shape changes on existing packets, add or extend a test
    asserting both pre- and post-NEW round-trips against
    gophertunnel goldens.

### E. Bump `__version__` and verify

14. Edit [protocol/__init__.py](protocol/__init__.py): change
    `__version__ = <OLD>` to `__version__ = NEW`. This is the
    last code edit in the change.
15. Rebuild and run the suite:
    ```sh
    cmake --build build
    ctest --test-dir build --output-on-failure
    ```
16. Any new failure is either:
    - a missed gate (a field still emitted at the wrong snapshot),
      or
    - a compiler limitation -- in which case **stop, revert the
      `__version__` bump, and raise**. The compiler stays untouched.

### F. Commit

17. Commit on `main` (per memory: this repo commits to main).
18. Body should cite the per-row change list from step 7 and name
    each upstream source that confirmed each row, so a reviewer can
    audit without re-walking the four repos. No
    `Co-Authored-By: Claude ...` line (CLAUDE.md rule 1).

## Quick reference

| Change | DSL form |
| --- | --- |
| New field | `name: T = field(since=NEW)` |
| Removed field | `name: T = field(until=NEW)` |
| Reshaped field | re-declare twice, `until=NEW` then `since=NEW` |
| New enum value | `MEMBER = value(N, since=NEW)` |
| Removed enum value | `MEMBER = value(N, until=NEW)` |
| Deprecated enum value | `MEMBER = value(N, deprecated=NEW)` |
| New packet | `@packet(id=I, since=NEW)` + golden test |
| Removed packet | **raise** (no lone `@packet(until=)`) |
| Rename | **raise** (no rename primitive) |
| Wire shape DSL can't express | **raise** (no compiler edits) |
