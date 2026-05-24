"""Synthetic compiler-coverage exercise for `dict[K, V]` (MappingType).

No real BDS packet currently uses a map-typed field, so MappingType codegen
has no end-to-end exerciser. `BiomeDefinitionListPacket` (v975) will, so this
file lands a minimal synthetic packet that the C++ test suite can round-trip
to prove the parser, resolver, type emitter, and serializer all agree.

These declarations are test scaffolding -- the `Test*` prefix and the
out-of-range `id=9999` make that explicit so a reader does not confuse them
with a real Mojang type.
"""

from protocol import field, packet, uint16, uvarint32

package = "bedrock.protocol"


class TestMappingValue:
    label: str
    weight: uint16


@packet(id=9999)
class TestMappingPacket:
    entries: dict[uint16, TestMappingValue] = field(prefix=uvarint32)
