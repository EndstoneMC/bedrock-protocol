// Bedrock::DDUI data-store value (cereal::DynamicValue), the recursive,
// self-describing value the DataStore packets carry. Each value is a 4-byte
// little-endian type tag followed by a payload selected by the tag; the Array
// and Object arms recurse into the value itself, so the codec is hand-written
// here rather than emitted by the DSL.
//
// Type tags and wire forms (confirmed against the BDS cereal schema loader and
// gophertunnel): Null(0) -> nothing, Boolean(1) -> 1 byte, Integer(2) -> int64
// LE, Number(3) -> double LE, String(4) -> varuint32 length + bytes, Array(5)
// -> varuint32 count + values, Object(6) -> varuint32 count + (string, value).
#pragma once

#include <cstdint>
#include <map>
#include <string>
#include <system_error>
#include <type_traits>
#include <utility>
#include <variant>
#include <vector>

#include "expected.hpp"
#include "serializer.hpp"
#include "stream.hpp"

namespace bedrock::protocol {

class DynamicValue;

namespace ddui {

// cereal::DynamicValue::Type. A DynamicValue's variant index is exactly this
// value, so the tag and the index never need translating.
enum class ValueType : std::uint32_t {
    Null = 0,
    Boolean = 1,
    Integer = 2,
    Number = 3,
    String = 4,
    Array = 5,
    Object = 6,
};

// The empty alternative a null DynamicValue holds.
struct NullType {
    friend bool operator==(NullType, NullType) noexcept { return true; }
    friend bool operator!=(NullType, NullType) noexcept { return false; }
};

}  // namespace ddui

// A single DDUI data-store value of any type. Default-constructs to Null.
// Object iterates by sorted key, matching CompoundTag, so serialization is
// deterministic.
class DynamicValue {
public:
    using Array = std::vector<DynamicValue>;
    using Object = std::map<std::string, DynamicValue>;
    using Storage = std::variant<ddui::NullType, bool, std::int64_t, double,
                                 std::string, Array, Object>;

    DynamicValue() noexcept : storage_(ddui::NullType{}) {}
    DynamicValue(ddui::NullType) noexcept : storage_(ddui::NullType{}) {}
    DynamicValue(bool v) : storage_(v) {}
    DynamicValue(std::int64_t v) : storage_(v) {}
    DynamicValue(double v) : storage_(v) {}
    DynamicValue(std::string v) : storage_(std::move(v)) {}
    DynamicValue(const char *v) : storage_(std::string(v)) {}
    DynamicValue(Array v) : storage_(std::move(v)) {}
    DynamicValue(Object v) : storage_(std::move(v)) {}

    [[nodiscard]] ddui::ValueType type() const noexcept
    {
        return static_cast<ddui::ValueType>(storage_.index());
    }

    template <typename T>
    [[nodiscard]] bool is() const noexcept
    {
        return std::holds_alternative<T>(storage_);
    }
    template <typename T>
    [[nodiscard]] T &get()
    {
        return std::get<T>(storage_);
    }
    template <typename T>
    [[nodiscard]] const T &get() const
    {
        return std::get<T>(storage_);
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

    friend bool operator==(const DynamicValue &a, const DynamicValue &b) noexcept
    {
        return a.storage_ == b.storage_;
    }
    friend bool operator!=(const DynamicValue &a, const DynamicValue &b) noexcept
    {
        return !(a == b);
    }

private:
    Storage storage_;
};

template <>
struct Serializer<DynamicValue> {
    static void serialize(BinaryStream &stream, const DynamicValue &value)
    {
        stream.write<std::uint32_t>(static_cast<std::uint32_t>(value.type()));
        value.visit([&](const auto &payload) {
            using V = std::decay_t<decltype(payload)>;
            if constexpr (std::is_same_v<V, ddui::NullType>) {
                // Null: no payload.
            }
            else if constexpr (std::is_same_v<V, bool>) {
                stream.write<bool>(payload);
            }
            else if constexpr (std::is_same_v<V, std::int64_t>) {
                stream.write<std::int64_t>(payload);
            }
            else if constexpr (std::is_same_v<V, double>) {
                stream.write<double>(payload);
            }
            else if constexpr (std::is_same_v<V, std::string>) {
                stream.write(payload);
            }
            else if constexpr (std::is_same_v<V, DynamicValue::Array>) {
                stream.writeVarInt<std::uint32_t>(payload.size());
                for (const auto &element : payload) {
                    serialize(stream, element);
                }
            }
            else if constexpr (std::is_same_v<V, DynamicValue::Object>) {
                stream.writeVarInt<std::uint32_t>(payload.size());
                for (const auto &[key, child] : payload) {
                    stream.write(key);
                    serialize(stream, child);
                }
            }
        });
    }

    static auto deserialize(BinaryReader &stream)
        -> std::expected<DynamicValue, std::error_code>
    {
        auto tag = stream.read<std::uint32_t>();
        if (!tag) return make_unexpected(tag.error());
        switch (static_cast<ddui::ValueType>(*tag)) {
        case ddui::ValueType::Null:
            return DynamicValue{};
        case ddui::ValueType::Boolean: {
            auto v = stream.read<bool>();
            if (!v) return make_unexpected(v.error());
            return DynamicValue{*v};
        }
        case ddui::ValueType::Integer: {
            auto v = stream.read<std::int64_t>();
            if (!v) return make_unexpected(v.error());
            return DynamicValue{*v};
        }
        case ddui::ValueType::Number: {
            auto v = stream.read<double>();
            if (!v) return make_unexpected(v.error());
            return DynamicValue{*v};
        }
        case ddui::ValueType::String: {
            auto v = stream.read<std::string>();
            if (!v) return make_unexpected(v.error());
            return DynamicValue{std::move(*v)};
        }
        case ddui::ValueType::Array: {
            auto count = stream.readVarInt<std::uint32_t>();
            if (!count) return make_unexpected(count.error());
            DynamicValue::Array out;
            for (std::uint32_t i = 0; i < *count; ++i) {
                auto element = deserialize(stream);
                if (!element) return make_unexpected(element.error());
                out.push_back(std::move(*element));
            }
            return DynamicValue{std::move(out)};
        }
        case ddui::ValueType::Object: {
            auto count = stream.readVarInt<std::uint32_t>();
            if (!count) return make_unexpected(count.error());
            DynamicValue::Object out;
            for (std::uint32_t i = 0; i < *count; ++i) {
                auto key = stream.read<std::string>();
                if (!key) return make_unexpected(key.error());
                auto child = deserialize(stream);
                if (!child) return make_unexpected(child.error());
                out.emplace(std::move(*key), std::move(*child));
            }
            return DynamicValue{std::move(out)};
        }
        }
        return make_unexpected(std::make_error_code(std::errc::illegal_byte_sequence));
    }
};

}  // namespace bedrock::protocol
