# CLAUDE.md

## Version gating

`since=` / `until=` must align to a declared `ProtocolVersion` snapshot
(`protocol/version.py`), never a raw changelog number. Gate a change at the
next snapshot at or after it: a packet or field the changelog dates to 977
gates `since=1001`, not `since=977`. Only 975 and 1001 are materialized, so an
off-snapshot boundary buys nothing — keep every `requires (V >= N)` on a real
snapshot.

## Tests

Name per-packet test files `test_{packet_id:03}_{name}.cpp` — the packet's
wire id zero-padded to three digits, then a descriptive name (e.g.
`test_348_update_sound_data.cpp`).

Golden bytes come from [gophertunnel](https://github.com/sandertv/gophertunnel)
(`minecraft/protocol/packet`), not hand-derivation: read the packet's `Marshal`
and encode each field as its `protocol.IO` call dictates (`Uint64` = fixed LE,
`String` = varuint32 length + bytes, etc.). Cite the source packet/method in a
comment above the golden. Where gophertunnel and BDS disagree, verify against
the BDS binary and note the deviation (as the attribute-layer name-code casing
does).
