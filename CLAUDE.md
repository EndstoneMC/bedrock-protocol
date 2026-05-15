# Project rules

1. **Never add Claude as a co-author.** No `Co-Authored-By: Claude ...` lines
   in commits or PR descriptions, ever.

2. **Jinja templates emit no explanatory comments into generated headers.**
   Files under `compiler/src/bedrock_protocol_compiler/templates/` should not
   write `//` blocks into the generated C++ output. Namespace close-markers
   like `}  // namespace bedrock::protocol` are fine (bracket-matching aids).
   Prose explanations above a code construct are not. If you want to leave
   a "why this exists" note in the generated file, document it in the Jinja
   template's own `{# ... #}` instead so it is seen by codegen maintainers,
   not by header consumers.

3. **Tests are usage examples too.** Keep them terse and high-signal, but
   demonstrate each public API shape. The `tests/` folder doubles as the
   canonical place a new dev reads to learn the library. Avoid:
    - Enumerating many similar values (`REQUIRE(Foo::A == 0); REQUIRE(Foo::B == 1); ...`).
      Two or three anchors are enough. Pick the first, a representative
      middle, and the latest.
    - `struct Case { ... }` + vector + for-loop scaffolding when the cases
      collapse to a single round-trip exercising the same path.
    - Multi-line explanatory comments restating what the test does or quoting
      reference implementations. One short inline comment is enough.
    - `SECTION` wrappers when each section is self-contained. Promote to
      separate `TEST_CASE`s.
    - Re-asserting state immediately after assigning it.
    - A standalone "wire format" test for a primitive when an outer round-trip
      already exercises the same encoding.

   Keep each public API shape demonstrated somewhere: explicit-version
   access (`Foo_<N>`), bare-name-for-latest, field gating,
   serialize/deserialize, aggregate init of generated structs, optional
   field handling. If consolidating drops the only demonstration of a
   form, fold it into a different test.

4. **Keep `README.md` minimal.** The library is still in active design.
   Every interface is subject to change. Do not expand the README with
   detailed API documentation, exhaustive examples, or extended rationale
   that will rot as the design moves. Cover the bare essentials: what the
   project is, how to build it, and the smallest possible "hello world"
   snippet. Link out for anything beyond that.

5. **ASCII only. No semicolons joining sentences.** Non-ASCII punctuation
   (em-dashes, en-dashes, Unicode arrows like the right-arrow character,
   smart quotes) and semicolons used to splice independent clauses are
   common LLM tells. Use plain ASCII throughout: regular hyphens, arrows
   like `->` or `=>`, straight quotes. If you reach for a semicolon to
   join two clauses, either rewrite as one sentence or break into two.

6. **Stream wire API is templated, not named.** `BinaryReader` and
   `BinaryStream` expose I/O exclusively through templates:
    - `read<T>()` / `write<T>(v)` -- fixed-width, native-endian little by
      default
    - `read<T, std::endian>()` / `write<T, std::endian>(v)` -- fixed-width
      with explicit byte order (swap only when `Order != std::endian::native`)
    - `readVarInt<T>()` / `writeVarInt<T>(v)` -- LEB128, zigzag for signed
      `T`
    - `read<std::string>()` / `write(string_view)` -- varuint32 length +
      bytes
