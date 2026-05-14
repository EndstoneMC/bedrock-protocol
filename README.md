# bedrock-protocol

A protoc-style codegen for Minecraft Bedrock wire packets. Schemas are
written in Python (read statically, never executed) and rendered to C++
through Jinja templates. CMake integration mirrors `protobuf_generate`.

> **Status:** active design. Interfaces are subject to change.

## Schema

A packet file is plain Python:

```python
@packet(id=5)
class DisconnectPacket:
    reason: DisconnectFailReason = field(type=varint32, since=622)
    messages: DisconnectPacketMessages | None = field(type=Union)
```

See `protocol/disconnect.py` for the current state, and `tests/` for
usage examples.

## Build

```sh
cmake -S . -B build
cmake --build build
```

The build invokes the codegen on files under `protocol/` and links the
generated headers into `libbedrock_protocol`.
