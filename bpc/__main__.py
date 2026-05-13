"""Bedrock-Protocol Compiler — the ``protoc`` of this project.

Parses packet definition files via the DSL parser (no Python execution),
runs the Jinja2 templates, and writes ``<Packet>.h`` / ``<Packet>.cpp`` into
the output directory. ``--list-outputs`` makes it print the file list
without writing anything; the CMake glue uses this at configure time to
discover generated sources.

Invoke as ``python -m bpc`` from the directory containing the ``bpc``
package (or set ``PYTHONPATH`` accordingly).
"""

import argparse
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .dsl import FieldDef, NamedType, PrimitiveType, SwitchType, parse_file

PACKAGE_DIR = Path(__file__).parent.resolve()


PRIMITIVE_CXX = {
    "u8": "std::uint8_t",
    "i8": "std::int8_t",
    "u16": "std::uint16_t",
    "i16": "std::int16_t",
    "u32": "std::uint32_t",
    "i32": "std::int32_t",
    "u64": "std::uint64_t",
    "i64": "std::int64_t",
    "uvarint32": "std::uint32_t",
    "varint32": "std::int32_t",
    "uvarint64": "std::uint64_t",
    "varint64": "std::int64_t",
    "string": "std::string",
    "bool": "bool",
    "float": "float",
    "double": "double",
}


def _case_cxx(case) -> str:
    if case is None:
        return "std::monostate"
    if isinstance(case, PrimitiveType):
        return PRIMITIVE_CXX.get(case.name, case.name)
    if isinstance(case, NamedType):
        return case.name
    raise ValueError(f"unsupported switch case: {case!r}")


def cxx_type(field: FieldDef) -> str:
    """C++ type used in the generated struct field declaration."""
    t = field.type
    if isinstance(t, PrimitiveType):
        return PRIMITIVE_CXX.get(t.name, t.name)
    if isinstance(t, NamedType):
        return t.name
    if isinstance(t, SwitchType):
        return f"std::variant<{', '.join(_case_cxx(c) for c in t.cases)}>"
    raise ValueError(f"unknown field type: {t!r}")


def wire_type(field: FieldDef) -> str:
    """Underlying wire type — what ``read_X`` / ``write_X`` to call."""
    t = field.type
    if isinstance(t, PrimitiveType):
        return t.name
    if isinstance(t, NamedType):
        # Named types in bare position are enums; default wire type is uvarint32.
        return "uvarint32"
    if isinstance(t, SwitchType):
        return t.discriminator
    raise ValueError(f"unknown field type: {t!r}")


def build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(PACKAGE_DIR / "templates")),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )
    env.filters["cxx_type"] = cxx_type
    env.filters["wire_type"] = wire_type
    env.tests["primitive_type"] = lambda x: isinstance(x, PrimitiveType)
    env.tests["named_type"] = lambda x: isinstance(x, NamedType)
    env.tests["switch_type"] = lambda x: isinstance(x, SwitchType)
    return env


def main():
    p = argparse.ArgumentParser(description="Bedrock-Protocol Compiler")
    p.add_argument("--out", required=True, help="output directory")
    p.add_argument("--header-only", action="store_true")
    p.add_argument(
        "--list-outputs",
        action="store_true",
        help="print generated file paths without writing",
    )
    p.add_argument("inputs", nargs="+", help="packet .py definition files")
    args = p.parse_args()

    env = build_env()
    h_tpl = env.get_template("packet.h.j2")
    cpp_tpl = env.get_template("packet.cpp.j2")

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    outputs = []
    for inp in args.inputs:
        for pkt in parse_file(Path(inp).resolve()):
            h_out = out_dir / f"{pkt.name}.h"
            outputs.append(h_out)
            if not args.list_outputs:
                h_out.write_text(h_tpl.render(packet=pkt))
            if not args.header_only:
                cpp_out = out_dir / f"{pkt.name}.cpp"
                outputs.append(cpp_out)
                if not args.list_outputs:
                    cpp_out.write_text(cpp_tpl.render(packet=pkt))

    if args.list_outputs:
        for o in outputs:
            print(o)


if __name__ == "__main__":
    main()
