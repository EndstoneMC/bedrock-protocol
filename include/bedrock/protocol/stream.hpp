// Ported verbatim from Endstone's bedrock/core/utility/binary_stream.{h,cpp}
// (commit d4c9c420ec38acc9bb3eb618fec964b3dc55279a), adapted to use
// std::expected for errors, std::string_view / std::string for the buffer, and
// without the doc-helper / hook-library scaffolding.
#pragma once

#include <algorithm>
#include <array>
#include <bit>
#include <concepts>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include <string>
#include <string_view>
#include <system_error>
#include <type_traits>

#include <expected>

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

namespace detail {
template <std::integral T>
std::expected<std::size_t, std::error_code> countValue(T value)
{
    if constexpr (std::is_signed_v<T>) {
        if (value < 0) return std::unexpected(std::make_error_code(std::errc::value_too_large));
    }
    if (static_cast<std::uintmax_t>(value) > std::numeric_limits<std::size_t>::max())
        return std::unexpected(std::make_error_code(std::errc::value_too_large));
    return static_cast<std::size_t>(value);
}

inline std::expected<std::size_t, std::error_code> countOperation(
    std::expected<std::size_t, std::error_code> a, std::expected<std::size_t, std::error_code> b, char operation)
{
    if (!a) return a;
    if (!b) return b;
    switch (operation) {
    case '*':
        if (*b && *a > std::numeric_limits<std::size_t>::max() / *b) break;
        return *a * *b;
    case '+':
        if (*a > std::numeric_limits<std::size_t>::max() - *b) break;
        return *a + *b;
    case '-':
        if (*a < *b) break;
        return *a - *b;
    case '&': return *a & *b;
    }
    return std::unexpected(std::make_error_code(std::errc::value_too_large));
}
}  // namespace detail

struct DecodeLimits {
    std::size_t max_decoded_elements = 1'048'576;
    std::size_t max_decoded_bytes = 64 * 1024 * 1024;
    std::size_t max_depth = 128;
};

class DecodeBudget {
public:
    explicit DecodeBudget(DecodeLimits limits = {}) : limits_(limits) {}

    bool charge(std::size_t count, std::size_t width, bool elements = true)
    {
        if ((elements && count > limits_.max_decoded_elements - elements_) ||
            (width && count > (limits_.max_decoded_bytes - bytes_) / width)) {
            resource_failure_ = true;
            return false;
        }
        elements_ += elements ? count : 0;
        bytes_ += count * width;
        return true;
    }
    [[nodiscard]] std::size_t maxDepth() const { return std::min(limits_.max_depth, std::size_t{128}); }
    [[nodiscard]] bool resourceFailure() const { return resource_failure_; }
    void markResourceFailure() { resource_failure_ = true; }

private:
    DecodeLimits limits_;
    std::size_t elements_ = 0;
    std::size_t bytes_ = 0;
    bool resource_failure_ = false;
};

class BinaryReader {
public:
    template <class T>
    using Result = std::expected<T, std::error_code>;

    explicit BinaryReader(std::string_view buf, DecodeBudget *budget = nullptr)
        : view_(buf), budget_(budget ? budget : &local_budget_) {}

    BinaryReader(const BinaryReader &other)
        : view_(other.view_), read_pos_(other.read_pos_), local_budget_(other.local_budget_),
          budget_(other.budget_ == &other.local_budget_ ? &local_budget_ : other.budget_), depth_(other.depth_) {}
    BinaryReader &operator=(const BinaryReader &other)
    {
        if (this != &other) {
            view_ = other.view_;
            read_pos_ = other.read_pos_;
            local_budget_ = other.local_budget_;
            budget_ = other.budget_ == &other.local_budget_ ? &local_budget_ : other.budget_;
            depth_ = other.depth_;
        }
        return *this;
    }

