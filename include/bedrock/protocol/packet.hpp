#pragma once

#include <type_traits>

// The packet registry. `bpc` compiles one module at a time, so no generated
// header sees every packet; each specializes `packet_of` for its own ids and the
// primary below answers `void` for an id nobody modelled. Reach it through
// <bedrock/protocol.hpp>, which stamps in every generated header -- a lone
// module include leaves its neighbours' packets reading as unmodelled.

namespace bedrock::protocol {

template <int V, int Id>
struct packet_of {
    using type = void;
};

template <int V, int Id>
using packet_of_t = typename packet_of<V, Id>::type;

template <int V, int Id>
inline constexpr bool has_packet_v = !std::is_void_v<packet_of_t<V, Id>>;

}  // namespace bedrock::protocol
