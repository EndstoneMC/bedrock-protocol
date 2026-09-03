#include <cstdio>
#include <string>

#include <bedrock/protocol.hpp>
#include <bedrock/protocol/player.h>

namespace bp = bedrock::protocol;

int main()
{
    using Packet = bp::SubChunkRequestPacket_<975>;
    Packet packet;
    packet.dimension_type = static_cast<bp::DimensionType>(0);

    std::string buffer;
    bp::BinaryWriter writer{buffer};
    bp::Serializer<Packet>::serialize(writer, packet);

    bp::BinaryReader reader{buffer};
    const auto back = bp::Serializer<Packet>::deserialize(reader);
    if (!back.has_value()) {
        std::puts("round trip failed");
        return 1;
    }

    const auto platform = bp::enum_name(bp::BuildPlatform::WINDOWS);
    std::printf("bedrock-protocol %s, latest protocol %d, BuildPlatform::WINDOWS is \"%.*s\"\n",
                BEDROCK_PROTOCOL_VERSION_STRING, bp::latest_version,
                static_cast<int>(platform.size()), platform.data());
    return platform == "win32" ? 0 : 1;
}
