# dev.endstone:bedrock-protocol

The Java runtime on Netty's `ByteBuf`, and the codecs [`bpc`](../compiler) generates for it.

## Install

Add the package from Maven Central to a Gradle build:

```kotlin
dependencies {
    implementation("dev.endstone:bedrock-protocol:X.Y.Z")
}
```

Or build it from a checkout with JDK 21 and Python 3.12 or newer into the local Maven repository:

```shell
git clone https://github.com/EndstoneMC/bedrock-protocol
cd bedrock-protocol/java
./gradlew publishToMavenLocal
```

## Encode and decode

```java
import dev.endstone.protocol.Protocol;
import dev.endstone.protocol.TextPacket;
import dev.endstone.protocol.TextPacketType;

TextPacket packet =
    TextPacket.newBuilder()
        .setMessageOnly(
            TextPacket.MessageOnly.newBuilder()
                .setType(TextPacketType.CHAT)
                .setMessage("hello")
                .build())
        .build();

byte[] data = Protocol.encode(packet);
TextPacket decoded = Protocol.decode(TextPacket.class, data);
assert decoded.equals(packet);
```

## Pick a protocol

```java
import dev.endstone.protocol.ProtocolVersion;

import java.util.Optional;

Optional<ProtocolVersion> version = ProtocolVersion.get(2259);
assert version.isPresent() && version.get().getName().equals("1.26.70");

byte[] pinned = Protocol.v2259.encode(packet);
TextPacket picked = Protocol.v2259.decode(TextPacket.class, pinned);
assert picked.equals(packet);
```

## Packages

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
