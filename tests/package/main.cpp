#include <concepts>
#include <expected>
#include <optional>
#include <string>

#include <bedrock/protocol.hpp>

namespace bp = bedrock::protocol;

static_assert(!std::invocable<decltype(bp::v2225::encode), const bp::Vec3 &>);

int main()
{
    bp::TextPacket packet;
    packet.body = bp::TextPacket::MessageOnly{.type = bp::TextPacketType::Chat, .message = "hello"};

    std::expected<std::string, bp::EncodeError> data = bp::encode(packet);
    if (!data) {
        return 1;
    }
    std::expected<bp::TextPacket, bp::DecodeError> decoded = bp::decode<bp::TextPacket>(*data);
    if (!decoded || *decoded != packet) {
        return 1;
    }

    std::expected<std::string, bp::EncodeError> pinned = bp::encode<bp::v2225::version>(packet);
    if (!pinned || *pinned != *data) {
        return 1;
    }
    std::expected<bp::TextPacket, bp::DecodeError> read = bp::decode<bp::v2225::version, bp::TextPacket>(*pinned);
    if (!read || *read != packet) {
        return 1;
    }

    {
        using bp::v2225::encode;
        std::expected<std::string, bp::EncodeError> found = encode(packet);
        if (!found || *found != *data) {
            return 1;
        }
    }

    std::optional<bp::Protocol> protocol = bp::protocol("1.26.63");
    if (!protocol || protocol != bp::protocol(2225)) {
        return 1;
    }
    std::expected<std::string, bp::EncodeError> encoded = protocol->encode(packet);
    if (!encoded) {
        return 1;
    }
    std::expected<bp::TextPacket, bp::DecodeError> picked = protocol->decode<bp::TextPacket>(*encoded);
    return picked && *picked == packet ? 0 : 1;
}
