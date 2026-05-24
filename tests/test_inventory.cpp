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
    item.stack_size = 1;
    item.aux_value = 0;
    item.block_runtime_id = 0;
    item.user_data_buffer = kEmptyUserData;
    REQUIRE(encode(item) == golden);

    bp::BinaryReader in{golden};
    auto rt = bp::deserialize<bp::NetworkItemInstanceDescriptor>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->id == 5);
    REQUIRE(rt->stack_size == 1);
    REQUIRE(rt->aux_value == 0);
    REQUIRE(rt->block_runtime_id == 0);
    REQUIRE(rt->user_data_buffer == kEmptyUserData);
    REQUIRE(in.getUnreadLength() == 0);
}

TEST_CASE("NetworkItemInstanceDescriptor: air omits the guarded body")
{
    // gophertunnel: Writer.Item(&ItemStack{}) -- an air item is a lone 0 id.
    const std::vector<std::uint8_t> golden{0x00};

    bp::NetworkItemInstanceDescriptor item;
    item.id = 0;
    item.user_data_buffer = "ignored";  // a guarded field, not serialized when id == 0
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
    item.stack_size = 64;
    item.aux_value = 0;
    item.net_id_variant = std::nullopt;
    item.block_runtime_id = 10;
    item.user_data_buffer = kEmptyUserData;
    REQUIRE(encode(item) == golden);

    bp::BinaryReader in{golden};
    auto rt = bp::deserialize<bp::NetworkItemStackDescriptor>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->id == 7);
    REQUIRE(rt->stack_size == 64);
    REQUIRE_FALSE(rt->net_id_variant.has_value());
    REQUIRE(rt->block_runtime_id == 10);
    REQUIRE(rt->user_data_buffer == kEmptyUserData);
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
    item.stack_size = 1;
    item.aux_value = 0;
    item.net_id_variant = 100;
    item.block_runtime_id = 0;
    item.user_data_buffer = kEmptyUserData;
    REQUIRE(encode(item) == golden);

    bp::BinaryReader in{golden};
    auto rt = bp::deserialize<bp::NetworkItemStackDescriptor>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->net_id_variant.has_value());
    REQUIRE(*rt->net_id_variant == 100);
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
    item.stack_size = 1;
    item.aux_value = 0;
    item.net_id_variant = std::nullopt;
    item.block_runtime_id = 0;
    item.user_data_buffer = "";
    REQUIRE(encode(item) == golden);

    bp::BinaryReader in{golden};
    auto rt = bp::deserialize<bp::SerializedNetworkItemStackDescriptor>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->id == 0);
    REQUIRE(rt->stack_size == 1);
    REQUIRE_FALSE(rt->net_id_variant.has_value());
    REQUIRE(rt->user_data_buffer.empty());
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
    item.stack_size = 1;
    item.aux_value = 0;
    item.net_id_variant = std::nullopt;
    item.block_runtime_id = 0;
    item.user_data_buffer = kEmptyUserData;
    REQUIRE(encode(item) == golden);

    bp::BinaryReader in{golden};
    auto rt = bp::deserialize<bp::SerializedNetworkItemStackDescriptor>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->id == 10);
    REQUIRE_FALSE(rt->net_id_variant.has_value());
    REQUIRE(rt->user_data_buffer == kEmptyUserData);
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
    item.stack_size = 2;
    item.aux_value = 5;
    item.net_id_variant = bp::ItemStackNetIdVariant{bp::ItemStackNetId{42}};
    item.block_runtime_id = 7;
    item.user_data_buffer = kEmptyUserData;
    REQUIRE(encode(item) == golden);

    bp::BinaryReader in{golden};
    auto rt = bp::deserialize<bp::SerializedNetworkItemStackDescriptor>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->id == 300);
    REQUIRE(rt->net_id_variant.has_value());
    REQUIRE(rt->net_id_variant->index() == 0);
    REQUIRE(std::get<bp::ItemStackNetId>(*rt->net_id_variant).id == 42);
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
        REQUIRE(rt->index() == nv.index());
        REQUIRE(in.getUnreadLength() == 0);
    }
}

TEST_CASE("bytes carries raw binary, including embedded NULs")
{
    bp::NetworkItemInstanceDescriptor item;
    item.id = 1;
    item.stack_size = 1;
    item.aux_value = 0;
    item.block_runtime_id = 0;
    item.user_data_buffer = std::string{"\x00\xFF\x00\x10", 4};

    auto buf = encode(item);
    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::NetworkItemInstanceDescriptor>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->user_data_buffer.size() == 4);
    REQUIRE(rt->user_data_buffer == std::string{"\x00\xFF\x00\x10", 4});
    REQUIRE(in.getUnreadLength() == 0);
}

