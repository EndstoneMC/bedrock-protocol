// Adapted from bedrock-bot (Apache-2.0); framing and boundary checks modified.
#pragma once

#include <array>
#include <cstdint>
#include <expected>
#include <memory>
#include <string>
#include <string_view>

#include <openssl/evp.h>

namespace bedrock::protocol::wire {

// One session, application owner thread only. Each direction is a continuous stream.
class PacketCipher {
public:
    PacketCipher(PacketCipher &&other) noexcept;
    PacketCipher &operator=(PacketCipher &&other) noexcept;
    ~PacketCipher();
    PacketCipher(const PacketCipher &) = delete;
    PacketCipher &operator=(const PacketCipher &) = delete;
    static std::expected<PacketCipher, std::string> create(const std::array<unsigned char, 32> &key);
    std::expected<std::string, std::string> encrypt(std::string_view plaintext);
    std::expected<std::string, std::string> decrypt(std::string_view ciphertext);

private:
    PacketCipher() = default;
    using Context = std::unique_ptr<EVP_CIPHER_CTX, decltype(&EVP_CIPHER_CTX_free)>;
    Context send_{nullptr, EVP_CIPHER_CTX_free};
    Context receive_{nullptr, EVP_CIPHER_CTX_free};
    std::array<unsigned char, 32> key_{};
    std::uint64_t send_counter_ = 0;
    std::uint64_t receive_counter_ = 0;
    bool poisoned_ = false;
};
}  // namespace bedrock::protocol::wire
