#include <concepts>
#include <expected>
#include <optional>
#include <string>
#include <string_view>
#include <utility>

#include <bedrock/protocol.hpp>

namespace bp = bedrock::protocol;

using std::string_view_literals::operator""sv;

namespace {

template <typename T>
auto encode(const T &packet) -> std::string_view;

}  // namespace

template <typename T, int... V>
concept encodable_at = requires(const T &packet) { bp::encode_<V...>(packet); };

static_assert(encodable_at<bp::TextPacket, bp::v2259::version>);
static_assert(!encodable_at<bp::TextPacket>);
static_assert(encodable_at<bp::v898::TextPacket, 2200>);
static_assert(!encodable_at<bp::v671::TextPacket, 670>);
static_assert(!encodable_at<bp::TextPacket, 2260>);
static_assert(bp::version == bp::ProtocolVersion::MAXIMUM_VERSION.getProtocol());
static_assert(
    std::same_as<decltype(bp::encode), decltype(bp::encode_<bp::ProtocolVersion::MAXIMUM_VERSION.getProtocol()>)>);
static_assert(std::same_as<decltype(encode(std::declval<const bp::TextPacket &>())), std::string_view>);
static_assert(!std::invocable<decltype(bp::v2259::encode), const bp::Vec3 &>);
static_assert(bp::ProtocolVersion::get(2259)->getName() == "1.26.70");
static_assert(bp::ProtocolVersion::get(2169)->getName() == "1.26.45");
static_assert(bp::ProtocolVersion::get(2169)->getProtocol() == 2169);
static_assert(bp::ProtocolVersion::get(2170)->getProtocol() == 2170);
static_assert(bp::ProtocolVersion::get(2170)->getName() == "1.26.45");
static_assert(bp::ProtocolVersion::get(2200)->getName() == "1.26.50");
static_assert(!bp::ProtocolVersion::get(670));
static_assert(!bp::ProtocolVersion::get(2260));
static_assert(bp::ProtocolVersion::MINIMUM_VERSION.getProtocol() == bp::v671::version);
static_assert(bp::ProtocolVersion::MAXIMUM_VERSION.getProtocol() == bp::v2259::version);

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

    std::expected<std::string, bp::EncodeError> pinned = bp::encode_<bp::v2259::version>(packet);
    if (!pinned || *pinned != *data) {
        return 1;
    }
    std::expected<bp::TextPacket, bp::DecodeError> read = bp::decode_<bp::v2259::version, bp::TextPacket>(*pinned);
    if (!read || *read != packet) {
        return 1;
    }

    {
        using bp::v2259::encode;
        std::expected<std::string, bp::EncodeError> found = encode(packet);
        if (!found || *found != *data) {
            return 1;
        }
    }

    std::expected<std::string, bp::EncodeError> picked = bp::v2259::encode(packet);
    if (!picked) {
        return 1;
    }
    std::expected<bp::TextPacket, bp::DecodeError> back = bp::v2259::decode<bp::TextPacket>(*picked);
    if (!back || *back != packet) {
        return 1;
    }

    // tests/goldens/v2168/009_text.json, message_only_arm
    const std::string_view golden = "\x00\x00\x0b\x1b{\"rawtext\":[{\"text\":\"hi\"}]}\x10"
                                    "2535400000000001\x02pc\x00"sv;
    std::expected<bp::v898::TextPacket, bp::DecodeError> unchanged = bp::decode_<2169, bp::v898::TextPacket>(golden);
    if (!unchanged) {
        return 1;
    }
    std::expected<std::string, bp::EncodeError> again = bp::encode_<2169>(*unchanged);
    return again && *again == golden ? 0 : 1;
}
