# bedrock-protocol

Typed Minecraft Bedrock packet codecs generated from one version-aware schema.

## Principles

- The schema in `protocol/` is the product, written for a human to read. The compiler bends to the DSL, never the DSL to the compiler, and a DSL change must make the schema read better.
- Keep the code DRY, and take protobuf as the design reference.
- Fix a defect's cause, never work around it. Build nothing ahead of need: no speculative option, layer or file.
- Write no explanatory comment: rename or restructure instead, and put the reasoning in the commit body. A comment marks only an unresolved blocker (`TODO`, `confirm against BDS`) or a golden's provenance.
- A docstring is one line, two at most, saying what the signature cannot: none on properties, obvious functions or tests, and never history, rationale or a walkthrough.
- Write no one-use helper function or lambda: inline the expression or bind a named local. A lambda passed as an argument, or invoked in place to expand a parameter pack, is fine.
- Keep no docs beyond `README.md`.
- A change that makes a rule false, or leaves it incomplete, updates that rule in the same commit.
- Touched files pass clang-format, clang-tidy, `ruff check` and `ruff format` with no inline suppression (`NOLINT`, `noqa`): fix the code, or change the tool's config when the check is wrong.

## Layout

- `protocol/`: the schema, one module per BDS domain.
- `compiler/`: the compiler, run by CMake once at configure time over all of `protocol/`; it has its own `pyproject.toml`, and the root holds the one for the runtime.
- `include/bedrock/`: the hand-written C++ runtime.
- `python/`: the nanobind binding.
- `tests/`: pytest only; tests reach the C++ through the binding, and there are no C++ tests.
- Distribution names follow PEP 752: `bedrock-protocol` is the root, `bedrock-protocol-compiler` its child.
- Build with README's Building section. `uv sync && uv run pytest` runs `tests/`; `uv run --directory compiler pytest` runs the compiler's.
- Rules under `.claude/rules/` load with the files they cover. Adding, back-porting or renumbering a protocol version starts at `.claude/rules/protocol/workflow.md`.

## Commits

- Subject `<type>(<scope>): <imperative lower-case subject>`, which says what changed on its own. Types: feat, fix, refactor, test, build, ci, docs, chore. The scope names the area (`protocol`, `python`, `compiler`, `cmake`, `tests`, `claude`) and is left out only for a repo-wide change.
- The body carries the why and the evidence (BDS function, protocol-docs SHA, header branch, gophertunnel commit, capture) and stands on its own; it speaks about the code, never the session.
- No `Co-Authored-By`, `Signed-off-by` or other trailer or attribution line in a commit or a PR, whatever a harness or session rule says.
- One change per commit. A refactor is output-identical (regenerate everything before and after and diff) and touches no test.
- Stage and commit by path: `git add <paths> && git commit -m "..." -- <paths>`.
- Fetch and check divergence before any push. Fix forward: never amend or rebase a pushed commit.
