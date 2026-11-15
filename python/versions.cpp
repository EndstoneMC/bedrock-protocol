#include <array>
#include <cstddef>
#include <cstdint>
#include <format>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include <nanobind/nanobind.h>
#include <nanobind/typing.h>

#include "_core.h"
#include "bedrock/protocol/packet.hpp"
#include "bedrock/protocol/serializer.hpp"
#include "bedrock/protocol/stream.hpp"
#include "bedrock/protocol/version.hpp"

namespace bedrock::protocol::python {

void init_versions(nb::module_ &parent)
{
    bind_struct<PacketHeader>(parent, "PacketHeader");
    static std::array<CodecTable, 2 * versions.size()> tables;
    std::vector<Version> bound;
    for (std::size_t i = 0; i < versions.size(); ++i) {
        const int number = versions[i];
        auto module = parent.def_submodule(std::format("v{}", number).c_str());
        auto pre_cereal =
            module.def_submodule("pre_cereal", "The pre-cereal shapes, where one name has two encodings.");
        bound.push_back(
            {.cereal = {.number = number, .noun = "type", .module = module, .codecs = &tables[2 * i]},
             .pre_cereal = {
                 .number = number, .noun = "pre-cereal type", .module = pre_cereal, .codecs = &tables[2 * i + 1]}});
    }
    init_types(bound);
    [&]<std::size_t... I>(std::index_sequence<I...>) {
        (
            [&] {
                constexpr int number = versions[I];
                const Version &version = bound[I];
                auto m = nb::borrow<nb::module_>(version.cereal.module);
                m.def(
                    "decode_packet",
                    [packets = version.cereal.packets, codecs = version.cereal.codecs](
                        const nb::bytes &data) -> nb::typed<nb::tuple, PacketHeader, nb::object> {
                        BinaryReader reader{std::string_view(data.c_str(), data.size())};
                        auto header = Serializer<PacketHeader, number>::deserialize(reader);
                        if (!header) {
                            throw_decode_error({.reason = header.error(),
                                                .type = "PacketHeader",
                                                .path = {},
                                                .offset = reader.getReadPointer(),
                                                .length = reader.getLength()});
                        }
                        nb::object cls = packets.get(nb::int_(header->packet_id), nb::none());
                        if (cls.is_none()) {
                            throw_decode_error({.reason = Errc::unknown_value,
                                                .type = "PacketHeader",
                                                .path = {"packet_id"},
                                                .offset = reader.getReadPointer(),
                                                .length = reader.getLength()});
                        }
                        nb::object packet = codecs->at(cls.ptr())->decode(reader);
                        return nb::make_tuple(*header, packet);
                    },
                    nb::arg("data"), "Reads a header and the body it names: `(PacketHeader, packet)`.");
                m.def(
                    "encode_packet",
                    [packets = version.cereal.packets, codecs = version.cereal.codecs, protocol_number = number](
                        nb::handle packet, std::uint8_t recipient_sub_id, std::uint8_t sender_sub_id) {
                        nb::object id = nb::getattr(packet.type(), "ID", nb::none());
                        if (!packets.get(id, nb::none()).is(packet.type())) {
                            throw nb::type_error(std::format("packet: {} is not a packet at protocol {}",
                                                             nb::repr(packet.type()).c_str(), protocol_number)
                                                     .c_str());
                        }
                        if (!nb::inst_ready(packet)) {
                            throw nb::type_error(
                                std::format("packet: {} instance is not initialized", nb::repr(packet.type()).c_str())
                                    .c_str());
                        }
                        std::string buffer;
                        BinaryWriter writer{buffer};
                        const PacketHeader header{
                            .packet_id = nb::cast<std::uint16_t>(id),
                            .recipient_sub_id = recipient_sub_id,
                            .sender_sub_id = sender_sub_id,
                        };
                        if (auto written = Serializer<PacketHeader, number>::serialize(writer, header); !written) {
                            throw_encode_error({.reason = written.error(), .type = "PacketHeader", .path = {}});
                        }
                        if (auto written = codecs->at(packet.type().ptr())->encode(writer, packet); !written) {
                            throw_encode_error(written.error());
                        }
                        return nb::bytes(buffer.data(), buffer.size());
                    },
                    nb::arg("packet"), nb::kw_only(), nb::arg("recipient_sub_id") = 0, nb::arg("sender_sub_id") = 0,
                    "Header and body, the bytes a batch length-prefixes.");
            }(),
            ...);
    }(std::make_index_sequence<versions.size()>{});
    for (const Version &version : bound) {
        for (const Scope *scope : {&version.cereal, &version.pre_cereal}) {
            auto m = nb::borrow<nb::module_>(scope->module);
            m.attr("_T") = nb::type_var("_T");
            m.attr("encodings") = nb::module_::import_("types").attr("MappingProxyType")(scope->encodings);
            m.def(
                "encode",
                [codecs = scope->codecs, noun = scope->noun, number = scope->number](nb::handle value) {
                    const auto codec = codecs->find(value.type().ptr());
                    if (codec == codecs->end()) {
                        throw nb::type_error(std::format("value: {} is not a {} at protocol {}",
                                                         nb::repr(value.type()).c_str(), noun, number)
                                                 .c_str());
                    }
                    if (!nb::inst_ready(value)) {
                        throw nb::type_error(
                            std::format("value: {} instance is not initialized", nb::repr(value.type()).c_str())
                                .c_str());
                    }
                    std::string buffer;
                    BinaryWriter writer{buffer};
                    if (auto written = codec->second->encode(writer, value); !written) {
                        throw_encode_error(written.error());
                    }
                    return nb::bytes(buffer.data(), buffer.size());
                },
                nb::arg("value"), "The encoded form at this protocol, without a packet header.");
            m.def(
                "decode",
                [codecs = scope->codecs, noun = scope->noun, number = scope->number](nb::handle cls,
                                                                                     const nb::bytes &data) {
                    const auto codec = codecs->find(cls.ptr());
                    if (codec == codecs->end()) {
                        throw nb::type_error(
                            std::format("cls: {} is not a {} at protocol {}", nb::repr(cls).c_str(), noun, number)
                                .c_str());
                    }
                    BinaryReader reader{std::string_view(data.c_str(), data.size())};
                    return codec->second->decode(reader);
                },
                nb::arg("cls"), nb::arg("data"), nb::sig("def decode(cls: type[_T], data: bytes) -> _T"),
                "Reads one `cls` at this protocol that must span all of `data`.");
        }
        auto m = nb::borrow<nb::module_>(version.cereal.module);
        m.attr("packets") = nb::module_::import_("types").attr("MappingProxyType")(version.cereal.packets);
        nb::list all;
        for (nb::handle name : m.attr("__dict__")) {
            const std::string_view text = nb::borrow<nb::str>(name).c_str();
            if (!text.starts_with('_') && text != "pre_cereal") {
                all.append(name);
            }
        }
        m.attr("__all__") = all;
    }
}

}  // namespace bedrock::protocol::python
