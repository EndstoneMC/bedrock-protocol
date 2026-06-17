# Bedrock protocol DSL

The DSL is the authoring surface the `bpc` compiler consumes. You write
Python modules under `protocol/` that describe Minecraft Bedrock packets and
their component types, and the compiler emits a versioned C++ codec. The
Python is never executed for its runtime behavior. It is read as a schema:
class bodies, annotations, and a small set of marker functions imported from
`protocol`.

This document is the syntax reference. It covers every declaration form, every
field annotation, every `field()` / `value()` keyword, and how each construct
maps onto the wire. It does not restate project conventions that live in
`CLAUDE.md` (naming, docstring sourcing, version-gating research process,
golden tests) -- those govern *what* to write, this governs *how the DSL
expresses it*.

## 1. Objective

Describe the Bedrock wire protocol once, in a typed Python schema, and compile
it to a C++ serializer that is correct for every protocol version in range. A
single schema carries the whole version history through `since` / `until`
gating, so one source tree generates the codec for any targeted snapshot.

Audience: contributors adding or correcting packets. The DSL is meant to read
like a struct definition, with version history and wire-shape overrides
expressed as lightweight annotations rather than imperative serialization code.

## 2. Compiler invocation

The DSL is compiled by `bpc`, a protoc analog:

```
bpc --language cpp --out <dir> [--import-path <dir>]... <inputs>...
```

- `--language NAME` (alias `--lang`) selects the registered backend. One
  backend per invocation. `cpp` is the only backend today.
