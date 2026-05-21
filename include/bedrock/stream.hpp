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

#if !defined(__cpp_lib_byteswap) || __cpp_lib_byteswap < 202110L
namespace std {
template <std::integral T>
constexpr T byteswap(T value) noexcept
{
    static_assert(std::has_unique_object_representations_v<T>, "T may not have padding bits");
    auto repr = std::bit_cast<std::array<std::byte, sizeof(T)>>(value);
    std::ranges::reverse(repr);
    return std::bit_cast<T>(repr);
}
}  // namespace std
#endif

namespace bedrock::protocol {

class BinaryReader {
public:
    template <class T>
    using Result = std::expected<T, std::error_code>;

    explicit BinaryReader(std::span<const std::uint8_t> buf) : view_(buf) {}

    void setReadPointer(std::size_t p) { read_pos_ = p; }
    [[nodiscard]] auto getReadPointer() const { return read_pos_; }
    [[nodiscard]] auto getUnreadLength() const { return view_.size() - read_pos_; }
    [[nodiscard]] auto getLength() const { return view_.size(); }
    [[nodiscard]] auto getView() const { return view_; }
    [[nodiscard]] auto canRead() const { return read_pos_ < view_.size(); }

    // Fixed-width read, native-endian little by default.
    template <typename T>
        requires(std::integral<T> || std::floating_point<T>)
    auto read() -> Result<T>
    {
        return read<T, std::endian::little>();
    }

    // Fixed-width read with explicit byte order. `bool` is a special case
    // that accepts any non-zero byte as true (matching the wire convention).
    template <typename T, std::endian Order>
        requires(std::integral<T> || std::floating_point<T>)
    auto read() -> Result<T>
    {
        if constexpr (std::same_as<T, bool>) {
            std::uint8_t b = 0;
            auto r = read(&b, 1);
            if (!r) {
                return make_unexpected(r.error());
            }
            return b != 0;
        }
        else {
            T value{};
            auto r = read(&value, sizeof(value));
            if (!r) {
                return make_unexpected(r.error());
            }
            if constexpr (sizeof(T) == 1 || Order == std::endian::native) {
                return value;
            }
            else if constexpr (std::floating_point<T>) {
                using U = std::conditional_t<sizeof(T) == 4, std::uint32_t, std::uint64_t>;
                return std::bit_cast<T>(std::byteswap(std::bit_cast<U>(value)));
            }
            else {
                return std::byteswap(value);
            }
        }
    }

    // Length-prefixed string (varuint32 byte count, then raw bytes).
    template <typename T>
        requires std::same_as<T, std::string>
    auto read() -> Result<std::string>
    {
        auto len = readVarInt<std::uint32_t>();
        if (!len) {
            return make_unexpected(len.error());
        }
        std::string out(*len, '\0');
        auto r = read(out.data(), *len);
        if (!r) {
            return make_unexpected(r.error());
        }
        return out;
    }

    // All remaining unread bytes in the frame. Used for trailing payloads
    // that the wire leaves length-less because the frame boundary
    // terminates them.
    auto readRemaining() -> Result<std::string>
    {
        const auto remaining = getUnreadLength();
        std::string out(remaining, '\0');
        auto r = read(out.data(), remaining);
        if (!r) {
            return make_unexpected(r.error());
        }
        return out;
    }

