#pragma once

#include <initializer_list>
#include <string>
#include <string_view>

#include <bedrock/enum.hpp>
#include <bedrock/nbt.hpp>
#include <bedrock/packet.hpp>
#include <bedrock/serializer.hpp>
#include <bedrock/stream.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

inline std::string bytes(std::initializer_list<int> raw)
{
    std::string out;
    for (int b : raw) {
        out.push_back(static_cast<char>(b));
    }
    return out;
}

template <class T>
std::string encode(const T &value)
{
    std::string buffer;
    bp::BinaryWriter writer{buffer};
    bp::Serializer<T>::serialize(writer, value);
    return buffer;
}

// The read succeeds and consumes the whole body.
template <class T>
T decode(std::string_view wire)
{
    bp::BinaryReader reader{wire};
    auto value = bp::Serializer<T>::deserialize(reader);
    REQUIRE(value.has_value());
    REQUIRE(reader.getUnreadLength() == 0);
    return *value;
}

// The read succeeds but leaves bytes over: the frame desynchronised rather than
// running short, so a wrong-era body comes back holding the wrong values.
template <class T>
T decode_partial(std::string_view wire)
{
    bp::BinaryReader reader{wire};
    auto value = bp::Serializer<T>::deserialize(reader);
    REQUIRE(value.has_value());
    REQUIRE(reader.getUnreadLength() != 0);
    return *value;
}

// The body is not a T at all: the read fails outright.
template <class T>
bool rejects(std::string_view wire)
{
    bp::BinaryReader reader{wire};
    return !bp::Serializer<T>::deserialize(reader).has_value();
}

// The cerealised item extra-data blob: Int16(0) NBT-length, then two empty
// uint32-counted string lists (can-place-on / can-break). All zero.
inline std::string empty_item_blob()
{
    return std::string(10, '\0');
}
