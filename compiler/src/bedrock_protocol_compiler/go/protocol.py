import json

from bedrock_protocol_compiler.go.message import MessageGenerator
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import Schema

IDENTIFIERS = (
    "Encode",
    "Decode",
    "ProtocolVersion",
    "SupportedVersions",
    "MinimumVersion",
    "MaximumVersion",
    "GetProtocolVersion",
)


def pin(number: int) -> str:
    return f"V{number}"


def identifiers(schema: Schema) -> list[tuple[str, str]]:
    found = [(name, "the protocol") for name in IDENTIFIERS]
    return found + [(pin(number), "a protocol") for number in schema.versions]


def definition(schema: Schema, p: Printer) -> None:
    p.emit("var (")
    with p.indent():
        for number in schema.versions:
            p.emit("$pin$ = Pinned{version: $number$}", pin=pin(number), number=number)
    p.emit(")")
    p.emit(
        """

        func Encode(packet Packet) ([]byte, error) {
            return $latest$.Encode(packet)
        }

        func Decode(data []byte, packet Packet) error {
            return $latest$.Decode(data, packet)
        }

        type ProtocolVersion struct {
            protocol int
            name     string
        }

        func (v ProtocolVersion) Protocol() int {
            return v.protocol
        }

        func (v ProtocolVersion) Name() string {
            return v.name
        }

        var (
            SupportedVersions = []ProtocolVersion{
                $releases$
            }
            MinimumVersion = SupportedVersions[0]
            MaximumVersion = SupportedVersions[$last$]
        )

        func GetProtocolVersion(protocol int) (ProtocolVersion, bool) {
            if protocol < $minimum$ || protocol > $maximum$ {
                return ProtocolVersion{}, false
            }
            below := MinimumVersion
            for _, version := range SupportedVersions {
                if version.protocol == protocol {
                    return version, true
                }
                if version.protocol < protocol {
                    below = version
                }
            }
            return ProtocolVersion{protocol, below.name}, true
        }
        """,
        latest=pin(schema.latest),
        releases=lambda: releases(schema, p),
        last=len(schema.releases) - 1,
        minimum=schema.versions[0],
        maximum=schema.latest,
    )


def releases(schema: Schema, p: Printer) -> None:
    for release in schema.releases:
        p.emit("{$number$, $first$},", number=release.number, first=json.dumps(release.first))


def registry(schema: Schema, generators: list[MessageGenerator], p: Printer) -> None:
    p.emit("var casePins = []Pinned{")
    with p.indent():
        for number in schema.versions:
            p.emit("$pin$,", pin=pin(number))
    p.emit("}")
    p.emit("")
    p.emit("var casePackets = []func() Packet{")
    with p.indent():
        for generator in generators:
            p.emit("func() Packet { return new($name$) },", name=generator.name)
    p.emit("}")
