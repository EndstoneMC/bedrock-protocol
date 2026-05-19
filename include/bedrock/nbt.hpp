// NBT (Named Binary Tag), the network-little-endian variant Bedrock uses on
// the wire. The tag types model an in-memory tree: ValueTag/ArrayTag leaves,
// the homogeneous ListTag, the CompoundTag map, and the Tag variant over all
// of them. The four codec functions in namespace nbt move that tree on and
// off a stream -- writeTag/readTag for a bare payload, writeNamedTag/
// readNamedTag for the [type][name][payload] form a CompoundTag entry takes.
#pragma once

#include <cstddef>
#include <cstdint>
#include <initializer_list>
#include <map>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>
#include <type_traits>
#include <utility>
#include <variant>
#include <vector>

#include "expected.hpp"
#include "serializer.hpp"
#include "stream.hpp"

namespace bedrock::protocol {

namespace nbt {

// Tag ids as they travel on the wire. A Tag's variant index is exactly this
// value, so the id and the index never need translating.
enum class Type : std::uint8_t {
    End = 0,
    Byte = 1,
    Short = 2,
    Int = 3,
    Long = 4,
    Float = 5,
    Double = 6,
    ByteArray = 7,
    String = 8,
    List = 9,
    Compound = 10,
    IntArray = 11,
    LongArray = 12,
};

// A leaf tag carrying a single scalar or string payload.
template <typename T>
class ValueTag {
public:
    using value_type = T;

    constexpr ValueTag() = default;
    constexpr explicit ValueTag(const T &v) : value_(v) {}
    constexpr explicit ValueTag(T &&v) : value_(std::move(v)) {}

    constexpr operator const T &() const noexcept { return value_; }

    [[nodiscard]] constexpr const T &value() const noexcept { return value_; }

    friend constexpr bool operator==(const ValueTag &a, const ValueTag &b) noexcept
    {
        return a.value_ == b.value_;
    }
    friend constexpr bool operator!=(const ValueTag &a, const ValueTag &b) noexcept
    {
        return !(a == b);
    }
    friend constexpr bool operator==(const ValueTag &a, const T &b) noexcept
    {
        return a.value_ == b;
    }
    friend constexpr bool operator==(const T &a, const ValueTag &b) noexcept
    {
        return a == b.value_;
    }
    friend constexpr bool operator!=(const ValueTag &a, const T &b) noexcept
    {
        return !(a == b);
    }
    friend constexpr bool operator!=(const T &a, const ValueTag &b) noexcept
    {
        return !(a == b);
    }

private:
    T value_{};
};

// A leaf tag carrying a length-prefixed array of a scalar type.
template <typename T>
class ArrayTag {
public:
    using value_type = T;
    using size_type = std::size_t;
    using storage_type = std::vector<value_type>;
    using iterator = typename storage_type::iterator;
    using const_iterator = typename storage_type::const_iterator;

    ArrayTag() = default;
    explicit ArrayTag(storage_type v) : v_(std::move(v)) {}
    template <typename It>
    ArrayTag(It first, It last) : v_(first, last) {}
    ArrayTag(std::initializer_list<value_type> init) : v_(init) {}

    [[nodiscard]] bool empty() const noexcept { return v_.empty(); }
    [[nodiscard]] size_type size() const noexcept { return v_.size(); }
    void clear() noexcept { v_.clear(); }

    value_type &at(size_type i) { return v_.at(i); }
    const value_type &at(size_type i) const { return v_.at(i); }
    value_type &operator[](size_type i) { return v_[i]; }
    const value_type &operator[](size_type i) const { return v_[i]; }
    value_type *data() noexcept { return v_.data(); }
    const value_type *data() const noexcept { return v_.data(); }

    void push_back(value_type v) { v_.push_back(v); }
    template <typename It>
    void assign(It first, It last) { v_.assign(first, last); }
    iterator insert(const_iterator pos, value_type v) { return v_.insert(pos, v); }
    iterator erase(const_iterator pos) { return v_.erase(pos); }

