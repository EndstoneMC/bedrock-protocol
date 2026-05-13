#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <system_error>
#include <vector>

#include "expected.hpp"  // IWYU pragma: keep

namespace bedrock::protocol {

class ReadOnlyBinaryStream {
public:
    template <class T>
    using Result = std::expected<T, std::error_code>;

    explicit ReadOnlyBinaryStream(std::span<const std::uint8_t> buf) : view_(buf) {}

    auto canRead() const { return read_pos_ < view_.size(); }

    auto getByte() -> Result<std::uint8_t>
    {
        if (!canRead()) {
            return tl::unexpected{std::make_error_code(std::errc::no_message_available)};
        }
        return view_[read_pos_++];
    }

    auto getUnsignedVarInt() -> Result<std::uint32_t>
    {
        constexpr auto kMaxBytes = 5;
        auto value = std::uint32_t{0};
        for (auto i = 0; i < kMaxBytes * 7; i += 7) {
            auto b = getByte();
            if (!b) {
                return tl::unexpected{b.error()};
            }
            value |= (static_cast<std::uint32_t>(*b) & 0x7Fu) << i;
            if ((*b & 0x80u) == 0) {
                return value;
            }
        }
        // Continuation bit still set after kMaxBytes - malformed varint.
        return tl::unexpected{std::make_error_code(std::errc::value_too_large)};
    }

private:
    std::span<const std::uint8_t> view_;
    std::size_t read_pos_ = 0;
};

class BinaryStream : public ReadOnlyBinaryStream {
public:
    // Default-constructed: own a fresh internal buffer.
    BinaryStream() : ReadOnlyBinaryStream({}), buffer_(owned_) {}

    // External-buffer constructor: write into the caller's vector.
    explicit BinaryStream(std::vector<std::uint8_t> &buffer) : ReadOnlyBinaryStream(buffer), buffer_(buffer) {}

    auto writeByte(std::uint8_t v) { buffer_.push_back(v); }

    auto writeUnsignedVarInt(std::uint32_t value)
    {
        // A uvarint32 of a uint32_t is at most ceil(32 / 7) = 5 bytes.
        do {
            const auto byte = static_cast<std::uint8_t>(value & 0x7Fu);
            value >>= 7;
            writeByte(value ? (byte | 0x80u) : byte);
        } while (value);
    }

private:
    std::vector<std::uint8_t> owned_;  // backing storage when default-constructed
    std::vector<std::uint8_t> &buffer_;
};

}  // namespace bedrock::protocol
