# Conventions and code style

**Enforced:** the rules hook blocks (a) any non-ASCII character in an edited file,
(b) `from __future__ import annotations` in a `.py` file, (c) a `ruff check` failure
on an edited `.py` file, (d) a `Co-Authored-By` trailer on `git commit`, and (e) a
`//` prose comment emitted from a Jinja template.

## ASCII only, no clause-splicing semicolons

Applies to all authored text: code, comments, docstrings, prose, and commit
messages.

- ASCII only, everywhere. Non-ASCII punctuation is a common LLM tell: em-dashes,
  en-dashes, Unicode arrow glyphs, and smart or curly quotes. Use plain ASCII
  throughout: regular hyphens, `->` or `=>` for arrows, straight quotes.
- Never use a semicolon to splice two independent clauses. Either rewrite as one
  sentence or break it into two. (Statement-separating semicolons in Python are a
  separate matter and are rarely wanted anyway.)

## Python

- No `from __future__ import annotations`. The compiler's Python omits it. Where an
  annotation needs a forward or recursive reference -- common in `schema.py`'s
  recursive IR (`TypeRef`, `Wire`, `Pred`) -- write that annotation as a string
  literal, e.g. `inner: "TypeRef"`.
- ruff is authoritative for lint and import order: line length 120, rule sets `I`
  (isort), `E` (pycodestyle), `F` (pyflakes). Keep every edited file ruff-clean.
- mypy runs in strict mode over `src` (`uv run mypy`). Run it before committing. It
  is the type gate. It is not run per edit because checking the whole tree on every
  change is too slow.

## Git and commits

- Never credit Claude as a co-author. No `Co-Authored-By: Claude ...` line in any
  commit message or PR description, ever.
- Commit protocol bumps and DSL work to `main`. This repo commits to main.
- A version-bump or wire-change commit body cites its sources. For each field, enum
  value, or packet that changed, name the upstream reference(s) that confirmed it
  (EndstoneMC/protocol-docs, Sandertv/gophertunnel, CloudburstMC/Protocol,
  CloudburstMC/Nukkit, MemoriesOfTime/Nukkit-MOT), so a reviewer can audit the
  change without re-walking the references. See `protocol.md`.

## Keep README.md minimal

The library is still in active design and every interface is subject to change. Do
not expand `README.md` with detailed API documentation, exhaustive examples, or
extended rationale that will rot as the design moves. Cover the bare essentials:
what the project is, how to build it, and the smallest possible "hello world"
snippet. Link out for anything beyond that.

## Generated C++ output: templates emit no explanatory comments

Files under `src/bedrock_protocol/compiler/cpp/templates/` must not write `//` prose
blocks into the generated C++ output. Namespace close-markers like
`}  // namespace bedrock::protocol` are fine -- they are bracket-matching aids. Prose
explanations above a code construct are not. To leave a "why this exists" note,
document it in the template's own `{# ... #}` block, so it is seen by codegen
maintainers rather than by header consumers.

## Stream wire API is templated, not named

`BinaryReader` and `BinaryStream` expose I/O exclusively through templates. Use these
forms, never named per-type methods:

- `read<T>()` / `write<T>(v)` -- fixed-width, native-endian (little) by default.
- `read<T, std::endian>()` / `write<T, std::endian>(v)` -- fixed-width with explicit
  byte order (swaps only when `Order != std::endian::native`).
- `readVarInt<T>()` / `writeVarInt<T>(v)` -- LEB128, zigzag for signed `T`.
- `read<std::string>()` / `write(string_view)` -- varuint32 length + bytes.
