from bedrock_protocol_compiler.context import GeneratorContext
from bedrock_protocol_compiler.cpp import names
from bedrock_protocol_compiler.cpp.file import FileGenerator
from bedrock_protocol_compiler.schema import Schema


def generate(schema: Schema, context: GeneratorContext) -> None:
    for module in schema.modules:
        file = FileGenerator(schema, module)
        file.header(context.open(f"{names.INCLUDE_DIR}/{module.stem}.h"))
        file.source(context.open(f"{names.INCLUDE_DIR}/{module.stem}.cpp"))
    context.open(f"{names.INCLUDE_DIR}/version.hpp").emit(
        """
        #pragma once

        #include <array>

        namespace $namespace$ {

        inline constexpr std::array versions{$versions$};

        inline constexpr int latest_version = versions.back();

        }  // namespace $namespace$
        """,
        namespace=names.namespace(schema),
        versions=", ".join(map(str, schema.versions)),
    )
