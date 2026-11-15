import json

from bedrock_protocol_compiler.context import GeneratorContext
from bedrock_protocol_compiler.descriptor import CompilerError, Enum
from bedrock_protocol_compiler.java import file, names, version
from bedrock_protocol_compiler.java.members import Members
from bedrock_protocol_compiler.java.message import type_generator
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import EnumShape, Schema, StructModel


def generate(schema: Schema, context: GeneratorContext) -> None:
    reserved = names.reserved(schema)
    declared: dict[str, StructModel | EnumShape] = {}
    for family in schema.order:
        if family.owner is not None:
            continue
        types = schema.shapes(family) if isinstance(family, Enum) else schema.models(family)
        for each in types:
            if not isinstance(each, StructModel | EnumShape):
                continue
            package = names.package(schema, each)
            name = names.declared(schema, each)
            spelled = f"{package}.{name}"
            if declared.get(spelled) is each:
                continue
            if name in reserved:
                raise CompilerError(f"{spelled}: shadows the imported {name}")
            if name == names.REGISTRY:
                raise CompilerError(f"{spelled}: has the name of the packet registries")
            if declared.setdefault(spelled, each) is not each:
                raise CompilerError(f"{spelled}: is declared twice")
            body = Printer()
            registry = Members(body)
            type_generator(schema, each, (), registry).definition(body)
            registry.check()
            file.write(schema, context.open(names.path(package, name)), package, body)
    if f"{schema.java_package}.{names.VERSION}" in declared:
        raise CompilerError(f"{schema.java_package}.{names.VERSION}: is the protocol version table")
    for number in schema.versions:
        package = names.registry(schema, number)
        body = Printer()
        packets(schema, number, body)
        file.write(schema, context.open(names.path(package, names.REGISTRY)), package, body)
    body = Printer()
    version.table(schema, body)
    file.write(schema, context.open(names.path(schema.java_package, names.VERSION)), schema.java_package, body)


def packets(schema: Schema, number: int, p: Printer) -> None:
    cases = sorted(
        (packet_id, encoding.model.family.name, names.qualified(schema, encoding.model), names.codec(encoding))
        for packet_id, encoding in schema.packets(number).items()
    )
    p.emit(
        """
        public final class $registry$ {
            private $registry$() {}

            public static void encode(@NotNull Packet packet, @NotNull ByteBuf buf) {
                switch (packet) {
                    $encodes$
                    default -> throw new IllegalArgumentException($unknown$);
                }
            }

            public static @NotNull Packet decode(int packetId, @NotNull ByteBuf buf) {
                return switch (packetId) {
                    $decodes$
                    default -> ByteBufCodec.decode(buf, "PacketHeader", body -> {
                        throw DecodeException.unknownValue(body.readerIndex()).prepend("packet_id");
                    });
                };
            }
        }
        """,
        registry=names.REGISTRY,
        encodes=lambda: encodes(p, cases),
        unknown=f'"packet: " + packet.getClass().getName() + {json.dumps(f" is not a packet at protocol {number}")}',
        decodes=lambda: decodes(p, cases),
    )


def encodes(p: Printer, cases: list[tuple[int, str, str, str]]) -> None:
    for _, _, spelled, codec in cases:
        p.emit("case $spelled$ value -> $spelled$.$codec$.INSTANCE.encode(value, buf);", spelled=spelled, codec=codec)


def decodes(p: Printer, cases: list[tuple[int, str, str, str]]) -> None:
    for packet_id, name, spelled, codec in cases:
        p.emit(
            'case $id$ -> ByteBufCodec.decode(buf, "$name$", $spelled$.$codec$.INSTANCE);',
            id=packet_id,
            name=name,
            spelled=spelled,
            codec=codec,
        )
