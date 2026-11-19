#include <concepts>
#include <expected>
#include <optional>
#include <string>
#include <string_view>

#include <bedrock/protocol.hpp>

namespace bp = bedrock::protocol;

using std::string_view_literals::operator""sv;

static_assert(!std::invocable<decltype(bp::v2225::encode), const bp::Vec3 &>);
static_assert(bp::ProtocolVersion::get(2193)->getName() == "1.26.50");
static_assert(bp::ProtocolVersion::get(2169)->getName() == "1.26.45");
static_assert(!bp::ProtocolVersion::get(2170));
static_assert(bp::ProtocolVersion::MINIMUM_VERSION.getProtocol() == bp::v729::version);
static_assert(bp::ProtocolVersion::MAXIMUM_VERSION.getProtocol() == bp::v2225::version);

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

    std::expected<std::string, bp::EncodeError> picked = bp::v2193::encode(packet);
    if (!picked) {
        return 1;
    }
    std::expected<bp::TextPacket, bp::DecodeError> back = bp::v2193::decode<bp::TextPacket>(*picked);
    if (!back || *back != packet) {
        return 1;
    }

    // tests/goldens/v2168/009_text.json, message_only_arm
    const std::string_view golden = "\x00\x00\x0b\x1b{\"rawtext\":[{\"text\":\"hi\"}]}\x10"
                                    "2535400000000001\x02pc\x00"sv;
    std::expected<bp::TextPacket, bp::DecodeError> unchanged = bp::decode<2169, bp::TextPacket>(golden);
    if (!unchanged) {
        return 1;
    }
    std::expected<std::string, bp::EncodeError> again = bp::encode<2169>(*unchanged);
    return again && *again == golden ? 0 : 1;
}
