"""Molang versions and expression opcodes: util/molang/ and
SharedTypes/versionless/Molang/. Tier-0: imports nothing but the DSL surface."""

from enum import IntEnum, auto

from protocol import int16, value

package = "bedrock.protocol"


class MolangVersion(IntEnum, int16):
    INVALID = -1
    BEFORE_VERSIONING = 0
    INITIAL = 1
    FIXED_ITEM_REMAINING_USE_DURATION_QUERY = 2
    EXPRESSION_ERROR_MESSAGES = 3
    UNEXPECTED_OPERATOR_ERRORS = 4
    CONDITIONAL_OPERATOR_ASSOCIATIVITY = 5
    COMPARISON_AND_LOGICAL_OPERATOR_PRECEDENCE = 6
    DIVIDE_BY_NEGATIVE_VALUE = 7
    FIXED_CAPE_FLAP_AMOUNT_QUERY = 8
    QUERY_BLOCK_PROPERTY_RENAMED_TO_STATE = 9
    DEPRECATE_OLD_BLOCK_QUERY_NAMES = 10
    DEPRECATED_SNIFFER_AND_CAMEL_QUERIES = 11
    LEAF_SUPPORTING_IN_FIRST_SOLID_BLOCK_BELOW = 12
    CARRYING_BLOCK_QUERY_ALL_ACTORS = value(13, since=827)
    NUM_VALID_VERSIONS = auto()
    LATEST = NUM_VALID_VERSIONS - 1
    HARDCODED_MOLANG = LATEST


class ExpressionOp(IntEnum, int16):
    UNKNOWN = -1
    LEFT_BRACE = 0
    RIGHT_BRACE = 1
    LEFT_BRACKET = 2
    RIGHT_BRACKET = 3
    LEFT_PARENTHESIS = 4
    RIGHT_PARENTHESIS = 5
    NEGATE = 6
    LOGICAL_NOT = 7
    ABS = 8
    ADD = 9
    ACOS = 10
    ASIN = 11
    ATAN = 12
    ATAN2 = 13
    CEIL = 14
    CLAMP = 15
    COPY_SIGN = 16
    COS = 17
    DIE_ROLL = 18
    DIE_ROLL_INT = 19
    DIV = 20
    EXP = 21
    FLOOR = 22
    HERMITE_BLEND = 23
    LERP = 24
    LERP_ROTATE = 25
    LN = 26
    MAX = 27
    MIN = 28
    MIN_ANGLE = 29
    MOD = 30
    MUL = 31
    POW = 32
    RANDOM = 33
    RANDOM_INT = 34
    ROUND = 35
    SIN = 36
    SIGN = 37
    SQRT = 38
    TRUNC = 39
    QUERY_FUNCTION = 40
    ARRAY_VARIABLE = 41
    CONTEXT_VARIABLE = 42
    ENTITY_VARIABLE = 43
    TEMP_VARIABLE = 44
    MEMBER_ACCESSOR = 45
    HASHED_STRING_HASH = 46
    GEOMETRY_VARIABLE = 47
    MATERIAL_VARIABLE = 48
    TEXTURE_VARIABLE = 49
    LESS_THAN = 50
    LESS_EQUAL = 51
    GREATER_EQUAL = 52
    GREATER_THAN = 53
    LOGICAL_EQUAL = 54
    LOGICAL_NOT_EQUAL = 55
    LOGICAL_OR = 56
    LOGICAL_AND = 57
    NULL_COALESCING = 58
    CONDITIONAL = 59
    CONDITIONAL_ELSE = 60
    FLOAT = 61
    PI = 62
    ARRAY = 63
    GEOMETRY = 64
    MATERIAL = 65
    TEXTURE = 66
    LOOP = 67
    FOR_EACH = 68
    BREAK = 69
    CONTINUE = 70
    ASSIGNMENT = 71
    POINTER = 72
    SEMICOLON = 73
    RETURN = 74
    COMMA = 75
    THIS = 76
    INTERNAL_NON_EVALUATED_ARRAY = 77
    INVERSE_LERP = value(78, since=859)
    EASE_IN_QUAD = value(79, since=859)
    EASE_OUT_QUAD = value(80, since=859)
    EASE_IN_OUT_QUAD = value(81, since=859)
    EASE_IN_CUBIC = value(82, since=859)
    EASE_OUT_CUBIC = value(83, since=859)
    EASE_IN_OUT_CUBIC = value(84, since=859)
    EASE_IN_QUART = value(85, since=859)
    EASE_OUT_QUART = value(86, since=859)
    EASE_IN_OUT_QUART = value(87, since=859)
    EASE_IN_QUINT = value(88, since=859)
    EASE_OUT_QUINT = value(89, since=859)
    EASE_IN_OUT_QUINT = value(90, since=859)
    EASE_IN_SINE = value(91, since=859)
    EASE_OUT_SINE = value(92, since=859)
    EASE_IN_OUT_SINE = value(93, since=859)
    EASE_IN_EXPO = value(94, since=859)
    EASE_OUT_EXPO = value(95, since=859)
    EASE_IN_OUT_EXPO = value(96, since=859)
    EASE_IN_CIRC = value(97, since=859)
    EASE_OUT_CIRC = value(98, since=859)
    EASE_IN_OUT_CIRC = value(99, since=859)
    EASE_IN_BOUNCE = value(100, since=859)
    EASE_OUT_BOUNCE = value(101, since=859)
    EASE_IN_OUT_BOUNCE = value(102, since=859)
    EASE_IN_BACK = value(103, since=859)
    EASE_OUT_BACK = value(104, since=859)
    EASE_IN_OUT_BACK = value(105, since=859)
    EASE_IN_ELASTIC = value(106, since=859)
    EASE_OUT_ELASTIC = value(107, since=859)
    EASE_IN_OUT_ELASTIC = value(108, since=859)
    COUNT = auto()
