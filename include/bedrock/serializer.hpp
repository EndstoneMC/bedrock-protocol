#pragma once

#include <concepts>

namespace bedrock::protocol {

class BinaryStream;
class ReadOnlyBinaryStream;

// Specialization point. Each generated type provides its own
// `SerializerFor<T>` with static `serialize` / `deserialize`.
template <typename T>
struct SerializerFor;

// For struct-typed values (the value's type IS the wrapper): T deduces from
// the argument.
template <typename T>
void serialize(BinaryStream &stream, const T &value)
{
    SerializerFor<T>::serialize(stream, value);
}

// For enums: the user holds a `Wrapper<P>::Value` (a nested enum type, which
// can't drive partial specialization). Caller supplies the wrapper as T
// explicitly; V is deduced from the enum value.
template <typename T, typename V>
    requires(!std::same_as<T, V>)
void serialize(BinaryStream &stream, const V &value)
{
    SerializerFor<T>::serialize(stream, value);
}

template <typename T>
auto deserialize(ReadOnlyBinaryStream &stream)
{
    return SerializerFor<T>::deserialize(stream);
}

}  // namespace bedrock::protocol
