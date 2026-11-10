---
paths:
  - "protocol/**"
---
# Declarations

`protocol/__init__.py` documents what each construct means on the wire; these rules say which construct to choose. Never restate those docstrings: what `when=` may read, presence bytes, prefixes, defaults.

## Nesting
- Nest a type as a class inside its owner. Reference it bare inside the owner and as `Owner.Inner` elsewhere.
- Repeat each nested type verbatim in every redeclared body of its owner.
- Where only a nested type is modelled, declare its owner with no fields.

## Fields
- Write a cerealised form as bare `name: Type` lines. Annotation clutter on one means the pre-cereal shape is being modelled.
- Write a split between declared and wire type as `name: DeclaredType = field(type=<wire>)`. Never drop to the raw primitive.
- Use `array[T, N]` for a BDS `std::array<T, N>` and `list[T]` for a length-prefixed sequence. Use `field(count=)` only for a length written elsewhere, as an expression over earlier fields, never as a constant.
- Spell an alias that BDS nests in a class inline at its use; never hoist it to a module-scope `type`.
- Never put a version-dependent width behind a `type X = <primitive>` alias; spell it inline.

## Conditions
- Turn a pre-cereal switch into `when=`: `field(when=...)` for one field, `with field(when=...):` for a run.
- Use `when=` for any implicit presence rule, such as a field gated on a sentinel value. Never use an optional for it, because an optional adds a byte BDS never wrote.

## Constants
- Model a dumped field that carries `"value"` as a `Literal`, under the name BDS bound it to.
- Spell an integer-coded constant as its enumerator (`Literal[ItemStackRequestActionType.TAKE]`), never as `Literal[0] = field(type=uint8)`. Spell a name-coded constant as the folded string it puts on the wire (`Literal["changeentity"]`).
- Start a field name with `_` only for bug noise. A tag BDS means to send keeps its own name.
- Give every variant alternative its tag `Literal`. A member that the dump gives `constraints.enum_values` instead of a `value` stays an ordinary field.

## Markers
- Model cereal's always-true member-present byte (`wire.md`) as its own `_true: Literal[True]` field, exactly where the byte falls, and leave the member after it bare. When there are several, name them `_true_1`, `_true_2` and so on.
- Never fold an always-true marker into `T | None`.

## Unions
- Order a union's cases to the wire's `uvarint32` index. Lead with `None` where BDS numbers from one (`value: None | bool | uvarint32 | float`).
- Spell `Union[T, None]` only where BDS cerealised a two-case variant; `T | None` is an optional.

## Shared types
- Model a shared type's encoding per call site, never with one `@type(until=)`/`@type(since=)` pair over the shared type. Declare the hand-written shape `@type(cereal=False)` and reach it with `field(cereal=False)`.
- Use `cereal=False` only where BDS reuses one class name for two wire shapes. Where BDS names the cerealised form separately, declare that name instead.

## Growing the DSL
- Import every DSL name a protocol file uses, `value` included.
- Add a DSL construct only when a packet first needs it, as its own reviewable change, with a test that exercises it.
