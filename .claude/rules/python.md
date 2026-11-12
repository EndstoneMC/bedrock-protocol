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
