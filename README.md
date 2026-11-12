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
| Java | Planned. |
| Rust | Planned. |
| TypeScript | Planned. |

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
import bedrock_protocol as bp

packet = bp.TextPacket()
packet.body = bp.TextPacket.MessageOnly(type=bp.TextPacketType.CHAT, message="hello")
data = bytes(packet)
assert bp.TextPacket.from_bytes(data) == packet
```

`versions` lists the numbers with a `v<N>` module. `releases` lists every number a release reported. `protocol_version(2169)` and `protocol_version("1.26.63")` look one up, and its `snapshot` names the `v<N>` that decodes it. `packets` maps packet ids to packet classes.

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
#include <cassert>

#include <bedrock/protocol.hpp>

namespace bp = bedrock::protocol;

bp::TextPacket packet;
packet.body = bp::TextPacket::MessageOnly{.type = bp::TextPacketType::Chat, .message = "hello"};

std::string data;
bp::BinaryWriter writer{data};
bp::serialize(writer, packet);

bp::BinaryReader reader{data};
std::expected<bp::TextPacket, bp::DecodeError> decoded = bp::decode<bp::TextPacket>(reader);
assert(decoded && *decoded == packet);
```

`bp::protocol_version(2169)` and `bp::protocol_version("1.26.63")` look up the same table in `<bedrock/protocol/version.hpp>`.

`<bedrock/protocol.hpp>` includes everything. `<bedrock/protocol/chunk.h>` and the headers beside it each include one domain.

## Pinning a Protocol Version

The `bp` names follow the latest protocol. To stay on protocol 2225, name it for each type that differs between protocols; a type that never changed, such as `TextPacketType`, keeps its `bp` name.

In Python, import its module:

```python
from bedrock_protocol import v2225

packet = v2225.TextPacket()
packet.body = v2225.TextPacket.MessageOnly(type=bp.TextPacketType.CHAT, message="hello")
```

In C++, pass it as the template argument:

```cpp
bp::TextPacket_<2225> packet;
packet.body = bp::TextPacket_<2225>::MessageOnly{.type = bp::TextPacketType::Chat, .message = "hello"};
```

The rest is unchanged.

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

A number with no `v<N>` module decodes with the newest one below it: 2169 with `v2168`.

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
