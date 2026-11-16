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
- Encode a bound value with `v<N>.encode(x)` and decode it with `v<N>.decode(X, data)`, which rejects trailing bytes and uses the default serialization mode; where a class has no default mode at N, because its name has two encodings there, pass `mode=SerializationMode.CEREAL` or `mode=SerializationMode.MANUAL`, and `v<N>.modes` lists each class's modes; a failure raises `EncodeError` or `DecodeError`, both `ValueError`s.
- Make every enum one class holding every member any protocol has, the same object in every `v<N>` where it is live; `.value` is the library value, its number at the newest protocol that has it.
- Raise `EncodeError` for a value the protocol cannot number or name, or its encoding cannot hold; decode a number the protocol gives no member to an `int`, and raise `DecodeError` for a number the protocol cannot place.
- Keep two names sharing a value as distinct members that compare equal, and lookup by the value gives the newest-live name.
