import ast
import subprocess
import sys
from contextlib import contextmanager
from enum import IntEnum
from io import StringIO

from harness import CompilerCase

from bedrock_protocol.compiler.nanobind.generator import NanobindGenerator


class Context:
    def __init__(self):
        self.files = {}

    @contextmanager
    def open(self, name):
        out = StringIO()
        yield out
        self.files[name] = out.getvalue()


class NanobindContract(CompilerCase):
    def generate(self, source, imports=None):
        resolved = self.resolve(source, imports=imports)
        context = Context()
        NanobindGenerator().generate(resolved, context)
        return resolved, context

    def test_typed_shapes_aliases_fields_and_keyword_escape(self):
        resolved, result = self.generate("""
from enum import IntEnum
from typing import Literal
from protocol import field, packet, uint8, uvarint32
package = "bedrock.protocol"

@packet(id=7)
class Root:
    class Kind(IntEnum, uint8):
        FIRST = 0
        SECOND = 1
    class Child:
        pass_: uvarint32
    fixed: Literal[True]
    kind: Kind
    child: Child
    extra: uvarint32 = field(since=2193)
    maybe: uvarint32 | None
    union: bool | uvarint32
""")
        cpp = result.files["mod.cpp"]
        assert 'nb::arg("pass_")' in cpp
        assert 'nb::arg("fixed")' not in cpp
        assert "nb::kw_only()" in cpp
        assert "Union<Scalar<bool>, Scalar<std::uint32_t>>" in cpp
        assert "Optional<Scalar<std::uint32_t>>" in cpp
        assert cpp.count("EnumMarker<") == 1
        assert cpp.count("using T = bedrock::protocol::base::Root::Child;") == 1
        old, new = result.files["bedrock_protocol/v1001.pyi"], result.files["bedrock_protocol/v2193.pyi"]
        assert "extra:" not in old and "extra: int" in new
        assert "pass_: int" in old
        assert "union: Variant[bool | int]" in old
        assert "maybe: int | None" in old
        assert "fixed: " not in old
        ast.parse(old)
        ast.parse(new)
        again = Context()
        NanobindGenerator().generate(resolved, again)
        assert result.files == again.files

    def test_derived_enum_values_follow_each_snapshot_and_preserve_aliases(self):
        _, result = self.generate("""
from enum import auto, Enum
from protocol import field, packet, value
package = "bedrock.protocol"

class Version(Enum):
    FIRST = 1
    SECOND = value(2, since=2193)
    COUNT = auto()
    LATEST = COUNT - 1
    CHAINED = LATEST

@packet(id=7)
class Root:
    version: Version = field(type=str)
""")
        cpp = result.files["mod.cpp"]
        for version, number, canonical in ((1001, 1, "FIRST"), (2193, 2, "SECOND")):
            stub = ast.parse(result.files[f"bedrock_protocol/v{version}.pyi"])
            declaration = next(node for node in stub.body if isinstance(node, ast.ClassDef) and node.name == "Version")
            namespace = {"IntEnum": IntEnum}
            exec(compile(ast.Module(body=[declaration], type_ignores=[]), "<generated stub>", "exec"), namespace)
            enum = namespace["Version"]
            assert enum.COUNT == number + 1
            assert enum.LATEST == enum.CHAINED == number
            assert enum.LATEST is enum.CHAINED is getattr(enum, canonical)
            assert enum.LATEST.name == canonical
            for name in ("LATEST", "CHAINED"):
                assert cpp.count(f'members["{name}"] = nb::int_({number}LL);') == 1

    def test_conditional_value_cannot_be_silently_omitted(self):
        _, result = self.generate("""
from protocol import field, packet, uint8
package = "bedrock.protocol"
@packet(id=1)
class Root:
    enabled: bool
    value: uint8 = field(when=lambda p: p.enabled == 1)
""")
        cpp = result.files["mod.cpp"]
        assert "must be None when its condition is false" in cpp
        assert "return nb::none()" in cpp
        assert "value: int | None" in result.files["bedrock_protocol/v1001.pyi"]
        assert "Root: TypeAlias = _v1001.Root" in result.files["bedrock_protocol/v2193.pyi"]

    def test_imported_types_are_in_the_same_generated_closure(self):
        _, result = self.generate(
            """
from protocol import packet
from protocol.shared import Shared
package = "bedrock.protocol"
@packet(id=7)
class Root:
    child: Shared
""",
            imports={
                "shared": """
from protocol import uint8
package = "bedrock.protocol"
class Shared:
    value: uint8
"""
            },
        )
        assert "shared.cpp" in result.files
        assert "bind_shared(types);" in result.files["bindings.cpp"]
        assert "Shared: TypeAlias = _v1001.Shared" in result.files["bedrock_protocol/v2193.pyi"]

    def test_construction_adapters_follow_wire_types_without_changing_view_types(self):
        _, result = self.generate("""
from protocol import array, field, int16, int32, packet, uint8, uint16, uvarint32
package = "bedrock.protocol"
type Number = int32
type Numbers = list[int32]
@packet(id=7)
class Root:
    enabled: bool
    scalar: int32 = field(type=uint8)
    alias: Number = field(type=uint8)
    maybe: int32 | None = field(type=uint8)
    union: int32 | int16 = field(type=uint8)
    conditional: int32 = field(type=uint8, when=lambda p: p.enabled)
    fixed: array[int32, 2] = field(type=uint8)
    short: list[int32] = field(prefix=uint16)
    signed: list[int32] = field(prefix=int16)
    wider: list[int32] = field(prefix=uvarint32)
    structural_alias: Numbers
    counted: list[int32] = field(count=lambda p: 2)
""")
        cpp = result.files["mod.cpp"]
        narrow = "Scalar<std::int32_t, std::uint8_t>"
        assert f"value.scalar = {narrow}::load(a1);" in cpp
        assert "value.alias = Alias<bedrock::protocol::Number, std::int32_t, std::uint8_t>::load(a2);" in cpp
        assert f"value.maybe = Optional<{narrow}>::load(a3);" in cpp
        assert f"Union<{narrow}, Scalar<std::int16_t, std::uint8_t>>::load(a4)" in cpp
        assert f"value.conditional = {narrow}::load(a5)" in cpp
        assert f"Sequence<std::array<typename {narrow}::Type, 2>, {narrow}>::load(a6)" in cpp
        sequence = "Sequence<std::vector<typename Scalar<std::int32_t>::Type>, Scalar<std::int32_t>"
        assert f"value.short = {sequence}, std::uint16_t>::load(a7);" in cpp
        assert f"value.signed = {sequence}, std::int16_t>::load(a8);" in cpp
        assert f"value.wider = {sequence}, std::uint32_t>::load(a9);" in cpp
        assert f"value.structural_alias = {sequence}, std::uint32_t>::load(a10);" in cpp
        assert f"value.counted = {sequence}>::load(a11);" in cpp
        assert "counted length disagrees with its count" in cpp
        bindings = result.files["bindings.cpp"]
        assert f"bindSequence<{sequence}>>" in bindings
        assert f"bindSequence<{sequence}, std::uint16_t>>" not in bindings
        assert f"bindSequence<{sequence}, std::uint32_t>>" not in bindings


def test_compiler_import_never_requires_native():
    script = """
import importlib.abc
import sys
class NoNative(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname.startswith("bedrock_protocol._native"):
            raise AssertionError("compiler attempted native import")
sys.meta_path.insert(0, NoNative())
import bedrock_protocol
from bedrock_protocol.cli import main
from bedrock_protocol.compiler.registry import GENERATORS
assert "nanobind" in GENERATORS
assert "bedrock_protocol._native" not in sys.modules
"""
    subprocess.run([sys.executable, "-c", script], check=True, timeout=30)
