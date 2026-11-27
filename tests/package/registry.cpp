#include <concepts>

#include <bedrock/protocol/packets_fwd.hpp>
#include <bedrock/protocol/version.hpp>

namespace bp = bedrock::protocol;

namespace {

constexpr int oldest = bp::ProtocolVersion::MINIMUM_VERSION.getProtocol();
constexpr int newest = bp::ProtocolVersion::MAXIMUM_VERSION.getProtocol();

}  // namespace

static_assert(std::same_as<bp::packet_of_t<newest, 11>, bp::StartGamePacket>);
static_assert(std::same_as<bp::packet_of_t<oldest, 11>, bp::v622::StartGamePacket>);
static_assert(!bp::has_packet_v<oldest - 1, 11>);
static_assert(!bp::has_packet_v<newest + 1, 11>);
