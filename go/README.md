# github.com/EndstoneMC/bedrock-protocol/go

The Go runtime and the codecs [`bpc`](../compiler) generates for it. See the [root README](../README.md#go) to install and use it.

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