- `--out DIR` is the backend output directory.
- `--import-path DIR` (alias for protoc's `--proto_path`, repeatable) is a
  search root for resolving `from X.Y import ...` between input modules.
- `<inputs>` are the DSL module files to compile.
- `-v` / `--verbose` prints one line per generated file.

The targeted protocol version is **not** a command-line knob. It is sourced
from `__version__` in `protocol/__init__.py`. Change that constant to retarget.

## 3. Module structure

Each DSL module is an ordinary Python file under `protocol/`. A module:

- imports the marker names it uses from `protocol`
  (`field`, `packet`, `type`, `value`, the primitive aliases, ...),
- declares `package = "bedrock.protocol"` (the C++ namespace the generated
  types land in),
- defines types as classes, optionally importing component types from sibling
  modules with `from protocol.<mod> import <Name>`.

```python
from enum import IntEnum

from protocol import field, packet, type, uint8, varint32, value
from protocol.common import Vec3

package = "bedrock.protocol"
```

Module-level rules from `CLAUDE.md` that bear on syntax:

- **No `from __future__ import annotations`** (rule 9). The compiler reads
  annotations as live objects. Where a forward or recursive reference is
  unavoidable, write that one annotation as a string literal
  (`inner: "TypeRef"`).
- `__version__` lives only in `protocol/__init__.py` and is an `int` protocol
  (network) version number.

### Primitive type aliases

Imported from `protocol`. Each is a Python `type` alias to `int` or `float`
that names a wire encoding:

| Alias | In-memory C++ | Wire form |
| --- | --- | --- |
| `int8` / `uint8` | `int8_t` / `uint8_t` | 1 byte |
| `int16` / `uint16` | `int16_t` / `uint16_t` | 2 bytes, little-endian |
| `int32` / `uint32` | `int32_t` / `uint32_t` | 4 bytes, little-endian |
| `int64` / `uint64` | `int64_t` / `uint64_t` | 8 bytes, little-endian |
| `varint32` / `varint64` | `int32_t` / `int64_t` | LEB128, zigzag (signed) |
| `uvarint32` / `uvarint64` | `uint32_t` / `uint64_t` | LEB128 (unsigned) |
| `float` (builtin) | `float` | 4 bytes, little-endian |
| `double` | `double` | 8 bytes, little-endian |

Bare `float` is a 32-bit float. `double` is the 64-bit alias. Endianness
defaults to little and is overridable per field with `endian=` (section 6).

## 4. Type declarations

A class in a DSL module declares one of three things, distinguished by its base
and decorator.

### 4.1 Struct

A plain class is a struct: an ordered list of wire fields. Field order in the
class body is wire order.

```python
class Vec3:
    x: float
    y: float
    z: float
```

An empty struct is legal and emits no bytes:

```python
class StopVideoCapture:
    pass
```

Do not "complete" an empty struct by copying members out of a BDS header. If
the wire references show no fields, the body stays empty (`CLAUDE.md` rule 12).

### 4.2 Enum

A class deriving `enum.IntEnum` is an enum. Its members supply C++ case labels
and wire values. Member-value forms are governed by `CLAUDE.md` rule 13 and
section 7 below.

```python
class GameType(IntEnum):
    UNDEFINED = -1
    SURVIVAL = 0
    CREATIVE = 1
    ADVENTURE = 2
    DEFAULT = 5
    SPECTATOR = 6
```

An enum has no wire form on its own. It rides the encoding of the field that
references it (section 5), defaulting to `varint32` unless the field overrides
with `field(type=...)`.

### 4.3 Packet

`@packet(id=N)` marks a struct as a top-level packet with wire id `N`.

```python
@packet(id=324, since=786)
class PlayerVideoCapturePacket:
    """Used by a test command to start/stop video capture."""

    params: StartVideoCapture | StopVideoCapture
```

`@packet` keywords:

- `id` (required): on-the-wire packet id.
- `since`: protocol version that introduced the packet. The generated type is
  absent from snapshots below it.
- `until`: first protocol version where *this declaration's* shape stops
  applying (exclusive). Meaningful only on a redeclared packet (section 8).

`serialize` writes the packet body only, with no id header. Golden tests assert
against that body (`CLAUDE.md` rule 8).

### 4.4 Decorators recap

| Decorator | Applies to | Keywords |
| --- | --- | --- |
| `@packet(...)` | a packet struct | `id` (req), `since`, `until` |
| `@type(...)` | an enum or non-packet struct | `since`, `until`, `deprecated` |
| `@builtin` | a hand-written type | none |

`@type` version-gates a non-packet type. `since=N` makes it absent below N.
`deprecated=N` keeps it emittable but stamps `[[deprecated("since vN")]]`.
`until` is meaningful only on a redeclared type (section 8). A struct or enum
with no version constraint needs no `@type` at all -- declare it bare.

```python
@type(since=622)
class DisconnectFailReason(IntEnum):
    UNKNOWN = 0
    CANT_CONNECT_NO_INTERNET = 1
    ...

@type(deprecated=944)
class NetworkBlockPos:
    x: int32 = field(type=varint32)
    y: int32 = field(type=uvarint32)
    z: int32 = field(type=varint32)
```

### 4.5 Builtins

`@builtin` marks a type the compiler must not define or serialize. It emits no
definition, references the type by name, and routes its fields through a
hand-written `Serializer<Name>` specialization (see `include/bedrock/nbt.hpp`).
Use it only for wire shapes the DSL cannot express. The twelve NBT tags in
`protocol/nbt.py` are the canonical case:

```python
@builtin
class CompoundTag:
    """An ordered list of named tags."""
```

`bitset[N]` is a builtin shipped by `protocol/__init__.py`; see section 5.

## 5. Field annotations and their wire forms

A field is `name: Annotation` in a struct body, optionally `= field(...)`. The
annotation is the *in-memory* type and, by default, the *wire* type too. The
table below is the default mapping. `field()` keywords (section 6) override the
wire half without touching the in-memory half.

| Annotation | Wire form |
| --- | --- |
| a primitive alias | per the section 3 table |
| `bool` | single byte (0 / 1) |
| `str` | `uvarint32` length prefix + UTF-8 bytes |
| `bytes` | `uvarint32` length prefix + raw bytes (or trailing, see `prefix=None`) |
| an enum type | the enum's underlying encoding (default `varint32`) |
| a struct type | that struct's fields inline, in order |
| `uuid.UUID` | 16 bytes |
| `bitset[N]` | base-128 little-endian dump of the N-bit value (7 payload bits/byte, high bit continues, lone `0x00` for empty) |
| `list[T]` | `uvarint32` count prefix + each element as `T` |
| `dict[K, V]` | `uvarint32` count prefix + each pair as `K` then `V` |
| `tuple[T, T, ...]` | exactly N elements, no prefix (fixed-length array) |
| `T \| None` | optional: 1-byte present flag + payload when present |
| `T1 \| T2 \| ...` | tagged union: `uvarint32` case index + active case body |

Examples:

```python
class TintMapColor:
    colors: tuple[Color, Color, Color, Color]   # fixed array of 4, no prefix

class CameraPresets:
    entity_priorities: dict[str, int32]          # count + (string, int32) pairs
    runtime_ids: list[ActorRuntimeID]            # count + each struct inline
    net_id_variant: varint32 | None              # bool flag + varint32 when set
```

A list / dict / tuple element may itself be a struct, an enum, an optional, or
an inline union. An inline union inside `list[T1 | T2]` tags every element
(section 6, `tag=`).

## 6. `field()` keywords

`field()` annotates the wire shape of a single field. Every keyword is
optional. The annotation owns the in-memory type, `field()` overrides only the
wire half.

### `type=` -- override the wire encoding

For an integer-primitive field, an integer primitive that changes the wire
encoding while the annotation keeps the in-memory type. The boundary
`static_cast`s.

```python
class NetworkBlockPos:
    y: int32 = field(type=uvarint32)   # int32_t in C++, uvarint on the wire
```

For an enum field, the primitive (or `str`) the enum is coded as. For an
optional field, passing `typing.Union` switches the presence marker from the
default 1-byte bool to a varint union-index discriminator. Index follows
annotation order: `X | None` encodes present as 0 / absent as 1, `None | X` the
reverse.

### `since=` / `until=` -- version-gate the field

`since=N` first version the field is present. `until=N` first version it is
removed (exclusive), so the field lives in `[since, until)`. Redeclaring the
same field name with adjacent ranges and differing annotations models a field
whose shape changed across versions (section 8).

```python
class AttributeData:
    modifiers: list[AttributeModifier] = field(since=544)
```

### `when=` -- gate on an earlier field's value

A one-argument lambda over earlier fields in the same struct. Nothing on the
wire marks presence: both serialize and deserialize recompute the predicate.
The field reads as `X` but compiles to an optional.

```python
class NetworkItemStackDescriptor:
    id: varint32
    stack_size: uint16 = field(when=lambda p: p.id != 0)
```

The lambda body may use attribute access on its parameter, `Enum.MEMBER`
literals, integer literals, comparisons, `and` / `or` / `not`, and bitwise `&`
(handy for testing a bit in a flags field, `p.flags & FLAG_HAS_X != 0`). It may
reference only fields declared before this one.

A single gated field uses the inline form above (`CLAUDE.md` rule 10). For two
or more fields sharing one gate, or to gate optional / union fields, use the
block form:

```python
class NetworkItemStackDescriptor:
    id: varint32
    with field(when=lambda p: p.id != 0):
        stack_size: uint16
        aux_value: uvarint32
        net_id_variant: varint32 | None
        block_runtime_id: varint32
        user_data_buffer: bytes
```

### `endian=` -- byte order for a fixed-width field

`"big"` or `"little"` (default). Bedrock is little-endian or varint almost
everywhere. The rare big-endian exceptions are a connection's initial protocol
version and the play status.

### `prefix=` -- length-prefix width, or trailing

For `list[T]` / `dict[K, V]`, the integer primitive that length-prefixes the
elements (default `uvarint32`). On a bare `bytes` field, `prefix=None` marks the
field as **trailing**: no length marker, the frame boundary ends the read. A
trailing field must be the last field of its struct.

### `count=` -- compute the element count

A one-argument lambda whose body is an integer expression over earlier fields,
valid only on `list[T]`. The wire carries no length prefix: both directions
compute the count from the expression.

```python
class ShapedRecipe:
    width: varint32
    height: varint32
    ingredients: list[Ingredient] = field(count=lambda p: p.width * p.height)
```

The expression may reference earlier fields (`p.<name>`), integer literals, and
`*`, `+`, `-`. `count=` suppresses the default prefix. Passing both `count=` and
`prefix=` is an error.

### `tag=` -- discriminator for a union

A multi-case union (`T1 | T2 | T3 | ...`, including an inline union inside a
`list[...]` where each element carries its own tag) is **always** prefixed on
the wire by a `uvarint32` active-case index. That width is fixed, so a plain
`std::variant` field takes **no `tag=`** -- declare the union bare and it gets
the `uvarint32` default:

```python
class PlayerVideoCapturePacket:
    params: StartVideoCapture | StopVideoCapture     # uvarint32 tag, implicit
```

Do not pass an integer primitive to set the width. `tag=uvarint32` is redundant
with the default and `tag=uint8` (or any other width) is not a real Bedrock
variant encoding, so both are discouraged. The parser still accepts an integer
primitive for flexibility, but the bare union is the idiom.

`tag=` has exactly one encouraged use: an **`IntEnum`**, for an
enum-discriminated union. The wire form then becomes `varint32` (zigzag,
matching BDS's recipe / action enums) and the enum's members supply the C++
case labels one-to-one with the union alternatives in declaration order:

```python
class GameRule:
    class Type(IntEnum):
        INVALID = 0
        BOOL = 1
        INT = 2
        FLOAT = 3

    value: bool | uvarint32 | float = field(tag=Type)   # varint32 tag + labels
```

`tag=` has no effect on a `T | None` optional. The field's resolved type must
contain a multi-case union or `tag=` is an error.

## 7. Enum member values

Three forms, picked by what the member needs (`CLAUDE.md` rule 13):

- **Bare integer literal** (`HARD = 3`) when the wire number is meaningful and
  worth reading: the anchor of a run (often the `0` baseline) or a
  wire-deliberate value (`UNDEFINED = -1`).
- **`value(N, since=, until=, deprecated=)`** when the member needs version
  gating or deprecation. The positional `N` is mandatory here: a version-windowed
  member must pin its number, since auto-numbering would shift if a sibling was
  added earlier in the run.
- **`auto()`** (from `enum.auto`) for everything else, including trailing
  count / width sentinels (`COUNT = auto()`). Auto-number is
  `previous_member + 1`, mirroring gophertunnel's `iota`.

```python
class DisconnectFailReason(IntEnum):
    UNKNOWN = 0                                          # anchor
    NETHER_NET_FAILED_TO_CREATE_OFFER = value(91, since=630)   # gated
    SOME_LATER_VALUE = auto()                            # previous + 1
```

`value(...)` keywords (`since` / `until` / `deprecated`) carry the same meaning
as on a field, applied to the member. A `deprecated=N` member stays on the wire
from version N on but emits `[[deprecated("since vN")]]`.

## 8. Version gating and redeclaration

A single schema spans the whole version history. Three mechanisms express it:

1. **Type gating.** `@packet(since=N)` / `@type(since=N)` make a type absent
   below N. Fields and members present from the type's introduction need no
   `since` of their own -- only later additions take `field(since=)` or
   `value(since=)`.

2. **Field / member gating.** `since=` / `until=` bound presence to
   `[since, until)`.

3. **Redeclaration for shape changes.** Declaring the same packet / type / field
   name more than once, each carrying an adjacent `[since, until)` range and a
   different shape, models a type or field that changed across versions. The
   compiler merges the declarations into one versioned type. The ranges must be
   contiguous (each `until` equals the next `since`) and only the last omits
   `until`. A redeclared packet must repeat the same `id` on every declaration.

The gating research process (which protocol version introduced or reshaped a
field, how to cross-check it against the reference libraries, and the v291
floor) is `CLAUDE.md` rule 7. This document only describes the DSL forms that
express the result.

## 9. Docstrings

A `@packet` / `@type` docstring is the Description from
`Mojang/bedrock-protocol-docs`, carried across faithfully (`CLAUDE.md` rule 11).
Write it as a single line. If `Mojang/bedrock-protocol-docs` gives no
Description, leave the type undocumented rather than inventing prose. Do not
restate version history that `since` / `until` already encode.

## 10. Worked example: a tagged union packet

`PlayerVideoCapturePacket` (id 324, since 786) is a test-command packet that
starts or stops video capture. BDS models the payload as a
`std::variant<StartVideoCapture, StopVideoCapture>`: the wire byte is the
variant index (0 = start, 1 = stop) followed by the active case's body. We
follow BDS ordering. (CloudburstMC uses the inverse mapping, STOP = 0 /
START = 1.)

```python
class StartVideoCapture:
    frame_rate: uint32
    file_prefix: str


class StopVideoCapture:
    pass


@packet(id=324, since=786)
class PlayerVideoCapturePacket:
    """Used by a test command to start/stop video capture."""

    params: StartVideoCapture | StopVideoCapture
```

What each construct does:

- The two cases are standalone structs combined into a bare multi-case union,
  the idiom in `protocol/book.py` and `protocol/attributes.py`.
- `StartVideoCapture` carries `frame_rate` (`uint32`) and `file_prefix` (`str`).
  `StopVideoCapture` is empty (section 4.1). The variant index gates the whole
  payload, so the start-only fields need no per-field `when=`.
- The union carries no `tag=`: a plain `std::variant` is always discriminated by
  a `uvarint32` index (section 6), so the default is exactly right. The
  index follows BDS ordering (0 = start, 1 = stop). CloudburstMC uses the
  inverse mapping (STOP = 0 / START = 1), which we do not follow.

This packet originally drafted the tag as `uint8` against an open question on
the discriminator width. That question is settled: a `std::variant` tag is
`uvarint32`, the same width the DSL applies by default. The reference libraries
that read a single byte (gophertunnel, CloudburstMC) agree on the wire bytes
here because the index is 0 or 1, which `uvarint32` and `uint8` encode
identically.

## 11. Testing strategy

- **Golden round-trip per packet** (`CLAUDE.md` rule 8). Every packet gets a
  test serializing the struct and asserting its bytes against a
  `const std::vector<std::uint8_t> golden` generated by `Sandertv/gophertunnel`,
  never hand-computed. Non-packet component types are exercised through a packet
  that embeds them.
- **Tests as usage examples** (`CLAUDE.md` rule 3). Keep each public API shape
  demonstrated somewhere (explicit-version access, bare-name-for-latest, field
  gating, serialize / deserialize, aggregate init, optional handling). Keep them
  terse: two or three anchors over exhaustive enumeration, no `struct Case` +
  loop scaffolding, no `SECTION` wrappers where separate `TEST_CASE`s read
  cleaner.

Existing tests live in `tests/test_NNN_<name>.cpp`, one per packet.

## 12. Boundaries

These are the hard rules from `CLAUDE.md` that touch DSL authoring. Read
`CLAUDE.md` for the full text and rationale.

Always:

- ASCII only, no semicolon clause-splices (rule 5).
- Resolve every symbol name through bedrock-headers, then EndstoneMC
  protocol-docs, then the Mojang `.dot` files, in that order (rule 12).
- Source docstrings from `Mojang/bedrock-protocol-docs` (rule 11).
- Cross-check field / member version history against gophertunnel and
  CloudburstMC before gating (rule 7).
- Add a gophertunnel-generated golden test for every new packet (rule 8).

Ask first / raise rather than guess:

- When protocol-docs disagrees with gophertunnel and CloudburstMC on a field's
  shape, name, type, or id, raise the discrepancy instead of silently picking
  one (rule 7).
- When no source names a symbol, raise it rather than inventing a name (rule 12).
- When a packet has no gophertunnel equivalent for a golden, raise it rather
  than hand-writing the bytes (rule 8).

Never:

- Add `Co-Authored-By: Claude` lines (rule 1).
- Emit explanatory `//` comments from Jinja templates into generated headers
  (rule 2).
- Use `from __future__ import annotations` (rule 9).
- Lift a symbol name from gophertunnel or CloudburstMC -- those date and shape
  symbols, they do not name them (rule 12).
- Infer wire fields from a BDS header -- headers name symbols, the protocol
  references define the wire shape (rule 12).
