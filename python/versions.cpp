#include "versions.hpp"

#include <cstddef>
#include <format>
#include <string>
#include <string_view>
#include <variant>

#include <nanobind/nanobind.h>

#include "bedrock/protocol/packet.hpp"
#include "bedrock/protocol/serializer.hpp"
#include "bedrock/protocol/stream.hpp"
#include "binder.hpp"
#include "module.hpp"

namespace bedrock::protocol::python {

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
        auto pre_cereal =
            module.def_submodule("pre_cereal", "The pre-cereal shapes, where one name has two encodings.");
        bound.push_back({.number = number, .module = module, .pre_cereal = pre_cereal});
    }
    init_types(bound);
    for (Version &version : bound) {
        auto m = nb::borrow<nb::module_>(version.module);
        m.attr("PROTOCOL") = version.number;
        m.attr("PACKETS") = nb::module_::import_("types").attr("MappingProxyType")(version.packets);
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
                nb::object cls = version.packets.get(nb::int_(header->packet_id), nb::none());
                if (cls.is_none()) {
                    throw_decode_error({.reason = Errc::unknown_value,
                                        .type = "PacketHeader",
                                        .path = {"packet_id"},
                                        .offset = reader.getReadPointer(),
                                        .length = reader.getLength()});
                }
                nb::object packet = nb::type_supplement<Codec>(cls).decode(reader);
                return nb::make_tuple(*header, packet);
            },
            nb::arg("data"), "Reads a header and the body it names: `(PacketHeader, packet)`.");
        m.def(
            "encode_packet",
            [version](nb::handle packet, std::uint8_t recipient_sub_id, std::uint8_t sender_sub_id) {
                nb::object id = nb::getattr(packet.type(), "ID", nb::none());
                if (!version.packets.get(id, nb::none()).is(packet.type())) {
                    throw nb::type_error(std::format("packet: {} is not a packet at protocol {}",
                                                     nb::repr(packet.type()).c_str(), version.number)
                                             .c_str());
                }
                std::string buffer;
                BinaryWriter writer{buffer};
                Serializer<PacketHeader>::serialize(writer, PacketHeader{
                                                                .packet_id = nb::cast<std::uint16_t>(id),
                                                                .recipient_sub_id = recipient_sub_id,
                                                                .sender_sub_id = sender_sub_id,
                                                            });
                auto body = nb::steal<nb::bytes>(PyObject_Bytes(packet.ptr()));
                if (!body.is_valid()) {
                    throw nb::python_error();
                }
                buffer.append(body.c_str(), body.size());
                return nb::bytes(buffer.data(), buffer.size());
            },
            nb::arg("packet"), nb::kw_only(), nb::arg("recipient_sub_id") = 0, nb::arg("sender_sub_id") = 0,
            "Header and body, the bytes a batch length-prefixes.");
        nb::list all;
        for (nb::handle name : m.attr("__dict__")) {
            const std::string_view text = nb::borrow<nb::str>(name).c_str();
            if (!text.starts_with('_') && text != "pre_cereal") {
                all.append(name);
            }
        }
        m.attr("__all__") = all;
    }
    for (const auto &[cls, annotations] : annotators()) {
        cls.attr("__annotations__") = annotations();
    }
}

}  // namespace bedrock::protocol::python
