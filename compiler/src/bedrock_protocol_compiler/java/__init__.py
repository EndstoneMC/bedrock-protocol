from bedrock_protocol_compiler.context import GeneratorContext
from bedrock_protocol_compiler.descriptor import CompilerError, Enum
from bedrock_protocol_compiler.java import file, names, protocol, version
from bedrock_protocol_compiler.java.enum import EnumGenerator
from bedrock_protocol_compiler.java.members import Members
from bedrock_protocol_compiler.java.message import MessageGenerator, type_generator
from bedrock_protocol_compiler.java.numbering import NumberingGenerator, reached
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import Encoding, EnumModel, Schema, StructModel


def generate(schema: Schema, context: GeneratorContext) -> None:
    reserved = names.reserved(schema)
    exported: set[Encoding] = set()
    for encodings in schema.model_encodings.values():
        for encoding in encodings:
            home = names.home(schema, encoding.model)
            for child in encoding.reached.values():
                if isinstance(child, Encoding) and names.home(schema, child.model) != home:
                    exported.add(child)
    declared: dict[str, StructModel | EnumModel] = {}
    generators: list[MessageGenerator | EnumGenerator] = []
    for family in schema.order:
        if family.owner is not None:
            continue
        types = schema.enum_types(family) if isinstance(family, Enum) else schema.models(family)
        for each in types:
            package = names.package(schema, each)
            name = names.declared(schema, each)
            spelled = f"{package}.{name}"
            if declared.get(spelled) is each:
                continue
            if name in reserved:
                raise CompilerError(f"{spelled}: shadows the imported {name}")
            if declared.setdefault(spelled, each) is not each:
                raise CompilerError(f"{spelled}: is declared twice")
            body = Printer()
            registry = Members(body)
            generator = type_generator(schema, each, (), registry, exported)
            generator.definition(body)
            registry.check()
            generators.append(generator)
            file.write(schema, context.open(names.path(package, name)), package, body)
    internal = names.internal(schema)
    for model in reached(schema):
        body = Printer()
        numbering = NumberingGenerator(schema, model)
        numbering.definition(body)
        file.write(schema, context.open(names.path(internal, numbering.name)), internal, body)
    for name, role in ((names.VERSION, "the protocol version table"), (names.PROTOCOL, "the protocol class")):
        if f"{schema.java_package}.{name}" in declared:
            raise CompilerError(f"{schema.java_package}.{name}: is {role}")
    body = Printer()
    version.table(schema, body)
    file.write(schema, context.open(names.path(schema.java_package, names.VERSION)), schema.java_package, body)
    body = Printer()
    protocol.definition(schema, generators, body)
    file.write(schema, context.open(names.path(schema.java_package, names.PROTOCOL)), schema.java_package, body)
