# github.com/EndstoneMC/bedrock-protocol/go

The Go runtime and the codecs [`bpc`](../compiler) generates for it.

## Install

Generate the codecs in a checkout with Go 1.26 and uv, then point a module at it:

```shell
git clone https://github.com/EndstoneMC/bedrock-protocol
(cd bedrock-protocol/go && go generate ./...)
go mod edit -require=github.com/EndstoneMC/bedrock-protocol/go@v0.0.0 -replace=github.com/EndstoneMC/bedrock-protocol/go=./bedrock-protocol/go
```

## Encode and decode

```go
import "github.com/EndstoneMC/bedrock-protocol/go/protocol"

packet := &protocol.TextPacket{}
packet.Body = &protocol.TextPacket_MessageOnly_{
    MessageOnly: &protocol.TextPacket_MessageOnly{Type: protocol.TextPacketType_CHAT, Message: "hello"},
}

data, err := protocol.Encode(packet)
if err != nil {
    panic(err)
}
decoded := &protocol.TextPacket{}
if err := protocol.Decode(data, decoded); err != nil {
    panic(err)
}
if decoded.GetMessageOnly().GetMessage() != "hello" {
    panic(decoded)
}
```

## Pick a protocol

```go
version, ok := protocol.GetProtocolVersion(2259)
if !ok || version.Name() != "1.26.70" {
    panic(version)
}

pinned, err := protocol.V2259.Encode(packet)
if err != nil {
    panic(err)
}
picked := &protocol.TextPacket{}
if err := protocol.V2259.Decode(pinned, picked); err != nil {
    panic(err)
}
if picked.GetMessageOnly().GetMessage() != "hello" {
    panic(picked)
}
```

## Packages

| Package | Holds |
| --- | --- |
| `protocol` | `Encode`, `Decode`, the `V<N>` protocols, `ProtocolVersion`, the runtime and every protocol's types, a type the latest protocol lacks as `<Name>_v<N>` |
| `stream` | The reader and writer of the encoding's primitives |
| `nbt` | NBT tags |
| `datastore` | `DynamicValue` |
| `uuid` | `UUID` |

From `go/`, with Go 1.26 or newer and uv:

```shell
go generate ./...
go vet ./...
go test ./...
```
