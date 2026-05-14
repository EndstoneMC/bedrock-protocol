// Ported verbatim from Endstone's bedrock/core/utility/binary_stream.{h,cpp}
// (commit d4c9c420ec38acc9bb3eb618fec964b3dc55279a), adapted to use
// std::expected for errors, std::vector<std::uint8_t> for the buffer, and
// without the doc-helper / hook-library scaffolding.
#pragma once

#include <algorithm>
#include <array>
#include <bit>
#include <concepts>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <span>
#include <string>
#include <string_view>
#include <system_error>
#include <type_traits>
#include <vector>

#include "expected.hpp"  // IWYU pragma: keep

namespace bedrock::protocol {

namespace details {
#if defined(__cpp_lib_byteswap) && __cpp_lib_byteswap >= 202110L
using std::byteswap;
#else
template <std::integral T>
constexpr T byteswap(T value) noexcept
{
    static_assert(std::has_unique_object_representations_v<T>,
                  "T may not have padding bits");
    auto repr = std::bit_cast<std::array<std::byte, sizeof(T)>>(value);
    std::ranges::reverse(repr);
    return std::bit_cast<T>(repr);
}
#endif
}  // namespace details

class ReadOnlyBinaryStream {
public:
    template <class T>
    using Result = std::expected<T, std::error_code>;

    explicit ReadOnlyBinaryStream(std::span<const std::uint8_t> buf) : view_(buf) {}

    void setReadPointer(std::size_t p) { read_pos_ = p; }
    [[nodiscard]] auto getReadPointer() const { return read_pos_; }
    [[nodiscard]] auto getUnreadLength() const { return view_.size() - read_pos_; }
    [[nodiscard]] auto getLength() const { return view_.size(); }
    [[nodiscard]] auto hasOverflowed() const { return overflowed_; }
    [[nodiscard]] auto getView() const { return view_; }
    [[nodiscard]] auto canRead() const { return read_pos_ < view_.size(); }

    auto getByte() -> Result<std::uint8_t>
    {
        std::uint8_t value = 0;
        auto r = read(&value, sizeof(value));
        if (!r) {
            return tl::unexpected{r.error()};
        }
        return value;
    }

    auto getBool() -> Result<bool>
    {
        auto b = getByte();
        if (!b) {
            return tl::unexpected{b.error()};
        }
        return *b != 0;
    }

    auto getUnsignedShort() -> Result<std::uint16_t> { return fixedLE<std::uint16_t>(); }
    auto getSignedShort() -> Result<std::int16_t> { return fixedLE<std::int16_t>(); }
    auto getUnsignedInt() -> Result<std::uint32_t> { return fixedLE<std::uint32_t>(); }
    auto getSignedInt() -> Result<std::int32_t> { return fixedLE<std::int32_t>(); }
    auto getUnsignedInt64() -> Result<std::uint64_t> { return fixedLE<std::uint64_t>(); }
    auto getSignedInt64() -> Result<std::int64_t> { return fixedLE<std::int64_t>(); }
    auto getFloat() -> Result<float> { return fixedLE<float>(); }
    auto getDouble() -> Result<double> { return fixedLE<double>(); }

    auto getSignedBigEndianInt() -> Result<std::int32_t>
    {
        std::int32_t value = 0;
        auto r = read(&value, sizeof(value));
        if (!r) {
            return tl::unexpected{r.error()};
        }
        return details::byteswap(value);
    }

    auto getUnsignedVarInt() -> Result<std::uint32_t>
    {
        std::uint32_t value = 0;
        for (auto i = 0;; i += 7) {
            auto byte = getByte();
            if (!byte) {
                return tl::unexpected{byte.error()};
            }
            value |= (static_cast<std::uint32_t>(*byte) & 0x7Fu) << i;
            if ((*byte & 0x80u) == 0) {
                break;
            }
        }
        return value;
    }

    auto getUnsignedVarInt64() -> Result<std::uint64_t>
    {
        std::uint64_t value = 0;
        for (auto i = 0;; i += 7) {
            auto byte = getByte();
            if (!byte) {
                return tl::unexpected{byte.error()};
            }
            value |= (static_cast<std::uint64_t>(*byte) & std::uint64_t{0x7F}) << i;
            if ((*byte & 0x80u) == 0) {
                break;
            }
        }
        return value;
    }

    auto getVarInt() -> Result<std::int32_t>
    {
        auto u = getUnsignedVarInt();
        if (!u) {
            return tl::unexpected{u.error()};
        }
        return static_cast<std::int32_t>((*u >> 1) ^ -(*u & 1u));
    }

