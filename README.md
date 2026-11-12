<div align="center">

<h3>bedrock-protocol</h3>

<p>
  <b>The Minecraft: Bedrock Edition network protocol as one schema</b><br>
  One library for C++ and Python that encodes and decodes every supported protocol version
</p>

[![CI](https://github.com/EndstoneMC/bedrock-protocol/actions/workflows/ci.yml/badge.svg)](https://github.com/EndstoneMC/bedrock-protocol/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

## Languages

Every language exposes the same packets, types and enums, and encodes the same bytes.

| Language | Get it |
| --- | --- |
| [Python](#python) | Download a wheel from the [releases](https://github.com/EndstoneMC/bedrock-protocol/releases). It is not on PyPI. |
| [C++](#c) | Download a package from the [releases](https://github.com/EndstoneMC/bedrock-protocol/releases). |

## Python

Each release carries a wheel for Linux and Windows on x86_64, for Python 3.12 or newer:

```shell
uv pip install bedrock_protocol-X.Y.Z-cp312-abi3-linux_x86_64.whl
```

To build it from a checkout instead, you need CMake and a C++23 compiler:

```shell
git clone https://github.com/EndstoneMC/bedrock-protocol
uv pip install ./bedrock-protocol
```

```python
from bedrock_protocol import TextPacket, TextPacketType, decode_packet, encode_packet

packet = TextPacket(body=TextPacket.MessageOnly(type=TextPacketType.CHAT, message="hello"))
header, back = decode_packet(encode_packet(packet))
assert back == packet and header.packet_id == TextPacket.ID
```

`VERSIONS` lists the protocol numbers. `PACKETS` maps packet ids to packet classes.

## C++

Each release carries these packages:

| Asset | Contents |
| --- | --- |
| `bedrock-protocol-X.Y.Z-linux-x86_64-gcc13.zip` | Linux, GCC 13, libstdc++ |
| `bedrock-protocol-X.Y.Z-linux-x86_64-clang18-libcxx.zip` | Linux, Clang 18, libc++ |
| `bedrock-protocol-X.Y.Z-windows-x86_64-msvc2022.zip` | Windows, MSVC 2022 |
| `bedrock-protocol-X.Y.Z-src.zip` | Sources, for `add_subdirectory` |

Unpack a package and point `CMAKE_PREFIX_PATH` at the folder:

```cmake
find_package(bedrock-protocol CONFIG REQUIRED)
target_link_libraries(my_target PRIVATE bedrock::protocol)
```

With the source package, replace `find_package` with `add_subdirectory(bedrock-protocol-X.Y.Z-src)`. Neither needs
Python. The library needs C++23.

```cpp
#include <bedrock/protocol.hpp>

namespace bp = bedrock::protocol;
using Packet = bp::SubChunkRequestPacket;

Packet packet;
packet.dimension_type = bp::DimensionType{0};
packet.center_pos = {.x = 1, .y = 2, .z = 3};

std::string bytes;
bp::BinaryWriter writer{bytes};
bp::serialize(writer, packet);

bp::BinaryReader reader{bytes};
std::expected<Packet, bp::DecodeError> decoded = bp::decode<Packet>(reader);
```

`<bedrock/protocol.hpp>` includes everything. `<bedrock/protocol/chunk.h>` and the headers beside it each include one domain.

## Pinning a Protocol Version

The bare names follow the latest protocol. To stay on protocol 2225, name it.

In Python, import its module:

```python
from bedrock_protocol import v2225

packet = v2225.TextPacket(body=v2225.TextPacket.MessageOnly(type=v2225.TextPacketType.CHAT, message="hello"))
```

In C++, pass it as the template argument:

```cpp
using Packet = bedrock::protocol::SubChunkRequestPacket_<2225>;
```

## Supported Protocols

- 729: 1.21.30
- 748: 1.21.40
- 766: 1.21.50
- 776: 1.21.60
- 786: 1.21.70
- 800: 1.21.80
- 818: 1.21.90
- 819: 1.21.93
- 827: 1.21.100
- 844: 1.21.111
- 859: 1.21.120
- 898: 1.21.132
- 924: 1.26.3
- 944: 1.26.14
- 975: 1.26.20
- 1001: 1.26.30
- 2168: 1.26.40
- 2193: 1.26.50
- 2225: 1.26.60

## Building from Source

You need CMake, Ninja, Python 3.12 or newer and a C++23 compiler:

```shell
cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
cmake --install build --prefix stage
```

`stage` holds the same tree as a C++ release package.

## License

MIT, see [LICENSE](LICENSE).
