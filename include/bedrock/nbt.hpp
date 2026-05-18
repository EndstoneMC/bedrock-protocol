// NBT (Named Binary Tag), the network-little-endian variant Bedrock uses on
// the wire. Every NBT type -- the leaf tags, the recursive Tag union, ListTag,
// and CompoundTag -- is hand-written here and declared as a compiler built-in
// in protocol/nbt.py, so the DSL emits no codec of its own for them.
#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>
#include <variant>
#include <vector>

#include "expected.hpp"
#include "serializer.hpp"
#include "stream.hpp"

namespace bedrock::protocol {

// The leaf tags each wrap a single payload. ListTag and CompoundTag are
// recursive, so they follow the forward-declared Tag, which is the variant
// over all twelve.
struct ByteTag {
    std::int8_t value;
};

struct ShortTag {
    std::int16_t value;
};

struct IntTag {
    std::int32_t value;
};

struct LongTag {
    std::int64_t value;
};

struct FloatTag {
    float value;
};

struct DoubleTag {
    double value;
};

struct StringTag {
    std::string value;
};

struct ByteArrayTag {
    std::vector<std::int8_t> values;
};

struct IntArrayTag {
    std::vector<std::int32_t> values;
};

struct LongArrayTag {
    std::vector<std::int64_t> values;
};

struct Tag;

// A compound is an ordered list of named tags. Order is preserved so that a
// decode then re-encode is byte-identical.
struct CompoundTag {
    std::vector<std::pair<std::string, Tag>> entries;
};

struct ListTag {
    std::vector<Tag> elements;
};

// The twelve NBT payload types in tag-id order: the variant index plus one is
// the on-the-wire tag id (1 = Byte ... 12 = LongArray).
struct Tag {
    std::variant<
        ByteTag, ShortTag, IntTag, LongTag, FloatTag, DoubleTag, ByteArrayTag,
        StringTag, ListTag, CompoundTag, IntArrayTag, LongArrayTag>
        value;
};

namespace nbt_detail {

// A leaf tag wraps one payload, and its codec is that payload's. FixedLeaf
// covers the fixed-width values, VarLeaf the varint ones, and ArrayLeaf a
// varuint32-prefixed run of a scalar leaf's payload.
template <typename Leaf, typename T>
struct FixedLeaf {
    static void serialize(BinaryStream &stream, const Leaf &value)
    {
        stream.write<T>(value.value);
    }

    static auto deserialize(BinaryReader &stream)
        -> std::expected<Leaf, std::error_code>
    {
        auto v = stream.read<T>();
        if (!v) return make_unexpected(v.error());
        return Leaf{*v};
    }
};

template <typename Leaf, typename T>
struct VarLeaf {
    static void serialize(BinaryStream &stream, const Leaf &value)
    {
        stream.writeVarInt<T>(value.value);
    }

    static auto deserialize(BinaryReader &stream)
        -> std::expected<Leaf, std::error_code>
    {
        auto v = stream.readVarInt<T>();
        if (!v) return make_unexpected(v.error());
        return Leaf{*v};
    }
};

template <typename Leaf, typename Element>
struct ArrayLeaf {
    static void serialize(BinaryStream &stream, const Leaf &value)
    {
        stream.writeVarInt<std::int32_t>(
            static_cast<std::int32_t>(value.values.size()));
        for (auto element : value.values) {
            Serializer<Element>::serialize(stream, Element{element});
        }
    }

    static auto deserialize(BinaryReader &stream)
        -> std::expected<Leaf, std::error_code>
    {
        auto count = stream.readVarInt<std::int32_t>();
        if (!count) return make_unexpected(count.error());
        Leaf out;
        for (std::int32_t i = 0; i < *count; ++i) {
            auto element = Serializer<Element>::deserialize(stream);
            if (!element) return make_unexpected(element.error());
            out.values.push_back(element->value);
        }
        return out;
    }
};

}  // namespace nbt_detail

template <>
struct Serializer<ByteTag> : nbt_detail::FixedLeaf<ByteTag, std::int8_t> {};
template <>
struct Serializer<ShortTag> : nbt_detail::FixedLeaf<ShortTag, std::int16_t> {};
template <>
struct Serializer<IntTag> : nbt_detail::VarLeaf<IntTag, std::int32_t> {};
template <>
struct Serializer<LongTag> : nbt_detail::VarLeaf<LongTag, std::int64_t> {};
template <>
struct Serializer<FloatTag> : nbt_detail::FixedLeaf<FloatTag, float> {};
template <>
struct Serializer<DoubleTag> : nbt_detail::FixedLeaf<DoubleTag, double> {};

template <>
struct Serializer<StringTag> {
    static void serialize(BinaryStream &stream, const StringTag &value)
    {
        stream.write(value.value);
    }

