# dev.endstone:bedrock-protocol

The Java runtime on Netty's `ByteBuf`, and the codecs [`bpc`](../compiler) generates for it. See the [root README](../README.md#java) to install and use it.

| Package | Holds |
| --- | --- |
| `dev.endstone.protocol` | `Protocol`, `ProtocolVersion`, the runtime and the latest protocol's types |
| `dev.endstone.protocol.v<N>` | The types protocol N introduced that the latest lacks, as `<Name>_v<N>` |
| `dev.endstone.protocol.internal` | `SerializationMode` and the enum numberings |
| `dev.endstone.protocol.nbt` | NBT tags |
| `dev.endstone.protocol.datastore` | `DynamicValue` |

From `java/`, with JDK 21 or newer, into `../build/java`:

```shell
./gradlew build
./gradlew spotlessApply
```