TEST_CASE("MobEquipmentPacket v975: NewItem is the cereal-form descriptor")
{
    STATIC_REQUIRE(bp::MobEquipmentPacket::Id == 31);

    bp::MobEquipmentPacket pkt;
    pkt.runtime_id = static_cast<bp::ActorRuntimeID>(1234);
    pkt.item.id = 5;
    pkt.item.stack_size = 2;
    pkt.item.aux_value = 0;
    pkt.item.net_id_variant = std::nullopt;
    pkt.item.block_runtime_id = 0;
    pkt.item.user_data_buffer = kEmptyUserData;
    pkt.slot = 4;
    pkt.selected_slot = 4;
    pkt.container_id = 0;

    // generated by gophertunnel:
    // packet.MobEquipment{EntityRuntimeID: 1234, NewItem: protocol.ItemInstance{Stack: protocol.ItemStack{ItemType: protocol.ItemType{NetworkID: 5}, Count: 2}}, InventorySlot: 4, HotBarSlot: 4, WindowID: 0}
    const std::vector<std::uint8_t> golden{
        0xD2, 0x09, 0x05, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x0A, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x04, 0x00,
    };
    REQUIRE(encode(pkt) == golden);

    bp::BinaryReader in{golden};
    auto rt = bp::deserialize<bp::MobEquipmentPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->runtime_id == static_cast<bp::ActorRuntimeID>(1234));
    REQUIRE(rt->item.id == 5);
    REQUIRE(rt->item.stack_size == 2);
    REQUIRE_FALSE(rt->item.net_id_variant.has_value());
    REQUIRE(rt->slot == 4);
    REQUIRE(rt->container_id == 0);
    REQUIRE(in.getUnreadLength() == 0);
}

TEST_CASE("MobEquipmentPacket v944: NewItem is the legacy bool-net-id descriptor")
{
    bp::MobEquipmentPacket_<944> pkt;
    pkt.runtime_id = static_cast<bp::ActorRuntimeID>(1234);
    pkt.item.id = 5;
    pkt.item.stack_size = 2;
    pkt.item.aux_value = 0;
    pkt.item.net_id_variant = std::nullopt;
    pkt.item.block_runtime_id = 0;
    pkt.item.user_data_buffer = kEmptyUserData;
    pkt.slot = 4;
    pkt.selected_slot = 4;
    pkt.container_id = 0;

    // generated by gophertunnel @eed76a6:
    // packet.MobEquipment{EntityRuntimeID: 1234, NewItem: protocol.ItemInstance{Stack: protocol.ItemStack{ItemType: protocol.ItemType{NetworkID: 5}, Count: 2}}, InventorySlot: 4, HotBarSlot: 4, WindowID: 0}
    const std::vector<std::uint8_t> golden{
        0xD2, 0x09, 0x0A, 0x02, 0x00, 0x00, 0x00, 0x00, 0x0A, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x04, 0x00,
    };
    REQUIRE(encode(pkt) == golden);

    bp::BinaryReader in{golden};
    auto rt = bp::deserialize<bp::MobEquipmentPacket_<944>>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->runtime_id == static_cast<bp::ActorRuntimeID>(1234));
    REQUIRE(rt->item.id == 5);
    REQUIRE(rt->item.stack_size == 2);
    REQUIRE_FALSE(rt->item.net_id_variant.has_value());
    REQUIRE(in.getUnreadLength() == 0);
}

TEST_CASE("InventorySlotPacket v975: optional Container and StorageItem, cereal NewItem")
{
    STATIC_REQUIRE(bp::InventorySlotPacket::Id == 50);

    bp::InventorySlotPacket pkt;
    pkt.inventory_id = 1;
    pkt.slot = 3;
    pkt.full_container_name = bp::FullContainerName{};
    pkt.full_container_name->name = bp::ContainerEnumName::InventoryContainer;
    pkt.full_container_name->dynamic_id = 42;
    pkt.storage_item = bp::SerializedNetworkItemStackDescriptor{};
    pkt.storage_item->id = 7;
    pkt.storage_item->stack_size = 1;
    pkt.storage_item->aux_value = 0;
    pkt.storage_item->net_id_variant = std::nullopt;
    pkt.storage_item->block_runtime_id = 0;
    pkt.storage_item->user_data_buffer = kEmptyUserData;
    pkt.item.id = 10;
    pkt.item.stack_size = 1;
    pkt.item.aux_value = 0;
    pkt.item.net_id_variant = std::nullopt;
    pkt.item.block_runtime_id = 0;
    pkt.item.user_data_buffer = kEmptyUserData;

    // generated by gophertunnel:
    // packet.InventorySlot{WindowID: 1, Slot: 3, Container: protocol.Option(protocol.FullContainerName{ContainerID: 29, DynamicContainerID: protocol.Option[uint32](42)}), StorageItem: protocol.Option(protocol.ItemInstance{Stack: protocol.ItemStack{ItemType: protocol.ItemType{NetworkID: 7}, Count: 1}}), NewItem: protocol.ItemInstance{Stack: protocol.ItemStack{ItemType: protocol.ItemType{NetworkID: 10}, Count: 1}}}
    const std::vector<std::uint8_t> golden{
        0x01, 0x03, 0x01, 0x1D, 0x01, 0x2A, 0x00, 0x00, 0x00, 0x01, 0x07, 0x00,
        0x01, 0x00, 0x00, 0x00, 0x00, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x0A, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x0A,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    };
    REQUIRE(encode(pkt) == golden);

    bp::BinaryReader in{golden};
    auto rt = bp::deserialize<bp::InventorySlotPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->full_container_name.has_value());
    REQUIRE(rt->full_container_name->name == bp::ContainerEnumName::InventoryContainer);
    REQUIRE(rt->full_container_name->dynamic_id.has_value());
    REQUIRE(*rt->full_container_name->dynamic_id == 42);
    REQUIRE(rt->storage_item.has_value());
    REQUIRE(rt->storage_item->id == 7);
    REQUIRE(rt->item.id == 10);
    REQUIRE(in.getUnreadLength() == 0);
}