    iterator begin() noexcept { return v_.begin(); }
    iterator end() noexcept { return v_.end(); }
    const_iterator begin() const noexcept { return v_.begin(); }
    const_iterator end() const noexcept { return v_.end(); }
    const_iterator cbegin() const noexcept { return v_.cbegin(); }
    const_iterator cend() const noexcept { return v_.cend(); }

    friend bool operator==(const ArrayTag &a, const ArrayTag &b) noexcept
    {
        return a.v_ == b.v_;
    }
    friend bool operator!=(const ArrayTag &a, const ArrayTag &b) noexcept
    {
        return !(a == b);
    }

private:
    storage_type v_;
};

}  // namespace nbt

using ByteTag = nbt::ValueTag<std::int8_t>;
using ShortTag = nbt::ValueTag<std::int16_t>;
using IntTag = nbt::ValueTag<std::int32_t>;
using LongTag = nbt::ValueTag<std::int64_t>;
using FloatTag = nbt::ValueTag<float>;
using DoubleTag = nbt::ValueTag<double>;
using StringTag = nbt::ValueTag<std::string>;
using ByteArrayTag = nbt::ArrayTag<std::int8_t>;
using IntArrayTag = nbt::ArrayTag<std::int32_t>;
using LongArrayTag = nbt::ArrayTag<std::int64_t>;

class Tag;

// A homogeneous, ordered sequence of tags. The first element appended fixes
// the element type that every later element must match. Its methods are
// defined out of line, below Tag, since they construct the still-incomplete Tag.
class ListTag {
public:
    using value_type = Tag;
    using size_type = std::size_t;
    using container_type = std::vector<value_type>;
    using iterator = container_type::iterator;
    using const_iterator = container_type::const_iterator;

    ListTag() = default;
    template <typename T>
        requires(!std::is_same_v<std::remove_cvref_t<T>, Tag>)
    ListTag(std::initializer_list<T> init);

    [[nodiscard]] bool empty() const noexcept;
    [[nodiscard]] size_type size() const noexcept;
    [[nodiscard]] nbt::Type type() const noexcept;

    value_type &at(size_type i);
    [[nodiscard]] const value_type &at(size_type i) const;
    value_type &operator[](size_type i);
    const value_type &operator[](size_type i) const;

    void clear() noexcept;
    void push_back(const value_type &v);
    void push_back(value_type &&v);
    template <typename... Args>
    value_type &emplace_back(Args &&...args);
    iterator erase(const_iterator pos);
    iterator erase(const_iterator first, const_iterator last);

    iterator begin() noexcept;
    iterator end() noexcept;
    [[nodiscard]] const_iterator begin() const noexcept;
    [[nodiscard]] const_iterator end() const noexcept;
    [[nodiscard]] const_iterator cbegin() const noexcept;
    [[nodiscard]] const_iterator cend() const noexcept;

    friend bool operator==(const ListTag &a, const ListTag &b) noexcept;
    friend bool operator!=(const ListTag &a, const ListTag &b) noexcept;

private:
    nbt::Type type_{nbt::Type::End};
    container_type elements_;
};

// An ordered map from name to tag. Iteration visits entries by sorted key.
// Like ListTag, its methods are defined out of line, below Tag.
class CompoundTag {
public:
    using key_type = std::string;
    using mapped_type = Tag;
    using map_type = std::map<key_type, mapped_type>;
    using value_type = map_type::value_type;
    using size_type = std::size_t;
    using iterator = map_type::iterator;
    using const_iterator = map_type::const_iterator;

    CompoundTag() = default;
    CompoundTag(std::initializer_list<std::pair<const key_type, mapped_type>> init);

    [[nodiscard]] bool empty() const noexcept;
    [[nodiscard]] size_type size() const noexcept;

    mapped_type &at(const key_type &key);
    [[nodiscard]] const mapped_type &at(const key_type &key) const;
    mapped_type &operator[](const key_type &key);
    [[nodiscard]] bool contains(const key_type &key) const noexcept;
    iterator find(const key_type &key) noexcept;
    [[nodiscard]] const_iterator find(const key_type &key) const noexcept;

