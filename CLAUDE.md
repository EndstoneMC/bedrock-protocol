# bedrock-protocol

A protoc-style codegen for Minecraft Bedrock wire packets. The schema is a Python
DSL under `protocol/` (read statically, never executed) compiled to C++ headers by
the compiler under `src/bedrock_protocol/`. Build with CMake, type-check with
`uv run mypy`, lint with ruff.

## Rules

The project's binding rules live under `.claude/rules/`, grouped into three files and
imported below. Read them before editing the DSL, the compiler, the tests, or the
docs.

@.claude/rules/style.md
@.claude/rules/protocol.md
@.claude/rules/tests.md

## Enforced automatically

`.claude/settings.json` wires `.claude/hooks/check_rules.py` as Pre/PostToolUse hooks
that block, before an edit or commit lands (all five map to `style.md`):

- non-ASCII characters in any edited file
- `from __future__ import annotations` in a `.py` file
- `ruff check` failures on an edited `.py` file
- `//` prose comments emitted from a Jinja template
- a `Co-Authored-By` trailer on `git commit`

Everything else is enforced by review. mypy strict (`uv run mypy`) is the type gate.
Run it before committing.

## Compatibility: former rule numbers

`SPEC.md` and the `add-protocol-version` skill reference the old "CLAUDE.md rule N"
numbering. The map from the old numbers to the rule file that now holds each one:

| Old | Now |
| --- | --- |
| rule 1  | `style.md` (commits) |
| rule 2  | `style.md` (no template comments) |
| rule 3  | `tests.md` (tests as usage examples) |
| rule 4  | `style.md` (keep README minimal) |
| rule 5  | `style.md` (ASCII, no semicolon splices) |
| rule 6  | `style.md` (stream wire API) |
| rule 7  | `protocol.md` (version-gating, sources) |
| rule 8  | `tests.md` (golden round-trip tests) |
| rule 9  | `style.md` (no `from __future__ import annotations`) |
| rule 10 | `protocol.md` (single-field gates) |
| rule 11 | `protocol.md` (docstrings) |
| rule 12 | `protocol.md` (names mirror BDS) |
| rule 13 | `protocol.md` (enum member values) |
