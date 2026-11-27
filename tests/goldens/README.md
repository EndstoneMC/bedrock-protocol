# Goldens

Packet values with the bytes Bedrock Dedicated Server (BDS) reads and writes back unchanged, checked both ways by `tests/test_goldens.py`, Java's `GoldensTest` and Go's `goldens_test.go`.

`v2168/` holds every packet live at 2168, and each other `v<protocol>/` the packets whose encoding differs from its neighbour's toward 2168; each folder is checked against the BDS build [`goldens.md`](../../.claude/rules/protocol/goldens.md) names.

`<id:03>_<snake_name>.json` holds one packet's cases as a JSON array of `{"id", "value", "bytes"}`: the state the case reaches, the packet's fields by their schema names, and its encoding at the folder's protocol without the packet id, in lowercase hex.

| Value | Form |
| --- | --- |
| Union arm | An object led by `"__class__"`, the arm's class |
| Enum | Its number at the folder's protocol, or its encoded name |
| Byte blob, non-UTF-8 string | `\xNN` per byte |
| UUID | Its canonical string |
| Packed `Color` | `#aarrggbb` |
| `Color255RGBA` | `#rrggbbaa` |
| Bitset | `0b` and its bits, most significant first |
| NBT | Compact SNBT |

```shell
uv run pytest tests/test_goldens.py -k v2259
```