    void clear() noexcept;
    template <typename P>
    std::pair<iterator, bool> insert(P &&v);
    template <typename... Args>
    std::pair<iterator, bool> emplace(Args &&...args);
    template <typename... Args>
    std::pair<iterator, bool> try_emplace(const key_type &key, Args &&...args);
    template <typename M>
    std::pair<iterator, bool> insert_or_assign(const key_type &key, M &&obj);
    iterator erase(const_iterator pos);
    size_type erase(const key_type &key);
    iterator erase(const_iterator first, const_iterator last);
    void swap(CompoundTag &other) noexcept;
    void merge(const CompoundTag &source);

    iterator begin() noexcept;
    iterator end() noexcept;
    [[nodiscard]] const_iterator begin() const noexcept;
    [[nodiscard]] const_iterator end() const noexcept;
    [[nodiscard]] const_iterator cbegin() const noexcept;
    [[nodiscard]] const_iterator cend() const noexcept;

    friend bool operator==(const CompoundTag &a, const CompoundTag &b) noexcept;
    friend bool operator!=(const CompoundTag &a, const CompoundTag &b) noexcept;

private:
    map_type entries_;
};

// A single NBT tag of any type. Default-constructs to an empty (End) tag.
class Tag {
public:
    using Storage =
        std::variant<std::monostate, ByteTag, ShortTag, IntTag, LongTag,
                     FloatTag, DoubleTag, ByteArrayTag, StringTag, ListTag,
                     CompoundTag, IntArrayTag, LongArrayTag>;

    Tag() noexcept : storage_(std::monostate{}) {}
    Tag(const ByteTag &v) : storage_(v) {}
    Tag(ByteTag &&v) : storage_(std::move(v)) {}
    Tag(const ShortTag &v) : storage_(v) {}
    Tag(ShortTag &&v) : storage_(std::move(v)) {}
    Tag(const IntTag &v) : storage_(v) {}
    Tag(IntTag &&v) : storage_(std::move(v)) {}
    Tag(const LongTag &v) : storage_(v) {}
    Tag(LongTag &&v) : storage_(std::move(v)) {}
    Tag(const FloatTag &v) : storage_(v) {}
    Tag(FloatTag &&v) : storage_(std::move(v)) {}
    Tag(const DoubleTag &v) : storage_(v) {}
    Tag(DoubleTag &&v) : storage_(std::move(v)) {}
    Tag(const ByteArrayTag &v) : storage_(v) {}
    Tag(ByteArrayTag &&v) : storage_(std::move(v)) {}
    Tag(const StringTag &v) : storage_(v) {}
    Tag(StringTag &&v) : storage_(std::move(v)) {}
    Tag(const ListTag &v) : storage_(v) {}
    Tag(ListTag &&v) : storage_(std::move(v)) {}
    Tag(const CompoundTag &v) : storage_(v) {}
    Tag(CompoundTag &&v) : storage_(std::move(v)) {}
    Tag(const IntArrayTag &v) : storage_(v) {}
    Tag(IntArrayTag &&v) : storage_(std::move(v)) {}
    Tag(const LongArrayTag &v) : storage_(v) {}
    Tag(LongArrayTag &&v) : storage_(std::move(v)) {}

    [[nodiscard]] nbt::Type type() const noexcept
    {
        return static_cast<nbt::Type>(storage_.index());
    }

    [[nodiscard]] std::size_t size() const noexcept
    {
        return std::visit(
            [](const auto &payload) -> std::size_t {
                using V = std::decay_t<decltype(payload)>;
                if constexpr (std::is_same_v<V, std::monostate>) {
                    return 0;
                }
                else if constexpr (std::is_same_v<V, ListTag> ||
                                   std::is_same_v<V, CompoundTag> ||
                                   std::is_same_v<V, ByteArrayTag> ||
                                   std::is_same_v<V, IntArrayTag> ||
                                   std::is_same_v<V, LongArrayTag>) {
                    return payload.size();
                }
                else {
                    return 1;
                }
            },
            storage_);
    }

