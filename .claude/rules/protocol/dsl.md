---
paths:
  - "protocol/**"
---

# Declarations

`compiler/src/bedrock_protocol_compiler/dsl.py` declares the constructs; these rules say which construct to choose.

## Nesting

- Nest a type as a class inside its owner. Reference it bare inside the owner and as `Owner.Inner` elsewhere.
- Repeat each nested type verbatim in every redeclared body of its owner, dropping gates the owner's range decides.
- Where only a nested type is modelled, declare its owner with no fields.

## Fields

- Write a cerealised form as bare `name: Type` lines. Annotation clutter on one means the pre-cereal shape is being modelled.
- Model a packet in the encoding its build sends by default: the hand-written write when golden mode's `serialization_mode` is below CerealOnly, cereal when its read goes through cereal.
- Write a split between declared and encoded type as `name: DeclaredType = field(type=<encoded>)`. Never drop to the raw primitive, except an `mce::UUID` BDS encodes as text, which is `str`.
- Use `field(type=<encoded>)` on a struct (or `list`/`array`/`Optional` of one) when that struct has one reencodable scalar field whose encoding changes at that call site, and `field(type=lambda p: ...)` when an earlier field picks the encoding.
- Use `field(type=<primitive>)` on an alias only for the members BDS holds as that plain primitive; its cereal JSON is a bare value there and a one-member wrapper object everywhere else.
- Use `array[T, N]` for a BDS `std::array<T, N>` and `list[T]` for a length-prefixed sequence. Use `field(count=)` only for a length BDS holds as its own member or writes apart from the list, as an expression over earlier fields, never as a constant.
- Declare a member that BDS writes several times in a row as one field with `field(duplicate=N)`, N the copies BDS writes: one per name the dump binds it under, or one per write in a hand-written encoding. Write a count that depends on an earlier member as a lambda like `when=`, `field(duplicate=lambda p: 2 if p.action & 0x80 != 0 else 1)`.
- Spell an alias that BDS nests in a class inline at its use; never hoist it to a module-scope `type`.
- Never put a version-dependent width behind a `type X = <primitive>` alias; spell it inline.
- Declare a top-level type that only wraps one primitive, such as an id, a handle or a duration, as a `type` alias under its own name (`type EffectDuration = varint32`), and spell a nested one's primitive at its use (`header: uint8`); never keep either as a one-field class. A data class that holds one member for now, a packet and a variant arm stay classes.

## Conditions

- Turn a pre-cereal switch into `when=`: `field(when=...)` for one field, `with field(when=...):` for a run.
- Write a run of fields that share one gate as `with field(since=, until=):`, and keep a field that narrows the gate inside the run with its own `since=`, `until=` or `when=`; a block never nests in another and takes `when=` beside the gate.
- Swap a field's type at one version by declaring it twice in place, `x: A = field(until=N)` then `x: B = field(since=N)`; swap a run as a `with field(until=N):` block directly followed by a `with field(since=N):` block with the same names in the same order.
- Use `when=` for any implicit presence rule, such as a field gated on a sentinel value. Never use an optional for it, because an optional adds a byte BDS never wrote.

## Constants

- Model a dumped field that carries `"value"` as a `Literal`, under the name BDS bound it to.
- Spell an integer-coded constant as its enumerator (`Literal[ItemStackRequestActionType.TAKE]`), never as `Literal[0] = field(type=uint8)`. Spell a name-coded constant as the folded string it encodes (`Literal["changeentity"]`).
- Start a field name with `_` only for bug noise or cereal's marker bytes, which print nothing in JSON; `_deprecated` is a real BDS member and prints. A tag BDS means to send keeps its own name.
- Give every variant alternative its tag `Literal`. A member that the dump gives `constraints.enum_values` instead of a `value` stays an ordinary field.

## Markers

- Model cereal's always-true member-present byte (`encoding.md`) as its own `_true: Literal[True]` field, exactly where the byte falls, and leave the member after it bare. When there are several, name them `_true_1`, `_true_2` and so on.
- Never fold an always-true marker into `T | None`.

## Unions

- Order a union's cases to the encoding's `uvarint32` index. Lead with `None` where BDS numbers from one (`value: None | bool | uvarint32 | float`).
- Spell `Union[T, None]` only where BDS cerealised a two-case variant; `T | None` is an optional.

## Shared types

- Gate a shared type with one `@type(until=N)`/`@type(since=N)` pair, or a union alias with one `with type(until=N):`/`with type(since=N):` pair, only where every call site changes encoding at N; otherwise model its encoding per call site.
- Use `cereal=False` only where one protocol version sends both encodings of a class name; everywhere else gate the two declarations by version. Where BDS names the cerealised form separately, declare that name instead.
- Mark each field of a `cereal=False` class whose type has a `cereal=False` declaration with `field(cereal=False)` too; a bare field takes the cereal declaration.
- Write a member that BDS leaves out at a call site of a shared type as `field(exclude="<member>")` on that call site; never declare a second type for it.

## Growing the DSL

- Import every DSL name a protocol file uses, `value` included.
- Add a DSL construct only when a packet first needs it, as its own reviewable change, with a test that exercises it.
