"""Enchantments and the enchanting table: world/item/enchanting/ -- the enchantment
type table, an instance and a slot's set of them, and the table's options.
Not the recipes that consume them -- world/item/crafting/, in crafting.py."""

from enum import IntEnum, auto

from protocol import array, field, int32, packet, uint8, uvarint32, value
from protocol.crafting import RecipeNetId

package = "bedrock.protocol"


class Enchant:
    class Type(IntEnum, uint8):
        PROTECTION = 0
        FIRE_PROTECTION = 1
        FEATHER_FALLING = 2
        BLAST_PROTECTION = 3
        PROJECTILE_PROTECTION = 4
        THORNS = 5
        RESPIRATION = 6
        DEPTH_STRIDER = 7
        AQUA_AFFINITY = 8
        SHARPNESS = 9
        SMITE = 10
        BANE_OF_ARTHROPODS = 11
        KNOCKBACK = 12
        FIRE_ASPECT = 13
        LOOTING = 14
        EFFICIENCY = 15
        SILK_TOUCH = 16
        UNBREAKING = 17
        FORTUNE = 18
        POWER = 19
        PUNCH = 20
        FLAME = 21
        INFINITY = 22
        LUCK_OF_THE_SEA = 23
        LURE = 24
        FROST_WALKER = 25
        MENDING = 26
        CURSE_OF_BINDING = 27
        CURSE_OF_VANISHING = 28
        IMPALING = 29
        RIPTIDE = 30
        LOYALTY = 31
        CHANNELING = 32
        MULTISHOT = 33
        PIERCING = 34
        QUICK_CHARGE = 35
        SOUL_SPEED = 36
        SWIFT_SNEAK = 37
        WIND_BURST = 38
        DENSITY = 39
        BREACH = 40
        LUNGE = value(41, since=898)
        NUM_ENCHANTMENTS = auto()
        INVALID_ENCHANTMENT = auto()


class EnchantmentInstance:
    enchant_type: Enchant.Type
    level: int32 = field(type=uint8)


class ItemEnchants:
    slot: int32
    item_enchants: array[list[EnchantmentInstance], 3]


class ItemEnchantOption:
    cost: int32 = field(type=uvarint32, until=975)
    cost: int32 = field(type=uint8, since=975)
    enchants: ItemEnchants
    enchant_name: str
    enchant_net_id: RecipeNetId


@packet(id=146)
class PlayerEnchantOptionsPacket:
    options: list[ItemEnchantOption]
