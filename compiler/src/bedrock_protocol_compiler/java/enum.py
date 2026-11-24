import json
from functools import partial

from bedrock_protocol_compiler.descriptor import Binary, CompilerError, Member, MemberRef
from bedrock_protocol_compiler.java import members, names
from bedrock_protocol_compiler.java.expression import enum_class
from bedrock_protocol_compiler.java.value import literal
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import EnumModel, Naming, Schema

UNRECOGNIZED = "UNRECOGNIZED"
NUMBER = "value"


class EnumGenerator:
    def __init__(self, schema: Schema, enum_type: EnumModel) -> None:
        enumerators = schema.enumerators(enum_type)
        self.name = names.declared(schema, enum_type)
        self.qualified = names.qualified(schema, enum_type)
        self.name_coded = any(form in schema.name_coded for form in enum_type.runs)
        self.namings = schema.namings(enum_type) if self.name_coded else []
        self.values = enumerators
        number = self.number = enum_class(enum_type)
        self.numbers = {member.name: literal(enumerators[member.name], number) for member in enum_type.members}
        self.constants: list[Member] = []
        self.aliases: list[tuple[Member, str]] = []
        self.canonical: dict[str, str] = {}
        for member in enum_type.members:
            if member.name == UNRECOGNIZED:
                raise CompilerError(f"{self.qualified}.{UNRECOGNIZED}: is the open enum's unknown value")
            if member.name == NUMBER:
                raise CompilerError(f"{self.qualified}.{NUMBER}: is the field that holds a constant's number")
            first = self.canonical.setdefault(self.numbers[member.name], member.name)
            if first == member.name:
                self.constants.append(member)
            else:
                self.aliases.append((member, first))
        reflected = sorted(enum_type.members, key=lambda member: not isinstance(member.value, MemberRef | Binary))
        self.encoded: dict[str, str] = {}
        for member in reflected:
            self.encoded.setdefault(self.canonical[self.numbers[member.name]], member.encoded_name)
        self.decoded = [(member.encoded_name, self.canonical[self.numbers[member.name]]) for member in reflected]

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
        if len(self.namings) > 1:
            self.protocol_codec(p)
        elif self.name_coded:
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

    def protocol_codec(self, p: Printer) -> None:
        message = json.dumps(f"{self.name}: is not a type at protocol ")
        unknown = f"throw new IllegalArgumentException({message} + protocol);"
        p.emit(
            """

            public void encode(int protocol, @NotNull ByteBuf buf) {
                $encodes$
            }

            public static @NotNull $name$ decode(int protocol, @NotNull ByteBuf buf) {
                $decodes$
            }
            """,
            name=self.name,
            encodes=lambda: members.ladder(
                p, [(each.runs, partial(self.encode_naming, p, each)) for each in self.namings], unknown
            ),
            decodes=lambda: members.ladder(
                p, [(each.runs, partial(self.decode_naming, p, each)) for each in self.namings], unknown
            ),
        )

    def encode_naming(self, p: Printer, naming: Naming) -> None:
        p.emit(
            """
            ByteBufCodec.writeString(buf, switch (this) {
                $names$
                default -> throw new IllegalArgumentException($unknown$);
            });
            return;
            """,
            names=lambda: self.written_cases(p, naming),
            unknown=json.dumps(f"{self.name}: has no encoded name at protocol ") + " + protocol",
        )

    def written_cases(self, p: Printer, naming: Naming) -> None:
        for member in self.constants:
            if self.values[member.name] in naming.written:
                encoded = json.dumps(naming.written[self.values[member.name]])
                p.emit("case $name$ -> $encoded$;", name=member.name, encoded=encoded)

    def decode_naming(self, p: Printer, naming: Naming) -> None:
        p.emit(
            """
            return switch (ByteBufCodec.foldAscii(ByteBufCodec.readString(buf))) {
                $constants$
                default -> throw DecodeException.unknownValue(buf.readerIndex());
            };
            """,
            constants=lambda: self.read_cases(p, naming),
        )

    def read_cases(self, p: Printer, naming: Naming) -> None:
        for encoded, value in naming.read.items():
            p.emit(
                "case $encoded$ -> $name$;",
                encoded=json.dumps(encoded),
                name=self.canonical[literal(value, self.number)],
            )

    def name_cases(self, p: Printer) -> None:
        for member in self.constants:
            p.emit("case $name$ -> $encoded$;", name=member.name, encoded=json.dumps(self.encoded[member.name]))

    def constant_cases(self, p: Printer) -> None:
        for encoded, constant in self.decoded:
            p.emit("case $encoded$ -> $name$;", encoded=json.dumps(encoded), name=constant)
