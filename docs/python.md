# Python

`bedrock-protocol` binds every packet, type and enum of the schema from the C++ that
bpc generates, so Python reads and writes exactly the bytes the C++ codecs do. One
generic binder walks the reflection each generated module carries, and nothing in it
is written per packet. `bedrock-protocol-compiler` is the schema and `bpc`. Only a
schema author or a source build needs it.

## Versions

A bare name is the latest protocol, as in C++, and `v<N>` pins one:

```python
import bedrock_protocol as bp       # protocol bp.LATEST_PROTOCOL
from bedrock_protocol import v2193  # protocol 2193

bp.PlayStatusPacket                 # bp::PlayStatusPacket
v2193.PlayStatusPacket              # bp::PlayStatusPacket_<2193>
```

A wheel binds the latest protocol and every version in the CMake list
`BEDROCK_PROTOCOL_PYTHON_VERSIONS` (`2193` by default). A type two versions share is
one class.

## Packets and values

```python
packet = v2193.TextPacket(body=v2193.TextPacket.MessageOnly(type=v2193.TextPacketType.CHAT, message="hello"))
framed = v2193.encode_packet(packet)
header, back = v2193.decode_packet(framed)
assert back == packet and header.packet_id == v2193.TextPacket.ID
assert bytes(packet) == framed[1:]
```

- Each version module has `encode(packet)` and `decode(packet_id, body)` for a bare
  body, `encode_packet` and `decode_packet` for a header and a body, `PACKETS`
  mapping every id to its class, and `PROTOCOL`.
- A class takes its fields positionally in declaration order or by keyword, and a
  field it is not given takes its C++ default. `bytes(value)` and
  `Class.from_bytes(data)` work on any value with a wire form, nested ones included.
- Values compare with `==`, print their fields and list them in `__match_args__`.
- A decode that fails or leaves bytes over raises `ValueError` naming the type, the
  reason and the byte offset. An id the version does not model raises `KeyError`.
- Values are mutable. A struct field is a live reference. A list, dict or optional
  field is a copy, so assign a changed one back.
- Enum members keep the schema's `UPPER_CASE` names. A value the schema does not
  name, such as a window id in a `ContainerID` field, reads and writes as an `int`.
- Strings read as `str`, with any byte that is not UTF-8 escaped to a lone surrogate
  so binary fields survive the trip. Setters take `str` or `bytes`. A UUID is a
  `uuid.UUID` and a bitset is an `int`.
- NBT is `bp.nbt`: `CompoundTag({"id": bp.nbt.IntTag(1)})`, `ListTag(tags, type=...)`
  and the scalar tags.

## The packet header

`encode_packet(packet, recipient_sub_id=0, sender_sub_id=0)` writes BDS's header,
one `uvarint32` holding the packet id in bits 0-9, the recipient sub-client in 10-11
and the sender in 12-13. `decode_packet` returns it as a `PacketHeader`.

## Building

The runtime builds from a checkout, which runs bpc, or from a source package that
already holds the generated C++ and needs neither the schema nor the compiler. Native
builds need CMake, Ninja, Conan and a C++23 compiler, and Conan host and build profiles
for it (`-C host-profile=... -C build-profile=...`).

From a checkout, stage the runtime's source tree and build both wheels:

```shell
python scripts/stage_native.py . .local/runtime
python -m build --wheel .local/runtime --outdir dist
python -m build --wheel --outdir dist
```

From generated sources, build the extension with CMake:

```shell
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DBEDROCK_PROTOCOL_BUILD_PYTHON=ON
cmake --build build
cmake --install build --prefix stage --component bedrock_protocol_wheel
```

nanobind is found through `python -m nanobind --cmake_dir` unless `nanobind_DIR` is
set. The extension is built against the stable ABI and the wheel is tagged
`cp312-abi3`.

## Tests

`tests/python` checks the binding: the header, construction, open enums, ownership,
and that every bound class at every bound version survives its own codec. The C++
suite holds the goldens.
