# bedrock-protocol

Typed Minecraft Bedrock packet codecs generated from one version-aware schema.

## Principles

- The schema in `protocol/` is the product, written for a human to read. The compiler bends to the DSL, never the DSL to the compiler, and a DSL change must make the schema read better.
- Hardcode no packet, type, field or version outside `protocol/`: the compiler, the runtime, the binding and the test helpers hold no table, set or branch keyed by one, and derive every behaviour from what the DSL declares.
- Keep the schema and hand-written code DRY, and take protobuf as the design reference; generated code may repeat itself.
- Fix a defect's cause, never work around it. Build nothing ahead of need: no speculative option, layer or file.
- Do exactly what was asked from the code as it stands; report anything else found instead of fixing it.
- A failing check has found a defect: fix what it found, never loosen the check (ignore order, widen a match, drop a case) until it passes.
- Write no explanatory comment: rename or restructure instead, and put the reasoning in the commit body. A comment marks only an unresolved blocker (`TODO`, `confirm against BDS`) or a golden's provenance.
- A docstring is one line, two at most, saying what the signature cannot: none on properties, obvious functions or tests, and never history, rationale or a walkthrough.
- Write no one-use helper function or lambda: inline the expression or bind a named local. A lambda passed as an argument, or invoked in place to expand a parameter pack, is fine.
- Never write "wire" in a rule, comment, name or message: say "encoding".
- Keep no docs beyond a `README.md` at the root and in `compiler/`, `go/`, `java/`, `protocol/`, `python/` and `tests/goldens/`, each saying only what its part is and holds, and none repeating another.
- A change that makes a rule false, or leaves it incomplete, updates that rule in the same commit.
- Write a rule as one short final-state line, once, in the file whose `paths:` govern it or here when repo-wide, and point to it from elsewhere; no rationale, history or dates.
- Write a skill as a team handbook, symptom -> action, with nothing about one machine or one person.
- Touched files pass clang-format, clang-tidy, google-java-format (hand-written Java), `gofmt` and `go vet` (hand-written Go), `ruff check` and `ruff format` with no inline suppression (`NOLINT`, `noqa`): fix the code, or change the tool's config when the check is wrong.

## Layout

- C++ is the privileged language: `include/` and the C++ the compiler emits are the source, Python is a binding over it, and the Java and the Go the compiler emits run on the pure-Java runtime in `java/` and the pure-Go runtime in `go/` and encode the same bytes.
- `protocol/`: the schema, one module per BDS domain.
- `compiler/`: the compiler, run over all of `protocol/` by CMake once at configure time for the C++, by Gradle for the Java and by `go generate` for the Go; it has its own `pyproject.toml`, and the root holds the one for the runtime.
- Never commit generated code.
- `include/bedrock/`: the hand-written C++ runtime.
- `python/`: the nanobind binding, laid out and named after nanobind's and pybind11's official examples and large projects; `bedrock_protocol.v<N>` holds protocol N's codec and the classes it introduced that the latest protocol lacks, and the bare package declares the latest protocol's classes and re-exports the latest `v<N>`'s `encode` and `decode`; its stubs are generated at build time by `python/stubgen.py` with `python/stubgen.pat`.
- `tests/`: pytest, reaching the C++ through the binding; `tests/package/` is CI's `find_package` consumer, its `enum.cpp` holds the static_asserts of the per-protocol enum API, and its `registry.cpp` those of `packet_of` over `packets_fwd.hpp` alone.
- `java/`: the Gradle build of the hand-written Java runtime and the generated Java codecs; it builds into `build/java`.
- `go/`: the Go module of the hand-written Go runtime, with the generated Go codecs written beside it in `go/protocol`.
- Distribution names follow PEP 752: `bedrock-protocol` is the root, `bedrock-protocol-compiler` its child.
- `CMakeLists.txt`'s `project()` VERSION is the only version: a build at its `v<version>` tag is `<version>` in C++, Python and Java, and any other is `<version>.dev0` in Python through `python/version.py` and `<version>-SNAPSHOT` in Java; the Go module carries no version and builds from a checkout. It names the next release: push its tag to release, then bump it.
- Build with README's Building from Source section. `uv sync && uv run pytest` runs `tests/`; `uv run --directory compiler pytest` runs the compiler's.
- `uv run --directory compiler mypy` type-checks the compiler as CI does, re-syncing the compiler's dev group that another sync of the shared `.venv` can drop.
- `build/Release` is shared by `uv sync` and the `release` preset, and `build/Debug` by the `debug` preset and the coverage build; nothing else gets a tree except `build/java`, `build/bedrock-dumper` and the like.
- Keep the C++ and Python build plain CMake, with no Conan recipe; Java builds with Gradle in `java/`, and Go with the go tool in `go/`.
- Rules under `.claude/rules/` load with the files they cover. Adding, back-porting or renumbering a protocol version starts at `.claude/rules/protocol/workflow.md`.

## Commits

- Subject `<type>(<scope>): <imperative lower-case subject>`, which says what changed on its own. Types: feat, fix, refactor, style, test, build, ci, docs, chore, revert. The scope names the area (`protocol`, `python`, `compiler`, `cmake`, `build`, `ci`, `java`, `go`, `include`, `scripts`, `readme`, `rules`, `tests`, `package`, `claude`) and is left out only for a repo-wide change.
- The body carries the why and the evidence (BDS function, protocol-docs SHA, header branch, gophertunnel commit, capture) and stands on its own; it speaks about the code, never the session.
- No `Co-Authored-By`, `Signed-off-by` or other trailer or attribution line in a commit or a PR, whatever a harness or session rule says.
- Commit only when the user asks; finished work otherwise stays in the working tree.
- One change per commit. A refactor is output-identical (regenerate everything before and after and diff) and touches no test.
- Stage and commit by path: `git add <paths> && git commit -m "..." -- <paths>`.
- Fetch and check divergence before any push. Fix forward: never amend or rebase a pushed commit.