    template <std::integral N>
    auto account(N count, std::size_t width, bool elements = true) -> Result<void>
    {
        if constexpr (std::is_signed_v<N>) {
            if (count < 0) return std::unexpected(std::make_error_code(std::errc::illegal_byte_sequence));
        }
        if (static_cast<std::uintmax_t>(count) > std::numeric_limits<std::size_t>::max() ||
            !budget_->charge(static_cast<std::size_t>(count), width, elements)) {
            budget_->markResourceFailure();
            return std::unexpected(std::make_error_code(std::errc::value_too_large));
        }
        return {};
    }

    class ReadScope {
    public:
        explicit ReadScope(BinaryReader &reader) : reader_(reader), entered_(reader.depth_ < reader.budget_->maxDepth())
        {
            if (entered_) ++reader_.depth_;
            else reader_.budget_->markResourceFailure();
        }
        ~ReadScope() { if (entered_) --reader_.depth_; }
        ReadScope(const ReadScope &) = delete;
        ReadScope &operator=(const ReadScope &) = delete;
        explicit operator bool() const { return entered_; }
    private:
        BinaryReader &reader_;
        bool entered_;
    };

    void setReadPointer(std::size_t p) { read_pos_ = p; }
    [[nodiscard]] auto getReadPointer() const { return read_pos_; }
    [[nodiscard]] auto getUnreadLength() const { return read_pos_ <= view_.size() ? view_.size() - read_pos_ : 0; }
    [[nodiscard]] auto getLength() const { return view_.size(); }
    [[nodiscard]] auto getView() const { return view_; }
    [[nodiscard]] auto canRead() const { return read_pos_ < view_.size(); }
    [[nodiscard]] bool resourceFailure() const { return budget_->resourceFailure(); }

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
                return std::unexpected(r.error());
            }
            return b != 0;
        }
        else {
            T value{};
            auto r = read(&value, sizeof(value));
            if (!r) {
                return std::unexpected(r.error());
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
            return std::unexpected(len.error());
        }
        if (*len > getUnreadLength()) {
            return std::unexpected(std::make_error_code(std::errc::message_size));
        }
        if (auto r = account(*len, 1, false); !r) return std::unexpected(r.error());
        std::string out(*len, '\0');
        auto r = read(out.data(), *len);
        if (!r) {
            return std::unexpected(r.error());
        }
        return out;
    }

    // All remaining unread bytes in the frame. Used for trailing payloads
    // that the wire leaves length-less because the frame boundary
    // terminates them.
    auto readRemaining() -> Result<std::string>
    {
        if (read_pos_ > view_.size()) return std::unexpected(std::make_error_code(std::errc::message_size));
        const auto remaining = getUnreadLength();
        if (auto r = account(remaining, 1, false); !r) return std::unexpected(r.error());
        std::string out(remaining, '\0');
        auto r = read(out.data(), remaining);
        if (!r) {
            return std::unexpected(r.error());
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
                return std::unexpected(r.error());
            }
            if (n == kMaxBytes - 1 && (b & 0x7fu) > (std::numeric_limits<U>::max() >> (n * 7))) {
                return std::unexpected(std::make_error_code(std::errc::value_too_large));
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
        return std::unexpected(std::make_error_code(std::errc::value_too_large));
    }

private:
    auto read(void *target, std::size_t num) -> Result<void>
    {
        if (num == 0) {
            return {};
        }
        const auto end = read_pos_ + num;
        if (end < read_pos_ || end > view_.size()) {
            return std::unexpected(std::make_error_code(std::errc::message_size));
        }
        std::memcpy(target, view_.data() + read_pos_, num);
        read_pos_ = end;
        return {};
    }

    std::string_view view_;
    std::size_t read_pos_ = 0;
    DecodeBudget local_budget_;
    DecodeBudget *budget_;
    std::size_t depth_ = 0;
};

class BinaryWriter {
public:
    explicit BinaryWriter(std::string &buffer) : buffer_(buffer) {}

    // Raw bytes, no length marker.
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
        buffer_.append(static_cast<const char *>(data), size);
    }

    std::string &buffer_;
};

}  // namespace bedrock::protocol
