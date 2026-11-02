#pragma once

#include <map>
#include <string_view>
#include <system_error>
#include <unordered_map>
#include <utility>
#include <vector>

#include <nanobind/nanobind.h>

#include <bedrock/protocol/stream.hpp>

namespace bedrock::protocol::python {

namespace nb = nanobind;

struct PacketCodec {
    int id;
    nb::handle type;
    void (*encode)(nb::handle packet, BinaryWriter &stream);
    nb::object (*decode)(BinaryReader &stream);
};

// One bound protocol version; the extension module owns the modules it borrows.
struct Version {
    int number;
    nb::handle module;
    nb::handle legacy;
    std::map<int, PacketCodec> packets;
};

// One bound version, as `versions.cpp` lists them.
struct VersionBinding {
    int number;
    std::vector<void (*)(Version &)> files;
    void (*check)(const Version &);
};

const std::vector<VersionBinding> &version_bindings();

// Every bound packet class, whichever versions share it.
std::unordered_map<PyTypeObject *, PacketCodec> &codecs();

// Each bound class with the function that fills its `__annotations__` once every type is bound.
std::vector<std::pair<nb::handle, nb::dict (*)()>> &annotators();

// Keeps a name alive for as long as the extension is loaded.
const char *intern(std::string_view name);

[[noreturn]] void throw_decode_error(std::string_view type, const BinaryReader &stream, std::string_view reason);

void bind_nbt(nb::module_ &parent);

}  // namespace bedrock::protocol::python