    [[nodiscard]] bool empty() const noexcept { return size() == 0; }

    Tag &operator[](const std::string &key)
    {
        if (std::holds_alternative<std::monostate>(storage_)) {
            storage_.emplace<CompoundTag>();
        }
        auto *compound = std::get_if<CompoundTag>(&storage_);
        if (compound == nullptr) {
            throw std::runtime_error("Tag::operator[](key) requires a CompoundTag");
        }
        return (*compound)[key];
    }

    Tag &operator[](std::size_t index)
    {
        if (std::holds_alternative<std::monostate>(storage_)) {
            storage_.emplace<ListTag>();
        }
        auto *list = std::get_if<ListTag>(&storage_);
        if (list == nullptr) {
            throw std::runtime_error("Tag::operator[](index) requires a ListTag");
        }
        return (*list)[index];
    }

    Tag &at(const std::string &key)
    {
        auto *compound = std::get_if<CompoundTag>(&storage_);
        if (compound == nullptr) {
            throw std::runtime_error("Tag::at(key) requires a CompoundTag");
        }
        return compound->at(key);
    }

    [[nodiscard]] const Tag &at(const std::string &key) const
    {
        const auto *compound = std::get_if<CompoundTag>(&storage_);
        if (compound == nullptr) {
            throw std::runtime_error("Tag::at(key) requires a CompoundTag");
        }
        return compound->at(key);
    }

    Tag &at(std::size_t index)
    {
        auto *list = std::get_if<ListTag>(&storage_);
        if (list == nullptr) {
            throw std::runtime_error("Tag::at(index) requires a ListTag");
        }
        return list->at(index);
    }

    [[nodiscard]] const Tag &at(std::size_t index) const
    {
        const auto *list = std::get_if<ListTag>(&storage_);
        if (list == nullptr) {
            throw std::runtime_error("Tag::at(index) requires a ListTag");
        }
        return list->at(index);
    }

    [[nodiscard]] bool contains(const std::string &key) const noexcept
    {
        const auto *compound = std::get_if<CompoundTag>(&storage_);
        return compound != nullptr && compound->contains(key);
    }

    template <typename... Args>
    ListTag &emplace_back(Args &&...args)
    {
        if (std::holds_alternative<std::monostate>(storage_)) {
            storage_.emplace<ListTag>();
        }
        auto *list = std::get_if<ListTag>(&storage_);
        if (list == nullptr) {
            throw std::runtime_error("Tag::emplace_back requires a ListTag");
        }
        list->emplace_back(std::forward<Args>(args)...);
        return *list;
    }

    template <typename... Args>
    std::pair<CompoundTag::iterator, bool> emplace(Args &&...args)
    {
        if (std::holds_alternative<std::monostate>(storage_)) {
            storage_.emplace<CompoundTag>();
        }
        auto *compound = std::get_if<CompoundTag>(&storage_);
        if (compound == nullptr) {
            throw std::runtime_error("Tag::emplace requires a CompoundTag");
        }
        return compound->emplace(std::forward<Args>(args)...);
    }

    template <typename T>
    [[nodiscard]] T &get()
    {
        if (auto *p = std::get_if<T>(&storage_)) {
            return *p;
        }
        throw std::runtime_error("Tag::get<T>(): tag holds a different type");
    }

    template <typename T>
    [[nodiscard]] const T &get() const
    {
        if (const auto *p = std::get_if<T>(&storage_)) {
            return *p;
        }
        throw std::runtime_error("Tag::get<T>(): tag holds a different type");
    }

    template <typename T>
    [[nodiscard]] T *get_if() noexcept
    {
        return std::get_if<T>(&storage_);
    }

    template <typename T>
    [[nodiscard]] const T *get_if() const noexcept
    {
        return std::get_if<T>(&storage_);
    }

