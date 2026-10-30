import pytest

import bedrock_protocol as bp


def replace(value, **changes):
    fields = {name: getattr(value, name) for name in value.to_dict()}
    return type(value)(**(fields | changes))


@pytest.mark.parametrize(
    "version,number,canonical_name",
    [
        (2168, 50, "CLONE_PARTIAL_BED_BLOCK_FIX"),
        (2193, 52, "TIME_OF_COMMAND_OVERLOADS"),
        (2225, 55, "UNKNOWN_055"),
    ],
)
def test_current_command_version_latest_wire_alias(version, number, canonical_name, golden):
    codec = bp.Codec(version)
    module = getattr(bp, f"v{version}")
    latest = module.CurrentCmdVersion.LATEST
    assert latest == number
    assert latest is getattr(module.CurrentCmdVersion, canonical_name)
    assert latest.name == canonical_name

    data = golden(77, "test_077_command_request.cpp")
    old_version = b"\x2atestforblockcommanddoesnotignoreblockstate"
    assert data.endswith(old_version)
    expected = data.removesuffix(old_version) + b"\x06latest"
    original = codec.decode_packet(data).payload
    packet = replace(original, version=latest)
    assert codec.encode_packet(packet) == expected
    decoded = codec.decode_packet(expected).payload
    assert decoded.version is latest
    assert codec.encode_packet(decoded) == expected


def test_update_block_runtime_id_accepts_an_ordinary_int(golden):
    codec = bp.Codec(2193)
    data = golden(21, "test_021_update_block.cpp")
    original = codec.decode_packet(data).payload
    assert type(original.runtime_id) is int
    assert original.runtime_id == 300
    packet = bp.v2193.UpdateBlockPacket(pos=original.pos, runtime_id=300, update_flags=3, layer=1)
    assert type(packet.runtime_id) is int
    assert codec.encode_packet(packet) == data
    assert codec.decode_packet(codec.encode_packet(packet)).payload.runtime_id == 300


def test_crafting_block_runtime_id_retains_signed_varint_override(golden):
    codec = bp.Codec(1001)
    data = golden(52, "test_052_crafting_data.cpp")
    packet = codec.decode_packet(data).payload
    entry = packet.crafting_entries[0]
    recipe = entry.shaped_recipe
    item = recipe.results[0]
    assert type(item.block_runtime_id) is int
    assert item.block_runtime_id == 9
    rebuilt_item = replace(item, block_runtime_id=9)
    entries = list(packet.crafting_entries)
    entries[0] = replace(entry, shaped_recipe=replace(recipe, results=[rebuilt_item]))
    rebuilt = replace(packet, crafting_entries=entries)
    assert codec.encode_packet(rebuilt) == data
    assert codec.decode_packet(data).payload.crafting_entries[0].shaped_recipe.results[0].block_runtime_id == 9


def test_biome_block_runtime_id_retains_fixed_uint32_override(golden):
    codec = bp.Codec(1001)
    data = golden(122, "test_122_biome_definition_list.cpp", "golden_gradient_v1001")
    packet = codec.decode_packet(data).payload
    definition = packet.biome_data[0]
    chunk = definition.chunk_gen_data
    surface = chunk.surface_builder_data
    gradient = surface.noise_gradient_surface
    specifier = gradient.gradient_block_ranges[0]
    assert type(specifier.block_runtime_id) is int
    assert specifier.block_runtime_id == 9
    specifier = replace(specifier, block_runtime_id=9)
    gradient = replace(gradient, gradient_block_ranges=[specifier])
    surface = replace(surface, noise_gradient_surface=gradient)
    chunk = replace(chunk, surface_builder_data=surface)
    definition = replace(definition, chunk_gen_data=chunk)
    rebuilt = replace(packet, biome_data={0: definition})
    assert codec.encode_packet(rebuilt) == data
    decoded = codec.decode_packet(codec.encode_packet(rebuilt)).payload
    gradient = decoded.biome_data[0].chunk_gen_data.surface_builder_data.noise_gradient_surface
    assert gradient.gradient_block_ranges[0].block_runtime_id == 9
