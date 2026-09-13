# bedrock-protocol

> Version-aware C++ packet codecs for the Minecraft: Bedrock protocol, generated from a Python schema.

[![CI](https://github.com/EndstoneMC/bedrock-protocol/actions/workflows/ci.yml/badge.svg)](https://github.com/EndstoneMC/bedrock-protocol/actions/workflows/ci.yml)

Bedrock's wire format moves between protocol versions: fields appear, packets get
reordered, and whole packets migrate to BDS's Cereal serialization. This repository
holds one schema covering every version it supports, and a protoc-shaped compiler
(`bpc`) that turns it into C++ types and serializers — one shape per version, so a
consumer names the version it wants and gets a compile error if it asks for a field
that era never had.

## Versions

| protocol | Minecraft |
| --- | --- |
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
| 2192 | 1.26.50 |
| 2208 | 1.26.60.23 |

## Example

The schema lives in `protocol/*.py`. A packet whose shape changed is declared once
per era; anything smaller carries its own version range:

```python
@packet(id=175, until=1001)
class SubChunkRequestPacket:
    dimension_type: DimensionType
    center_pos: SubChunkPos
    sub_chunk_pos_offsets: list[SubChunkPacket.SubChunkPosOffset] = field(prefix=uint32)


@packet(id=175, since=1001)
class SubChunkRequestPacket:
    dimension_type: DimensionType
    sub_chunk_pos_offsets: list[SubChunkPacket.SubChunkPosOffset]
    center_pos: SubChunkPos
```

Cerealising this packet both moved `center_pos` behind the offsets and swapped the
offset count from a fixed `uint32` to a varint; the schema gates that at 1001. The
compiler emits one struct per version behind a selector alias, so both eras are
reachable from a single name and the one you spell decides which bytes you get:

```cpp
#include <bedrock/protocol.hpp>

namespace bp = bedrock::protocol;
using Packet = bp::SubChunkRequestPacket_<975>;

Packet packet;
packet.dimension_type = bp::DimensionType{0};
packet.center_pos = {.x = 1, .y = 2, .z = 3};
packet.sub_chunk_pos_offsets.push_back({.x = -1, .y = 0, .z = 1});

std::string buffer;
bp::BinaryWriter writer{buffer};
bp::serialize(writer, packet);  // 11 bytes here, 17 at 1001

bp::BinaryReader reader{buffer};
std::expected<Packet, std::error_code> back = bp::deserialize<Packet>(reader);
```

Unversioned types keep their plain name; `bp::SubChunkRequestPacket` without the
suffix is the latest version.

## Reflection

Everything the compiler knows about a generated enum, packet or struct is emitted
alongside it, so a consumer can ask at compile time. There is no macro to register a
type and nothing to keep in sync — the tables come out of the same schema the codecs
do.

```cpp
namespace bp = bedrock::protocol;
using Packet = bp::SubChunkRequestPacket_<975>;

// Enums carry their enumerators in declaration order, and the lowercased names
// BDS writes for a name-coded field.
static_assert(bp::enum_count<bp::BossBarColor>() == 8);
static_assert(bp::enum_name(bp::BossBarColor::Red) == "red");
static_assert(bp::enum_cast<bp::BossBarColor>("RED") == bp::BossBarColor::Red);

// A packet id resolves to the type that version modelled, and to `void` otherwise.
static_assert(std::is_same_v<bp::packet_of_t<975, 175>, Packet>);
static_assert(bp::has_packet_v<2208, 353>);   // ClientboundMatchmakingStatePacket
static_assert(!bp::has_packet_v<2192, 353>);  // ... which 1.26.50 did not have

// A struct carries its name and its members, so the reorder above is a fact you
// can assert on rather than something to go read out of the header.
static_assert(bp::struct_name<Packet>() == "SubChunkRequestPacket");
static_assert(bp::field_count<Packet>() == 3);
static_assert(bp::field_name<1, bp::SubChunkRequestPacket_<975>>() == "center_pos");
static_assert(bp::field_name<1, bp::SubChunkRequestPacket_<1001>>() == "sub_chunk_pos_offsets");
static_assert(!bp::field_contains<Packet>("cache_enabled"));
```

`for_each_named_field` expands a pack rather than erasing to a variant, so every
member arrives under its own static type and a walk can recurse into nested structs:

```cpp
void dump(std::string_view name, const auto &value, int indent = 0)
{
    using T = std::remove_cvref_t<decltype(value)>;
    if constexpr (bp::Reflected<T>) {
        std::println("{:{}}{} : {}", "", indent, name, bp::struct_name<T>());
        bp::for_each_named_field(value, [indent](std::string_view member, const auto &v) {
            dump(member, v, indent + 2);
        });
    }
    else if constexpr (std::ranges::input_range<T>) {
        for (const auto &item : value) {
            dump(name, item, indent);
        }
    }
    else {
        std::println("{:{}}{} = {}", "", indent, name, static_cast<std::int64_t>(value));
    }
}

dump("packet", packet);
```

```text
packet : SubChunkRequestPacket
  dimension_type = 0
  center_pos : SubChunkPos
    x = 1
    y = 2
    z = 3
  sub_chunk_pos_offsets : SubChunkPacket::SubChunkPosOffset
    x = -1
    y = 0
    z = 1
```

`field_get` reaches one member by index, and `field_index` is consteval, so naming a
member by string costs nothing at runtime and a typo is a compile error rather than a
miss:

```cpp
bp::field_get<bp::field_index<Packet>("center_pos")>(packet).y = 9;
```

The enum surface follows [magic_enum](https://github.com/Neargye/magic_enum) and the
struct surface follows [Boost.PFR](https://github.com/boostorg/pfr), spelled the same
way but without the limits each works around: no bounded value range to scan, no
arity cap, no aggregate requirement, and member names on every compiler. A type the
compiler did not emit is simply unreflected rather than an error, so `bp::Reflected`
is safe to branch on.

## Building

Requires CMake, a C++23 compiler, and [uv](https://docs.astral.sh/uv/), which runs
the compiler during the build. CI covers GCC (libstdc++), Clang 18 (libc++) and
MSVC.

```shell
cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
```

`BEDROCK_PROTOCOL_BUILD_TESTS` and `BEDROCK_PROTOCOL_INSTALL` both default to on for a
top-level build and off when the project is added as a subdirectory.

Code generation is wired into the build, but `bpc` can be run directly:

```shell
uv run bpc --language cpp --out build/protocol --import-path . protocol/inventory.py
```

## Using it

As a subproject. Code generation runs during the build, so this needs uv on the
consumer's machine too:

```cmake
add_subdirectory(bedrock-protocol)
target_link_libraries(my_target PRIVATE bedrock::protocol)
```

Or install it once and consume the built artifacts, which needs no Python at all:

```shell
cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/opt/bedrock-protocol
cmake --build build
cmake --install build
```

```cmake
find_package(bedrock-protocol CONFIG REQUIRED)
target_link_libraries(my_target PRIVATE bedrock::protocol)
```

The install tree:

| path | |
| --- | --- |
| `include/bedrock/protocol.hpp` | umbrella — the runtime plus every generated header |
| `include/bedrock/protocol/*.h` | one generated header per packet family, each paired with a compiled `.cpp` |
| `include/bedrock/protocol/*.hpp` | header-only runtime — binary streams, `Serializer`, NBT, UUID |
| `include/bedrock/protocol/detail/` | plumbing the generated code leans on, not meant to be included directly |
| `lib/libbedrock_protocol.a` | the generated serializer bodies |
| `lib/cmake/bedrock-protocol/` | the CMake package `find_package` resolves |

A consumer that only touches one family can include `<bedrock/protocol/inventory.h>`
rather than the umbrella.

## Layout

| path | |
| --- | --- |
| `protocol/` | the schema — one module per BDS domain, named after its folder in the game tree |
| `src/bedrock_protocol/` | the compiler: `compiler/` (parser, descriptors, pool) and `compiler/cpp/` (backend) |
| `include/bedrock/protocol/` | hand-written runtime — binary streams, the `Serializer` entry point, NBT |
| `tests/` | per-packet round-trip tests against goldens generated by running gophertunnel |

Wire shapes are taken from [protocol-docs](https://github.com/EndstoneMC/protocol-docs),
names and C++ types from reverse-engineered BDS headers, and golden bytes from
[gophertunnel](https://github.com/Sandertv/gophertunnel). `CLAUDE.md` documents those
sources and the conventions the schema follows.

## License

MIT. See [LICENSE](LICENSE).
