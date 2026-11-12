#include <string>

#include <bedrock/protocol.hpp>
#include <bedrock/protocol/player.h>

namespace bp = bedrock::protocol;

int main()
{
    bp::SubChunkRequestPacket_<975> packet;
    std::string buffer;
    bp::BinaryWriter writer{buffer};
    bp::Serializer<bp::SubChunkRequestPacket_<975>>::serialize(writer, packet);
}
