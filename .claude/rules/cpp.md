---
paths:
  - "include/**"
  - "python/**/*.{cpp,hpp,h}"
---
# Hand-written C++

- Include the repo's own headers with quotes and the full path from the include root (`"bedrock/protocol/stream.hpp"`); use `<>` only for the standard library and third-party headers; never use `./` or `../`.
- Open every header with `#pragma once`, with nothing above it.
- Keep one code path for every platform, toolchain and version: no `#if` alternative and no polyfill; raise the toolchain floor instead.
- Keep one namespace block per file with inner namespaces nested inside it; never close a namespace and reopen it.
- Use `struct` only for passive data with no invariant; anything with an invariant is a `class` with private members.
- Declare public, then protected, then private; within each, declare types, constants, constructors, methods, then data members.
- Mark a single-argument constructor `explicit`, except a sum type's constructors from its own alternatives.
- Return results as values (`std::expected`, or a struct to destructure); never write through an out-parameter.
- Report bad wire bytes as `std::unexpected(std::error_code)`, never as an exception; throw a `std::` exception only for API misuse, such as wrong-type access.
- Spell the return type of every function in a public header; deduce one only where it cannot be named.
- Give every overload of a name one meaning; a length-prefixed write and a raw write take different names.
- Use `std::` fixed-width integers at the width the wire declares, and `std::size_t` for counts and indices.
- Capture explicitly in a lambda that outlives its scope; use `[&]` only in one that runs in place.
- Constrain templates with concepts, `if constexpr` and fold expressions; never use SFINAE, `enable_if` or recursive instantiation.
- Own heap objects by value or through `std::unique_ptr`; never use an owning `new`.
- Build strings with `std::format`, never with `+` chains of `std::string` and `std::to_string`.
- Name a std-shaped facility the std way (`packet_of_t`, `has_packet_v`, `enum_cast`); a hand-written type that mirrors a BDS type keeps BDS's names.
- Run clang-format and clang-tidy on hand-written files only, never on generated code.
