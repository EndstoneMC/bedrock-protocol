<div align="center">

<h3>bedrock-protocol</h3>

<p>
  <b>The Minecraft: Bedrock Edition network protocol for C++ and Python</b>
</p>

[![CI](https://github.com/EndstoneMC/bedrock-protocol/actions/workflows/ci.yml/badge.svg)](https://github.com/EndstoneMC/bedrock-protocol/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

## Python

### Install

Download the Linux or Windows wheel for Python 3.12 or newer from the [releases](https://github.com/EndstoneMC/bedrock-protocol/releases):

```shell
uv pip install bedrock_protocol-X.Y.Z-cp312-abi3-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl
uv pip install bedrock_protocol-X.Y.Z-cp312-abi3-win_amd64.whl
```

Or build it from a checkout with CMake and a C++23 compiler:

```shell
git clone https://github.com/EndstoneMC/bedrock-protocol
uv pip install ./bedrock-protocol
```

### Encode and decode

```python
import bedrock_protocol as bp

packet = bp.TextPacket()
packet.body = bp.TextPacket.MessageOnly(type=bp.TextPacketType.CHAT, message="hello")
data = bp.v2225.encode(packet)
decoded = bp.v2225.decode(bp.TextPacket, data)
assert decoded == packet
```

### Pick a protocol

```python
by_number = bp.protocol_version(2225)
by_release = bp.protocol_version("1.26.63")
assert by_number.snapshot == by_release.snapshot == 2225

codec = getattr(bp, f"v{by_release.snapshot}")
decoded = codec.decode(bp.TextPacket, codec.encode(packet))
assert decoded == packet
```

## C++

### Install

Unpack a package from the [releases](https://github.com/EndstoneMC/bedrock-protocol/releases) and point `CMAKE_PREFIX_PATH` at its folder:

```cmake
find_package(bedrock-protocol CONFIG REQUIRED)
target_link_libraries(my_target PRIVATE bedrock::protocol)
```

### Encode and decode

```cpp
#include <cassert>

#include <bedrock/protocol.hpp>

namespace bp = bedrock::protocol;

bp::TextPacket packet;
packet.body = bp::TextPacket::MessageOnly{.type = bp::TextPacketType::Chat, .message = "hello"};

std::expected<std::string, bp::EncodeError> data = bp::v2225::encode(packet);
assert(data);
std::expected<bp::TextPacket, bp::DecodeError> decoded = bp::v2225::decode<bp::TextPacket>(*data);
assert(decoded && *decoded == packet);
```

### Pick a protocol

```cpp
std::optional<bp::Protocol> protocol = bp::protocol("1.26.63");
assert(protocol && protocol == bp::protocol(2225));
std::expected<std::string, bp::EncodeError> encoded = protocol->encode(packet);
assert(encoded);
std::expected<bp::TextPacket, bp::DecodeError> picked = protocol->decode<bp::TextPacket>(*encoded);
assert(picked && *picked == packet);
```

## Supported Protocols

| Protocol | Releases |
| --- | --- |
| 729 | 1.21.30 to 1.21.31 |
| 748 | 1.21.40 to 1.21.44 |
| 766 | 1.21.50 to 1.21.51 |
| 776 | 1.21.60 to 1.21.62 |
| 786 | 1.21.70 to 1.21.73 |
| 800 | 1.21.80 to 1.21.84 |
| 818 | 1.21.90 to 1.21.92 |
| 819 | 1.21.93 to 1.21.95 |
| 827 | 1.21.100 to 1.21.102 |
| 844 | 1.21.111 to 1.21.114 |
| 859 | 1.21.120 to 1.21.123 |
| 860 | 1.21.124 |
| 898 | 1.21.130 to 1.21.132 |
| 924 | 1.26.0 to 1.26.3 |
| 944 | 1.26.10 to 1.26.14 |
| 975 | 1.26.20 to 1.26.23 |
| 1001 | 1.26.30 to 1.26.36 |
| 2168 | 1.26.40 to 1.26.44 |
| 2169 | 1.26.45 |
| 2193 | 1.26.50 to 1.26.52 |
| 2225 | 1.26.6x |

## Building from Source

With CMake, Ninja, Python 3.12 or newer and a C++23 compiler, from a Visual Studio developer prompt on Windows:

```shell
cmake --preset release
cmake --build --preset release
cmake --install build/Release --prefix stage
uv sync
```

## License

MIT, see [LICENSE](LICENSE).
