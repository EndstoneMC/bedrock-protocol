#include <cstdint>
#include <string>
#include <vector>

#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

namespace {

template <typename T>
std::vector<std::uint8_t> encode(const T &value)
{
    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, value);
    return buf;
}

// The user-data buffer gophertunnel emits for an item with no NBT, no
// can-place/can-break entries and no shield blocking tick: an int16 NBT-length
// of 0, then a uint32 can-place count of 0 and a uint32 can-break count of 0.
const std::string kEmptyUserData(10, '\0');

}  // namespace

TEST_CASE("NetworkItemInstanceDescriptor: non-air round-trip")
{
    // gophertunnel: Writer.Item(&ItemStack{ItemType: {NetworkID: 5}, Count: 1})
    const std::vector<std::uint8_t> golden{
        0x0a, 0x01, 0x00, 0x00, 0x00, 0x0a, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    };

    bp::NetworkItemInstanceDescriptor item;
    item.id = 5;
    item.count = 1;
    item.aux_value = 0;
    item.block_runtime_id = 0;
    item.user_data = kEmptyUserData;
    REQUIRE(encode(item) == golden);

    bp::BinaryReader in{golden};
    auto rt = bp::deserialize<bp::NetworkItemInstanceDescriptor>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->id == 5);
    REQUIRE(rt->count == 1);
    REQUIRE(rt->aux_value == 0);
    REQUIRE(rt->block_runtime_id == 0);
    REQUIRE(rt->user_data == kEmptyUserData);
    REQUIRE(in.getUnreadLength() == 0);
}

TEST_CASE("NetworkItemInstanceDescriptor: air omits the guarded body")
{
    // gophertunnel: Writer.Item(&ItemStack{}) -- an air item is a lone 0 id.
    const std::vector<std::uint8_t> golden{0x00};

    bp::NetworkItemInstanceDescriptor item;
    item.id = 0;
    item.user_data = "ignored";  // a guarded field, not serialized when id == 0
    REQUIRE(encode(item) == golden);

    bp::BinaryReader in{golden};
    auto rt = bp::deserialize<bp::NetworkItemInstanceDescriptor>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->id == 0);
    REQUIRE(in.getUnreadLength() == 0);
}

TEST_CASE("NetworkItemStackDescriptor: net id absent")
{
    // gophertunnel: Writer.ItemInstance(&ItemInstance{StackNetworkID: 0,
    //   Stack: ItemStack{ItemType: {NetworkID: 7}, Count: 64, BlockRuntimeID: 10}})
    const std::vector<std::uint8_t> golden{
        0x0e, 0x40, 0x00, 0x00, 0x00, 0x14, 0x0a, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    };

    bp::NetworkItemStackDescriptor item;
    item.id = 7;
    item.count = 64;
    item.aux_value = 0;
    item.net_id = std::nullopt;
    item.block_runtime_id = 10;
    item.user_data = kEmptyUserData;
    REQUIRE(encode(item) == golden);

    bp::BinaryReader in{golden};
    auto rt = bp::deserialize<bp::NetworkItemStackDescriptor>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->id == 7);
    REQUIRE(rt->count == 64);
    REQUIRE_FALSE(rt->net_id.has_value());
    REQUIRE(rt->block_runtime_id == 10);
    REQUIRE(rt->user_data == kEmptyUserData);
    REQUIRE(in.getUnreadLength() == 0);
}

TEST_CASE("NetworkItemStackDescriptor: net id present")
{
    // gophertunnel: Writer.ItemInstance(&ItemInstance{StackNetworkID: 100,
    //   Stack: ItemStack{ItemType: {NetworkID: 7}, Count: 1}})
    const std::vector<std::uint8_t> golden{
        0x0e, 0x01, 0x00, 0x00, 0x01, 0xc8, 0x01, 0x00, 0x0a, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    };

    bp::NetworkItemStackDescriptor item;
    item.id = 7;
    item.count = 1;
    item.aux_value = 0;
    item.net_id = 100;
    item.block_runtime_id = 0;
    item.user_data = kEmptyUserData;
    REQUIRE(encode(item) == golden);

    bp::BinaryReader in{golden};
    auto rt = bp::deserialize<bp::NetworkItemStackDescriptor>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->net_id.has_value());
    REQUIRE(*rt->net_id == 100);
    REQUIRE(in.getUnreadLength() == 0);
}

TEST_CASE("NetworkItemStackDescriptor: air omits the guarded body")
{
    // gophertunnel: Writer.ItemInstance(&ItemInstance{})
    const std::vector<std::uint8_t> golden{0x00};

    bp::NetworkItemStackDescriptor item;
    item.id = 0;
    REQUIRE(encode(item) == golden);
}

