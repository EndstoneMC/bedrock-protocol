# bedrock-protocol

Typed packet codecs for Minecraft Bedrock, generated from one version-aware
Python schema. Use the C++ library for native applications, the Python runtime
for immutable packet values and codecs, or `bpc` to compile schemas.

[![CI](https://github.com/EndstoneMC/bedrock-protocol/actions/workflows/ci.yml/badge.svg)](https://github.com/EndstoneMC/bedrock-protocol/actions/workflows/ci.yml)

## Python

The `bedrock-protocol` distribution contains the schema compiler and `bpc` command.
`bedrock-protocol-native` adds the native runtime, generated version modules and
type stubs, and requires the matching compiler distribution. Compiler-only use
does not require a native toolchain. See the [Python guide](docs/python.md) for
installation, packet construction, limits and ownership.

```python
from bedrock_protocol import Codec, v2193

codec = Codec(2193)
packet = v2193.RequestNetworkSettingsPacket(client_network_version=2193)
wire = codec.encode_packet(packet)
decoded = codec.decode_packet(wire)
assert decoded.payload.client_network_version == 2193
```

## C++

Choose a protocol explicitly with the generated selector aliases. A type without
a version suffix names the latest shape; fields unavailable in the selected era
are absent from that type.

```cpp
#include <bedrock/protocol.hpp>

namespace bp = bedrock::protocol;
using Packet = bp::SubChunkRequestPacket_<975>;

Packet packet;
packet.dimension_type = bp::DimensionType{0};
packet.center_pos = {.x = 1, .y = 2, .z = 3};
packet.sub_chunk_pos_offsets.push_back({.x = -1, .y = 0, .z = 1});

std::string bytes;
bp::BinaryWriter writer{bytes};
bp::serialize(writer, packet);

bp::BinaryReader reader{bytes};
std::expected<Packet, std::error_code> decoded = bp::deserialize<Packet>(reader);
```

Link the library as a subproject:

```cmake
add_subdirectory(bedrock-protocol)
target_link_libraries(my_target PRIVATE bedrock::protocol)
```

Or consume an installed package:

```cmake
find_package(bedrock-protocol CONFIG REQUIRED)
target_link_libraries(my_target PRIVATE bedrock::protocol)
```

The umbrella header includes every generated family. Include an individual header
such as `<bedrock/protocol/inventory.h>` when only that family is needed.

## Supported protocols

Both runtimes cover the active packet shapes and their dependent types in these
schema versions. Retired packets and declaration gaps remain absent in the
corresponding version. Python exposes the exact list as `SUPPORTED_VERSIONS` and
active IDs through `Codec.supported_packet_ids`.

| Protocol | Minecraft Bedrock |
| --- | --- |
| 729 | 1.21.30 |
| 748 | 1.21.40 |
| 766 | 1.21.50 |
| 776 | 1.21.60 |
| 786 | 1.21.70 |
| 800 | 1.21.80 |
| 818 | 1.21.90 |
| 819 | 1.21.93 |
| 827 | 1.21.100 |
| 844 | 1.21.111 |
| 859 | 1.21.120 |
| 898 | 1.21.132 |
| 924 | 1.26.3 |
| 944 | 1.26.14 |
| 975 | 1.26.20 |
| 1001 | 1.26.30 |
| 2168 | 1.26.40 |
| 2193 | 1.26.50.5 |
| 2225 | 1.26.60.30 |

## Reflection

Generated enums, structs and packets carry compile-time metadata from the same
schema as their codecs:

```cpp
static_assert(bp::enum_name(bp::BossBarColor::Red) == "red");
static_assert(bp::enum_cast<bp::BossBarColor>("RED") == bp::BossBarColor::Red);
static_assert(std::is_same_v<bp::packet_of_t<975, 175>, Packet>);
static_assert(!bp::has_packet_v<2193, 353>);
static_assert(bp::field_name<1, Packet>() == "center_pos");
```

Use `for_each_named_field` to visit members with their static types, and
`field_get<field_index<T>("name")>` to access a member by compile-time name.
`Reflected<T>` is safe to test for types outside the generated schema. Enum
metadata preserves declaration order and the wire names of name-coded fields.

## Building

Requires CMake and a C++23 compiler. Building a checkout also requires Python
3.12+ and the compiler dependencies declared in `pyproject.toml`. Pregenerated C++
source releases and installed C++ packages need no Python.

```shell
cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
```

Code generation is part of the build. `BEDROCK_PROTOCOL_BUILD_TESTS` and
`BEDROCK_PROTOCOL_INSTALL` default to on for top-level builds and off for
subprojects. `BEDROCK_PROTOCOL_BUILD_PYTHON` and `BEDROCK_PROTOCOL_BUILD_WIRE` are
optional and default to off. The wire target is `bedrock::protocol_wire`.

Install the C++ headers, library and CMake package with `cmake --install build`.
Set `CMAKE_INSTALL_PREFIX` at configuration time to choose the destination.
Python distribution builds are described in the [Python guide](docs/python.md#building).

## Contributing

Schemas live in `protocol/`; the compiler and its backends live in
`src/bedrock_protocol/`. Hand-written C++ runtime headers are under
`include/bedrock/protocol/`. Keep schema changes version-aware and retain older
shapes when the wire format changes.

Wire definitions draw on [protocol-docs](https://github.com/EndstoneMC/protocol-docs),
BDS type information and [gophertunnel](https://github.com/Sandertv/gophertunnel)
golden bytes. See `CLAUDE.md` for schema conventions and source attribution.

## License

The original C++ library, schema and compiler use [MIT](LICENSE). Native attribution
is in [the wire notice](src/wire/NOTICE) and [the Python extension notice](src/python/NOTICE).
