from bedrock_protocol_compiler.context import GeneratorContext
from bedrock_protocol_compiler.cpp import names
from bedrock_protocol_compiler.cpp.file import FileGenerator
from bedrock_protocol_compiler.schema import Schema


def generate(schema: Schema, context: GeneratorContext) -> None:
    for module in schema.modules:
        FileGenerator(schema, module).generate(context.open(f"{names.INCLUDE_DIR}/{module.stem}.h"))
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
