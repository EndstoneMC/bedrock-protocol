#include <algorithm>
#include <cstdint>
#include <optional>
#include <string_view>
#include <type_traits>
#include <utility>

#include <bedrock/protocol.hpp>

namespace bp = bedrock::protocol;

namespace {

template <int From, int To>
constexpr std::optional<std::uint32_t> carrySound(std::uint32_t number) noexcept
{
    const auto sound = bp::enum_cast_<From, bp::LevelSoundEvent>(number).value_or(bp::LevelSoundEvent::Undefined);
    return bp::enum_integer_<To>(sound).or_else([] { return bp::enum_integer_<To>(bp::LevelSoundEvent::Undefined); });
}

template <int V, typename E>
concept numbered = requires(E value) { bp::enum_integer_<V>(value); };

template <int V, typename E>
concept named = requires(E value) { bp::enum_name_<V>(value); };

using CmdEntry = std::pair<bp::CurrentCmdVersion, std::string_view>;

constexpr int below = bp::ProtocolVersion::MINIMUM_VERSION.getProtocol() - 1;
constexpr int above = bp::ProtocolVersion::MAXIMUM_VERSION.getProtocol() + 1;

}  // namespace

static_assert(carrySound<2225, 2193>(615U) == 614U);
static_assert(carrySound<2225, 2193>(614U) == 614U);
static_assert(*bp::enum_integer_<2225>(bp::ContainerType::DiscPress) == 38);
static_assert(!bp::enum_integer_<2193>(bp::ContainerType::DiscPress));
static_assert(!bp::enum_contains_<2193>(bp::ContainerType::DiscPress));
static_assert(bp::enum_contains_<2225>(bp::ContainerType::DiscPress));
static_assert(std::ranges::all_of(bp::enum_values_<2225, bp::ContainerType>(), [](bp::ContainerType type) {
    return bp::enum_contains_<2193>(type) || type == bp::ContainerType::DiscPress;
}));
static_assert(std::ranges::none_of(bp::enum_values_<2193, bp::ContainerType>(),
                                   [](bp::ContainerType type) { return type == bp::ContainerType::DiscPress; }));
static_assert(bp::enum_count_<2193, bp::ContainerType>() + 1 == bp::enum_count_<2225, bp::ContainerType>());
static_assert(bp::enum_count_<2225, bp::ContainerType>() == bp::enum_values_<2225, bp::ContainerType>().size());
static_assert(*bp::enum_integer_<2168>(bp::LevelSoundEvent::Undefined) == 614);
static_assert(*bp::enum_integer_<2225>(bp::LevelSoundEvent::Undefined) == 615);
static_assert(!bp::enum_integer_<2168>(bp::LevelSoundEvent::IceBallBreak));
static_assert(bp::enum_integer_<2169>(bp::LevelSoundEvent::Undefined) == 614);
static_assert(bp::enum_integer_<2170>(bp::LevelSoundEvent::Undefined) == 614);
static_assert(*bp::enum_integer_<898>(bp::ActorDamageCause::Dehydration) == 35);
static_assert(!bp::enum_integer_<729>(bp::ActorDamageCause::Dehydration));
static_assert(*bp::enum_integer_<729>(bp::MolangVersion::Latest) == 12);
static_assert(bp::enum_cast_<729, bp::MolangVersion>(12) == bp::MolangVersion::Latest);
static_assert(bp::enum_cast_<2193, bp::CurrentCmdVersion>(52) == bp::CurrentCmdVersion::Latest);
static_assert(bp::enum_name(bp::MolangVersion::CarryingBlockQueryAllActors) == "latest");
static_assert(bp::enum_name(bp::EditorLevelMigrationVersion::EditorAchievements) == "current");
static_assert(std::ranges::count(bp::enum_values_<2225, bp::MolangVersion>(), bp::MolangVersion::Latest) == 1);
static_assert(*bp::enum_integer_<2168>(bp::PieceType::Unsupported) == 28);
static_assert(!bp::enum_integer_<2168>(bp::PieceType::CoCo));
static_assert(*bp::enum_integer_<2193>(bp::CurrentCmdVersion::Latest) == 52);
static_assert(!bp::enum_cast_<2168, bp::ContainerID>(126));
static_assert(!bp::enum_contains_<2168, bp::ContainerID>(126));
static_assert(*bp::enum_integer_<2225>(static_cast<bp::ContainerType>(100)) == 100);
static_assert(bp::enum_cast_<2225, bp::ContainerType>(100) == static_cast<bp::ContainerType>(100));
static_assert(!bp::enum_integer_<2193>(bp::CursorItemDragState::Start));
static_assert(!bp::enum_cast_<2193, bp::CursorItemDragState>(0));
static_assert(bp::enum_values_<2193, bp::CursorItemDragState>().empty());
static_assert(bp::enum_count_<2193, bp::CursorItemDragState>() == 0);
static_assert(*bp::enum_integer_<2225>(bp::CursorItemDragState::Stop) == 1);
static_assert(numbered<2170, bp::ContainerType>);
static_assert(!numbered<below, bp::ContainerType>);
static_assert(!numbered<above, bp::ContainerType>);

