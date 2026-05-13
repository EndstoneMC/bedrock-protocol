// Minimal Bedrock-Protocol runtime. Just enough surface area for the generated
// code to compile and link. Real implementations replace these symbols.
#pragma once

#include <cstdint>
#include <variant>

#include <bedrock/stream.hpp>

namespace bedrock::protocol {

// ---------- uvarint32 ---------------------------------------------------

inline void write_uvarint32(BinaryStream& s, std::uint32_t v) {
    while (v >= 0x80u) {
        s.put_u8(static_cast<std::uint8_t>(v | 0x80u));
        v >>= 7;
    }
    s.put_u8(static_cast<std::uint8_t>(v));
}

inline std::uint32_t read_uvarint32(ReadOnlyBinaryStream& s) {
    auto v     = std::uint32_t{0};
    auto shift = 0;
    while (true) {
        auto b = s.getByte();
        v |= static_cast<std::uint32_t>(b & 0x7fu) << shift;
        if ((b & 0x80u) == 0) break;
        shift += 7;
    }
    return v;
}

// ---------- switch-case payload defaults --------------------------------
// The generated code calls these to (de)serialise the payload of a switch
// case after the discriminator has been written. The default template
// no-ops, so empty placeholder structs link cleanly; overload for any
// payload type that has a real wire format.

template <class T>
inline void write_payload(BinaryStream&, const T&) {}

template <class T>
inline void read_payload(ReadOnlyBinaryStream&, T&) {}

inline void write_payload(BinaryStream&, std::monostate) {}
inline void read_payload(ReadOnlyBinaryStream&, std::monostate&) {}

}  // namespace bedrock::protocol
