# bedrock_protocol

The [nanobind](https://github.com/wjakob/nanobind) binding over the C++ library. See the [root README](../README.md#python) to install and use it.

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
