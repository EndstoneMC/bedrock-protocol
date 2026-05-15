// std::expected compatibility shim.
//
// On C++23-capable standard libraries (__cpp_lib_expected >= 202211L) this is
// just <expected>; on older toolchains, aliases tl::expected as std::expected
// so all sites can speak std::expected uniformly.
#pragma once

#if defined(__cpp_lib_expected) && __cpp_lib_expected >= 202211L
#include <expected>

#else
#include <tl/expected.hpp>

namespace std {
template <class T, class E>
using expected = ::tl::expected<T, E>;

template <class E>
using unexpected = ::tl::unexpected<E>;
}  // namespace std

#endif
