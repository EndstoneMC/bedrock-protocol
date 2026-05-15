// std::expected compatibility shim.
//
// On C++23-capable standard libraries (__cpp_lib_expected >= 202211L) this is
// just <expected>; on older toolchains, aliases tl::expected as std::expected
// so all sites can speak std::expected uniformly.

#pragma once

#include <type_traits>
#include <utility>

#if defined(__cpp_lib_expected) && __cpp_lib_expected >= 202211L
#include <expected>
#else
#include <tl/expected.hpp>

namespace std {

template <class T, class E>
using expected = ::tl::expected<T, E>;

}  // namespace std

#endif

namespace bedrock::protocol {

template <class E>
constexpr auto make_unexpected(E &&error)
{
#if defined(__cpp_lib_expected) && __cpp_lib_expected >= 202211L
    return std::unexpected<std::decay_t<E>>{std::forward<E>(error)};
#else
    return ::tl::unexpected<std::decay_t<E>>{std::forward<E>(error)};
#endif
}

}  // namespace bedrock::protocol
