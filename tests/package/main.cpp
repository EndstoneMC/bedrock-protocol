#include <string>

#include <bedrock/protocol.hpp>

namespace bp = bedrock::protocol;

int main()
{
    bp::SubChunkRequestPacket_<975> packet;
    std::string buffer;
    bp::BinaryWriter writer{buffer};
    bp::serialize(writer, packet);
}
