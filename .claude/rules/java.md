---
paths:
  - "java/**"
  - "compiler/src/bedrock_protocol_compiler/java/**"
---

# Java

- Throw `DecodeException` for bad encoded bytes and nothing else for them; programming errors stay `NullPointerException`, `IllegalArgumentException`, `IllegalStateException` and Netty's own exceptions.
- Catch only `DecodeException`, where a packet enters or to prepend a path segment; never catch `Throwable`, `Error`, `Exception`, `RuntimeException` or `IndexOutOfBoundsException`, and never write an empty catch.
- Create a `DecodeException` through its factories (`truncated`, `outOfRange`, `unknownValue`, `trailingBytes`), as protobuf's `InvalidProtocolBufferException` does; it carries no reason enum.
- Carry the partly decoded message on a `DecodeException`, as protobuf's `setUnfinishedMessage` does: a generated decode sets what its builder holds at the catch that prepends the field, so the outermost message wins.
- Never put encoded text in an exception message.
- Declare every class `final`.
- Annotate every public and protected reference parameter, return and field `org.jetbrains.annotations.NotNull`, or `Nullable` where null is allowed, and add no `package-info.java` for nullness.
- Name a `ByteBufCodec` read or write after CloudburstMC Protocol's, Netty's for a fixed width: `readUnsignedVarInt`, `readVarInt`, `readString`, `readShortLE`.
- Keep `read` and `write` for `ByteBufCodec`'s primitives and the schema's builtins, and name every other type's encoding `encode` and `decode`, NBT tags included.
- Map a schema builtin `Name` from module `stem` to the type `<java_package>.<stem without underscores>.<Name>`, read by `ByteBufCodec.read<Name>` and written by `write<Name>` with `Name` in Google camel case (`readUuid`), with `getDefaultInstance()` and `copy()`; the DSL's own `UUID` is `java.util.UUID`.
- Emit each message as protobuf's generated Java does: an immutable class with `getDefaultInstance()`, `newBuilder()` and `toBuilder()`, a nested `Builder` with `setX`, `clearX` and `build()`, and `getX` on both; `hasX` for an optional, `getXList`, `getXCount` and `addX` for a list, `getXMap` and `putX` for a map, and `getXCase()` for a union.
- Hold a union field as a oneof on its message, and wrap a union in a message of its own as a list, array or map element, inside an optional, or beside a union whose case names it shares.
- Default a union to its first case; clearing a required one restores that case, and clearing an optional one gives its `NOT_SET` case.
- Order a map's keys as the C++ `std::map` does: strings by their unsigned bytes, floats by `<`, so `-0.0` and `0.0` are one key.
- Keep an int-coded enum open as protobuf's are: `getXValue()`, `forNumber`, and `UNRECOGNIZED` for a number with no member.
- Emit each literal field as a public constant on its message, named by its DSL name in upper case without leading underscores (`ACTION_TYPE`), and `@Deprecated` when its member or that member's canonical constant is deprecated.
- Name a packet's id accessor `getPacketId()`, and fail the compile when a field's generated accessor would equal another generated member.
- Define a shape live at the latest version in the bare `java_package`, and any other in the `v<since>` or `base` package the C++ backend names it by, under `precereal` for a pre-cereal family; a nested shape lives in the newest owner shape that holds it.
- Generate `v<N>.Packets` for every modelled version, a bare `Packets` for the latest, and a bare `ProtocolVersion` mirroring the C++ `version.hpp`.
- Shape the `nbt` package after Java Edition's `net.minecraft.nbt` under Mojang's mappings: `Tag`, `CompoundTag`, `ListTag`, `NumericTag`, the `valueOf` factories, `getIntOr` accessors and `TAG_*` ids.
- Write one-line javadoc, only where the signature cannot say it; comment only as CLAUDE.md allows.
- Test in JUnit 6 under `.claude/rules/tests.md`: a behaviour-named method, one behaviour each, no loop, `if` or `try`, `assertThrows` with the message, `@ParameterizedTest` with `argumentSet` for cases, no mocks.
