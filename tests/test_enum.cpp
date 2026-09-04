#include <optional>
#include <string_view>
#include <type_traits>

#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

// The name tables are the C++ enumerator lowercased with no separator -- they double as
// the wire table for a name-coded enum, where BDS's own string is that same fold.
TEST_CASE("enum to string", "[enum]")
{
    STATIC_REQUIRE(bp::enum_name(bp::BossBarColor::RebeccaPurple) == "rebeccapurple");
    STATIC_REQUIRE(bp::enum_name<bp::BossBarColor::Pink>() == "pink");
    STATIC_REQUIRE(bp::enum_name(static_cast<bp::BossBarColor>(99)).empty());
    STATIC_REQUIRE(bp::enum_contains(bp::BossBarOverlay::Notched20));
    STATIC_REQUIRE_FALSE(bp::enum_contains(static_cast<bp::BossBarOverlay>(5)));
}

// Folding the name given against a folded table makes every lookup case-insensitive,
// with no predicate to pass.
TEST_CASE("string to enum", "[enum]")
{
    STATIC_REQUIRE(bp::enum_cast<bp::BossEventUpdateType>("updatestyle") == bp::BossEventUpdateType::UpdateStyle);
    STATIC_REQUIRE(bp::enum_cast<bp::BossEventUpdateType>("UPDATESTYLE") == bp::BossEventUpdateType::UpdateStyle);
    STATIC_REQUIRE(bp::enum_cast<bp::BossEventUpdateType>("UpdateStyle") == bp::BossEventUpdateType::UpdateStyle);
    STATIC_REQUIRE(bp::enum_cast<bp::BossEventUpdateType>("NOPE") == std::nullopt);
    STATIC_REQUIRE(bp::enum_contains<bp::BossEventUpdateType>("QUERY"));
}

TEST_CASE("integer to enum", "[enum]")
{
    STATIC_REQUIRE(bp::enum_cast<bp::BossBarColor>(2) == bp::BossBarColor::Red);
    STATIC_REQUIRE(bp::enum_cast<bp::BossBarColor>(8) == std::nullopt);
    STATIC_REQUIRE_FALSE(bp::enum_contains<bp::BossBarColor>(8));
    STATIC_REQUIRE(bp::enum_integer(bp::BossBarColor::White) == 7);
    STATIC_REQUIRE(bp::enum_underlying(bp::BossBarColor::White) == 7);
}

TEST_CASE("enum tables", "[enum]")
{
    STATIC_REQUIRE(bp::enum_type_name<bp::BossBarOverlay>() == "BossBarOverlay");
    STATIC_REQUIRE(bp::enum_count<bp::BossBarOverlay>() == 5);
    STATIC_REQUIRE(bp::enum_index(bp::BossBarOverlay::Notched12) == 3);
    STATIC_REQUIRE(bp::enum_index<bp::BossBarOverlay::Notched12>() == 3);
    STATIC_REQUIRE(bp::enum_value<bp::BossBarOverlay>(0) == bp::BossBarOverlay::Progress);
    STATIC_REQUIRE(bp::enum_value<bp::BossBarOverlay, 1>() == bp::BossBarOverlay::Notched6);
    STATIC_REQUIRE(bp::enum_values<bp::BossBarOverlay>()[0] == bp::BossBarOverlay::Progress);
    STATIC_REQUIRE(bp::enum_names<bp::BossBarOverlay>()[1] == "notched6");
    STATIC_REQUIRE(bp::enum_entries<bp::BossBarOverlay>()[4].second == "notched20");
}

// The tables are in declaration order, so a negative leading member stays first.
TEST_CASE("declaration order", "[enum]")
{
    STATIC_REQUIRE(bp::enum_value<bp::MovementEffectType>(0) == bp::MovementEffectType::Invalid);
    STATIC_REQUIRE(bp::enum_integer(bp::enum_value<bp::MovementEffectType>(0)) == -1);
}

