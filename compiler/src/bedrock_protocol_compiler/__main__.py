import argparse
from pathlib import Path

from bedrock_protocol_compiler import cpp
from bedrock_protocol_compiler.builder import build
from bedrock_protocol_compiler.context import GeneratorContext
from bedrock_protocol_compiler.descriptor import CompilerError
from bedrock_protocol_compiler.schema import Schema


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="bpc")
    parser.add_argument("package", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args(argv)
    context = GeneratorContext(arguments.out)
    try:
        cpp.generate(Schema(build(arguments.package)), context)
    except CompilerError as error:
        raise SystemExit(f"bpc: {error}") from error
    context.commit()


if __name__ == "__main__":
    main()
