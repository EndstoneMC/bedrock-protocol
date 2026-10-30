// Adapted from bedrock-bot (Apache-2.0); framing and boundary checks modified.
#include <bedrock/protocol/wire/crypto.h>

#include <algorithm>
#include <climits>
#include <limits>
#include <utility>

#include <openssl/crypto.h>

namespace bedrock::protocol::wire {
namespace {
std::expected<std::array<unsigned char, 32>, std::string> checksum(std::uint64_t counter, std::string_view payload,
                                                                   const std::array<unsigned char, 32> &key)
{
    std::array<unsigned char, 8> count{};
    for (std::size_t i = 0; i < count.size(); ++i) {
        count[i] = static_cast<unsigned char>(counter >> (8 * i));
    }
    std::unique_ptr<EVP_MD_CTX, decltype(&EVP_MD_CTX_free)> ctx(EVP_MD_CTX_new(), EVP_MD_CTX_free);
    std::array<unsigned char, 32> digest{};
    unsigned int size = 0;
    if (!ctx || EVP_DigestInit_ex(ctx.get(), EVP_sha256(), nullptr) != 1 ||
        EVP_DigestUpdate(ctx.get(), count.data(), count.size()) != 1 ||
        EVP_DigestUpdate(ctx.get(), payload.data(), payload.size()) != 1 ||
        EVP_DigestUpdate(ctx.get(), key.data(), key.size()) != 1 ||
        EVP_DigestFinal_ex(ctx.get(), digest.data(), &size) != 1 || size != digest.size()) {
        return std::unexpected("batch checksum computation failed");
    }
    return digest;
}
}  // namespace

PacketCipher::PacketCipher(PacketCipher &&other) noexcept
    : send_(std::move(other.send_)), receive_(std::move(other.receive_)), key_(other.key_),
      send_counter_(other.send_counter_), receive_counter_(other.receive_counter_), poisoned_(other.poisoned_)
{
    OPENSSL_cleanse(other.key_.data(), other.key_.size());
    other.poisoned_ = true;
}

PacketCipher &PacketCipher::operator=(PacketCipher &&other) noexcept
{
    if (this != &other) {
        OPENSSL_cleanse(key_.data(), key_.size());
        send_ = std::move(other.send_);
        receive_ = std::move(other.receive_);
        key_ = other.key_;
        send_counter_ = other.send_counter_;
        receive_counter_ = other.receive_counter_;
        poisoned_ = other.poisoned_;
        OPENSSL_cleanse(other.key_.data(), other.key_.size());
        other.poisoned_ = true;
    }
    return *this;
}

PacketCipher::~PacketCipher()
{
    OPENSSL_cleanse(key_.data(), key_.size());
}

std::expected<PacketCipher, std::string> PacketCipher::create(const std::array<unsigned char, 32> &key)
{
    PacketCipher cipher;
    cipher.key_ = key;
    cipher.send_.reset(EVP_CIPHER_CTX_new());
    cipher.receive_.reset(EVP_CIPHER_CTX_new());
    std::array<unsigned char, 16> iv{};
    std::copy_n(key.begin(), 12, iv.begin());
    iv.back() = 2;
    if (!cipher.send_ || !cipher.receive_ ||
        EVP_EncryptInit_ex2(cipher.send_.get(), EVP_aes_256_ctr(), key.data(), iv.data(), nullptr) != 1 ||
        EVP_EncryptInit_ex2(cipher.receive_.get(), EVP_aes_256_ctr(), key.data(), iv.data(), nullptr) != 1) {
        return std::unexpected("AES-256-CTR initialization failed");
    }
    return cipher;
}

std::expected<std::string, std::string> PacketCipher::encrypt(std::string_view plaintext)
{
    if (poisoned_ || !send_) {
        return std::unexpected("packet cipher is no longer usable");
    }
    if (plaintext.size() > INT_MAX - 8 || send_counter_ == std::numeric_limits<std::uint64_t>::max()) {
        poisoned_ = true;
        return std::unexpected("packet cipher send limit exceeded");
    }
    auto digest = checksum(send_counter_, plaintext, key_);
    if (!digest) {
        poisoned_ = true;
        return std::unexpected(digest.error());
    }
    std::string result(plaintext);
    result.append(reinterpret_cast<const char *>(digest->data()), 8);
    int written = 0;
    if (EVP_EncryptUpdate(send_.get(), reinterpret_cast<unsigned char *>(result.data()), &written,
                          reinterpret_cast<const unsigned char *>(result.data()),
                          static_cast<int>(result.size())) != 1 ||
        static_cast<std::size_t>(written) != result.size()) {
        poisoned_ = true;
        return std::unexpected("batch encryption failed");
    }
    ++send_counter_;
    return result;
}

std::expected<std::string, std::string> PacketCipher::decrypt(std::string_view ciphertext)
{
    if (poisoned_ || !receive_) {
        return std::unexpected("packet cipher is no longer usable");
    }
    if (ciphertext.size() < 8 || ciphertext.size() > INT_MAX ||
        receive_counter_ == std::numeric_limits<std::uint64_t>::max()) {
        poisoned_ = true;
        return std::unexpected("invalid encrypted batch size or receive counter");
    }
    std::string result(ciphertext.size(), '\0');
    int written = 0;
    if (EVP_EncryptUpdate(receive_.get(), reinterpret_cast<unsigned char *>(result.data()), &written,
                          reinterpret_cast<const unsigned char *>(ciphertext.data()),
                          static_cast<int>(ciphertext.size())) != 1 ||
        static_cast<std::size_t>(written) != result.size()) {
        poisoned_ = true;
        return std::unexpected("batch decryption failed");
    }
    auto payload = std::string_view(result).substr(0, result.size() - 8);
    auto digest = checksum(receive_counter_, payload, key_);
    if (!digest || CRYPTO_memcmp(digest->data(), result.data() + payload.size(), 8) != 0) {
        poisoned_ = true;
        return std::unexpected("encrypted batch checksum mismatch");
    }
    ++receive_counter_;
    result.resize(payload.size());
    return result;
}
}  // namespace bedrock::protocol::wire
