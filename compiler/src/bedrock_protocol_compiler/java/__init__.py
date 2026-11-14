from bedrock_protocol_compiler.context import GeneratorContext
from bedrock_protocol_compiler.descriptor import CompilerError, Enum, Struct
from bedrock_protocol_compiler.java import file, names, version
from bedrock_protocol_compiler.java.members import Members
from bedrock_protocol_compiler.java.message import shape_generator
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import Schema


def generate(schema: Schema, context: GeneratorContext) -> None:
    reserved = names.reserved(schema)
    declared: dict[str, Struct | Enum] = {}
    for family in schema.order:
        if family.owner is not None:
            continue
        for shape in schema.shapes(family):
            package = names.package(schema, shape)
            spelled = f"{package}.{family.name}"
            if family.name in reserved:
                raise CompilerError(f"{spelled}: shadows the imported {family.name}")
            if declared.setdefault(spelled, family) is not family:
                raise CompilerError(f"{spelled}: is declared twice")
            body = Printer()
            registry = Members(body)
            shape_generator(schema, shape, (), registry).definition(body)
            registry.check()
            file.write(schema, context.open(names.path(package, family.name)), package, body)
    packages = [(names.registry(schema, each), each) for each in schema.versions]
    for package, each in [*packages, (schema.java_package, schema.latest)]:
        if f"{package}.{names.REGISTRY}" in declared:
            raise CompilerError(f"{package}.{names.REGISTRY}: is the packet registry of {each}")
        body = Printer()
        packets(schema, each, body)
        file.write(schema, context.open(names.path(package, names.REGISTRY)), package, body)
    if f"{schema.java_package}.{names.VERSION}" in declared:
        raise CompilerError(f"{schema.java_package}.{names.VERSION}: is the protocol version table")
    body = Printer()
    version.table(schema, body)
    file.write(schema, context.open(names.path(schema.java_package, names.VERSION)), schema.java_package, body)


def packets(schema: Schema, number: int, p: Printer) -> None:
    found: dict[int, str] = {}
    cases: list[tuple[int, str, str]] = []
    for family in schema.order:
        if not isinstance(family, Struct) or family.packet_id is None or (family, number) not in schema.live:
            continue
        first = found.setdefault(family.packet_id, family.name)
        if first != family.name:
            raise CompilerError(
                f"{names.registry(schema, number)}: {first} and {family.name} share id {family.packet_id}"
            )
        cases.append((family.packet_id, family.name, names.qualified(schema, schema.shape_at(family, number))))
    p.emit(
        """
        public final class $registry$ {
            private $registry$() {}

            public static @NotNull Packet decode(int packetId, @NotNull ByteBuf buf) {
                return switch (packetId) {
                    $cases$
                    default -> ByteBufCodec.decode(buf, "PacketHeader", body -> {
                        throw DecodeException.unknownValue(body.readerIndex()).prepend("packet_id");
                    });
                };
            }
        }
        """,
        registry=names.REGISTRY,
        cases=lambda: switch(p, sorted(cases)),
    )


def switch(p: Printer, cases: list[tuple[int, str, str]]) -> None:
    for packet_id, name, spelled in cases:
        p.emit(
            'case $id$ -> ByteBufCodec.decode(buf, "$name$", $spelled$::decode);',
            id=packet_id,
            name=name,
            spelled=spelled,
        )
