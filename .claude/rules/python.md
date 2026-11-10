---
paths:
  - "**/*.py"
---

# Python

The modules under `protocol/` follow the DSL rules, not the naming and style rules below; ruff already exempts them.

- Annotate every parameter and return of hand-written library and compiler code so it passes `mypy --strict`; tests need no annotations.
- Use absolute imports and never `import *`.
- Never write `# type: ignore` or a `cast` to silence a type error; fix the type.
- Use f-strings, never `%`, `str.format` or `+` chains.
- Use `pathlib.Path` for paths and `read_text`/`write_text` for whole-file I/O; open any other file in a `with` block.
- Limit a comprehension to two `for` clauses and one `if`; write longer ones as loops.
- Catch the narrowest exception and never `except Exception`; let anything unexpected propagate.
- Validate input with `raise`, never `assert`.
- Raise with a message that names the offending type and value, starts lower-case, ends without a period and stays stable enough for `match=`.
- Name a value for what it is (`packets`), not for its type (`packet_list`).
- Test emptiness and truthiness implicitly (`if not items`); compare to `None` only with `is`.
- Use `@dataclass(frozen=True, slots=True)` for passive data and `enum` for a closed set of constants; never a bare dict or tuple with positional meaning.
- Keep no module-level mutable state; build it in a function and pass it in.
- Put a script's work in `main()` and call it under `if __name__ == "__main__":`.