static_assert(!bp::enum_name_<2193>(bp::PieceType::CoCo));
static_assert(bp::enum_name_<2225>(bp::PieceType::CoCo) == "coco");
static_assert(bp::enum_cast_<2225, bp::PieceType>("CoCo") == bp::PieceType::CoCo);
static_assert(!bp::enum_contains_<2193, bp::PieceType>("coco"));
static_assert(std::ranges::count_if(bp::enum_entries_<2225, bp::PieceType>(),
                                    [](const auto &entry) { return !bp::enum_name_<2193>(entry.first); }) == 1);
static_assert(std::ranges::equal(bp::enum_names_<2225, bp::PieceType>(), bp::enum_entries_<2225, bp::PieceType>(), {},
                                 {}, &std::pair<bp::PieceType, std::string_view>::second));
static_assert(bp::enum_name_<2169>(bp::PieceType::Emote) == bp::enum_name_<2168>(bp::PieceType::Emote));
static_assert(!bp::enum_name_<2169>(bp::PieceType::CoCo));
static_assert(bp::enum_contains_<2225, bp::PieceType>(std::underlying_type_t<bp::PieceType>{28}));
static_assert(bp::enum_name_<2193>(bp::CurrentCmdVersion::Latest) == "latest");
static_assert(bp::enum_cast_<2193, bp::CurrentCmdVersion>("latest") == bp::CurrentCmdVersion::Latest);
static_assert(bp::enum_cast_<2225, bp::CurrentCmdVersion>("latest") == bp::CurrentCmdVersion::Latest);
static_assert(bp::enum_name_<2168>(bp::CurrentCmdVersion::Latest) == "latest");
static_assert(bp::enum_name_<2225>(bp::CurrentCmdVersion::Latest) == "latest");
static_assert(bp::enum_cast_<2168, bp::CurrentCmdVersion>("clonepartialbedblockfix") ==
              bp::CurrentCmdVersion::ClonePartialBedBlockFix);
static_assert(bp::enum_name(bp::CurrentCmdVersion::TimeCommandClocksRelease) == "latest");
static_assert(bp::enum_cast_<2193, bp::CurrentCmdVersion>("agentsweepingblocktest") == bp::CurrentCmdVersion{34});
static_assert(bp::enum_contains_<2193, bp::CurrentCmdVersion>("AgentSweepingBlockTest"));
static_assert(bp::enum_name_<2193>(bp::CurrentCmdVersion{34}) ==
              "commandselectorhasitemfilternolongercallssameitemfunction");
static_assert(std::ranges::count(bp::enum_entries_<2193, bp::CurrentCmdVersion>(), bp::CurrentCmdVersion{34},
                                 &CmdEntry::first) == 1);
static_assert(std::ranges::count(bp::enum_entries_<2193, bp::CurrentCmdVersion>(), bp::CurrentCmdVersion::Latest,
                                 &CmdEntry::first) == 1);
static_assert(!bp::enum_name_<2193>(*bp::enum_cast_<2225, bp::CurrentCmdVersion>("timecommandpreventnegativetime")));
static_assert(!bp::enum_name_<2193>(bp::CurrentCmdVersion::RedstoneCircuitStateChangeFix));
static_assert(bp::enum_name_<2225>(bp::AudioContentPlaybackType::Music) == "music");
static_assert(!bp::enum_name_<2193>(bp::AudioContentPlaybackType::Music));
static_assert(!bp::enum_cast_<2193, bp::AudioContentPlaybackType>("music"));
static_assert(!bp::enum_contains_<2193, bp::AudioContentPlaybackType>("music"));
static_assert(bp::enum_names_<2193, bp::AudioContentPlaybackType>().empty());
static_assert(bp::enum_entries_<2193, bp::AudioContentPlaybackType>().empty());
static_assert(bp::enum_name_<729>(bp::ArmSizeType::Wide) == "wide");
static_assert(!bp::enum_name_<2168>(bp::ArmSizeType::Wide));
static_assert(!bp::enum_contains_<2168, bp::ArmSizeType>("wide"));
static_assert(bp::enum_entries_<2168, bp::ArmSizeType>().empty());
static_assert(bp::enum_cast<bp::PieceType>("coco") == bp::PieceType::CoCo);
static_assert(bp::enum_name(bp::PieceType::CoCo) == "coco");
static_assert(named<2225, bp::PieceType>);
static_assert(!named<2225, bp::ContainerType>);
static_assert(!named<below, bp::PieceType>);
static_assert(!named<above, bp::PieceType>);