    auto getVarInt64() -> Result<std::int64_t>
    {
        auto u = getUnsignedVarInt64();
        if (!u) {
            return tl::unexpected{u.error()};
        }
        return static_cast<std::int64_t>((*u >> 1) ^ -(*u & std::uint64_t{1}));
    }

    auto getString() -> Result<std::string>
    {
        auto len = getUnsignedVarInt();
        if (!len) {
            return tl::unexpected{len.error()};
        }
        std::string out(*len, '\0');
        auto r = read(out.data(), *len);
        if (!r) {
            return tl::unexpected{r.error()};
        }
        return out;
    }

private:
    auto read(void *target, std::size_t num) -> Result<void>
    {
        if (overflowed_) {
            return tl::unexpected{std::make_error_code(std::errc::invalid_seek)};
        }
        if (num == 0) {
            return {};
        }
        const auto end = read_pos_ + num;
        if (end < read_pos_ || end > view_.size()) {
            overflowed_ = true;
            return tl::unexpected{std::make_error_code(std::errc::no_message_available)};
        }
        std::memcpy(target, view_.data() + read_pos_, num);
        read_pos_ = end;
        return {};
    }

    template <class T>
    auto fixedLE() -> Result<T>
    {
        T value{};
        auto r = read(&value, sizeof(value));
        if (!r) {
            return tl::unexpected{r.error()};
        }
        return value;  // host is LE; wire is LE; direct memcpy is the wire value
    }

    std::span<const std::uint8_t> view_;
    std::size_t read_pos_ = 0;
    bool overflowed_ = false;
};

class BinaryStream : public ReadOnlyBinaryStream {
public:
    BinaryStream() : ReadOnlyBinaryStream({}), buffer_(owned_) {}
    explicit BinaryStream(std::vector<std::uint8_t> &buffer) : ReadOnlyBinaryStream(buffer), buffer_(buffer) {}

    void writeByte(std::uint8_t value) { write(&value, sizeof(value)); }
    void writeBool(bool value) { writeByte(value ? 1u : 0u); }
    void writeUnsignedShort(std::uint16_t v) { write(&v, sizeof(v)); }
    void writeSignedShort(std::int16_t v) { write(&v, sizeof(v)); }
    void writeUnsignedInt(std::uint32_t v) { write(&v, sizeof(v)); }
    void writeSignedInt(std::int32_t v) { write(&v, sizeof(v)); }
    void writeUnsignedInt64(std::uint64_t v) { write(&v, sizeof(v)); }
    void writeSignedInt64(std::int64_t v) { write(&v, sizeof(v)); }
    void writeFloat(float v) { write(&v, sizeof(v)); }
    void writeDouble(double v) { write(&v, sizeof(v)); }

    void writeSignedBigEndianInt(std::int32_t value)
    {
        auto v = details::byteswap(value);
        write(&v, sizeof(v));
    }

    void writeUnsignedVarInt(std::uint32_t value)
    {
        do {
            std::uint8_t byte = value & 0x7Fu;
            value >>= 7;
            writeByte(value ? (byte | 0x80u) : byte);
        } while (value);
    }

    void writeUnsignedVarInt64(std::uint64_t value)
    {
        do {
            std::uint8_t byte = value & 0x7Fu;
            value >>= 7;
            writeByte(value ? (byte | 0x80u) : byte);
        } while (value);
    }

    void writeVarInt(std::int32_t value)
    {
        writeUnsignedVarInt(static_cast<std::uint32_t>((value >> 31) ^ (value << 1)));
    }

    void writeVarInt64(std::int64_t value)
    {
        writeUnsignedVarInt64(static_cast<std::uint64_t>((value >> 63) ^ (value << 1)));
    }

    void writeString(std::string_view value)
    {
        writeUnsignedVarInt(static_cast<std::uint32_t>(value.size()));
        write(value.data(), value.size());
    }

    void writeRawBytes(std::span<const std::uint8_t> bytes) { write(bytes.data(), bytes.size()); }

private:
    void write(const void *data, std::size_t size)
    {
        if (size == 0) {
            return;
        }
        const auto *p = static_cast<const std::uint8_t *>(data);
        buffer_.insert(buffer_.end(), p, p + size);
    }

    std::vector<std::uint8_t> owned_;
    std::vector<std::uint8_t> &buffer_;
};

}  // namespace bedrock::protocol