// An enum BDS declares inside a class is nested in C++ too, and reflects under
// its qualified name. A versioned owner shares one definition across snapshots
// unless the nested enum gates on its own: ActionType gained UseAsAttack at 844
// and is one C++ type per era, while its ungated siblings stay single.
TEST_CASE("nested enum", "[enum]")
{
    using Transaction = bp::ItemUseInventoryTransaction;
    STATIC_REQUIRE(bp::enum_type_name<Transaction::ActionType>() == "ItemUseInventoryTransaction::ActionType");
    STATIC_REQUIRE(bp::enum_count<Transaction::TriggerType>() == 3);
    STATIC_REQUIRE(bp::enum_name(Transaction::ActionType::UseAsAttack) == "useasattack");
    STATIC_REQUIRE(bp::enum_cast<Transaction::PredictedResult>("SUCCESS") == Transaction::PredictedResult::Success);
    STATIC_REQUIRE(std::is_same_v<bp::base::ItemUseInventoryTransaction::TriggerType,
                                  bp::v1001::ItemUseInventoryTransaction::TriggerType>);
    STATIC_REQUIRE_FALSE(std::is_same_v<bp::base::ItemUseInventoryTransaction::ActionType,
                                        bp::v1001::ItemUseInventoryTransaction::ActionType>);
    STATIC_REQUIRE(bp::enum_count<bp::ItemUseInventoryTransaction_<827>::ActionType>() == 3);
    STATIC_REQUIRE(bp::enum_count<bp::ItemUseInventoryTransaction_<844>::ActionType>() == 4);
    STATIC_REQUIRE(bp::enum_type_name<bp::InventorySource::InventorySourceFlags>() ==
                   "InventorySource::InventorySourceFlags");
}

// A versioned enum reflects the member set of the snapshot it is spelled at.
TEST_CASE("versioned enum", "[enum]")
{
    STATIC_REQUIRE(bp::enum_count<bp::base::MovementEffectType>() == 4);
    STATIC_REQUIRE(bp::enum_count<bp::v1001::MovementEffectType>() == 5);
    STATIC_REQUIRE(bp::enum_type_name<bp::base::MovementEffectType>() == "MovementEffectType");
    STATIC_REQUIRE(bp::enum_cast<bp::base::MovementEffectType>("GEYSERBOOST") == std::nullopt);
    STATIC_REQUIRE(bp::enum_name(bp::v1001::MovementEffectType::GeyserBoost) == "geyserboost");
    STATIC_REQUIRE(bp::enum_name(bp::MovementEffectType_<975>::Count) == "count");
    STATIC_REQUIRE(bp::enum_integer(bp::MovementEffectType_<975>::Count) == 2);
    STATIC_REQUIRE(bp::enum_integer(bp::MovementEffectType_<1001>::Count) == 3);
}

// A trailing sentinel written `auto()` re-resolves against the members present at each
// snapshot, so the three sound events added at 2168 push UNDEFINED from 611 to 614.
TEST_CASE("level sound event trailing sentinel", "[enum]")
{
    STATIC_REQUIRE(bp::enum_cast<bp::LevelSoundEvent_<975>>("MOUNT") == std::nullopt);
    STATIC_REQUIRE(bp::enum_cast<bp::LevelSoundEvent_<1001>>("MOUNT") == std::nullopt);
    STATIC_REQUIRE(bp::enum_cast<bp::LevelSoundEvent_<1001>>("DISMOUNT") == std::nullopt);
    STATIC_REQUIRE(bp::enum_cast<bp::LevelSoundEvent_<1001>>("STRAW_BED_BREAK_LEAVE") == std::nullopt);
    STATIC_REQUIRE(bp::enum_integer(bp::LevelSoundEvent_<2168>::Mount) == 611);
    STATIC_REQUIRE(bp::enum_integer(bp::LevelSoundEvent_<2168>::Dismount) == 612);
    STATIC_REQUIRE(bp::enum_integer(bp::LevelSoundEvent_<2168>::StrawBedBreakLeave) == 613);
    STATIC_REQUIRE(bp::enum_integer(bp::LevelSoundEvent_<975>::Undefined) == 601);
    STATIC_REQUIRE(bp::enum_integer(bp::LevelSoundEvent_<1001>::Undefined) == 611);
    STATIC_REQUIRE(bp::enum_integer(bp::LevelSoundEvent_<2168>::Undefined) == 614);
    STATIC_REQUIRE(bp::enum_count<bp::LevelSoundEvent_<2168>>() ==
                   bp::enum_count<bp::LevelSoundEvent_<1001>>() + 3);
}
