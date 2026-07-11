#pragma once

#include <concepts>

namespace bedrock::protocol {

class BinaryWriter;
class BinaryReader;

template <typename T>
struct Serializer;

template <typename T>
void serialize(BinaryWriter &stream, const T &value)
{
    Serializer<T>::serialize(stream, value);
}

template <typename T, typename V>
    requires (!std::same_as<T, V>)
void serialize(BinaryWriter &stream, const V &value)
{
    Serializer<T>::serialize(stream, value);
}

template <typename T>
auto deserialize(BinaryReader &stream)
{
    return Serializer<T>::deserialize(stream);
}

}  // namespace bedrock::protocol
