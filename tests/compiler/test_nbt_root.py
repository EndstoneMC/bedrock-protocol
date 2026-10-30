"""Compound payload framing is a field option and part of snapshot identity."""

from harness import CompilerCase

from bedrock_protocol.compiler.nanobind.model import Model
from bedrock_protocol.descriptor import StructType

PREAMBLE = """
from protocol import array, builtin, field, packet, varint32

package = "bedrock.protocol"

@builtin
class CompoundTag:
    pass

class Other:
    pass
"""

VERSIONED = (
    PREAMBLE
    + """
@packet(id=124, until=2193)
class Event:
    event_id: varint32
    data: CompoundTag

@packet(id=124, since=2193, until=2194)
class Event:
    event_id: varint32
    data: CompoundTag = field(nbt_root=False)

@packet(id=124, since=2194)
class Event:
    event_id: varint32
    data: CompoundTag
"""
)


class NbtRoot(CompilerCase):
    def test_framing_survives_merging_and_snapshot_narrowing(self):
        resolved = self.resolve(VERSIONED)
        self.assertEqual([s.lo for s in resolved.fresh_snapshots("Event")], [0, 2193, 2194])
        for version in (*resolved.pool.file_set.supported_versions, 2192, 2194):
            with self.subTest(version=version):
                view = resolved.present_at("Event", version).struct
                data = next(f for f in view.fields if f.name == "data").versions[0]
                self.assertEqual(data.type, StructType("CompoundTag"))
                self.assertEqual(data.nbt_root, version != 2193)

    def test_each_snapshot_gets_its_own_codec_and_latest_stays_supported(self):
        header, source = self.compile(VERSIONED)
        self.assertIn("using Event = Event_<2225>;", header)
        self.assertNotIn("using Event = Event_<2194>;", header)
        for snapshot, namespace in ((0, "base"), (2193, "v2193"), (2194, "v2194")):
            write = self.body(source, f"void Serializer<{namespace}::Event>::serialize")
            read = self.body(source, f"auto Serializer<{namespace}::Event>::deserialize")
            if snapshot == 2193:
                self.assertIn("nbt::writeTag(stream, Tag{value.data});", write)
                self.assertIn("nbt::readTag(stream, nbt::Type::Compound)", read)
                self.assertIn("out.data = std::move(v->get<CompoundTag>());", read)
            else:
                self.assertIn("Serializer<CompoundTag>::serialize", write)
                self.assertIn("Serializer<CompoundTag>::deserialize", read)
        model = Model(self.resolve(VERSIONED))
        self.assertNotIn(2194, model.versions)
        self.assertEqual(set(model.packets), set(model.versions))
        self.assertNotEqual(model.packets[2193][124], model.packets[2225][124])
        self.assertNotEqual(model.packets[2193][124], model.packets[2168][124])

    def test_unrelated_compound_keeps_named_root(self):
        _, source = self.compile(
            PREAMBLE
            + """
@packet(id=1)
class Event:
    payload: CompoundTag = field(nbt_root=False)
    explicit_root: CompoundTag = field(nbt_root=True)
    default_root: CompoundTag
"""
        )
        write = self.body(source, "void Serializer<Event>::serialize")
        self.assertIn("nbt::writeTag(stream, Tag{value.payload});", write)
        self.assertIn("Serializer<CompoundTag>::serialize(stream, value.explicit_root);", write)
        self.assertIn("Serializer<CompoundTag>::serialize(stream, value.default_root);", write)

    def test_non_boolean_values_reject(self):
        for value in ("0", "1", "None", '"False"', "[]"):
            with self.subTest(value=value):
                message = self.rejects(
                    PREAMBLE
                    + f"""
@packet(id=1)
class Event:
    data: CompoundTag = field(nbt_root={value})
"""
                )
                self.assertIn("nbt_root=...) takes True or False", message)

    def test_non_direct_compounds_reject_even_with_explicit_default(self):
        for target in (
            "varint32",
            "Other",
            "list[CompoundTag]",
            "CompoundTag | None",
            "array[CompoundTag, 2]",
            "dict[str, CompoundTag]",
            "CompoundTag | Other",
        ):
            for value in ("True", "False"):
                with self.subTest(target=target, value=value):
                    message = self.rejects(
                        PREAMBLE
                        + f"""
@packet(id=1)
class Event:
    data: {target} = field(nbt_root={value})
"""
                    )
                    self.assertIn("only to a direct CompoundTag field", message)
