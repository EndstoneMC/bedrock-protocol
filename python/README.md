# bedrock_protocol

The [nanobind](https://github.com/wjakob/nanobind) binding over the C++ library.

## Install

Install the Linux or Windows wheel for Python 3.12 or newer from PyPI:

```shell
uv pip install bedrock-protocol
```

Or build it from a checkout with CMake and a C++23 compiler:

```shell
git clone https://github.com/EndstoneMC/bedrock-protocol
uv pip install ./bedrock-protocol
```

## Encode and decode

```python
import bedrock_protocol as bp

packet = bp.TextPacket()
packet.body = bp.TextPacket.MessageOnly(type=bp.TextPacketType.CHAT, message="hello")
data = bp.encode(packet)
decoded = bp.decode(bp.TextPacket, data)
assert decoded == packet
```

## Pick a protocol

```python
version = bp.ProtocolVersion.get(2259)
assert version is not None and version.name == "1.26.70"

pinned = bp.v2259.encode(packet)
picked = bp.v2259.decode(bp.TextPacket, pinned)
assert picked == packet
```

## Modules

| Module | Holds |
| --- | --- |
| `bedrock_protocol` | The latest protocol's classes, `ProtocolVersion`, `EncodeError`, `DecodeError`, `encode` and `decode` |
| `bedrock_protocol.v<N>` | Protocol N's `encode`, `decode` and `packets`, and the classes it introduced that the latest lacks |
| `bedrock_protocol.nbt` | NBT tags |
| `bedrock_protocol._core` | `encode` and `decode` of any type at any protocol and mode, `encodings` and `modes` |

```shell
uv sync
uv run pytest
```
