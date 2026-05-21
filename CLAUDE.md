# Project rules

1. **Never add Claude as a co-author.** No `Co-Authored-By: Claude ...` lines
   in commits or PR descriptions, ever.

2. **Jinja templates emit no explanatory comments into generated headers.**
   Files under `src/bedrock_protocol/compiler/cpp/templates/` should not
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

7. **Version-gate new packets against reference implementations.** The
   EndstoneMC protocol-docs JSON describes only the latest schema, so it
   never reveals when a field appeared or was removed. Before adding (or
   omitting) `field(since=)` / `value(since=, until=)` gating, cross-check
   each field's history against two reference libraries:
    - `CloudburstMC/Protocol` -- `bedrock-codec` keeps a per-protocol-version
      serializer at
      `.../bedrock/codec/vNNN/serializer/<Packet>Serializer_vNNN.java`.
      A field that first appears in a later `vNNN` serializer is `since=NNN`,
      and the oldest `vNNN` that defines the serializer at all is the
      packet's own `since` -- except for the v291 floor, see below.
    - `Sandertv/gophertunnel` -- `minecraft/protocol/packet/<name>.go` for the
      current field shape, plus `git log -S<field>` on that file to date
      when each field was added or removed.

   Use the protocol (network) version number. Gate the type itself at the
   version it first appears -- `@packet(since=N)` for a packet, `@type(since=N)`
   for an enum or non-packet struct -- so the generated type is absent from
   earlier snapshots. Fields and members present from that introduction need
   no `since` of their own. Only later additions take `field(since=)` or
   `value(since=)`. A type or field that neither reference models is left
   ungated.

   CloudburstMC's codec history begins at protocol 291, so v291 is a floor,
   not a real introduction point: a packet or enum whose oldest serializer is
   `v291` cannot be told apart from one that predates the reference window.
   Leave it ungated -- no `since=291`. The earliest introduction worth gating
   is 292 or later. The same applies to a `field(since=)` / `value(since=)`
   that would land on 291: drop it.

   The protocol-docs JSON is mechanically dumped from a Bedrock server and
   the dumper is not perfect. When protocol-docs disagrees with gophertunnel
   and CloudburstMC -- a field's shape, name, type, or id -- do not silently
   pick one. Raise the discrepancy.

8. **Every packet gets a golden round-trip test generated by gophertunnel.**
   When you add a packet, add a test that serializes the struct and asserts
   its bytes against a `const std::vector<std::uint8_t> golden`. Do not
   hand-compute the golden. Construct the equivalent `packet.<Name>` in
   `Sandertv/gophertunnel`, marshal it through a `protocol.Writer` (this
   writes the body only, with no packet-id header, matching our `serialize`),
   and embed the resulting bytes. Precede the `golden` with a two-line
   comment: a first line `// generated by gophertunnel:` and a second line
   with the marshalled `packet.<Name>{...}` literal. If a packet has no
   gophertunnel equivalent, do not hand-write the golden -- raise it
   instead. Golden tests cover packets only -- a non-packet component type
   is exercised through a packet that embeds it, not on its own.

   A golden for a protocol version older than gophertunnel's current one
   cannot come from `master`: a packet's `Marshal` there reflects only the
   latest protocol. Check out `Sandertv/gophertunnel` at the historical
   commit whose marshaller matches that era -- find it with
   `git log -- minecraft/protocol/packet/<name>.go` -- marshal there, and
   record the commit in the comment: `// generated by gophertunnel @<commit>:`.
   Commits before the 2023 Marshal/Unmarshal merge use a different API
   (`Marshal(buf *bytes.Buffer)`), so the driver differs per era. Never
   hand-compute a golden, not even by reading the `Marshal` source.

   For a packet whose body is (or contains) a `CompoundTag`, the Go-side NBT
   struct used to build the golden must declare its `nbt:"..."`-tagged fields
   in alphabetical key order, and a `map[string]any` payload must be replaced
   by such a struct. Our `CompoundTag` is `std::map`-backed and writes entries
   in sorted-key order, while gophertunnel's NBT encoder follows Go's struct
   declaration order and randomizes map iteration -- mismatch yields the same
   compound semantically but a different byte sequence, and the round-trip
   `REQUIRE(buf == golden)` fails. Sort the Go struct fields before generating.

9. **Field names come from protocol-docs.** When adding a packet, name each
   field after the EndstoneMC protocol-docs JSON (the same source rule 7
   draws on), carried into the project's `snake_case` convention. Do not
   invent or paraphrase names, and do not lift them from gophertunnel or
   CloudburstMC -- those references date and shape fields, they do not name
   them. If a field is absent from protocol-docs, fall back to the `.dot`
   files in the `Mojang/bedrock-protocol-docs` repository and take the name
   from there. Raise anything neither source names.

10. **No `from __future__ import annotations`.** The compiler's Python omits
    it. Where an annotation needs a forward or recursive reference -- common
    in `schema.py`'s recursive IR (`TypeRef`, `Wire`, `Pred`) -- write that
    annotation as a string literal, e.g. `inner: "TypeRef"`.

11. **Single-field gates use `= field(when=...)`, not a `with` block.** When
    only one field is guarded by a predicate, write it inline as
    `name: T = field(when=lambda p: ...)`. Reserve `with field(when=...):`
    for groups of two or more fields that share the same gate, or for the
    optional / union case the inline form does not support (see the `when`
    docstring in `protocol/__init__.py`). A solo field inside a `with` block
    is just noise.

12. **Packet and type docstrings come from `Mojang/bedrock-protocol-docs`.**
    The docstring of a `@packet` or `@type` is the Description that
    `Mojang/bedrock-protocol-docs` gives for it -- the single source of truth
    for docstring prose. A packet with a text page under `docs/` carries its
    Description in `<div class="description">` blocks (there may be more than
    one, and a leading short name like `Interact` or `Animate Actor` is a
    title, not part of the description). A packet that appears only as a tree
    under `html/` -- an embedded SVG with no prose -- has no Description.
    Carry the Description across faithfully: decode HTML entities, fix obvious
    rendering typos, and adjust only for the ASCII / no-semicolon-splice rule
    (rule 5). Write each docstring as a single line; hand-wrap only the ones
    `ruff check` flags over-length (E501), since `ruff format` does not
    reflow docstring prose. Do not invent prose, paraphrase a description from
    gophertunnel
    or CloudburstMC, or restate version history that `since` / `until` already
    encode. If `Mojang/bedrock-protocol-docs` gives no Description, leave the
    type undocumented rather than writing one.
