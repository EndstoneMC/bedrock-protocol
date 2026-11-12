---
paths:
  - "java/**"
  - "compiler/src/bedrock_protocol_compiler/java/**"
---

# Java

- Throw `DecodeException` for bad wire bytes and nothing else for them; programming errors stay `NullPointerException`, `IllegalArgumentException`, `IllegalStateException` and Netty's own exceptions.
- Catch only `DecodeException`, where a packet enters or to prepend a path segment; never catch `Throwable`, `Error`, `Exception`, `RuntimeException` or `IndexOutOfBoundsException`, and never write an empty catch.
- Never put wire text in an exception message.
- Declare every class `final`.
- Write one-line javadoc, only where the signature cannot say it; comment only as CLAUDE.md allows.
- Test in JUnit 6 under `.claude/rules/tests.md`: a behaviour-named method, one behaviour each, no loop, `if` or `try`, `assertThrows` with the message, `@ParameterizedTest` with `argumentSet` for cases, no mocks.
