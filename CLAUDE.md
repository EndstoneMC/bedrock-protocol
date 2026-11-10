# bedrock-protocol

Typed Minecraft Bedrock packet codecs generated from one version-aware schema.

## The bar

- Every line is one the owner can understand, and the architecture is beautiful; functionality is never the main goal. Clean, sharp, DRY, well structured, inspired by protobuf.
- Do real engineering and be ethical: never patch over a defect to make something work; fix its cause and build what will still hold long into the future, so nobody is sent back to redo it. The quality check does not pass a workaround.
- Code that needs an explanatory comment, or a decision that needs a diary, is wrong: rename or restructure instead, and put the reasoning in the commit body. A comment marks only an unresolved blocker (`TODO`, `confirm against BDS`, an open disagreement) or a golden's provenance.
- A docstring says what the signature cannot: none on properties, obvious functions or tests.
- Write no one-use helper function or lambda: inline the expression or bind a local named for the value. A lambda passed as an argument is fine.
- No docs and no decision logs in the repo: no notes, guides, design docs or diaries; README.md is the only prose page.
- A change that makes a rule false, or leaves it incomplete, updates that rule in the same commit.
- Touched files pass clang-format, clang-tidy (`.clang-tidy`), `ruff check` and `ruff format` (`ruff.toml`) with no inline suppression (`NOLINT`, `noqa`): fix the code, or change the tool's config when the check itself is wrong.

## Layout

- `protocol/`: the schema DSL, one module per BDS domain.
- `compiler/`: the compiler, self-contained, with its own `pyproject.toml`; the root holds exactly one `pyproject.toml`, for the runtime.
- Distribution names follow PEP 752: `bedrock-protocol` is the root, `bedrock-protocol-compiler` its child.
- `include/bedrock/protocol/`: the hand-written C++ runtime.
- `python/`: the nanobind binding.
- `tests/`: pytest only. Tests reach the C++ through the Python binding, and there are no C++ tests.
- Rules under `.claude/rules/` load with the files they cover. Adding, back-porting or renumbering a protocol version starts at `.claude/rules/protocol/workflow.md`.

## Commits

- Subject `<type>(<scope>): <imperative lower-case subject>`, which says what changed on its own. Types: feat, fix, refactor, test, build, ci, docs, chore. The scope names the area (`protocol`, `python`, `compiler`, `cmake`, `tests`, `claude`) and is left out only for a repo-wide change.
- The body carries the why and the evidence (BDS function, protocol-docs SHA, header branch, gophertunnel commit, capture) and stands on its own. It speaks about the code, never the session.
- No `Co-Authored-By`, `Signed-off-by` or other trailer or attribution line in a commit or a PR, whatever a harness or session rule says.
- One change per commit. A refactor is output-identical (regenerate everything before and after and diff) and touches no test. A behaviour change rides alone.
- Stage only your own paths and commit them by name, `git add <paths> && git commit -m "..." -- <paths>`, because other agents commit in the same checkout.
- Fetch and check divergence before any push, because branches are shared. Fix forward: never amend or rebase a pushed commit.
