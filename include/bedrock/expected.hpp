// Small helpers over C++23 std::expected.
#pragma once

#include <expected>
#include <type_traits>
#include <utility>

namespace bedrock::protocol {

template <class E>
constexpr auto make_unexpected(E &&error)
{
    return std::unexpected<std::decay_t<E>>{std::forward<E>(error)};
}

}  // namespace bedrock::protocol
