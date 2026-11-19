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
    std::expected<std::string, bp::EncodeError> encoded = protocol->encode(packet);
    if (!encoded) {
        return 1;
    }
    std::expected<bp::TextPacket, bp::DecodeError> picked = protocol->decode<bp::TextPacket>(*encoded);
    if (!picked || *picked != packet) {
        return 1;
    }

    const bp::GameRule rule{.name = "pvp", .can_be_modified_by_player = true, .value = true};
    std::optional<bp::Protocol> oldest = bp::protocol(729);
    if (!oldest) {
        return 1;
    }
    std::expected<std::string, bp::EncodeError> manual = oldest->encode(rule, bp::manual);
    if (!manual) {
        return 1;
    }
    std::expected<bp::GameRule, bp::DecodeError> read = oldest->decode<bp::GameRule>(*manual, bp::manual);
    return read && *read == rule ? 0 : 1;
}
