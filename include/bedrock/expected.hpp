// std::expected compatibility shim.
//
// On C++23-capable standard libraries (__cpp_lib_expected >= 202211L) this is
// just <expected>; on older toolchains, aliases tl::expected as std::expected
// so all sites can speak std::expected uniformly.
//
// We deliberately do NOT alias `std::unexpected`: libstdc++ keeps the
// deprecated `void std::unexpected()` function (the old set_unexpected_handler
// mechanism) around even in C++20 mode, which shadows any type-alias we'd
// add. Instead, callers construct errors via `tl::unexpected{e}`, which
// converts implicitly to `std::expected`. On the C++23 path we mirror
// `tl::unexpected` to `std::unexpected` so call-sites are identical.
#pragma once

#if defined(__cpp_lib_expected) && __cpp_lib_expected >= 202211L
#  include <expected>

namespace tl {

template <class E>
using unexpected = std::unexpected<E>;

}  // namespace tl

#else
#  include <tl/expected.hpp>

namespace std {

template <class T, class E>
using expected = ::tl::expected<T, E>;

}  // namespace std

#endif
