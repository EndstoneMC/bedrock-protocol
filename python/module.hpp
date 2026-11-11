#pragma once

#include <string_view>
#include <system_error>
#include <unordered_map>
#include <utility>
#include <vector>

#include <nanobind/nanobind.h>

#include <bedrock/protocol/stream.hpp>

namespace bedrock::protocol::python {

namespace nb = nanobind;

struct Codec {
    nb::object (*decode)(BinaryReader &stream);
};

// One bound protocol version; the extension module owns the modules it borrows.
struct Version {
    int number;
    nb::handle module;
    nb::handle legacy;
    nb::dict packets;
};

// One bound version, as `versions.cpp` lists them.
struct VersionBinding {
    int number;
    std::vector<void (*)(Version &)> files;
};

const std::vector<VersionBinding> &version_bindings();

// Each bound class with the function that fills its `__annotations__` once every type is bound.
std::vector<std::pair<nb::handle, nb::dict (*)()>> &annotators();

[[noreturn]] void throw_decode_error(std::string_view type, const BinaryReader &stream, std::string_view reason);

void bind_nbt(nb::module_ &parent);

}  // namespace bedrock::protocol::python