    template <typename Fn>
    decltype(auto) visit(Fn &&fn) &
    {
        return std::visit(std::forward<Fn>(fn), storage_);
    }

    template <typename Fn>
    decltype(auto) visit(Fn &&fn) const &
    {
        return std::visit(std::forward<Fn>(fn), storage_);
    }

    friend bool operator==(const Tag &a, const Tag &b) noexcept
    {
        return a.storage_ == b.storage_;
    }
    friend bool operator!=(const Tag &a, const Tag &b) noexcept
    {
        return !(a == b);
    }

private:
    Storage storage_;
};

// --- ListTag ---

template <typename T>
    requires(!std::is_same_v<std::remove_cvref_t<T>, Tag>)
ListTag::ListTag(std::initializer_list<T> init)
{
    for (const auto &item : init) {
        emplace_back(item);
    }
}

inline bool ListTag::empty() const noexcept { return elements_.empty(); }

inline ListTag::size_type ListTag::size() const noexcept { return elements_.size(); }

inline nbt::Type ListTag::type() const noexcept { return type_; }

inline ListTag::value_type &ListTag::at(size_type i) { return elements_.at(i); }

inline const ListTag::value_type &ListTag::at(size_type i) const
{
    return elements_.at(i);
}

inline ListTag::value_type &ListTag::operator[](size_type i) { return elements_[i]; }

inline const ListTag::value_type &ListTag::operator[](size_type i) const
{
    return elements_[i];
}

inline void ListTag::clear() noexcept
{
    elements_.clear();
    type_ = nbt::Type::End;
}

inline void ListTag::push_back(const value_type &v) { emplace_back(v); }

inline void ListTag::push_back(value_type &&v) { emplace_back(std::move(v)); }

template <typename... Args>
ListTag::value_type &ListTag::emplace_back(Args &&...args)
{
    value_type v(std::forward<Args>(args)...);
    const auto t = v.type();
    if (t == nbt::Type::End) {
        throw std::invalid_argument("ListTag cannot hold End tags");
    }
    if (type_ == nbt::Type::End) {
        type_ = t;
    }
    else if (t != type_) {
        throw std::invalid_argument("ListTag elements must all share one type");
    }
    return elements_.emplace_back(std::move(v));
}

inline ListTag::iterator ListTag::erase(const_iterator pos)
{
    return elements_.erase(pos);
}

inline ListTag::iterator ListTag::erase(const_iterator first, const_iterator last)
{
    return elements_.erase(first, last);
}

inline ListTag::iterator ListTag::begin() noexcept { return elements_.begin(); }
inline ListTag::iterator ListTag::end() noexcept { return elements_.end(); }
inline ListTag::const_iterator ListTag::begin() const noexcept
{
    return elements_.begin();
}
inline ListTag::const_iterator ListTag::end() const noexcept
{
    return elements_.end();
}
inline ListTag::const_iterator ListTag::cbegin() const noexcept
{
    return elements_.cbegin();
}
inline ListTag::const_iterator ListTag::cend() const noexcept
{
    return elements_.cend();
}

inline bool operator==(const ListTag &a, const ListTag &b) noexcept
{
    return a.elements_ == b.elements_;
}
inline bool operator!=(const ListTag &a, const ListTag &b) noexcept
{
    return !(a == b);
}

// --- CompoundTag ---

inline CompoundTag::CompoundTag(
    std::initializer_list<std::pair<const key_type, mapped_type>> init)
    : entries_(init)
{
}

inline bool CompoundTag::empty() const noexcept { return entries_.empty(); }

inline CompoundTag::size_type CompoundTag::size() const noexcept
{
    return entries_.size();
}

inline CompoundTag::mapped_type &CompoundTag::at(const key_type &key)
{
    return entries_.at(key);
}

inline const CompoundTag::mapped_type &CompoundTag::at(const key_type &key) const
{
    return entries_.at(key);
}

inline CompoundTag::mapped_type &CompoundTag::operator[](const key_type &key)
{
    return entries_[key];
}

inline bool CompoundTag::contains(const key_type &key) const noexcept
{
    return entries_.contains(key);
}

inline CompoundTag::iterator CompoundTag::find(const key_type &key) noexcept
{
    return entries_.find(key);
}

inline CompoundTag::const_iterator CompoundTag::find(const key_type &key) const noexcept
{
    return entries_.find(key);
}

inline void CompoundTag::clear() noexcept { entries_.clear(); }

template <typename P>
std::pair<CompoundTag::iterator, bool> CompoundTag::insert(P &&v)
{
    return entries_.insert(std::forward<P>(v));
}

template <typename... Args>
std::pair<CompoundTag::iterator, bool> CompoundTag::emplace(Args &&...args)
{
    return entries_.emplace(std::forward<Args>(args)...);
}

template <typename... Args>
std::pair<CompoundTag::iterator, bool> CompoundTag::try_emplace(
    const key_type &key, Args &&...args)
{
    return entries_.try_emplace(key, std::forward<Args>(args)...);
}

template <typename M>
std::pair<CompoundTag::iterator, bool> CompoundTag::insert_or_assign(
    const key_type &key, M &&obj)
{
    return entries_.insert_or_assign(key, std::forward<M>(obj));
}

inline CompoundTag::iterator CompoundTag::erase(const_iterator pos)
{
    return entries_.erase(pos);
}

inline CompoundTag::size_type CompoundTag::erase(const key_type &key)
{
    return entries_.erase(key);
}

inline CompoundTag::iterator CompoundTag::erase(const_iterator first,
                                                const_iterator last)
{
    return entries_.erase(first, last);
}

inline void CompoundTag::swap(CompoundTag &other) noexcept
{
    entries_.swap(other.entries_);
}

inline void CompoundTag::merge(const CompoundTag &source)
{
    for (const auto &[key, value] : source.entries_) {
        entries_.try_emplace(key, value);
    }
}

inline CompoundTag::iterator CompoundTag::begin() noexcept { return entries_.begin(); }
inline CompoundTag::iterator CompoundTag::end() noexcept { return entries_.end(); }
inline CompoundTag::const_iterator CompoundTag::begin() const noexcept
{
    return entries_.begin();
}
inline CompoundTag::const_iterator CompoundTag::end() const noexcept
{
    return entries_.end();
}
inline CompoundTag::const_iterator CompoundTag::cbegin() const noexcept
{
    return entries_.cbegin();
}
inline CompoundTag::const_iterator CompoundTag::cend() const noexcept
{
    return entries_.cend();
}

inline bool operator==(const CompoundTag &a, const CompoundTag &b) noexcept
{
    return a.entries_ == b.entries_;
}
inline bool operator!=(const CompoundTag &a, const CompoundTag &b) noexcept
{
    return !(a == b);
}

// --- codec ---

namespace nbt {

void writeTag(BinaryStream &stream, const Tag &tag);
std::expected<Tag, std::error_code> readTag(BinaryReader &stream, Type type);
void writeNamedTag(BinaryStream &stream, std::string_view name, const Tag &tag);
std::expected<std::pair<std::string, Tag>, std::error_code> readNamedTag(
    BinaryReader &stream);

// Write a tag's payload only -- no id, no name, just the bytes the value
// occupies. An End tag writes nothing.
inline void writeTag(BinaryStream &stream, const Tag &tag)
{
    tag.visit([&](const auto &payload) {
        using V = std::decay_t<decltype(payload)>;
        if constexpr (std::is_same_v<V, std::monostate>) {
            // End: no payload.
        }
        else if constexpr (std::is_same_v<V, ByteTag>) {
            stream.write<std::int8_t>(payload.value());
        }
        else if constexpr (std::is_same_v<V, ShortTag>) {
            stream.write<std::int16_t>(payload.value());
        }
        else if constexpr (std::is_same_v<V, IntTag>) {
            stream.writeVarInt<std::int32_t>(payload.value());
        }
        else if constexpr (std::is_same_v<V, LongTag>) {
            stream.writeVarInt<std::int64_t>(payload.value());
        }
        else if constexpr (std::is_same_v<V, FloatTag>) {
            stream.write<float>(payload.value());
        }
        else if constexpr (std::is_same_v<V, DoubleTag>) {
            stream.write<double>(payload.value());
        }
        else if constexpr (std::is_same_v<V, StringTag>) {
            stream.write(payload.value());
        }
        else if constexpr (std::is_same_v<V, ByteArrayTag>) {
            stream.writeVarInt<std::int32_t>(
                static_cast<std::int32_t>(payload.size()));
            for (auto element : payload) {
                stream.write<std::int8_t>(element);
            }
        }
        else if constexpr (std::is_same_v<V, IntArrayTag>) {
            stream.writeVarInt<std::int32_t>(
                static_cast<std::int32_t>(payload.size()));
            for (auto element : payload) {
                stream.writeVarInt<std::int32_t>(element);
            }
        }
        else if constexpr (std::is_same_v<V, LongArrayTag>) {
            stream.writeVarInt<std::int32_t>(
                static_cast<std::int32_t>(payload.size()));
            for (auto element : payload) {
                stream.writeVarInt<std::int64_t>(element);
            }
        }
        else if constexpr (std::is_same_v<V, ListTag>) {
            stream.write<std::uint8_t>(static_cast<std::uint8_t>(payload.type()));
            stream.writeVarInt<std::int32_t>(
                static_cast<std::int32_t>(payload.size()));
            for (const auto &element : payload) {
                writeTag(stream, element);
            }
        }
        else if constexpr (std::is_same_v<V, CompoundTag>) {
            for (const auto &[name, child] : payload) {
                writeNamedTag(stream, name, child);
            }
            stream.write<std::uint8_t>(0);  // TAG_End
        }
    });
}

// Read a payload of the given type, returning the tag it forms.
inline std::expected<Tag, std::error_code> readTag(BinaryReader &stream, Type type)
{
    switch (type) {
    case Type::End:
        return Tag{};
    case Type::Byte: {
        auto v = stream.read<std::int8_t>();
        if (!v) return make_unexpected(v.error());
        return Tag{ByteTag{*v}};
    }
    case Type::Short: {
        auto v = stream.read<std::int16_t>();
        if (!v) return make_unexpected(v.error());
        return Tag{ShortTag{*v}};
    }
    case Type::Int: {
        auto v = stream.readVarInt<std::int32_t>();
        if (!v) return make_unexpected(v.error());
        return Tag{IntTag{*v}};
    }
    case Type::Long: {
        auto v = stream.readVarInt<std::int64_t>();
        if (!v) return make_unexpected(v.error());
        return Tag{LongTag{*v}};
    }
    case Type::Float: {
        auto v = stream.read<float>();
        if (!v) return make_unexpected(v.error());
        return Tag{FloatTag{*v}};
    }
    case Type::Double: {
        auto v = stream.read<double>();
        if (!v) return make_unexpected(v.error());
        return Tag{DoubleTag{*v}};
    }
    case Type::String: {
        auto v = stream.read<std::string>();
        if (!v) return make_unexpected(v.error());
        return Tag{StringTag{std::move(*v)}};
    }
    case Type::ByteArray: {
        auto count = stream.readVarInt<std::int32_t>();
        if (!count) return make_unexpected(count.error());
        ByteArrayTag out;
        for (std::int32_t i = 0; i < *count; ++i) {
            auto element = stream.read<std::int8_t>();
            if (!element) return make_unexpected(element.error());
            out.push_back(*element);
        }
        return Tag{std::move(out)};
    }
    case Type::IntArray: {
        auto count = stream.readVarInt<std::int32_t>();
        if (!count) return make_unexpected(count.error());
        IntArrayTag out;
        for (std::int32_t i = 0; i < *count; ++i) {
            auto element = stream.readVarInt<std::int32_t>();
            if (!element) return make_unexpected(element.error());
            out.push_back(*element);
        }
        return Tag{std::move(out)};
    }
    case Type::LongArray: {
        auto count = stream.readVarInt<std::int32_t>();
        if (!count) return make_unexpected(count.error());
        LongArrayTag out;
        for (std::int32_t i = 0; i < *count; ++i) {
            auto element = stream.readVarInt<std::int64_t>();
            if (!element) return make_unexpected(element.error());
            out.push_back(*element);
        }
        return Tag{std::move(out)};
    }
    case Type::List: {
        auto element_type = stream.read<std::uint8_t>();
        if (!element_type) return make_unexpected(element_type.error());
        auto count = stream.readVarInt<std::int32_t>();
        if (!count) return make_unexpected(count.error());
        if (*element_type > static_cast<std::uint8_t>(Type::LongArray) ||
            (*count > 0 && *element_type == 0)) {
            return make_unexpected(
                std::make_error_code(std::errc::illegal_byte_sequence));
        }
        ListTag out;
        for (std::int32_t i = 0; i < *count; ++i) {
            auto element = readTag(stream, static_cast<Type>(*element_type));
            if (!element) return make_unexpected(element.error());
            out.push_back(std::move(*element));
        }
        return Tag{std::move(out)};
    }
    case Type::Compound: {
        CompoundTag out;
        for (;;) {
            auto entry = readNamedTag(stream);
            if (!entry) return make_unexpected(entry.error());
            if (entry->second.type() == Type::End) {
                break;  // TAG_End
            }
            out.emplace(std::move(entry->first), std::move(entry->second));
        }
        return Tag{std::move(out)};
    }
    }
    return make_unexpected(std::make_error_code(std::errc::illegal_byte_sequence));
}

// Write [type:uint8][name:string][payload]. An End tag writes a bare 0 byte,
// matching the terminator a CompoundTag ends with.
inline void writeNamedTag(BinaryStream &stream, std::string_view name,
                          const Tag &tag)
{
    const auto type = tag.type();
    stream.write<std::uint8_t>(static_cast<std::uint8_t>(type));
    if (type == Type::End) {
        return;
    }
    stream.write(name);
    writeTag(stream, tag);
}

// Read [type:uint8][name:string][payload]. A bare 0 byte yields an empty name
// and an End tag, so a CompoundTag reader can stop on it.
inline std::expected<std::pair<std::string, Tag>, std::error_code> readNamedTag(
    BinaryReader &stream)
{
    auto type = stream.read<std::uint8_t>();
    if (!type) return make_unexpected(type.error());
    if (*type == 0) {
        return std::pair<std::string, Tag>{};
    }
    if (*type > static_cast<std::uint8_t>(Type::LongArray)) {
        return make_unexpected(
            std::make_error_code(std::errc::illegal_byte_sequence));
    }
    auto name = stream.read<std::string>();
    if (!name) return make_unexpected(name.error());
    auto payload = readTag(stream, static_cast<Type>(*type));
    if (!payload) return make_unexpected(payload.error());
    return std::pair<std::string, Tag>{std::move(*name), std::move(*payload)};
}

}  // namespace nbt

// A CompoundTag packet field is a root compound: a named tag with an empty
// name carrying the compound payload.
template <>
struct Serializer<CompoundTag> {
    static void serialize(BinaryStream &stream, const CompoundTag &value)
    {
        nbt::writeNamedTag(stream, std::string_view{}, Tag{value});
    }

    static auto deserialize(BinaryReader &stream)
        -> std::expected<CompoundTag, std::error_code>
    {
        auto named = nbt::readNamedTag(stream);
        if (!named) return make_unexpected(named.error());
        auto *compound = named->second.get_if<CompoundTag>();
        if (compound == nullptr) {
            return make_unexpected(
                std::make_error_code(std::errc::illegal_byte_sequence));
        }
        return std::move(*compound);
    }
};

}  // namespace bedrock::protocol
