// Adapted from bedrock-bot (Apache-2.0); transport marker removed and terminal checks added.
#include <array>
#include <iostream>
#include <stdexcept>
#include <thread>

#include <bedrock/protocol/wire/batch.h>
#include <bedrock/protocol/wire/crypto.h>

#include "cipher_vectors.h"

namespace bw = bedrock::protocol::wire;

std::string unhex(std::string_view hex)
{
    std::string out;
    for (std::size_t i = 0; i < hex.size(); i += 2) {
        out.push_back(static_cast<char>(std::stoul(std::string(hex.substr(i, 2)), nullptr, 16)));
    }
    return out;
}

void check(bool condition, const char *message)
{
    if (!condition) {
        throw std::runtime_error(message);
    }
}

int main()
{
    try {
        const auto packet = unhex("010203");
        std::array<std::string_view, 1> packets{packet};
        for (auto [mode, hex] :
             std::array<std::pair<bw::Compression, const char *>, 3>{{{bw::Compression::zlib, "00636664620600"},
                                                                      {bw::Compression::snappy, "01040c03010203"},
                                                                      {bw::Compression::none, "ff03010203"}}}) {
            for (std::uint16_t threshold : {0, 4, 5}) {
                bw::BatchCodec codec;
                check(codec.setCompression(mode, threshold).has_value(), "compression configuration");
                const auto expected = unhex(threshold == 5 ? "ff03010203" : hex);
                check(codec.encode(packets) == expected, "independent compression bytes");
                check(codec.decode(expected) == std::vector<std::string>{packet}, "independent compression decode");
            }
        }
        bw::BatchCodec plain;
        std::array<std::string_view, 2> text{"abc", "de"};
        check(plain.encode(text) == unhex("03616263026465"), "no transport marker");
        check(plain.decode(unhex("810061")) == std::vector<std::string>{"a"}, "safe noncanonical length");
        for (const auto *hex : {"", "00", "80", "04616263", "ffffffff10", "808080808000", "ffffffff0f"}) {
            bw::BatchCodec codec;
            check(!codec.decode(unhex(hex)), "malformed frame accepted");
            check(!codec.encode(packets), "terminal encode accepted");
            check(!codec.setCompression(bw::Compression::none, 0), "terminal configuration accepted");
            check(!codec.enableEncryption({}), "terminal encryption accepted");
        }
        for (auto [mode, hex] :
             std::array<std::pair<bw::Compression, const char *>, 7>{{{bw::Compression::zlib, "0063666462060000"},
                                                                      {bw::Compression::zlib, "006366646206"},
                                                                      {bw::Compression::zlib, "006360a03d000000"},
                                                                      {bw::Compression::snappy, "01ffffffff0f"},
                                                                      {bw::Compression::snappy, "01040c030102"},
                                                                      {bw::Compression::snappy, "01040c0301020300"},
                                                                      {bw::Compression::snappy, "01040003"}}}) {
            bw::BatchCodec codec({4, 3, 2});
            check(codec.setCompression(mode, 0).has_value(), "compression configuration");
            check(!codec.decode(unhex(hex)), "compressed bound or trailing data accepted");
        }
        std::array<unsigned char, 32> key{};
        for (std::size_t i = 0; i < key.size(); ++i) {
            key[i] = static_cast<unsigned char>(i);
        }
        auto cipher = bw::PacketCipher::create(key);
        check(cipher.has_value(), "cipher initialization");
        for (const auto &[plaintext, ciphertext] : cipherVectors) {
            check(cipher->encrypt(unhex(plaintext)) == unhex(ciphertext), "independent continuous encryption");
            check(cipher->decrypt(unhex(ciphertext)) == unhex(plaintext), "independent continuous decryption");
        }
        auto corrupt = bw::PacketCipher::create(key);
        auto altered = unhex(cipherVectors[0].second);
        altered.back() ^= 1;
        check(!corrupt->decrypt(altered), "checksum corruption accepted");
        check(!corrupt->encrypt("cannot reuse"), "poisoned cipher reused");
        bool rejected = false;
        std::thread thread([&] { rejected = !plain.encode(packets); });
        thread.join();
        check(rejected, "nonowner access accepted");
        check(plain.encode(packets).has_value(), "nonowner failure consumed owner state");
        std::cout << "native wire vectors and terminal boundaries passed\n";
        return 0;
    }
    catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
