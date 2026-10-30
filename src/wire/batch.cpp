// Adapted from bedrock-bot (Apache-2.0); framing and boundary checks modified.
#include <bedrock/protocol/wire/batch.h>

#include <snappy.h>
#include <zlib.h>

#include <array>
#include <climits>
#include <limits>

namespace bedrock::protocol::wire {
namespace {
bool validLimits(const BatchLimits &limits)
{
    // The compression/EVP entry points take bounded integer sizes. This also makes
    // the conservative compressed-wire cap below safe to calculate without overflow.
    return limits.max_batch_bytes > 0 && limits.max_batch_bytes <= (INT_MAX - 1024) / 2 &&
           limits.max_packet_bytes > 0 && limits.max_packets > 0;
}
std::size_t varintSize(std::uint32_t value)
{
    std::size_t size = 1;
    while (value >= 128) {
        value >>= 7;
        ++size;
    }
    return size;
}
void appendVarint(std::string &out, std::uint32_t value)
{
    while (value >= 128) {
        out.push_back(static_cast<char>((value & 127) | 128));
        value >>= 7;
    }
    out.push_back(static_cast<char>(value));
}
std::expected<std::uint32_t, std::string> takeLength(std::string_view &input)
{
    std::uint32_t value = 0;
    for (unsigned int i = 0; i < 5; ++i) {
        if (input.empty()) {
            return std::unexpected("truncated packet length");
        }
        const auto byte = static_cast<unsigned char>(input.front());
        input.remove_prefix(1);
        if (i == 4 && byte > 15) {
            return std::unexpected("packet length overflows uint32");
        }
        value |= std::uint32_t(byte & 127) << (7 * i);
        if ((byte & 128) == 0) {
            return value;
        }
    }
    return std::unexpected("invalid packet length");
}
std::expected<std::string, std::string> deflateRaw(std::string_view input)
{
    z_stream stream{};
    if (deflateInit2(&stream, Z_DEFAULT_COMPRESSION, Z_DEFLATED, -MAX_WBITS, 8, Z_DEFAULT_STRATEGY) != Z_OK) {
        return std::unexpected("raw DEFLATE initialization failed");
    }
    struct End {
        z_stream *stream;
        ~End() { deflateEnd(stream); }
    } end{&stream};
    std::string result(deflateBound(&stream, static_cast<uLong>(input.size())), '\0');
    stream.next_in = reinterpret_cast<Bytef *>(const_cast<char *>(input.data()));
    stream.avail_in = static_cast<uInt>(input.size());
    stream.next_out = reinterpret_cast<Bytef *>(result.data());
    stream.avail_out = static_cast<uInt>(result.size());
    if (deflate(&stream, Z_FINISH) != Z_STREAM_END || stream.avail_in != 0) {
        return std::unexpected("raw DEFLATE compression failed");
    }
    result.resize(stream.total_out);
    return result;
}
std::expected<std::string, std::string> inflateRaw(std::string_view input, std::size_t limit)
{
    z_stream stream{};
    if (inflateInit2(&stream, -MAX_WBITS) != Z_OK) {
        return std::unexpected("raw DEFLATE initialization failed");
    }
    struct End {
        z_stream *stream;
        ~End() { inflateEnd(stream); }
    } end{&stream};
    stream.next_in = reinterpret_cast<Bytef *>(const_cast<char *>(input.data()));
    stream.avail_in = static_cast<uInt>(input.size());
    std::string result;
    std::array<char, 16384> chunk{};
    for (;;) {
        stream.next_out = reinterpret_cast<Bytef *>(chunk.data());
        stream.avail_out = static_cast<uInt>(chunk.size());
        const auto before = stream.avail_in;
        const auto status = inflate(&stream, Z_NO_FLUSH);
        const auto count = chunk.size() - stream.avail_out;
        if (count > limit - result.size()) {
            return std::unexpected("decompressed batch exceeds byte limit");
        }
        result.append(chunk.data(), count);
        if (status == Z_STREAM_END) {
            if (stream.avail_in != 0) {
                return std::unexpected("trailing raw DEFLATE bytes");
            }
            return result;
        }
        if (status != Z_OK || (before == stream.avail_in && count == 0)) {
            return std::unexpected("invalid or truncated raw DEFLATE batch");
        }
    }
}
}  // namespace

BatchCodec::BatchCodec(BatchLimits limits) : limits_(limits) {}

std::expected<void, std::string> BatchCodec::setCompression(Compression compression, std::uint16_t threshold)
{
    if (auto access = checkAccess(); !access) return std::unexpected(access.error());
    if (compression != Compression::none && compression != Compression::zlib && compression != Compression::snappy) {
        return std::unexpected("unsupported batch compression");
    }
    compression_ = compression;
    threshold_ = threshold;
    return {};
}

std::expected<void, std::string> BatchCodec::enableEncryption(const std::array<unsigned char, 32> &key)
{
    if (auto access = checkAccess(); !access) return std::unexpected(access.error());
    if (cipher_) {
        return std::unexpected("batch encryption is already enabled");
    }
    auto cipher = PacketCipher::create(key);
    if (!cipher) {
        return std::unexpected(cipher.error());
    }
    cipher_.emplace(std::move(*cipher));
    return {};
}

std::expected<std::string, std::string> BatchCodec::encode(std::span<const std::string_view> packets)
{
    if (auto access = checkAccess(); !access) return std::unexpected(access.error());
    if (!validLimits(limits_)) {
        return std::unexpected("invalid batch limits");
    }
    if (packets.empty() || packets.size() > limits_.max_packets) {
        return std::unexpected("invalid batch packet count");
    }
    std::size_t size = 0;
    for (const auto packet : packets) {
        if (packet.empty() || packet.size() > limits_.max_packet_bytes || packet.size() > UINT32_MAX) {
            return std::unexpected("invalid packet byte length");
        }
        const auto prefix_size = varintSize(static_cast<std::uint32_t>(packet.size()));
        if (prefix_size > limits_.max_batch_bytes - size ||
            packet.size() > limits_.max_batch_bytes - size - prefix_size) {
            return std::unexpected("batch exceeds byte limit");
        }
        size += prefix_size + packet.size();
    }
    std::string payload;
    payload.reserve(size);
    for (const auto packet : packets) {
        appendVarint(payload, static_cast<std::uint32_t>(packet.size()));
        payload.append(packet);
    }
    if (compression_) {
        const auto mode = payload.size() < threshold_ ? Compression::none : *compression_;
        if (mode == Compression::zlib) {
            auto compressed = deflateRaw(payload);
            if (!compressed) {
                return std::unexpected(compressed.error());
            }
            payload = std::move(*compressed);
        }
        else if (mode == Compression::snappy) {
            std::string compressed;
            snappy::Compress(payload.data(), payload.size(), &compressed);
            payload = std::move(compressed);
        }
        payload.insert(payload.begin(), mode == Compression::none ? static_cast<char>(0xff) : static_cast<char>(mode));
    }
    if (cipher_) {
        auto encrypted = cipher_->encrypt(payload);
        if (!encrypted) {
            return std::unexpected(encrypted.error());
        }
        payload = std::move(*encrypted);
    }
    return payload;
}

std::expected<void, std::string> BatchCodec::checkAccess() const
{
    if (std::this_thread::get_id() != owner_) return std::unexpected("BatchCodec accessed outside its owner thread");
    if (terminal_) return std::unexpected("BatchCodec is terminal");
    return {};
}

std::expected<std::vector<std::string>, std::string> BatchCodec::decode(std::string_view wire)
{
    if (auto access = checkAccess(); !access) return std::unexpected(access.error());
    struct Failure {
        bool &terminal;
        bool success = false;
        ~Failure() { if (!success) terminal = true; }
    } failure{terminal_};
    auto result = decodeImpl(wire);
    failure.success = result.has_value();
    return result;
}

std::expected<std::vector<std::string>, std::string> BatchCodec::decodeImpl(std::string_view wire)
{
    if (!validLimits(limits_)) {
        return std::unexpected("invalid batch limits");
    }
    // Bound ciphertext before EVP allocates. Both supported codecs' worst-case
    // output fits this cap, including selector, checksum and marker overhead.
    if (wire.size() > limits_.max_batch_bytes * 2 + 1024) {
        return std::unexpected("wire batch exceeds byte limit");
    }
    std::string decrypted;
    if (cipher_) {
        auto result = cipher_->decrypt(wire);
        if (!result) {
            return std::unexpected(result.error());
        }
        decrypted = std::move(*result);
        wire = decrypted;
    }
    std::string decompressed;
    if (compression_) {
        if (wire.empty()) {
            return std::unexpected("missing batch compression selector");
        }
        const auto selector = static_cast<unsigned char>(wire.front());
        wire.remove_prefix(1);
        if (selector != 0xff) {
            if (*compression_ == Compression::none || selector != static_cast<std::uint16_t>(*compression_)) {
                return std::unexpected("unexpected batch compression selector");
            }
            if (*compression_ == Compression::zlib) {
                auto result = inflateRaw(wire, limits_.max_batch_bytes);
                if (!result) {
                    return std::unexpected(result.error());
                }
                decompressed = std::move(*result);
            }
            else {
                std::size_t length = 0;
                if (!snappy::GetUncompressedLength(wire.data(), wire.size(), &length) ||
                    length > limits_.max_batch_bytes) {
                    return std::unexpected("invalid or oversized Snappy length");
                }
                if (!snappy::IsValidCompressedBuffer(wire.data(), wire.size())) {
                    return std::unexpected("invalid or trailing Snappy bytes");
                }
                decompressed.resize(length);
                if (!snappy::RawUncompress(wire.data(), wire.size(), decompressed.data())) {
                    return std::unexpected("invalid Snappy batch");
                }
            }
            wire = decompressed;
        }
    }
    if (wire.empty() || wire.size() > limits_.max_batch_bytes) {
        return std::unexpected("invalid batch byte length");
    }
    std::vector<std::string> packets;
    while (!wire.empty()) {
        if (packets.size() >= limits_.max_packets) {
            return std::unexpected("batch packet count exceeds limit");
        }
        auto length = takeLength(wire);
        if (!length) {
            return std::unexpected(length.error());
        }
        if (*length == 0 || *length > limits_.max_packet_bytes || *length > wire.size()) {
            return std::unexpected("invalid or truncated packet byte length");
        }
        packets.emplace_back(wire.substr(0, *length));
        wire.remove_prefix(*length);
    }
    return packets;
}
}  // namespace bedrock::protocol::wire
