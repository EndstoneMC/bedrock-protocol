#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <utility>
#include <variant>
#include <vector>

#include <nanobind/nanobind.h>
#include <nanobind/operators.h>
#include <nanobind/stl/vector.h>

#include <bedrock/protocol/nbt.hpp>

#include "casters.hpp"
#include "module.hpp"

namespace nb = nanobind;
namespace bp = bedrock::protocol;

NAMESPACE_BEGIN(NB_NAMESPACE)
NAMESPACE_BEGIN(detail)

// A tag crosses as an instance of its own class; the empty tag is None.
template <>
struct type_caster<bp::Tag> {
    NB_TYPE_CASTER(bp::Tag, const_name("object"))

    bool from_python(handle src, uint8_t flags, cleanup_list *cleanup) noexcept
    {
        return try_as<bp::ByteTag, bp::ShortTag, bp::IntTag, bp::Int64Tag, bp::FloatTag, bp::DoubleTag,
                      bp::ByteArrayTag, bp::StringTag, bp::ListTag, bp::CompoundTag, bp::IntArrayTag>(src, flags,
                                                                                                       cleanup);
    }

    static handle from_cpp(const bp::Tag &value, rv_policy, cleanup_list *cleanup) noexcept
    {
        return value.visit([&](const auto &payload) -> handle {
            using V = std::decay_t<decltype(payload)>;
            if constexpr (std::is_same_v<V, std::monostate>) {
                return none().release();
            }
            else {
                return make_caster<V>::from_cpp(payload, rv_policy::copy, cleanup);
            }
        });
    }

private:
    template <typename... T>
    bool try_as(handle src, uint8_t flags, cleanup_list *cleanup) noexcept
    {
        if (src.is_none()) {
            value = bp::Tag{};
            return true;
        }
        return (try_one<T>(src, flags, cleanup) || ...);
    }

    template <typename T>
    bool try_one(handle src, uint8_t flags, cleanup_list *cleanup) noexcept
    {
        make_caster<T> caster;
        if (!caster.from_python(src, flags & ~static_cast<uint8_t>(cast_flags::convert), cleanup)) {
            return false;
        }
        value = bp::Tag{caster.operator cast_t<T>()};
        return true;
    }
};

NAMESPACE_END(detail)
NAMESPACE_END(NB_NAMESPACE)

