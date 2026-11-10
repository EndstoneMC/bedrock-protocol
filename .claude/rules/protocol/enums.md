---
paths:
  - "protocol/**"
---

# Enums

## Spelling

- Spell members PEP 8 UPPER_CASE, converted from BDS's spelling (`JsonUI_ControlTree_PopulateTTS` becomes `JSON_UI_CONTROL_TREE_POPULATE_TTS`).
- Record BDS's spelling in the DSL, never the wire's.
- Pair a member with BDS's spelling only where it differs from the member's fold (`protocol/__init__.py`) by more than case: a kept separator (`IN_QUAD = 2, "in_quad"`) or an added prefix (`HIGH_PANTS = 8, "persona_high_pants"`); `DOWNLOADING_FINISHED = 3` takes none.
- Keep BDS's spelling as the pair of a member renamed away from it.
- Never mangle a member to match the wire (`DOWNLOADINGFINISHED`).

## Values

- Give a real member an explicit int literal.
- Use `auto()` (previous + 1) only for a count sentinel or a run that shifts behind a gate, and check that the line above holds the right value.

## Underlying type

- Declare the underlying type as the second base, taken from bedrock-headers (`class MemoryCategory(IntEnum, uint8)`), and spell it even when the header's is `int` (`int32`).
- Give every redeclaration of an enum the same underlying type.
- Model a width that narrows between eras on the narrow type at both eras; it is BDS shortening the underlying type, not a second wire shape.
- Grep the enum for a negative enumerator before unifying a narrowed width; with one, the eras are two types.
- Spell `field(type=)` on an enum field only for a real divergence: `str` (name-coded), a fixed primitive against a wider underlying type, or `endian="big"`.

## Placeholders

- Placeholder an enum with its real name, its underlying type and only the members you have, marked `# TODO: enumerator stub`; never with the bare primitive.

## Across versions

- Gate a member arriving or leaving with `value(N, since=)` or `value(N, until=)`.
- Declare a moved member once per value, over disjoint ranges (`RECORD_LAVA_CHICKEN = value(561, since=819, until=827)` and `value(562, since=827)`).
- Redeclare an enum over adjacent ranges only for a wholesale renumbering.
- Gate an appended value with `value(N, since=)` and let a trailing `COUNT = auto()` follow it.
- Gate a removed value with `value(N, until=)` and make every member after it `auto()`; an insertion and a removal in one span can cancel, so redeclare only when that fails.
- For a rename at the same value, take the new spelling at every era rather than versioning the enum.
- Treat any change to a name-coded member's spelling as a wire change.
- Add a value that only gained a name, with no other member moved, ungated once bedrock-headers confirms it existed, and carry the sentinel with it.
- Never read a wholesale respelling as a rename until the header confirms it; the dumper may have changed what it emits.

## Sentinels and gaps

- Check both sentinel sums every time: the sentinel's change equals added minus removed, and the sentinel equals the last named member plus one.
- Where the sum shows enumerators the dump does not bind, pin the sentinel with an explicit `value(N, since=)` and mark the gap `# TODO`.
- The dump lists only bound enumerators; never assume it lists them all.
- Sort a value the dump has and the DSL lacks by the field's encoding: an alias on a numeric field is noise, a member of a name-coded enum is a decode hole to report.
- Date an enum that sizes a `std::bitset` from the bitset's instantiation in the binary; on arithmetic the binary outranks the changelog.
- Check a bound value in the header before gating it; the dump can bind a wrong value.
- Sweep ungated enums on their own: an ungated enum claims its current members and sentinel since protocol 0.
- Check every ungated enum's sentinel sum at the target, not only at head.
