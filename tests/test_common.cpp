#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("TintMapColor: round-trip of a fixed-count tuple field")
{
    bp::TintMapColor tint;
    tint.colors = {bp::Color{1}, bp::Color{2}, bp::Color{3}, bp::Color{4}};

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, tint);
    REQUIRE(buf == std::vector<std::uint8_t>{
        0x01, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00,  // no length prefix:
        0x03, 0x00, 0x00, 0x00, 0x04, 0x00, 0x00, 0x00,  // exactly 4 elements
    });

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::TintMapColor>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->colors.size() == 4);
    REQUIRE(rt->colors[3] == bp::Color{4});
}
