// Byte-stream primitives used by the Bedrock-Protocol runtime and the
// generated packet (de)serialisers. Kept separate from <bedrock/protocol.hpp>
// so the stream types can be reused without dragging in everything else.
#pragma once

#include <cstdint>
#include <span>
#include <vector>

namespace bedrock::protocol {

class BinaryStream {
public:
    std::vector<std::uint8_t> data;
    auto put_u8(std::uint8_t v) { data.push_back(v); }
};

class ReadOnlyBinaryStream {
public:
    explicit ReadOnlyBinaryStream(std::span<const std::uint8_t> buf)
        : buf_(buf), pos_(buf.data()) {}

    auto getByte() { return *pos_++; }
    auto eof() const { return pos_ >= buf_.data() + buf_.size(); }

private:
    std::span<const std::uint8_t> buf_;
    const std::uint8_t*           pos_;
};

}  // namespace bedrock::protocol
