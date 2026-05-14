#pragma once

// IWYU pragma: begin_keep
#include "expected.hpp"
#include "stream.hpp"
// IWYU pragma: end_keep

namespace bedrock::protocol {
template <typename T>
struct Serializer;
}  // namespace bedrock::protocol

#include "protocol/all.hpp"  // IWYU pragma: keep