TEST_CASE("SerializedNetworkItemStackDescriptor: id 0 writes a full header")
{
    // gophertunnel: Writer.ItemInstanceNew(&ItemInstance{StackNetworkID: 0,
    //   Stack: ItemStack{ItemType: {NetworkID: 0}, Count: 1}})
    // The cereal form has no air shortcut -- every field is always present.
    const std::vector<std::uint8_t> golden{
        0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00,
    };

    bp::SerializedNetworkItemStackDescriptor item;
    item.id = 0;
    item.count = 1;
    item.aux_value = 0;
    item.net_id = std::nullopt;
    item.block_runtime_id = 0;
    item.user_data = "";
    REQUIRE(encode(item) == golden);

    bp::BinaryReader in{golden};
    auto rt = bp::deserialize<bp::SerializedNetworkItemStackDescriptor>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->id == 0);
    REQUIRE(rt->count == 1);
    REQUIRE_FALSE(rt->net_id.has_value());
    REQUIRE(rt->user_data.empty());
    REQUIRE(in.getUnreadLength() == 0);
}

TEST_CASE("SerializedNetworkItemStackDescriptor: net id absent")
{
    // gophertunnel: Writer.ItemInstanceNew(&ItemInstance{StackNetworkID: 0,
    //   Stack: ItemStack{ItemType: {NetworkID: 10}, Count: 1}})
    const std::vector<std::uint8_t> golden{
        0x0a, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x0a, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    };

    bp::SerializedNetworkItemStackDescriptor item;
    item.id = 10;
    item.count = 1;
    item.aux_value = 0;
    item.net_id = std::nullopt;
    item.block_runtime_id = 0;
    item.user_data = kEmptyUserData;
    REQUIRE(encode(item) == golden);

    bp::BinaryReader in{golden};
    auto rt = bp::deserialize<bp::SerializedNetworkItemStackDescriptor>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->id == 10);
    REQUIRE_FALSE(rt->net_id.has_value());
    REQUIRE(rt->user_data == kEmptyUserData);
    REQUIRE(in.getUnreadLength() == 0);
}

TEST_CASE("SerializedNetworkItemStackDescriptor: tagged net-id variant")
{
    // gophertunnel: Writer.ItemInstanceNew(&ItemInstance{StackNetworkID: 42,
    //   Stack: ItemStack{ItemType: {NetworkID: 300, MetadataValue: 5},
    //   Count: 2, BlockRuntimeID: 7}})
    // gophertunnel always writes net-id variant tag 0 (the server net id).
    const std::vector<std::uint8_t> golden{
        0x2c, 0x01, 0x02, 0x00, 0x05, 0x01, 0x00, 0x54, 0x07, 0x0a,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    };

    bp::SerializedNetworkItemStackDescriptor item;
    item.id = 300;
    item.count = 2;
    item.aux_value = 5;
    item.net_id = bp::ItemStackNetIdVariant{bp::ItemStackServerNetId{42}};
    item.block_runtime_id = 7;
    item.user_data = kEmptyUserData;
    REQUIRE(encode(item) == golden);

    bp::BinaryReader in{golden};
    auto rt = bp::deserialize<bp::SerializedNetworkItemStackDescriptor>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->id == 300);
    REQUIRE(rt->net_id.has_value());
    REQUIRE(rt->net_id->value.index() == 0);
    REQUIRE(std::get<bp::ItemStackServerNetId>(rt->net_id->value).id == 42);
    REQUIRE(in.getUnreadLength() == 0);
}

TEST_CASE("ItemStackNetIdVariant: request and legacy cases round-trip")
{
    // gophertunnel only ever emits variant tag 0, so the request (1) and
    // legacy-request (2) cases are exercised by a plain round-trip.
    bp::ItemStackNetIdVariant request{bp::ItemStackRequestId{7}};
    bp::ItemStackNetIdVariant legacy{bp::ItemStackLegacyRequestId{9}};

    for (const auto &nv : {request, legacy}) {
        auto buf = encode(nv);
        bp::BinaryReader in{buf};
        auto rt = bp::deserialize<bp::ItemStackNetIdVariant>(in);
        REQUIRE(rt.has_value());
        REQUIRE(rt->value.index() == nv.value.index());
        REQUIRE(in.getUnreadLength() == 0);
    }
}

TEST_CASE("bytes carries raw binary, including embedded NULs")
{
    bp::NetworkItemInstanceDescriptor item;
    item.id = 1;
    item.count = 1;
    item.aux_value = 0;
    item.block_runtime_id = 0;
    item.user_data = std::string{"\x00\xFF\x00\x10", 4};

    auto buf = encode(item);
    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::NetworkItemInstanceDescriptor>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->user_data.size() == 4);
    REQUIRE(rt->user_data == std::string{"\x00\xFF\x00\x10", 4});
    REQUIRE(in.getUnreadLength() == 0);
}
