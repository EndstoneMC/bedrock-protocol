#include <expected>
#include <optional>
#include <string>

#include <bedrock/protocol.hpp>

namespace bp = bedrock::protocol;

int main()
{
    bp::TextPacket packet;
    packet.body = bp::TextPacket::MessageOnly{.type = bp::TextPacketType::Chat, .message = "hello"};

    std::expected<std::string, bp::EncodeError> data = bp::v2225::encode(packet);
    if (!data) {
        return 1;
    }
    std::expected<bp::TextPacket, bp::DecodeError> decoded = bp::v2225::decode<bp::TextPacket>(*data);
    if (!decoded || *decoded != packet) {
        return 1;
    }

    std::optional<bp::Protocol> protocol = bp::protocol("1.26.63");
    if (!protocol || protocol != bp::protocol(2225)) {
        return 1;
    }
    std::expected<bp::TextPacket, bp::DecodeError> picked = protocol->decode<bp::TextPacket>(*protocol->encode(packet));
    return picked && *picked == packet ? 0 : 1;
}