    // LEB128 varint, zigzag-decoded for signed `T`. Reading more than
    // ceil(bits(T)/7) continuation bytes is malformed input (5 for 32-bit,
    // 10 for 64-bit) and yields `value_too_large`.
    template <std::integral T>
    auto readVarInt() -> Result<T>
    {
        using U = std::make_unsigned_t<T>;
        constexpr int kMaxBytes = (sizeof(T) * 8 + 6) / 7;
        U value = 0;
        for (int n = 0; n < kMaxBytes; ++n) {
            std::uint8_t b = 0;
            auto r = read(&b, 1);
            if (!r) {
                return make_unexpected(r.error());
            }
            value |= (static_cast<U>(b) & U{0x7F}) << (n * 7);
            if ((b & 0x80u) == 0) {
                if constexpr (std::is_signed_v<T>) {
                    return static_cast<T>((value >> 1) ^ -(value & U{1}));
                }
                else {
                    return static_cast<T>(value);
                }
            }
        }
        return make_unexpected(std::make_error_code(std::errc::value_too_large));
    }

private:
    auto read(void *target, std::size_t num) -> Result<void>
    {
        if (num == 0) {
            return {};
        }
        const auto end = read_pos_ + num;
        if (end < read_pos_ || end > view_.size()) {
            return make_unexpected(std::make_error_code(std::errc::no_message_available));
        }
        std::memcpy(target, view_.data() + read_pos_, num);
        read_pos_ = end;
        return {};
    }

    std::span<const std::uint8_t> view_;
    std::size_t read_pos_ = 0;
};

class BinaryStream {
public:
    explicit BinaryStream(std::vector<std::uint8_t> &buffer) : buffer_(buffer) {}

    void writeRawBytes(std::span<const std::uint8_t> bytes) { write(bytes.data(), bytes.size()); }

    // Same, accepting a string_view so a `bytes` field (carried as
    // std::string) can be written without reinterpret_cast at the call site.
    void writeRawBytes(std::string_view bytes) { write(bytes.data(), bytes.size()); }

    // Fixed-width write, native-endian little by default. `value` is converted
    // to the wire type `T`, so callers need not spell the cast.
    template <typename T, typename V>
        requires((std::integral<T> || std::floating_point<T>) &&
                 requires(V v) { static_cast<T>(v); })
    void write(V value)
    {
        write<T, std::endian::little>(value);
    }

    // Fixed-width write with explicit byte order.
    template <typename T, std::endian Order, typename V>
        requires((std::integral<T> || std::floating_point<T>) &&
                 requires(V v) { static_cast<T>(v); })
    void write(V raw)
    {
        const T value = static_cast<T>(raw);
        if constexpr (sizeof(T) == 1) {
            const auto byte = static_cast<std::uint8_t>(value);
            write(&byte, 1);
        }
        else if constexpr (Order != std::endian::native) {
            if constexpr (std::floating_point<T>) {
                using U = std::conditional_t<sizeof(T) == 4, std::uint32_t, std::uint64_t>;
                U bits = std::byteswap(std::bit_cast<U>(value));
                write(&bits, sizeof(bits));
            }
            else {
                T swapped = std::byteswap(value);
                write(&swapped, sizeof(swapped));
            }
        }
        else {
            write(&value, sizeof(value));
        }
    }

    // Length-prefixed string (varuint32 byte count, then raw bytes).
    void write(std::string_view value)
    {
        writeVarInt<std::uint32_t>(value.size());
        write(value.data(), value.size());
    }

    // LEB128 varint, zigzag-encoded for signed `T`. The argument is converted
    // to `T`, as in `write`.
    template <std::integral T, typename V>
        requires requires(V v) { static_cast<T>(v); }
    void writeVarInt(V raw)
    {
        const T value = static_cast<T>(raw);
        using U = std::make_unsigned_t<T>;
        U bits;
        if constexpr (std::is_signed_v<T>) {
            constexpr int kShift = sizeof(T) * 8 - 1;
            bits = static_cast<U>((value >> kShift) ^ (value << 1));
        }
        else {
            bits = value;
        }
        do {
            std::uint8_t byte = bits & U{0x7F};
            bits >>= 7;
            const auto out = static_cast<std::uint8_t>(bits ? (byte | 0x80u) : byte);
            write(&out, 1);
        } while (bits);
    }

private:
    void write(const void *data, std::size_t size)
    {
        if (size == 0) {
            return;
        }
        const auto *p = static_cast<const std::uint8_t *>(data);
        buffer_.insert(buffer_.end(), p, p + size);
    }

    std::vector<std::uint8_t> &buffer_;
};

}  // namespace bedrock::protocol
