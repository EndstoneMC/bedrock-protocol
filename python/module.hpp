#pragma once

#include <string_view>
#include <system_error>
#include <utility>
#include <vector>

#include <nanobind/nanobind.h>

#include "bedrock/protocol/stream.hpp"

namespace bedrock::protocol::python {

namespace nb = nanobind;

struct Codec {
    nb::object (*decode)(BinaryReader &stream);
};

struct Version {
    int number;
    nb::handle module;
    nb::handle legacy;
    nb::dict packets;
};

struct VersionBinding {
    int number;
    std::vector<void (*)(Version &)> files;
};

const std::vector<VersionBinding> &version_bindings();

std::vector<std::pair<nb::handle, nb::dict (*)()>> &annotators();

[[noreturn]] void throw_decode_error(std::string_view type, const BinaryReader &stream, std::string_view reason);

void bind_nbt(nb::module_ &parent);

}  // namespace bedrock::protocol::python