    static auto deserialize(BinaryReader &stream)
        -> std::expected<StringTag, std::error_code>
    {
        auto v = stream.read<std::string>();
        if (!v) return make_unexpected(v.error());
        return StringTag{std::move(*v)};
    }
};

template <>
struct Serializer<ByteArrayTag> : nbt_detail::ArrayLeaf<ByteArrayTag, ByteTag> {};
template <>
struct Serializer<IntArrayTag> : nbt_detail::ArrayLeaf<IntArrayTag, IntTag> {};
template <>
struct Serializer<LongArrayTag> : nbt_detail::ArrayLeaf<LongArrayTag, LongTag> {};

namespace nbt_detail {

void writePayload(BinaryStream &stream, const Tag &tag);
void writeCompound(BinaryStream &stream, const CompoundTag &tag);
void writeList(BinaryStream &stream, const ListTag &tag);
std::error_code readPayload(BinaryReader &stream, int tag_id, Tag &out);
std::error_code readCompound(BinaryReader &stream, CompoundTag &out);
std::error_code readList(BinaryReader &stream, ListTag &out);

inline void writePayload(BinaryStream &stream, const Tag &tag)
{
    switch (tag.value.index()) {
    case 0: Serializer<ByteTag>::serialize(stream, std::get<0>(tag.value)); break;
    case 1: Serializer<ShortTag>::serialize(stream, std::get<1>(tag.value)); break;
    case 2: Serializer<IntTag>::serialize(stream, std::get<2>(tag.value)); break;
    case 3: Serializer<LongTag>::serialize(stream, std::get<3>(tag.value)); break;
    case 4: Serializer<FloatTag>::serialize(stream, std::get<4>(tag.value)); break;
    case 5: Serializer<DoubleTag>::serialize(stream, std::get<5>(tag.value)); break;
    case 6: Serializer<ByteArrayTag>::serialize(stream, std::get<6>(tag.value)); break;
    case 7: Serializer<StringTag>::serialize(stream, std::get<7>(tag.value)); break;
    case 8: writeList(stream, std::get<8>(tag.value)); break;
    case 9: writeCompound(stream, std::get<9>(tag.value)); break;
    case 10: Serializer<IntArrayTag>::serialize(stream, std::get<10>(tag.value)); break;
    case 11: Serializer<LongArrayTag>::serialize(stream, std::get<11>(tag.value)); break;
    }
}

inline void writeCompound(BinaryStream &stream, const CompoundTag &tag)
{
    for (const auto &[name, child] : tag.entries) {
        stream.write<std::uint8_t>(static_cast<std::uint8_t>(child.value.index() + 1));
        stream.write(std::string_view{name});
        writePayload(stream, child);
    }
    stream.write<std::uint8_t>(0);  // TAG_End
}

inline void writeList(BinaryStream &stream, const ListTag &tag)
{
    const auto element_id = tag.elements.empty()
        ? std::uint8_t{0}
        : static_cast<std::uint8_t>(tag.elements.front().value.index() + 1);
    stream.write<std::uint8_t>(element_id);
    stream.writeVarInt<std::int32_t>(static_cast<std::int32_t>(tag.elements.size()));
    for (const auto &element : tag.elements) {
        writePayload(stream, element);
    }
}

template <typename T>
inline std::error_code readLeaf(BinaryReader &stream, Tag &out)
{
    auto value = Serializer<T>::deserialize(stream);
    if (!value) return value.error();
    out.value = *value;
    return {};
}

inline std::error_code readPayload(BinaryReader &stream, int tag_id, Tag &out)
{
    switch (tag_id) {
    case 1: return readLeaf<ByteTag>(stream, out);
    case 2: return readLeaf<ShortTag>(stream, out);
    case 3: return readLeaf<IntTag>(stream, out);
    case 4: return readLeaf<LongTag>(stream, out);
    case 5: return readLeaf<FloatTag>(stream, out);
    case 6: return readLeaf<DoubleTag>(stream, out);
    case 7: return readLeaf<ByteArrayTag>(stream, out);
    case 8: return readLeaf<StringTag>(stream, out);
    case 9: {
        ListTag list;
        if (auto error = readList(stream, list)) return error;
        out.value = std::move(list);
        return {};
    }
    case 10: {
        CompoundTag compound;
        if (auto error = readCompound(stream, compound)) return error;
        out.value = std::move(compound);
        return {};
    }
    case 11: return readLeaf<IntArrayTag>(stream, out);
    case 12: return readLeaf<LongArrayTag>(stream, out);
    default: return std::make_error_code(std::errc::illegal_byte_sequence);
    }
}

inline std::error_code readCompound(BinaryReader &stream, CompoundTag &out)
{
    for (;;) {
        auto tag_id = stream.read<std::uint8_t>();
        if (!tag_id) return tag_id.error();
        if (*tag_id == 0) return {};  // TAG_End
        auto name = stream.read<std::string>();
        if (!name) return name.error();
        Tag child;
        if (auto error = readPayload(stream, *tag_id, child)) return error;
        out.entries.emplace_back(std::move(*name), std::move(child));
    }
}

inline std::error_code readList(BinaryReader &stream, ListTag &out)
{
    auto element_id = stream.read<std::uint8_t>();
    if (!element_id) return element_id.error();
    auto count = stream.readVarInt<std::int32_t>();
    if (!count) return count.error();
    for (std::int32_t i = 0; i < *count; ++i) {
        Tag element;
        if (auto error = readPayload(stream, *element_id, element)) return error;
        out.elements.push_back(std::move(element));
    }
    return {};
}

}  // namespace nbt_detail

// A CompoundTag packet field is a root compound: tag id 10, an empty name,
// then the entries, then TAG_End.
template <>
struct Serializer<CompoundTag> {
    static void serialize(BinaryStream &stream, const CompoundTag &value)
    {
        stream.write<std::uint8_t>(10);
        stream.write(std::string_view{});
        nbt_detail::writeCompound(stream, value);
    }

    static auto deserialize(BinaryReader &stream)
        -> std::expected<CompoundTag, std::error_code>
    {
        auto tag_id = stream.read<std::uint8_t>();
        if (!tag_id) return make_unexpected(tag_id.error());
        if (*tag_id != 10) {
            return make_unexpected(std::make_error_code(std::errc::illegal_byte_sequence));
        }
        auto name = stream.read<std::string>();
        if (!name) return make_unexpected(name.error());
        CompoundTag out;
        if (auto error = nbt_detail::readCompound(stream, out)) {
            return make_unexpected(error);
        }
        return out;
    }
};

}  // namespace bedrock::protocol