TEST_CASE("InventorySlotPacket v944: Container is non-optional, items are legacy descriptors")
{
    bp::InventorySlotPacket_<944> pkt;
    pkt.inventory_id = 0;
    pkt.slot = 5;
    pkt.full_container_name.name = bp::ContainerEnumName::InventoryContainer;
    pkt.full_container_name.dynamic_id = std::nullopt;
    // air storage_item + air item -- the legacy descriptor's id == 0 shortcut omits the body.
    pkt.storage_item.id = 0;
    pkt.item.id = 0;

    // generated by gophertunnel @eed76a6:
    // packet.InventorySlot{WindowID: 0, Slot: 5, Container: protocol.FullContainerName{ContainerID: 29}, StorageItem: protocol.ItemInstance{}, NewItem: protocol.ItemInstance{}}
    const std::vector<std::uint8_t> golden{
        0x00, 0x05, 0x1D, 0x00, 0x00, 0x00,
    };
    REQUIRE(encode(pkt) == golden);

    bp::BinaryReader in{golden};
    auto rt = bp::deserialize<bp::InventorySlotPacket_<944>>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->full_container_name.name == bp::ContainerEnumName::InventoryContainer);
    REQUIRE_FALSE(rt->full_container_name.dynamic_id.has_value());
    REQUIRE(rt->storage_item.id == 0);
    REQUIRE(rt->item.id == 0);
    REQUIRE(in.getUnreadLength() == 0);
}

TEST_CASE("PlayerEnchantOptionsPacket: id + round-trip with one ItemEnchantOption")
{
    STATIC_REQUIRE(bp::PlayerEnchantOptionsPacket::Id == 146);

    bp::PlayerEnchantOptionsPacket pkt;
    bp::ItemEnchantOption opt;
    opt.cost = 7;
    opt.enchants.slot = 0;
    std::get<1>(opt.enchants.item_enchants).push_back(bp::EnchantmentInstance{5, 2});
    opt.enchant_name = "calm imbue range";
    opt.enchant_net_id = 42;
    pkt.options.push_back(opt);

    // generated by gophertunnel:
    // packet.PlayerEnchantOptions{Options: []protocol.EnchantmentOption{{
    //   Cost: 7,
    //   Enchantments: protocol.ItemEnchantments{Slot: 0,
    //     Enchantments: [3][]protocol.EnchantmentInstance{{}, {{Type: 5, Level: 2}}, {}}},
    //   Name: "calm imbue range", RecipeNetworkID: 42}}}
    const std::vector<std::uint8_t> golden{
        0x01, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x05, 0x02, 0x00, 0x10,
        0x63, 0x61, 0x6C, 0x6D, 0x20, 0x69, 0x6D, 0x62, 0x75, 0x65, 0x20, 0x72,
        0x61, 0x6E, 0x67, 0x65, 0x2A,
    };

    REQUIRE(encode(pkt) == golden);

    bp::BinaryReader in{golden};
    auto rt = bp::deserialize<bp::PlayerEnchantOptionsPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->options.size() == 1);
    REQUIRE(rt->options[0].cost == 7);
    REQUIRE(rt->options[0].enchant_name == "calm imbue range");
    REQUIRE(std::get<1>(rt->options[0].enchants.item_enchants).size() == 1);
    REQUIRE(std::get<1>(rt->options[0].enchants.item_enchants)[0].enchant_type == 5);
    REQUIRE(std::get<1>(rt->options[0].enchants.item_enchants)[0].level == 2);
}
