import json

from bedrock_protocol_compiler.descriptor import Binary, CompilerError, Member, MemberRef
from bedrock_protocol_compiler.java import names
from bedrock_protocol_compiler.java.expression import enum_class
from bedrock_protocol_compiler.java.value import literal
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import EnumShape, Schema

UNRECOGNIZED = "UNRECOGNIZED"
NUMBER = "value"


class EnumGenerator:
    def __init__(self, schema: Schema, shape: EnumShape) -> None:
        self.shape = shape
        self.name = shape.family.name
        self.qualified = names.qualified(schema, shape)
        self.name_coded = shape.family in schema.name_coded
        number = enum_class(shape)
        self.numbers = {member.name: literal(shape.numbers[member.name], number) for member in shape.members}
        self.constants: list[Member] = []
        self.aliases: list[tuple[Member, str]] = []
        canonical: dict[str, str] = {}
        for member in shape.members:
            if member.name == UNRECOGNIZED:
                raise CompilerError(f"{self.qualified}.{UNRECOGNIZED}: is the open enum's unknown value")
            if member.name == NUMBER:
                raise CompilerError(f"{self.qualified}.{NUMBER}: is the field that holds a constant's number")
            first = canonical.setdefault(self.numbers[member.name], member.name)
            if first == member.name:
                self.constants.append(member)
            else:
                self.aliases.append((member, first))
        reflected = sorted(shape.members, key=lambda member: not isinstance(member.value, MemberRef | Binary))
        self.encoded: dict[str, str] = {}
        for member in reflected:
            self.encoded.setdefault(canonical[self.numbers[member.name]], member.encoded_name)
        self.decoded = [(member.encoded_name, canonical[self.numbers[member.name]]) for member in reflected]

    def definition(self, p: Printer) -> None:
        p.emit("public enum $name$ {", name=self.name)
        with p.indent():
            self.body(p)
        p.emit("}")

    def body(self, p: Printer) -> None:
        for member in self.constants:
            if member.deprecated:
                p.emit("@Deprecated")
            p.emit("$name$($number$),", name=member.name, number=self.numbers[member.name])
        p.emit("$name$(-1);", name=UNRECOGNIZED)
        p.emit("")
        for member, canonical in self.aliases:
            if member.deprecated:
                p.emit("@Deprecated")
            p.emit(
                "public static final @NotNull $enum$ $name$ = $canonical$;",
                enum=self.name,
                name=member.name,
                canonical=canonical,
            )
        if self.aliases:
            p.emit("")
        p.emit(
            """
            private final int value;

            $name$(int value) {
                this.value = value;
            }

            public int getNumber() {
                if (this == UNRECOGNIZED) {
                    throw new IllegalArgumentException("Can't get the number of an unknown enum value.");
                }
                return value;
            }

            public static @Nullable $name$ forNumber(int value) {
                return switch (value) {
                    $cases$
                    default -> null;
                };
            }
            """,
            name=self.name,
            cases=lambda: self.number_cases(p),
        )
        if self.name_coded:
            self.codec(p)

    def number_cases(self, p: Printer) -> None:
        for member in self.constants:
            p.emit("case $number$ -> $name$;", number=self.numbers[member.name], name=member.name)

    def codec(self, p: Printer) -> None:
        p.emit(
            """

            public void encode(@NotNull ByteBuf buf) {
                ByteBufCodec.writeString(buf, switch (this) {
                    $names$
                    case UNRECOGNIZED -> throw new IllegalArgumentException($unknown$);
                });
            }

            public static @NotNull $name$ decode(@NotNull ByteBuf buf) {
                return switch (ByteBufCodec.foldAscii(ByteBufCodec.readString(buf))) {
                    $constants$
                    default -> throw DecodeException.unknownValue(buf.readerIndex());
                };
            }
            """,
            names=lambda: self.name_cases(p),
            unknown=json.dumps(f"{self.name}.{UNRECOGNIZED}: has no encoded name"),
            name=self.name,
            constants=lambda: self.constant_cases(p),
        )

    def name_cases(self, p: Printer) -> None:
        for member in self.constants:
            p.emit("case $name$ -> $encoded$;", name=member.name, encoded=json.dumps(self.encoded[member.name]))

    def constant_cases(self, p: Printer) -> None:
        for encoded, constant in self.decoded:
            p.emit("case $encoded$ -> $name$;", encoded=json.dumps(encoded), name=constant)
