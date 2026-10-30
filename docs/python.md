# Python protocol guide

`bedrock-protocol` supplies the pure Python schema compiler and `bpc` command.
`bedrock-protocol-native` supplies the native runtime, version modules and type
stubs, with an exact dependency on its matching compiler distribution. The two
packages own disjoint files; removing the native package leaves the compiler
available. Both require Python 3.12 or newer.

The runtime covers every active packet and dependent type in the 19
[supported schema versions](../README.md#supported-protocols).
`SUPPORTED_VERSIONS` lists them; `Codec.supported_packet_ids` and
`Codec.known_packet_ids` are matching readonly tuples of active IDs for a codec.

## Encode and decode packets

```python
from bedrock_protocol import Codec, DecodeLimits, v2193
from bedrock_protocol.wire import BatchCodec

codec = Codec(2193, limits=DecodeLimits())
request = v2193.RequestNetworkSettingsPacket(client_network_version=2193)
wire = codec.encode_packet(request)

decoded = codec.decode_packet(wire)
assert decoded.header.packet_id == 193
assert decoded.payload.client_network_version == 2193

batch = BatchCodec(codec)
message = batch.encode([request])
assert batch.decode(message)[0].payload.client_network_version == 2193
```

A schema-unknown ID produces an owned `UnknownPacket`, whose body can be inspected
or forwarded. Known parse errors and trailing body bytes fail decoding.
`ProtocolError` exposes `protocol`, packet ID, `reason` and an offset when available.

## Construct values

All nonliteral fields are required keyword arguments, including explicit `None`
for absent optional or conditional fields. A false condition exposes `None` and
rejects a supplied value. Literal fields are readonly constants. Unions use
`Variant(index, value)`; optionals use a value or `None`. Enum fields require the
matching generated `IntEnum`. Unknown numeric values retain that type within its
underlying range; a name-coded value must have a wire name.

Integers outside a narrower field encoding raise `TypeError`. Same-width
signed/unsigned mappings retain their bit patterns. Sequences exceeding their
length prefix's nonnegative range raise `ValueError`; explicit count fields must
match sequence length. Mapping inputs, including NBT compounds, require `items()`
to yield actual 2-tuples; other entry types or lengths raise `TypeError`.

Version modules alias shared native shapes. Constructed values have
`protocol is None`: access through `v2193` does not attach a version origin.
Decoded envelopes and subviews retain the decoding protocol. `encode_packet`
checks that the actual packet shape exists in the codec's version.

`DynamicValue` aliases `Variant`. Every node has an explicit tag: 0 for `None`,
1 for `bool`, 2 for signed 64-bit `int` excluding `bool`, 3 for `float`, 4 for `str`,
5 for an array and 6 for a string-keyed object. Children are also `Variant` values.
Arrays accept lists, tuples or matching native sequence views; objects accept
dictionaries or matching native map views. Cycles and nesting beyond 128
DynamicValue nodes are rejected; repeated acyclic references are copied.

## Ownership and materialization

Values, sequences, maps and binary fields own immutable native storage. Retained
children, iterators and readonly buffers remain valid after their parent and codec
are destroyed. Construction snapshots mutable buffers and containers.

`copy()` detaches a selected subtree. `to_dict()`, `to_list()` and `to_bytes()`
explicitly materialize values. `wire_bytes()` re-encodes a value's body; it does
not promise the original spelling of noncanonical input.

Binary fields such as photo data, resource-pack hashes, compressed biome data and
serialized sub-chunks return `BinaryView`. Conditional and optional absence is
preserved for the selected protocol. Compressed biome bytes remain opaque;
packet 301 is absent from protocol 800 onward.

Binary views export readonly format `B`; NBT byte arrays export signed format `b`.
NBT preserves tag kinds, including an empty list's element kind:

```python
from bedrock_protocol import Nbt, NbtType

empty_ints = Nbt(NbtType.LIST, [], element_type=NbtType.INT)
signed = Nbt(NbtType.BYTE_ARRAY, [-1, 0, 127])
assert memoryview(signed).format == "b"
```

Text converts strictly to UTF-8 when accessed as a Python string. Malformed text
may decode and later raise `UnicodeDecodeError` in a getter or `to_dict()`,
including NBT string values. Invalid NBT compound names raise `RuntimeError`
during iteration or materialization. Re-encoding preserves their native bytes.
A later text conversion failure does not make `BatchCodec` terminal.

## Batches and prepared packets

`Codec` is immutable and permits independent calls from different threads.
`BatchCodec` belongs to its creating thread and one connection; reentrant and
cross-thread calls are rejected. Fatal decode failure makes it terminal, including
configuration and encode calls.

`Codec.prepare_packet(packet, sender_subclient_id=0, target_subclient_id=0)` uses
the same serializer and validation as `encode_packet` and returns an immutable
`EncodedPacket`. Its readonly `protocol`, `packet_id` and `len(token)` describe
owned bytes including the subclient header. Tokens survive destruction of their
codec and source packet and have no public constructor or buffer interface.

```python
prepared = codec.prepare_packet(request)
message = batch.encode_prepared([prepared])
```

`encode_prepared` retains every token during the native call and accepts tokens
from any codec with the same protocol. A non-token raises `TypeError`; a different
protocol raises `EncodeError` with reason `prepared_packet_protocol_mismatch`.
Iterable, type and protocol failures occur before encryption advances. Packet and
batch limits still apply. Compression and encryption use the batch configuration
at send time, so tokens can survive a negotiated configuration change.

Wait for transport backpressure before `encode()` or `encode_prepared()`.
Successful encoding advances cipher state: send every returned message in order.
Argument validation before cipher mutation may fail without consuming the cipher.
Change compression or encryption at the negotiated boundary after processing the
current batch and before decoding the next. Batch framing supports raw DEFLATE,
Snappy, no compression, checksum and directional counters; it adds no RakNet
`0xFE` prefix.

## Selection and error recovery

`decode(data, packet_ids=...)` filters bodies after validating every frame length
and header. `PacketBatch.headers`, `packet_count`, `decoded_count`, `filtered` and
`skipped_packet_ids` describe selection. Unselected bodies may remain undecoded.
By default, a selected-body failure rejects the entire batch and makes the codec
terminal.

`decode(data, recover_packet_errors=True)` recovers isolated malformed bodies.
Successful values keep their normal immutable storage. `PacketBatch.errors` is a
readonly tuple of owned `PacketDecodeError` values in wire order: `protocol`,
zero-based `packet_index` into `headers`, `header`, frame-relative `offset`
(including its header) and `reason`.

Errors are distinct from filtered skips:
`packet_count == decoded_count + len(skipped_packet_ids) + len(errors)`.
Unknown IDs still yield `UnknownPacket`; every active known packet has a typed binding.

Recovery covers malformed fields, truncation, discriminators, constants, varints,
scalar narrowing, bitset overflow and trailing body bytes. Framing, compression,
decryption, checksum, any packet header, resource limits and unexpected native
exceptions remain fatal and return no partial batch. Headers validate before any
body. Failed bodies retain their charges in the cumulative batch budget. A
recovered batch consumes encryption state normally; lazy text conversion remains
separate and is not validated eagerly by recovery.

## Resource limits

Defaults are 4 MiB per packet, 16 MiB per decompressed batch, 4096 packets,
128 nesting levels, 1,048,576 decoded container elements and 64 MiB of accounted
decoded storage. `DecodeLimits` configures depth, elements and storage; depth
cannot exceed 128.

Accounting covers string/binary bytes and native container elements, not process
RSS or allocator overhead. Nested readers share one packet budget; selected
bodies share one batch budget. Enclosing schema scopes count toward nesting, so
an NBT subtree's depth alone does not determine whether decoding fits. Successful
construction, copying, materialization or encoding does not establish that a value
fits a decode budget.

## Building

The compiler uses the root `pyproject.toml`; native distribution metadata is in
`pyproject.native.toml`. Build requirements and dependency versions are declared
there. Native wheels must match the target Python interpreter and platform.

From the repository root, build the pure compiler wheel and source distribution:

```shell
python -m pip install build
python -m build --outdir dist
```

Native builds need CMake, Ninja, Conan and a compatible C++23 toolchain. Configure
Conan host and build profiles for that compiler and standard library. The example
uses a profile named `delivery`; on Windows, the repository provides a
[clang-cl profile](../cmake/conan/windows-clang.profile) for a Visual Studio
developer prompt. Use a private Conan home for local builds.

Stage native build inputs into a new directory, build its source distribution,
then build the wheel from that extracted archive:

```shell
python scripts/stage_native.py . .local/native-source
python -m build --sdist .local/native-source --outdir dist
mkdir .local/native-sdist
tar -xf dist/bedrock_protocol_native-0.5.0.dev0.tar.gz -C .local/native-sdist
python -m build --wheel .local/native-sdist/bedrock_protocol_native-0.5.0.dev0 --outdir dist -C host-profile=delivery -C build-profile=delivery -C build-dir=.local/native-build
```

The staging destination must not exist. Adjust archive filenames to the package
version being built and profile arguments to your toolchain. Staging leaves the
checkout's compiler metadata unchanged. The native archive is self-contained.

Install the compiler and native wheels in a test environment, selecting the native
filename for its Python/platform tag, then run the compiler and native API tests:

```shell
python -m pip install pytest dist/bedrock_protocol-0.5.0.dev0-py3-none-any.whl NATIVE_WHEEL
python -I -m pytest tests/compiler tests/python
```

Replace `NATIVE_WHEEL` with the path produced by the native build.

For standalone C++, leaving `BEDROCK_PROTOCOL_BUILD_PYTHON` and
`BEDROCK_PROTOCOL_BUILD_WIRE` off avoids native Python and wire dependencies.
Enabling wire support adds `bedrock::protocol_wire`. C++ and Python packages have
independent package versions.

Code generation uses the build interpreter and source compiler without installing
the native extension first. Native wheels include every supported version module
and type stub; native source distributions include the inputs needed to regenerate
them. Pregenerated C++ releases need no Python compiler. See the
[C++ build instructions](../README.md#building).
