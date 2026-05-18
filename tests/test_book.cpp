#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("BookEditPacket: id + round-trip of a tagged-union field")
{
    STATIC_REQUIRE(bp::BookEditPacket::Id == 97);

    bp::BookEditPacket pkt;
    pkt.book_slot = 3;
    pkt.operation = bp::BookEditActionAddPage{7, "hello", ""};

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == std::vector<std::uint8_t>{
        0x06,                                // book_slot: varint 3
        0x01,                                // discriminator: arm 1 (AddPage)
        0x0E,                                // page_index: varint 7
        0x05, 0x68, 0x65, 0x6C, 0x6C, 0x6F,  // page_text: "hello"
        0x00,                                // photo_name: ""
    });

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::BookEditPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->operation.index() == 1);
    REQUIRE(std::get<bp::BookEditActionAddPage>(rt->operation).page_text == "hello");
}
