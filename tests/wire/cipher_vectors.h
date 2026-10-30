// Independent Go vectors from bedrock-bot/tests/fixtures/generate_wire_vectors.go.
#pragma once
#include <array>
#include <string_view>
#include <utility>
inline constexpr std::array<std::pair<std::string_view, std::string_view>, 2> cipherVectors{{
    {"6669727374207061796c6f6164", "216ba468b1c5b27af42df8ead564aa71c23f74b82f"},
    {"ff030102030405060708090a0b0c0d0e0f1011", "845c7d3a64e1801b6e08bb0b1ba2f1a1ce02895de9856045b0f738"},
}};
