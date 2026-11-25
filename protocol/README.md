# protocol

The schema: each supported protocol's packets, types and enums, in the DSL [`bpc`](../compiler) compiles. `__init__.py` holds `versions`; every other module holds one BDS domain, named in its docstring.

| Construct | Declares |
| --- | --- |
| `@packet(id=)` | A packet |
| `class Name:` | A struct, its fields in encoding order |
| `class Name(IntEnum, uint8):` | An enum over its underlying type |
| `type Name = varint32`, `type Name = A \| B` | A primitive alias, a union alias |
| `@builtin` | A type the hand-written runtime implements |
| `T \| None`, `list[T]`, `array[T, N]`, `dict[K, V]`, `bitset[E.M]`, `Literal[c]` | An optional, a counted list, a fixed array, a map, a bitset, a constant |
| `field(type=, endian=, prefix=, count=, duplicate=)` | A field encoded other than its type's default |
| `field(when=lambda p: ...)` | A field present only where earlier fields say |
| `value(N, "Name")`, `auto()`, `sentinel()` | An enum member, the next number, an ungenerated count |

`since=` and `until=` gate `@packet`, `@type`, `field`, `value` and their `with` blocks to `[since, until)`, each bound a key of `versions`. [`dsl.py`](../compiler/src/bedrock_protocol_compiler/dsl.py) lists every option, and [`.claude/rules/protocol/`](../.claude/rules/protocol) the modelling rules.
