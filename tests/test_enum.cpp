#include <optional>
#include <string_view>
#include <type_traits>

#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("enum to string", "[enum]")
{
    STATIC_REQUIRE(bp::enum_name(bp::BossBarColor::REBECCA_PURPLE) == "REBECCA_PURPLE");
    STATIC_REQUIRE(bp::enum_name<bp::BossBarColor::PINK>() == "PINK");
    STATIC_REQUIRE(bp::enum_name(static_cast<bp::BossBarColor>(99)).empty());
    STATIC_REQUIRE(bp::enum_contains(bp::BossBarOverlay::NOTCHED_20));
    STATIC_REQUIRE_FALSE(bp::enum_contains(static_cast<bp::BossBarOverlay>(5)));
}

TEST_CASE("string to enum", "[enum]")
{
    STATIC_REQUIRE(bp::enum_cast<bp::BossEventUpdateType>("UPDATE_STYLE") == bp::BossEventUpdateType::UPDATE_STYLE);
    STATIC_REQUIRE(bp::enum_cast<bp::BossEventUpdateType>("update_style") == std::nullopt);
    STATIC_REQUIRE(bp::enum_cast<bp::BossEventUpdateType>("NOPE") == std::nullopt);
    STATIC_REQUIRE(bp::enum_contains<bp::BossEventUpdateType>("QUERY"));
}

TEST_CASE("integer to enum", "[enum]")
{
    STATIC_REQUIRE(bp::enum_cast<bp::BossBarColor>(2) == bp::BossBarColor::RED);
    STATIC_REQUIRE(bp::enum_cast<bp::BossBarColor>(8) == std::nullopt);
    STATIC_REQUIRE_FALSE(bp::enum_contains<bp::BossBarColor>(8));
    STATIC_REQUIRE(bp::enum_integer(bp::BossBarColor::WHITE) == 7);
    STATIC_REQUIRE(bp::enum_underlying(bp::BossBarColor::WHITE) == 7);
}

TEST_CASE("enum tables", "[enum]")
{
    STATIC_REQUIRE(bp::enum_type_name<bp::BossBarOverlay>() == "BossBarOverlay");
    STATIC_REQUIRE(bp::enum_count<bp::BossBarOverlay>() == 5);
    STATIC_REQUIRE(bp::enum_index(bp::BossBarOverlay::NOTCHED_12) == 3);
    STATIC_REQUIRE(bp::enum_index<bp::BossBarOverlay::NOTCHED_12>() == 3);
    STATIC_REQUIRE(bp::enum_value<bp::BossBarOverlay>(0) == bp::BossBarOverlay::PROGRESS);
    STATIC_REQUIRE(bp::enum_value<bp::BossBarOverlay, 1>() == bp::BossBarOverlay::NOTCHED_6);
    STATIC_REQUIRE(bp::enum_values<bp::BossBarOverlay>()[0] == bp::BossBarOverlay::PROGRESS);
    STATIC_REQUIRE(bp::enum_names<bp::BossBarOverlay>()[1] == "NOTCHED_6");
    STATIC_REQUIRE(bp::enum_entries<bp::BossBarOverlay>()[4].second == "NOTCHED_20");
}

// The tables are in declaration order, so a negative leading member stays first.
TEST_CASE("declaration order", "[enum]")
{
    STATIC_REQUIRE(bp::enum_value<bp::MovementEffectType>(0) == bp::MovementEffectType::INVALID);
    STATIC_REQUIRE(bp::enum_integer(bp::enum_value<bp::MovementEffectType>(0)) == -1);
}

// An enum BDS declares inside a class is nested in C++ too, and reflects under
// its qualified name. A versioned owner shares one definition across snapshots,
// so the nested type is the same C++ type at every one.
TEST_CASE("nested enum", "[enum]")
{
    using Transaction = bp::ItemUseInventoryTransaction;
    STATIC_REQUIRE(bp::enum_type_name<Transaction::ActionType>() == "ItemUseInventoryTransaction::ActionType");
    STATIC_REQUIRE(bp::enum_count<Transaction::TriggerType>() == 3);
    STATIC_REQUIRE(bp::enum_name(Transaction::ActionType::USE_AS_ATTACK) == "USE_AS_ATTACK");
    STATIC_REQUIRE(bp::enum_cast<Transaction::PredictedResult>("SUCCESS") == Transaction::PredictedResult::SUCCESS);
    STATIC_REQUIRE(std::is_same_v<bp::base::ItemUseInventoryTransaction::ActionType,
                                  bp::v1001::ItemUseInventoryTransaction::ActionType>);
    STATIC_REQUIRE(bp::enum_type_name<bp::InventorySource::InventorySourceFlags>() ==
                   "InventorySource::InventorySourceFlags");
}

// A versioned enum reflects the member set of the snapshot it is spelled at.
TEST_CASE("versioned enum", "[enum]")
{
    STATIC_REQUIRE(bp::enum_count<bp::base::MovementEffectType>() == 4);
    STATIC_REQUIRE(bp::enum_count<bp::v1001::MovementEffectType>() == 5);
    STATIC_REQUIRE(bp::enum_type_name<bp::base::MovementEffectType>() == "MovementEffectType");
    STATIC_REQUIRE(bp::enum_cast<bp::base::MovementEffectType>("GEYSER_BOOST") == std::nullopt);
    STATIC_REQUIRE(bp::enum_name(bp::v1001::MovementEffectType::GEYSER_BOOST) == "GEYSER_BOOST");
    STATIC_REQUIRE(bp::enum_name(bp::MovementEffectType_<975>::COUNT) == "COUNT");
    STATIC_REQUIRE(bp::enum_integer(bp::MovementEffectType_<975>::COUNT) == 2);
    STATIC_REQUIRE(bp::enum_integer(bp::MovementEffectType_<1001>::COUNT) == 3);
}
