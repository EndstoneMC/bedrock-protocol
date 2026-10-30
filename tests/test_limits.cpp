#include <bedrock/protocol/data_store.hpp>
#include <bedrock/protocol/item_stack.h>
#include <bedrock/protocol/network.h>

#include "fixture.hpp"

TEST_CASE("reader rejects overflowing terminal varint bytes")
{
    const auto over32 = bytes({0xff, 0xff, 0xff, 0xff, 0x10});
    bp::BinaryReader reader(over32);
    REQUIRE_FALSE(reader.readVarInt<std::uint32_t>());
    REQUIRE_FALSE(reader.resourceFailure());
    const auto over64 = bytes({0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x02});
    bp::BinaryReader wide(over64);
    REQUIRE_FALSE(wide.readVarInt<std::uint64_t>());
    REQUIRE_FALSE(wide.resourceFailure());
}

TEST_CASE("string length is checked before allocating storage")
{
    const auto data = bytes({0xff, 0xff, 0xff, 0xff, 0x0f});
    bp::BinaryReader reader(data);
    const auto value = reader.read<std::string>();
    REQUIRE_FALSE(value);
    REQUIRE(value.error() == std::make_error_code(std::errc::message_size));
}

TEST_CASE("decoded storage accounting can be shared by independent readers")
{
    const auto data = bytes({0x02, 'a', 'b'});
    bp::DecodeBudget budget({2, 3, 128});
    bp::BinaryReader first(data, &budget);
    REQUIRE(first.read<std::string>() == "ab");
    bp::BinaryReader second(data, &budget);
    REQUIRE_FALSE(second.read<std::string>());
    REQUIRE(budget.resourceFailure());
}

TEST_CASE("typed empty NBT lists retain their declared element kind")
{
    bp::ListTag list(bp::nbt::Type::Int);
    std::string bytes;
    bp::BinaryWriter writer(bytes);
    bp::nbt::writeTag(writer, bp::Tag{list});
    bp::BinaryReader reader(bytes);
    auto result = bp::nbt::readTag(reader, bp::nbt::Type::List);
    REQUIRE(result);
    REQUIRE(result->get<bp::ListTag>().empty());
    REQUIRE(result->get<bp::ListTag>().type() == bp::nbt::Type::Int);
}

TEST_CASE("named NBT reader retains its single argument function signature")
{
    auto *read_named_tag = &bp::nbt::readNamedTag;
    const auto data = bytes({0x03, 0x00, 0x02});
    bp::BinaryReader reader(data);
    const auto result = read_named_tag(reader);
    REQUIRE(result);
    REQUIRE(result->first.empty());
    REQUIRE(result->second.get<bp::IntTag>().value() == 1);
}

TEST_CASE("NBT count, allocation and nesting budgets reject excessive input")
{
    bp::ListTag list;
    list.push_back(bp::IntTag{1});
    std::string bytes;
    bp::BinaryWriter writer(bytes);
    bp::nbt::writeTag(writer, bp::Tag{list});
    bp::DecodeBudget elements({0, 1024, 128});
    bp::BinaryReader limited(bytes, &elements);
    REQUIRE_FALSE(bp::nbt::readTag(limited, bp::nbt::Type::List));
    REQUIRE(elements.resourceFailure());
    bp::DecodeBudget depth({100, 1024, 1});
    bp::BinaryReader shallow(bytes, &depth);
    REQUIRE_FALSE(bp::nbt::readTag(shallow, bp::nbt::Type::List));
    REQUIRE(depth.resourceFailure());
    const auto negative = ::bytes({0x01});
    bp::BinaryReader array(negative);
    REQUIRE_FALSE(bp::nbt::readTag(array, bp::nbt::Type::ByteArray));
}

TEST_CASE("count arithmetic rejects overflow before multiplication")
{
    auto maximum = bp::detail::countValue(std::numeric_limits<std::size_t>::max());
    REQUIRE_FALSE(bp::detail::countOperation(maximum, bp::detail::countValue(2), '*'));
    REQUIRE_FALSE(bp::detail::countOperation(maximum, bp::detail::countValue(1), '+'));
    REQUIRE_FALSE(bp::detail::countOperation(bp::detail::countValue(0), bp::detail::countValue(1), '-'));
    REQUIRE(bp::detail::countOperation(bp::detail::countValue(2), bp::detail::countValue(3), '*') == 6);
}

TEST_CASE("integral primitive readers reject narrowing beyond declared int16")
{
    using Slot = bp::v1001::ItemStackResponseSlotInfo;
    const auto prefix = bytes({0x03, 0x03, 0x40, 0x12, 0x00, 0x00});
    REQUIRE(decode<Slot>(prefix + bytes({0xff, 0xff, 0x03})).durability_correction == -32768);
    REQUIRE(decode<Slot>(prefix + bytes({0xfe, 0xff, 0x03})).durability_correction == 32767);
    REQUIRE(rejects<Slot>(prefix + bytes({0x80, 0x80, 0x04})));
    REQUIRE(rejects<Slot>(prefix + bytes({0x81, 0x80, 0x04})));
}

TEST_CASE("same-width signed unsigned primitive wire mapping remains lossless")
{
    using Position = bp::NetworkBlockPosition_<729>;
    const auto wire = bytes({0x00, 0xff, 0xff, 0xff, 0xff, 0x0f, 0x00});
    const auto position = decode<Position>(wire);
    REQUIRE(position.y == -1);
    REQUIRE(encode(position) == wire);
}
