#include <cstdint>
#include <string>
#include <type_traits>

#include <bedrock/protocol/actor.h>
#include <bedrock/protocol/attribute.h>

#include "fixture.hpp"

TEST_CASE("a primitive alias is its own type, not a spelling of the primitive", "[alias]")
{
    STATIC_REQUIRE_FALSE(std::is_same_v<bp::ActorRuntimeID, std::uint64_t>);
    STATIC_REQUIRE_FALSE(std::is_same_v<bp::ActorRuntimeID, bp::ActorUniqueID>);
}

TEST_CASE("an alias is built only by an explicit construction", "[alias]")
{
    STATIC_REQUIRE_FALSE(std::is_convertible_v<std::uint64_t, bp::ActorRuntimeID>);
    STATIC_REQUIRE(std::is_constructible_v<bp::ActorRuntimeID, std::uint64_t>);
    STATIC_REQUIRE(static_cast<std::uint64_t>(bp::ActorRuntimeID{7}) == 7);
}

TEST_CASE("an alias converts back to its primitive implicitly", "[alias]")
{
    STATIC_REQUIRE(std::is_convertible_v<bp::ActorRuntimeID, std::uint64_t>);

    constexpr bp::ActorRuntimeID id{7};
    const std::uint64_t raw = id;
    REQUIRE(raw == 7);
}

TEST_CASE("an alias compares against its primitive without a cast", "[alias]")
{
    constexpr bp::ActorRuntimeID id{7};
    STATIC_REQUIRE(id == 7);
    STATIC_REQUIRE(id != 8);
    STATIC_REQUIRE(id < 8);
    STATIC_REQUIRE(id == bp::ActorRuntimeID{7});
    STATIC_REQUIRE(id != bp::ActorRuntimeID{8});
}

TEST_CASE("a default-constructed alias is zero", "[alias]")
{
    STATIC_REQUIRE(bp::ActorRuntimeID{} == 0);
    STATIC_REQUIRE(bp::DimensionType{} == 0);
}

TEST_CASE("a signed alias keeps its sign", "[alias]")
{
    constexpr bp::ActorUniqueID id{-3};
    STATIC_REQUIRE(id == -3);
    STATIC_REQUIRE(id < 0);
}

TEST_CASE("an alias still round-trips on the wire", "[alias]")
{
    bp::RemoveActorPacket packet;
    packet.entity_id = bp::ActorUniqueID{-3};
    REQUIRE(decode<bp::RemoveActorPacket>(encode(packet)).entity_id == -3);
}
