#pragma once

#include <concepts>

namespace bedrock::protocol {

class BinaryStream;
class ReadOnlyBinaryStream;

template <typename T>
struct Serializer;

template <typename T>
void serialize(BinaryStream &stream, const T &value)
{
    Serializer<T>::serialize(stream, value);
}

template <typename T, typename V>
    requires (!std::same_as<T, V>)
void serialize(BinaryStream &stream, const V &value)
{
    Serializer<T>::serialize(stream, value);
}

template <typename T>
auto deserialize(ReadOnlyBinaryStream &stream)
{
    return Serializer<T>::deserialize(stream);
}

}  // namespace bedrock::protocol
