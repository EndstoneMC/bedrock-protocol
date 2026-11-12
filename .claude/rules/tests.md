---
paths:
  - "tests/**"
---

# Tests

## Goldens

- Take a golden from BDS alone, never from a third-party codec (Sandertv/gophertunnel, CloudburstMC/Protocol) and never by hand (the `generating-goldens` skill).
- Keep goldens in `tests/goldens/<protocol>/<id:03>_<snake_name>.json` (`<snake_name>` is the class name without its trailing `Packet`, in snake case, keeping any Clientbound or Serverbound prefix), one file per packet, a JSON array of cases `{"id", "writer", "value", "bytes"}` plus `bds_json` where the build prints one and `other_writer_bytes` where BDS's other writer differs; `tests/goldens/builds.json` names the BDS build that wrote each folder.
- Hold every packet live at 2168, the base, in `tests/goldens/2168/`; a folder of another protocol holds a packet only when it is dirty against its neighbour toward 2168.
- Cover every path of a packet in its file: each variant alternative, optional present and absent, each gated or `when=` branch.
- Generate `value` from the schema with `scripts/goldens/values.py`, spelling a field by its schema name and an enum by the bound member's `.name`; never write one by hand.
- Seed the bytes with the library at HEAD; BDS of that version reads them and writes its own bytes, and its JSON where the build prints one.
- A difference in either, or a read BDS rejects, is a schema defect; fix the schema first.
- Freeze a case once BDS's bytes and JSON agree with the library's; never regenerate it or change its `bytes` or `bds_json` (a rename rewrites only the names in its `value`), and never run BDS from a test.
- Record `writer` as the one the packet's own `SerializationMode` picks, `manual` or `cereal`; a golden is that default write, compared with the other writer only below `SerializationMode` 5 (`CerealOnly` has none).
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

## Files

- Add a case to the test that owns its packet or topic; never open a second file for it.
- Take a packet's id at each version from `tests/packet_ids.json` (protocol-docs, else gophertunnel; `unlisted` holds a live packet neither lists), checked in `test_packet.py`; never assert it in a per-packet file.
- Run every golden through `test_goldens.py`, which `conftest.py` parametrizes over `tests/goldens/*/*.json`; never copy a golden's bytes into another test.
- Per-packet tests live in `test_{id:03}_{name}.py` (`test_009_text.py`); topics live in `test_<topic>.py`.
- Give a type that no modelled packet reaches its own test, named for the type.
