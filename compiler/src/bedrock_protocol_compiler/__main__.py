import argparse
from pathlib import Path

from bedrock_protocol_compiler import cpp, go, java
from bedrock_protocol_compiler.builder import build
from bedrock_protocol_compiler.context import GeneratorContext
from bedrock_protocol_compiler.descriptor import CompilerError
from bedrock_protocol_compiler.schema import Schema


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="bpc")
    parser.add_argument("package", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--java-out", type=Path)
    parser.add_argument("--go-out", type=Path)
    arguments = parser.parse_args(argv)
    outs = (arguments.out, arguments.java_out, arguments.go_out)
    if all(out is None for out in outs):
        parser.error("one of --out, --java-out and --go-out is required")
    contexts: list[GeneratorContext] = []
    try:
        schema = Schema(build(arguments.package))
        if arguments.out is not None:
            contexts.append(GeneratorContext(arguments.out))
            cpp.generate(schema, contexts[-1])
        if arguments.java_out is not None:
            contexts.append(GeneratorContext(arguments.java_out))
            java.generate(schema, contexts[-1])
        if arguments.go_out is not None:
            contexts.append(GeneratorContext(arguments.go_out, go.OWNED))
            go.generate(schema, contexts[-1])
    except CompilerError as error:
        raise SystemExit(f"bpc: {error}") from error
    for context in contexts:
        context.commit()


if __name__ == "__main__":
    main()
