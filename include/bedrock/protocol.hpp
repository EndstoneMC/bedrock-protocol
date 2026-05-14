#pragma once

// IWYU pragma: begin_keep
#include "expected.hpp"
#include "stream.hpp"
// IWYU pragma: end_keep

namespace bedrock::protocol {

// Primary Codec template — protocol types specialize this in their generated
// header. Each specialization provides `serialize(BinaryStream&, ...)` and
// `deserialize(ReadOnlyBinaryStream&) -> std::expected<..., std::error_code>`.
template <typename T, int ProtocolVersion>
struct Codec;

}  // namespace bedrock::protocol

// Has to come after Codec is declared so the generated specializations bind to
// the primary template defined above.
#include "protocol/all.hpp"  // IWYU pragma: keep
