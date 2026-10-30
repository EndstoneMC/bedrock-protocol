#include <array>
#include <cstdio>
#include <string_view>

#include <bedrock/protocol/wire/batch.h>
#include <bedrock/protocol/wire/crypto.h>

namespace wire = bedrock::protocol::wire;

int main()
{
    wire::BatchCodec sender;
    wire::BatchCodec receiver;
    const std::array<unsigned char, 32> key{1, 2, 3, 4};
    if (!sender.setCompression(wire::Compression::zlib, 0) ||
        !receiver.setCompression(wire::Compression::zlib, 0) ||
        !sender.enableEncryption(key) || !receiver.enableEncryption(key)) {
        std::puts("wire configuration failed");
        return 1;
    }

    const std::array packets{std::string_view{"installed-wire"}, std::string_view{"\0\xff", 2}};
    const auto encoded = sender.encode(packets);
    if (!encoded) {
        std::puts("wire encoding failed");
        return 1;
    }
    const auto decoded = receiver.decode(*encoded);
    if (!decoded || decoded->size() != packets.size() ||
        (*decoded)[0] != packets[0] || (*decoded)[1] != packets[1]) {
        std::puts("wire round trip failed");
        return 1;
    }
    std::puts("installed wire compression and encryption passed");
    return 0;
}
