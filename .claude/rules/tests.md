---
paths:
  - "tests/**"
---

# Tests

## Goldens

- Pin a new field a second way: two bodies that differ only in it must differ only in its bytes.
- Never assert a reorder by size; pin the order with a body whose bytes move.
- When a change materializes a snapshot (`versions.md`), re-check every test that builds one era's types against another era's golden.
- Check every golden both ways: encoding the packet yields the bytes, and decoding the bytes yields the packet.
- Write expected bytes only as literals; never compute them by re-implementing varints, zigzag, header packing or the codec.

## Writing a test

- Name a test for the behaviour it proves, as a lower-case sentence (`test_decode_rejects_trailing_bytes`), never for the function it calls.
- Prove one behaviour per test; a name that needs `and` is two tests.
- Put no loop, `if` or `try` in a test body: parametrize the cases with readable ids, assert a failure with `pytest.raises(..., match=...)`, and mark a known gap with `pytest.mark.xfail(strict=True)`.
- Reach the code only through the public `bedrock_protocol` package, never through a `_`-prefixed name; a missing public name is a gap in the binding.
- Pin a version-specific test by importing that version's module by name, never by position.
- Run version-independent behaviour over every bound version through one parametrized fixture.
- Share through fixtures, never `from conftest import`; a fixture never hides a value an assertion depends on.
- Use no mocks, monkeypatching or other doubles; drive the real extension with real values.
- Before trusting a new test, break the schema or the golden once and watch the test fail.

## Running

- Run pytest as `.venv/bin/python -m pytest` while another build runs; `uv run` rebuilds the binding whenever one of its cache keys changed.

## Files

- Add a case to the test that owns its packet or topic; never open a second file for it.
- Packet cases live in `tests/goldens/` and run through `test_goldens.py` (`.claude/rules/protocol/goldens.md`); topics live in `test_<topic>.py`.
- Give a type that no modelled packet reaches its own test, named for the type.
- Build a tests-only helper that copies a BDS component, such as the cereal JSON reader and writer, as BDS's own classes and virtuals under BDS's names in Python style, never as a flat set of functions.