namespace bedrock::protocol::python {

namespace {

template <typename T>
void bind_value_tag(nb::module_ &m, const char *name)
{
    using V = typename T::value_type;
    nb::class_<T>(m, name)
        .def(nb::init<V>(), nb::arg("value") = V{})
        .def_prop_ro("value", [](const T &self) { return self.value(); })
        .def(nb::self == nb::self)
        .def("__hash__", [](const T &self) { return nb::hash(nb::cast(self.value())); })
        .def("__repr__", [name](const T &self) {
            return std::string(name) + "(" + nb::repr(nb::cast(self.value())).c_str() + ")";
        });
}

template <typename T>
void bind_array_tag(nb::module_ &m, const char *name)
{
    using V = typename T::value_type;
    nb::class_<T>(m, name)
        .def(
            "__init__", [](T *self, const std::vector<V> &values) { new (self) T(values); },
            nb::arg("value") = std::vector<V>{})
        .def_prop_ro("value", [](const T &self) { return std::vector<V>(self.begin(), self.end()); })
        .def("__len__", &T::size)
        .def(nb::self == nb::self)
        .def("__repr__", [name](const T &self) {
            return std::string(name) + "(" +
                   nb::repr(nb::cast(std::vector<V>(self.begin(), self.end()))).c_str() + ")";
        });
}

}  // namespace

void bind_nbt(nb::module_ &parent)
{
    auto m = parent.def_submodule("nbt", "NBT tags, the network little-endian variant.");

    bind_value_tag<ByteTag>(m, "ByteTag");
    bind_value_tag<ShortTag>(m, "ShortTag");
    bind_value_tag<IntTag>(m, "IntTag");
    bind_value_tag<Int64Tag>(m, "Int64Tag");
    bind_value_tag<FloatTag>(m, "FloatTag");
    bind_value_tag<DoubleTag>(m, "DoubleTag");
    bind_value_tag<StringTag>(m, "StringTag");
    bind_array_tag<ByteArrayTag>(m, "ByteArrayTag");
    bind_array_tag<IntArrayTag>(m, "IntArrayTag");

    nb::class_<ListTag>(m, "ListTag")
        .def(
            "__init__",
            [](ListTag *self, const std::vector<Tag> &tags, int type) {
                if (type < 0 || type > static_cast<int>(nbt::Type::IntArray)) {
                    throw nb::value_error("ListTag type is not a tag type");
                }
                ListTag out(static_cast<nbt::Type>(type));
                for (const auto &tag : tags) {
                    out.push_back(tag);
                }
                new (self) ListTag(std::move(out));
            },
            nb::arg("tags") = std::vector<Tag>{}, nb::arg("type") = 0)
        .def_prop_ro("type", [](const ListTag &self) { return static_cast<int>(self.type()); })
        .def("__len__", &ListTag::size)
        .def("__getitem__",
             [](const ListTag &self, std::ptrdiff_t i) -> Tag {
                 const auto n = static_cast<std::ptrdiff_t>(self.size());
                 if (i < 0) {
                     i += n;
                 }
                 if (i < 0 || i >= n) {
                     throw nb::index_error("ListTag index out of range");
                 }
                 return self[static_cast<std::size_t>(i)];
             })
        .def("append", [](ListTag &self, const Tag &tag) { self.push_back(tag); })
        .def(nb::self == nb::self)
        .def("__repr__", [](const ListTag &self) {
            std::string out = "ListTag([";
            for (std::size_t i = 0; i < self.size(); ++i) {
                out += i ? ", " : "";
                out += nb::repr(nb::cast(self[i])).c_str();
            }
            return out + "])";
        });

    nb::class_<CompoundTag>(m, "CompoundTag")
        .def(
            "__init__",
            [](CompoundTag *self, nb::dict entries) {
                CompoundTag out;
                for (auto [key, tag] : entries) {
                    out.insert_or_assign(nb::cast<std::string>(key), nb::cast<Tag>(tag));
                }
                new (self) CompoundTag(std::move(out));
            },
            nb::arg("entries") = nb::dict())
        .def("__len__", &CompoundTag::size)
        .def("__contains__", [](const CompoundTag &self, const std::string &key) { return self.contains(key); })
        .def("__getitem__",
             [](const CompoundTag &self, const std::string &key) -> Tag {
                 const auto it = self.find(key);
                 if (it == self.end()) {
                     throw nb::key_error(key.c_str());
                 }
                 return it->second;
             })
        .def("__setitem__",
             [](CompoundTag &self, const std::string &key, const Tag &tag) { self.insert_or_assign(key, tag); })
        .def("__delitem__",
             [](CompoundTag &self, const std::string &key) {
                 if (self.erase(key) == 0) {
                     throw nb::key_error(key.c_str());
                 }
             })
        .def("keys",
             [](const CompoundTag &self) {
                 std::vector<std::string> out;
                 for (const auto &[key, _] : self) {
                     out.push_back(key);
                 }
                 return out;
             })
        .def("__iter__", [](nb::handle self) { return nb::iter(self.attr("keys")()); })
        .def("items",
             [](const CompoundTag &self) {
                 nb::list out;
                 for (const auto &[key, tag] : self) {
                     out.append(nb::make_tuple(nb::cast(key), nb::cast(tag)));
                 }
                 return out;
             })
        .def(nb::self == nb::self)
        .def("__repr__", [](const CompoundTag &self) {
            std::string out = "CompoundTag({";
            bool first = true;
            for (const auto &[key, tag] : self) {
                out += first ? "" : ", ";
                out += nb::repr(nb::cast(key)).c_str();
                out += ": ";
                out += nb::repr(nb::cast(tag)).c_str();
                first = false;
            }
            return out + "})";
        });
}

}  // namespace bedrock::protocol::python
