// cereal::DynamicValue, the recursive self-describing value a DDUI data-store
// change carries. Each value is a 4-byte little-endian type tag followed by a
// payload the tag selects; the array and object arms recurse into the value
// itself, which is why the codec is hand-written here rather than emitted.
#pragma once

#include <cstdint>
#include <expected>
#include <map>
#include <string>
#include <system_error>
#include <type_traits>
#include <utility>
#include <variant>
#include <vector>

#include <bedrock/protocol/serializer.hpp>
#include <bedrock/protocol/stream.hpp>

namespace bedrock::protocol {

class DynamicValue {
public:
    using Bool = bool;
    using Integer = std::int64_t;
    using Number = double;
    using String = std::string;
    using Array = std::vector<DynamicValue>;
    using Object = std::map<std::string, DynamicValue>;

    enum class Type : std::uint32_t {
        null = 0,
        boolean = 1,
        integer = 2,
        number = 3,
        string = 4,
        array = 5,
        object = 6,
    };

    using Storage = std::variant<std::monostate, Bool, Integer, Number, String, Array, Object>;

    DynamicValue() noexcept : storage_(std::monostate{}) {}
    DynamicValue(std::monostate) noexcept : storage_(std::monostate{}) {}
    DynamicValue(Bool v) : storage_(v) {}
    DynamicValue(Integer v) : storage_(v) {}
    DynamicValue(Number v) : storage_(v) {}
    DynamicValue(String v) : storage_(std::move(v)) {}
    DynamicValue(const char *v) : storage_(String{v}) {}
    DynamicValue(Array v) : storage_(std::move(v)) {}
    DynamicValue(Object v) : storage_(std::move(v)) {}

    [[nodiscard]] Type type() const noexcept { return static_cast<Type>(storage_.index()); }

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

    friend bool operator==(const DynamicValue &a, const DynamicValue &b) noexcept { return a.storage_ == b.storage_; }
    friend bool operator!=(const DynamicValue &a, const DynamicValue &b) noexcept { return !(a == b); }

private:
    Storage storage_;
};

template <>
struct Serializer<DynamicValue> {
    static void serialize(BinaryWriter &stream, const DynamicValue &value)
    {
        stream.write<std::uint32_t>(static_cast<std::uint32_t>(value.type()));
        value.visit([&](const auto &payload) {
            using V = std::decay_t<decltype(payload)>;
            if constexpr (std::is_same_v<V, std::monostate>) {
                // null: no payload.
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
            else if constexpr (std::is_same_v<V, DynamicValue::String>) {
                stream.write(payload);
            }
            else {
                stream.write<V>(payload);
            }
        });
    }

    static auto deserialize(BinaryReader &stream) -> std::expected<DynamicValue, std::error_code>
    {
        auto tag = stream.read<std::uint32_t>();
        if (!tag) {
            return std::unexpected(tag.error());
        }
        switch (static_cast<DynamicValue::Type>(*tag)) {
        case DynamicValue::Type::null:
            return DynamicValue{};
        case DynamicValue::Type::boolean: {
            auto v = stream.read<DynamicValue::Bool>();
            if (!v) {
                return std::unexpected(v.error());
            }
            return DynamicValue{*v};
        }
        case DynamicValue::Type::integer: {
            auto v = stream.read<DynamicValue::Integer>();
            if (!v) {
                return std::unexpected(v.error());
            }
            return DynamicValue{*v};
        }
        case DynamicValue::Type::number: {
            auto v = stream.read<DynamicValue::Number>();
            if (!v) {
                return std::unexpected(v.error());
            }
            return DynamicValue{*v};
        }
        case DynamicValue::Type::string: {
            auto v = stream.read<DynamicValue::String>();
            if (!v) {
                return std::unexpected(v.error());
            }
            return DynamicValue{std::move(*v)};
        }
        case DynamicValue::Type::array: {
            auto count = stream.readVarInt<std::uint32_t>();
            if (!count) {
                return std::unexpected(count.error());
            }
            DynamicValue::Array out;
            for (std::uint32_t i = 0; i < *count; ++i) {
                auto element = deserialize(stream);
                if (!element) {
                    return std::unexpected(element.error());
                }
                out.push_back(std::move(*element));
            }
            return DynamicValue{std::move(out)};
        }
        case DynamicValue::Type::object: {
            auto count = stream.readVarInt<std::uint32_t>();
            if (!count) {
                return std::unexpected(count.error());
            }
            DynamicValue::Object out;
            for (std::uint32_t i = 0; i < *count; ++i) {
                auto key = stream.read<std::string>();
                if (!key) {
                    return std::unexpected(key.error());
                }
                auto child = deserialize(stream);
                if (!child) {
                    return std::unexpected(child.error());
                }
                out.emplace(std::move(*key), std::move(*child));
            }
            return DynamicValue{std::move(out)};
        }
        }
        return std::unexpected(std::make_error_code(std::errc::illegal_byte_sequence));
    }
};

}  // namespace bedrock::protocol
