#include "bedrock/protocol/nbt.hpp"

#include <cstddef>
#include <format>
#include <string>
#include <utility>
#include <vector>

#include <nanobind/nanobind.h>
#include <nanobind/operators.h>
#include <nanobind/stl/bind_map.h>
#include <nanobind/stl/vector.h>

#include "casters.hpp"
#include "module.h"

namespace bedrock::protocol::python {

namespace {

template <typename T>
void bind_value_tag(nb::module_ &m, const char *name)
{
    using V = typename T::value_type;
    nb::class_<T>(m, name, nb::is_final())
        .def(nb::init<V>(), nb::arg("value") = V{})
        .def_prop_ro("value", [](const T &self) { return self.value(); })
        .def(nb::self == nb::self)
        .def("__hash__", [](const T &self) { return nb::hash(nb::cast(self.value())); })
        .def("__repr__",
             [name](const T &self) { return std::format("{}({})", name, nb::repr(nb::cast(self.value())).c_str()); });
}

template <typename T>
void bind_array_tag(nb::module_ &m, const char *name)
{
    using V = typename T::value_type;
    nb::class_<T>(m, name, nb::is_final())
        .def(
            "__init__", [](T *self, const std::vector<V> &values) { new (self) T(values); },
            nb::arg("value") = std::vector<V>{})
        .def_prop_ro("value", [](const T &self) { return std::vector<V>(self.begin(), self.end()); })
        .def("__len__", &T::size)
        .def(nb::self == nb::self)
        .def("__repr__", [name](const T &self) {
            return std::format("{}({})", name, nb::repr(nb::cast(std::vector<V>(self.begin(), self.end()))).c_str());
        });
}

}  // namespace

void init_nbt(nb::module_ &parent)
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

    nb::class_<ListTag>(m, "ListTag", nb::is_final())
        .def(
            "__init__",
            [](ListTag *self, const std::vector<Tag> &tags, int type) {
                if (type < 0 || type > static_cast<int>(nbt::Type::IntArray)) {
                    throw nb::value_error(std::format("type: {} is not a tag type", type).c_str());
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
            std::string tags;
            for (std::size_t i = 0; i < self.size(); ++i) {
                tags += std::format("{}{}", i ? ", " : "", nb::repr(nb::cast(self[i])).c_str());
            }
            return std::format("ListTag([{}])", tags);
        });

    nb::bind_map<CompoundTag>(m, "CompoundTag", nb::is_final()).attr("__hash__") = nb::none();

    m.attr("Tag") = m.attr("ByteTag") | m.attr("ShortTag") | m.attr("IntTag") | m.attr("Int64Tag") |
                    m.attr("FloatTag") | m.attr("DoubleTag") | m.attr("StringTag") | m.attr("ByteArrayTag") |
                    m.attr("IntArrayTag") | m.attr("ListTag") | m.attr("CompoundTag");
}

}  // namespace bedrock::protocol::python
