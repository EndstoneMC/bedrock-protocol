---
paths:
  - "include/**"
  - "python/**/*.{cpp,hpp,h}"
  - "compiler/src/bedrock_protocol_compiler/cpp/**"
---

# Hand-written C++

- Include the repo's own headers with quotes and the full path from the include root (`"bedrock/protocol/stream.hpp"`); use `<>` only for the standard library and third-party headers; never use `./` or `../`.
- Name a header with its own `.cpp` `.h` and a header-only one `.hpp`; this holds for the generated headers too.
- Emit each schema module as a `.h` and a `.cpp` in the static library; never make generated code header-only.
- Give every version that shares a shape one C++ type, written out whole; never derive one version's type from another's.
- Open every header with `#pragma once`, with nothing above it.
- Keep one code path for every platform, toolchain and version: no `#if` alternative and no polyfill; raise the toolchain floor instead.
- Keep one namespace block per file with inner namespaces nested inside it; never close a namespace and reopen it.
- Use `struct` only for passive data with no invariant; anything with an invariant is a `class` with private members.
- Declare public, then protected, then private; within each, declare types, constants, constructors, methods, then data members.
- Mark a single-argument constructor `explicit`, except a sum type's constructors from its own alternatives.
- Return results as values (`std::expected`, or a struct to destructure); never write through an out-parameter.
- Report bad wire bytes as `std::unexpected(Errc)`; generated code names the failing field with `stream.fail`; never throw for wire bytes.
- Decode any integer an integer-coded enum carries, named or not; reject a name a name-coded enum lacks, and text a text-coded `UUID` cannot parse, with `Errc::unknown_value`.
- Spell the return type of every function in a public header; deduce one only where it cannot be named.
- Give every overload of a name one meaning; a length-prefixed write and a raw write take different names.
- Use `std::` fixed-width integers at the width the wire declares, and `std::size_t` for counts and indices.
- Capture explicitly in a lambda that outlives its scope; use `[&]` only in one that runs in place.
- Constrain templates with concepts, branch with `if constexpr` and expand packs with fold expressions; never use SFINAE, `enable_if` or recursive instantiation.
- Own an object by value, or through `std::unique_ptr` when it must live on the heap; never use an owning `new`.
- Build strings with `std::format`, never with `+` chains of `std::string` and `std::to_string`.
- Name a std-shaped facility the std way (`packet_of_t`, `has_packet_v`, `enum_cast`); a hand-written type that mirrors a BDS type keeps BDS's names.
- Name a bound Python attribute in caps when it holds one value (`ID`) and in lower case when it holds a collection (`versions`, `packets`).
- Give a caster's name and a bound signature the type its stub must read: the module path (`bedrock_protocol.nbt.CompoundTag`), a generic's arguments, `object` for `__eq__`.
- Never run clang-format or clang-tidy on generated code.
