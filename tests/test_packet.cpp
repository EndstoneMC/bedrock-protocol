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

// The pack is one entry per packet id, which is far past Clang's 256-deep
// expression nesting limit as a fold. Expanding into an array and walking it
// keeps the pack one level deep.
template <int V, int... Id>
constexpr int modelled(std::integer_sequence<int, Id...>)
{
    const bool present[] = {bp::has_packet_v<V, Id>...};
    int count = 0;
    for (const bool one : present) {
        count += one ? 1 : 0;
    }
    return count;
}

template <int V, int... Id>
constexpr bool ids_agree(std::integer_sequence<int, Id...>)
{
    const bool agrees[] = {id_agrees<V, Id>()...};
    for (const bool one : agrees) {
        if (!one) {
            return false;
        }
    }
    return true;
}

template <int V>
constexpr int end_id = static_cast<int>(bp::MinecraftPacketIds_<V>::EndId);

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
    STATIC_REQUIRE_FALSE(bp::has_packet_v<1001, 0>);
    STATIC_REQUIRE(std::is_void_v<bp::packet_of_t<1001, 0>>);
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
