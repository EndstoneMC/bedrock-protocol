<div align="center">

<h3>bedrock-protocol</h3>

<p>
  <b>The Minecraft: Bedrock Edition network protocol for C++, Python, Java and Go</b>
</p>

[![CI](https://github.com/EndstoneMC/bedrock-protocol/actions/workflows/ci.yml/badge.svg)](https://github.com/EndstoneMC/bedrock-protocol/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

## Languages

- C++, below
- [Python](python/README.md)
- [Java](java/README.md)
- [Go](go/README.md)

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

std::expected<std::string, bp::EncodeError> data = bp::encode(packet);
assert(data);
std::expected<bp::TextPacket, bp::DecodeError> decoded = bp::decode<bp::TextPacket>(*data);
assert(decoded && *decoded == packet);
```

### Pick a protocol

```cpp
std::optional<bp::ProtocolVersion> version = bp::ProtocolVersion::get(2259);
assert(version && version->getName() == "1.26.70");

std::expected<std::string, bp::EncodeError> pinned = bp::v2259::encode(packet);
assert(pinned);
std::expected<bp::TextPacket, bp::DecodeError> picked = bp::v2259::decode<bp::TextPacket>(*pinned);
assert(picked && *picked == packet);
```

## Supported Protocols

| Protocol | Releases |
| --- | --- |
| 685 | 1.21.0 to 1.21.1 |
| 686 | 1.21.2 to 1.21.3 |
| 712 | 1.21.20 to 1.21.23 |
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
| 2225 | 1.26.60 to 1.26.66 |
| 2259 | 1.26.7x |

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
