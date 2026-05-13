// Byte-stream primitives used by the Bedrock-Protocol runtime and the
// generated packet (de)serialisers. Kept separate from <bedrock/protocol.hpp>
// so the stream types can be reused without dragging in everything else.
#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <system_error>
#include <vector>

#include <bedrock/expected.hpp>

namespace bedrock::protocol {

class ReadOnlyBinaryStream {
public:
    template <class T>
    using Result = std::expected<T, std::error_code>;

    explicit ReadOnlyBinaryStream(std::span<const std::uint8_t> buf) : view_(buf) {}

    auto canRead() const { return read_pos_ < view_.size(); }

    auto getByte() -> Result<std::uint8_t> {
        if (!canRead())
            return tl::unexpected{std::make_error_code(std::errc::no_message_available)};
        return view_[read_pos_++];
    }

private:
    std::span<const std::uint8_t> view_;
    std::size_t                   read_pos_ = 0;
};

class BinaryStream : public ReadOnlyBinaryStream {
public:
    // Default-constructed: own a fresh internal buffer.
    BinaryStream() : ReadOnlyBinaryStream({}), buffer_(owned_) {}

    // External-buffer constructor: write into the caller's vector.
    explicit BinaryStream(std::vector<std::uint8_t>& buffer)
        : ReadOnlyBinaryStream(buffer), buffer_(buffer) {}

    auto writeByte(std::uint8_t v) { buffer_.push_back(v); }

private:
    std::vector<std::uint8_t>  owned_;  // backing storage when default-constructed
    std::vector<std::uint8_t>& buffer_;
};

}  // namespace bedrock::protocol
