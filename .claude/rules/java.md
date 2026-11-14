---
paths:
  - "java/**"
  - "compiler/src/bedrock_protocol_compiler/java/**"
---

# Java

- Throw `DecodeException` for bad encoded bytes and nothing else for them; programming errors stay `NullPointerException`, `IllegalArgumentException`, `IllegalStateException` and Netty's own exceptions.
- Catch only `DecodeException`, where a packet enters or to prepend a path segment; never catch `Throwable`, `Error`, `Exception`, `RuntimeException` or `IndexOutOfBoundsException`, and never write an empty catch.
- Never put encoded text in an exception message.
- Declare every class `final`.
- Annotate every public and protected reference parameter, return and field `org.jetbrains.annotations.NotNull`, or `Nullable` where null is allowed, and add no `package-info.java` for nullness.
- Name a `ByteBufCodec` read or write after CloudburstMC Protocol's, Netty's for a fixed width: `readUnsignedVarInt`, `readVarInt`, `readString`, `readShortLE`.
- Keep `read` and `write` for `ByteBufCodec`'s primitives, and name every other type's encoding `encode` and `decode`, NBT tags included.
- Shape the `nbt` package after Java Edition's `net.minecraft.nbt` under Mojang's mappings: `Tag`, `CompoundTag`, `ListTag`, `NumericTag`, the `valueOf` factories, `getIntOr` accessors and `TAG_*` ids.
- Write one-line javadoc, only where the signature cannot say it; comment only as CLAUDE.md allows.
- Test in JUnit 6 under `.claude/rules/tests.md`: a behaviour-named method, one behaviour each, no loop, `if` or `try`, `assertThrows` with the message, `@ParameterizedTest` with `argumentSet` for cases, no mocks.
