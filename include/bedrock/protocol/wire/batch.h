// Adapted from bedrock-bot (Apache-2.0); framing and boundary checks modified.
#pragma once

#include <cstddef>
#include <cstdint>
#include <expected>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>
#include <thread>

#include <bedrock/protocol/wire/crypto.h>

namespace bedrock::protocol::wire {
enum class Compression : std::uint16_t {
    zlib = 0,
    snappy = 1,
    none = 0xffff
};
struct BatchLimits {
    std::size_t max_batch_bytes = 16 * 1024 * 1024;
    std::size_t max_packet_bytes = 4 * 1024 * 1024;
    std::size_t max_packets = 4096;
};

// Owns all output and crypto state; call only on the application's owner thread.
class BatchCodec {
public:
    explicit BatchCodec(BatchLimits limits = {});
    BatchCodec(const BatchCodec &) = delete;
    BatchCodec &operator=(const BatchCodec &) = delete;
    void invalidate() { terminal_ = true; }
    std::expected<void, std::string> setCompression(Compression compression, std::uint16_t threshold);
    std::expected<void, std::string> enableEncryption(const std::array<unsigned char, 32> &key);
    std::expected<std::string, std::string> encode(std::span<const std::string_view> packets);
    std::expected<std::vector<std::string>, std::string> decode(std::string_view wire);

private:
    std::expected<std::vector<std::string>, std::string> decodeImpl(std::string_view wire);
    std::expected<void, std::string> checkAccess() const;
    const std::thread::id owner_ = std::this_thread::get_id();
    bool terminal_ = false;
    BatchLimits limits_;
    std::optional<Compression> compression_;
    std::uint16_t threshold_ = 0;
    std::optional<PacketCipher> cipher_;
};
}  // namespace bedrock::protocol::wire
