#include <cstdint>
#include <map>
#include <string>
#include <variant>
#include <vector>

#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("ClientboundDataStorePacket: id + round-trip over a recursive DynamicValue")
{
    STATIC_REQUIRE(bp::ClientboundDataStorePacket::Id == 330);

    bp::ClientboundDataStorePacket pkt;

    // One "change" entry whose new value is an object holding an array of two
    // integers -- exercising the recursive DynamicValue (object -> array ->
    // integer), including the array arm gophertunnel/Cloudburst omit.
    bp::DataStoreChange change;
    change.data_store_name = "store";
    change.property = "prop";
    change.update_count = 7;

    bp::DynamicValue::Array arr;
    arr.push_back(bp::DynamicValue{std::int64_t{1}});
    arr.push_back(bp::DynamicValue{std::int64_t{2}});
    bp::DynamicValue::Object obj;
    obj.emplace("v", bp::DynamicValue{std::move(arr)});
    change.new_data = bp::DynamicValue{std::move(obj)};

    pkt.updates.push_back(change);

    // Wire layout. The DynamicValue tag is a 4-byte LE uint32; container counts
    // are varuint32; integers are int64 LE (cereal schema, confirmed in BDS):
    //   updates       varuint32 count = 1
    //   entry         varuint32 ChangeType = 1 (Change)
    //     name        "store"
    //     property    "prop"
    //     updateCount uint32 LE = 7
    //     newData     tag Object(6); varuint32 members = 1
    //       key "v"   tag Array(5); varuint32 len = 2
    //         tag Integer(2); int64 LE 1
    //         tag Integer(2); int64 LE 2
    const std::vector<std::uint8_t> golden{
        0x01,                                            // updates count
        0x01,                                            // ChangeType = Change
        0x05, 0x73, 0x74, 0x6F, 0x72, 0x65,              // "store"
        0x04, 0x70, 0x72, 0x6F, 0x70,                    // "prop"
        0x07, 0x00, 0x00, 0x00,                          // update_count = 7
        0x06, 0x00, 0x00, 0x00,                          // new_data: Object
        0x01,                                            // object members = 1
        0x01, 0x76,                                      // key "v"
        0x05, 0x00, 0x00, 0x00,                          // value: Array
        0x02,                                            // array length = 2
        0x02, 0x00, 0x00, 0x00,                          // Integer
        0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 1
        0x02, 0x00, 0x00, 0x00,                          // Integer
        0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // 2
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::ClientboundDataStorePacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->updates.size() == 1);

    const auto &entry = rt->updates[0];
    REQUIRE(std::holds_alternative<bp::DataStoreChange>(entry));
    const auto &rc = std::get<bp::DataStoreChange>(entry);
    REQUIRE(rc.data_store_name == "store");
    REQUIRE(rc.property == "prop");
    REQUIRE(rc.update_count == 7);

    REQUIRE(rc.new_data.type() == bp::ddui::ValueType::Object);
    const auto &robj = rc.new_data.get<bp::DynamicValue::Object>();
    REQUIRE(robj.size() == 1);
    const auto &rarr = robj.at("v").get<bp::DynamicValue::Array>();
    REQUIRE(rarr.size() == 2);
    REQUIRE(rarr[0].get<std::int64_t>() == 1);
    REQUIRE(rarr[1].get<std::int64_t>() == 2);
}
