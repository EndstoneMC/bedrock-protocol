from bedrock_protocol_compiler.context import GeneratorContext
from bedrock_protocol_compiler.descriptor import CompilerError, Enum
from bedrock_protocol_compiler.go import file, names, protocol
from bedrock_protocol_compiler.go.enum import EnumGenerator
from bedrock_protocol_compiler.go.message import MessageGenerator, type_generator
from bedrock_protocol_compiler.java.members import check_names
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import EnumModel, Numbering, Schema, StructModel

OWNED = ("*.bpc.go", "*.bpc_test.go")


def packets(generators: list[MessageGenerator | EnumGenerator]) -> list[MessageGenerator]:
    found: list[MessageGenerator] = []
    for generator in generators:
        if isinstance(generator, MessageGenerator):
            if generator.packet_id is not None and generator.codecs:
                found.append(generator)
            found += packets(generator.nested)
    return found


def generate(schema: Schema, context: GeneratorContext) -> None:
    package = names.package(schema)
    numbered: set[EnumModel] = set()
    for encodings in schema.model_encodings.values():
        for encoding in encodings:
            reached = [each for each in encoding.reached.values() if isinstance(each, Numbering)]
            numbered |= {each.model for each in reached if not each.identity}
    taken: set[str] = set()
    declared: dict[str, StructModel | EnumModel] = {}
    modules: dict[str, list[MessageGenerator | EnumGenerator]] = {}
    for family in schema.order:
        if family.owner is not None:
            continue
        types = schema.enum_types(family) if isinstance(family, Enum) else schema.models(family)
        for each in types:
            name = names.declared(schema, each)
            if declared.get(name) is each:
                continue
            if declared.setdefault(name, each) is not each:
                raise CompilerError(f"{package}.{name}: is declared twice")
            generator = type_generator(schema, each, taken, numbered)
            modules.setdefault(names.home(schema, each), []).append(generator)
    generators = [generator for listed in modules.values() for generator in listed]
    for generator in generators:
        if isinstance(generator, MessageGenerator):
            for union in generator.all_unions():
                union.wrap(taken)
    identifiers = [(name, "the runtime") for name in names.RUNTIME] + protocol.identifiers(schema)
    for generator in generators:
        identifiers += generator.identifiers()
        if isinstance(generator, MessageGenerator):
            generator.check()
    check_names(package, identifiers)
    for stem, listed in modules.items():
        if stem == package:
            raise CompilerError(f"{stem}.py: names the file that holds the protocol")
        body = Printer()
        cases = Printer()
        for generator in listed:
            generator.definition(body)
            if isinstance(generator, MessageGenerator):
                generator.cases(cases)
        if body.lines:
            file.write(schema, context.open(names.path(schema, stem)), names.path(schema, stem), body)
        if cases.lines:
            file.write(schema, context.open(names.test_path(schema, stem)), names.test_path(schema, stem), cases)
    body = Printer()
    protocol.definition(schema, body)
    file.write(schema, context.open(names.path(schema, package)), names.path(schema, package), body)
    body = Printer()
    protocol.registry(schema, packets(generators), body)
    file.write(schema, context.open(names.test_path(schema, package)), names.test_path(schema, package), body)
