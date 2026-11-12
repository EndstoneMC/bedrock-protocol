#pragma once

#include <span>
#include <utility>
#include <vector>

#include <nanobind/nanobind.h>

#include "bedrock/protocol/serializer.hpp"
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

std::vector<std::pair<nb::handle, nb::dict (*)()>> &annotators();

[[noreturn]] void throw_decode_error(DecodeError error);

void init_nbt(nb::module_ &parent);
void init_versions(nb::module_ &parent);

void init_types(std::span<const Version> bound);

}  // namespace bedrock::protocol::python
