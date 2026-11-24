---
paths:
  - "**/*.py"
---

# Hand-written Python

The schema modules under `protocol/` follow `.claude/rules/protocol/` instead of this file; the DSL in `compiler/src/bedrock_protocol_compiler/dsl.py` follows this file.

- Annotate hand-written code so it passes `mypy --strict` with no `# type: ignore`; tests need no annotations.
- Limit a comprehension to two `for` clauses and one `if`; write longer ones as loops.
- Catch the narrowest exception and never `except Exception`.
- Validate input with `raise`, never `assert`.
- Write an error message as `<offending name>: <lower-case reason>`, naming the bad value, with no trailing period.
- Name a value for what it is (`packets`), not for its type (`packet_list`).
- Encode a packet with `encode(packet)` and decode it with `decode(Packet, data)`, the package's at the latest protocol and `v<N>`'s at N, which reject trailing bytes; both take only a packet class of protocol N, raise `TypeError` for anything else and take no mode, and a failure raises `EncodeError` or `DecodeError`, both `ValueError`s; a bare type and a serialization mode go only through `bedrock_protocol._core`'s `encode(N, x, mode=...)`, `decode(N, X, data, mode=...)`, `modes` and `encodings`.
- Answer a protocol's enum numbers with `v<N>`'s `enum_integer(value)`, `enum_cast(cls, number)`, `enum_contains(value)`, `enum_contains(cls, number)`, `enum_values(cls)` and `enum_count(cls)`, as C++'s `enum_*_<N>` do, with an `int` for a number no member holds and `TypeError` for anything but an enum.
- Bind each class once, where C++ declares it (`cpp.md`): in the package for the root of `bedrock::protocol`, in `v<N>` for `bedrock::protocol::v<N>` and under its owner when nested, so `__module__` names that module and `v<N>` holds no class it did not introduce.
- Make every enum one class holding every member any protocol has; `.value` is the library value, its number at the newest protocol that has it.
- Raise `EncodeError` for a value the protocol cannot number or name, or its encoding cannot hold; decode a number the protocol gives no member to an `int`, and raise `DecodeError` for a number the protocol cannot place.
- Keep two names sharing a value as distinct members that compare equal, and lookup by the value gives the newest-live name.
