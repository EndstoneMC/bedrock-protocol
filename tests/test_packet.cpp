#include <type_traits>
#include <utility>

#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

namespace {

template <int V, int Id>
constexpr bool id_agrees()
{
    if constexpr (bp::has_packet_v<V, Id>) {
        return bp::packet_of_t<V, Id>::Id == Id;
    } else {
        return true;
    }
}

template <int V, int... Id>
constexpr int modelled(std::integer_sequence<int, Id...>)
{
    return (0 + ... + (bp::has_packet_v<V, Id> ? 1 : 0));
}

template <int V, int... Id>
constexpr bool ids_agree(std::integer_sequence<int, Id...>)
{
    return (id_agrees<V, Id>() && ...);
}

template <int V>
constexpr int end_id = static_cast<int>(bp::MinecraftPacketIds_<V>::END_ID);

}  // namespace

TEST_CASE("packet by id", "[packet]")
{
    STATIC_REQUIRE(std::is_same_v<bp::packet_of_t<975, 74>, bp::base::BossEventPacket>);
    STATIC_REQUIRE(std::is_same_v<bp::packet_of_t<1001, 74>, bp::v1001::BossEventPacket>);
    STATIC_REQUIRE(std::is_same_v<bp::packet_of_t<2168, 74>, bp::v1001::BossEventPacket>);
    STATIC_REQUIRE(std::is_same_v<bp::packet_of_t<975, 1>, bp::LoginPacket>);
}

TEST_CASE("an unmodelled id is void", "[packet]")
{
    STATIC_REQUIRE_FALSE(bp::has_packet_v<1001, 2>);
    STATIC_REQUIRE(std::is_void_v<bp::packet_of_t<1001, 2>>);
    STATIC_REQUIRE_FALSE(bp::has_packet_v<1001, 999>);
}

TEST_CASE("a packet resolves only inside its version range", "[packet]")
{
    // ClientboundUpdateSoundDataPacket arrives at 1001.
    STATIC_REQUIRE_FALSE(bp::has_packet_v<975, 348>);
    STATIC_REQUIRE(bp::has_packet_v<1001, 348>);
    // ClientboundAttributeLayerSyncPacket arrives at 944.
    STATIC_REQUIRE_FALSE(bp::has_packet_v<940, 345>);
    STATIC_REQUIRE(bp::has_packet_v<975, 345>);
}

TEST_CASE("the registry is walkable by id", "[packet]")
{
    STATIC_REQUIRE(modelled<975>(std::make_integer_sequence<int, end_id<975>>{}) == 35);
    STATIC_REQUIRE(modelled<1001>(std::make_integer_sequence<int, end_id<1001>>{}) == 38);
    STATIC_REQUIRE(modelled<2168>(std::make_integer_sequence<int, end_id<2168>>{}) == 38);
    STATIC_REQUIRE(ids_agree<1001>(std::make_integer_sequence<int, end_id<1001>>{}));
}
