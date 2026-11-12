#include "versions.hpp"

#include <cstddef>
#include <format>
#include <string>
#include <string_view>
#include <variant>

#include <nanobind/nanobind.h>

#include "bedrock/protocol/packet.hpp"
#include "bedrock/protocol/serializer.hpp"
#include "binder.hpp"
#include "module.hpp"

namespace bedrock::protocol::python {

namespace {

std::uint16_t id_of(nb::handle packet)
{
    nb::object id = nb::getattr(packet.type(), "ID", nb::none());
    if (id.is_none()) {
        throw nb::type_error(std::format("not a packet: {}", nb::repr(packet.type()).c_str()).c_str());
    }
    return nb::cast<std::uint16_t>(id);
}

nb::bytes encode_body(nb::handle packet)
{
    id_of(packet);
    auto body = nb::steal<nb::bytes>(PyObject_Bytes(packet.ptr()));
    if (!body.is_valid()) {
        throw nb::python_error();
    }
    return body;
}

nb::bytes encode_framed(nb::handle packet, std::uint8_t recipient_sub_id, std::uint8_t sender_sub_id)
{
    std::string buffer;
    BinaryWriter writer{buffer};
    Serializer<PacketHeader>::serialize(writer, PacketHeader{
                                                    .packet_id = id_of(packet),
                                                    .recipient_sub_id = recipient_sub_id,
                                                    .sender_sub_id = sender_sub_id,
                                                });
    nb::bytes body = encode_body(packet);
    buffer.append(body.c_str(), body.size());
    return nb::bytes(buffer.data(), buffer.size());
}

nb::object decode_body(const Version &version, int id, BinaryReader &reader)
{
    nb::object cls = version.packets.get(nb::int_(id), nb::none());
    if (cls.is_none()) {
        throw nb::key_error(std::format("no packet {} at protocol {}", id, version.number).c_str());
    }
    return nb::type_supplement<Codec>(cls).decode(reader);
}

}  // namespace

void throw_decode_error(DecodeError error)
{
    std::vector<std::string> names;
    names.reserve(error.path.size());
    nb::list path;
    for (auto &segment : error.path) {
        if (const auto *name = std::get_if<std::string_view>(&segment)) {
            segment = std::string_view(names.emplace_back(python_name(*name)));
            path.append(nb::str(names.back().c_str()));
        }
        else {
            path.append(std::get<std::size_t>(segment));
        }
    }
    nb::object type = nb::module_::import_("bedrock_protocol").attr("DecodeError");
    nb::object exception =
        type(std::format("{}", error), std::format("{}", error.reason), nb::tuple(path), error.offset);
    PyErr_SetObject(type.ptr(), exception.ptr());
    throw nb::python_error();
}

void init_versions(nb::module_ &parent)
{
    bind_type<PacketHeader>(parent, nullptr);
    std::vector<Version> bound;
    for (const int number : versions) {
        auto module = parent.def_submodule(std::format("v{}", number).c_str());
        auto legacy = module.def_submodule("legacy", "The pre-cereal shapes, where one name has two encodings.");
        bound.push_back({.number = number, .module = module, .legacy = legacy});
    }
    init_types(bound);
    for (Version &version : bound) {
        auto m = nb::borrow<nb::module_>(version.module);
        m.attr("PROTOCOL") = version.number;
        m.attr("PACKETS") = nb::module_::import_("types").attr("MappingProxyType")(version.packets);
        m.def(
            "decode",
            [version](int packet_id, nb::bytes data) {
                BinaryReader reader{std::string_view(data.c_str(), data.size())};
                return decode_body(version, packet_id, reader);
            },
            nb::arg("packet_id"), nb::arg("data"), "Reads a packet body.");
        m.def(
            "decode_packet",
            [version](nb::bytes data) {
                BinaryReader reader{std::string_view(data.c_str(), data.size())};
                auto header = Serializer<PacketHeader>::deserialize(reader);
                if (!header) {
                    throw_decode_error({.reason = header.error(),
                                        .type = "PacketHeader",
                                        .path = {},
                                        .offset = reader.getReadPointer(),
                                        .length = reader.getLength()});
                }
                nb::object packet = decode_body(version, header->packet_id, reader);
                return nb::make_tuple(*header, packet);
            },
            nb::arg("data"), "Reads a header and the body it names: `(PacketHeader, packet)`.");
        m.def("encode", &encode_body, nb::arg("packet"), "The packet body, without its header.");
        m.def("encode_packet", &encode_framed, nb::arg("packet"), nb::arg("recipient_sub_id") = 0,
              nb::arg("sender_sub_id") = 0, "Header and body, the bytes a batch length-prefixes.");
    }
    for (const auto &[cls, annotations] : annotators()) {
        cls.attr("__annotations__") = annotations();
    }
}

}  // namespace bedrock::protocol::python
