#include <format>
#include <string>
#include <string_view>

#include <nanobind/nanobind.h>

#include <bedrock/protocol/packet.hpp>
#include <bedrock/protocol/version.hpp>

#include "binder.hpp"
#include "module.hpp"

namespace bedrock::protocol::python {

std::unordered_map<PyTypeObject *, PacketCodec> &codecs()
{
    static std::unordered_map<PyTypeObject *, PacketCodec> table;
    return table;
}

std::vector<std::pair<nb::handle, nb::dict (*)()>> &annotators()
{
    static std::vector<std::pair<nb::handle, nb::dict (*)()>> list;
    return list;
}

void throw_decode_error(std::string_view type, const BinaryReader &stream, std::string_view reason)
{
    throw nb::value_error((std::string(type) + ": " + std::string(reason) + " at byte " +
                           std::to_string(stream.getReadPointer()) + " of " + std::to_string(stream.getLength()))
                              .c_str());
}

namespace {

const PacketCodec &codec_of(nb::handle packet)
{
    const auto it = codecs().find(reinterpret_cast<PyTypeObject *>(packet.type().ptr()));
    if (it == codecs().end()) {
        throw nb::type_error(std::format("not a packet: {}", nb::repr(packet.type()).c_str()).c_str());
    }
    return it->second;
}

nb::bytes encode_body(nb::handle packet)
{
    std::string buffer;
    BinaryWriter writer{buffer};
    codec_of(packet).encode(packet, writer);
    return nb::bytes(buffer.data(), buffer.size());
}

nb::bytes encode_framed(nb::handle packet, std::uint8_t recipient_sub_id, std::uint8_t sender_sub_id)
{
    const auto &codec = codec_of(packet);
    std::string buffer;
    BinaryWriter writer{buffer};
    Serializer<PacketHeader>::serialize(writer, PacketHeader{
                                                    .packet_id = static_cast<std::uint16_t>(codec.id),
                                                    .recipient_sub_id = recipient_sub_id,
                                                    .sender_sub_id = sender_sub_id,
                                                });
    codec.encode(packet, writer);
    return nb::bytes(buffer.data(), buffer.size());
}

const PacketCodec &codec_for(const Version &version, int id)
{
    const auto it = version.packets.find(id);
    if (it == version.packets.end()) {
        throw nb::key_error(std::format("no packet {} at protocol {}", id, version.number).c_str());
    }
    return it->second;
}

nb::object decode_body(const Version &version, int id, BinaryReader &reader)
{
    nb::object packet = codec_for(version, id).decode(reader);
    if (reader.getUnreadLength() != 0) {
        throw_decode_error(nb::type_name(packet.type()).c_str(), reader, "trailing bytes");
    }
    return packet;
}

void bind_version_api(Version &version)
{
    auto m = nb::borrow<nb::module_>(version.module);
    m.attr("PROTOCOL") = version.number;
    m.attr("PacketHeader") = nb::type<PacketHeader>();
    nb::dict packets;
    for (const auto &[id, codec] : version.packets) {
        packets[nb::int_(id)] = codec.type;
    }
    m.attr("PACKETS") = packets;
    m.def(
        "decode",
        [version](int packet_id, nb::bytes data) {
            BinaryReader reader{std::string_view(data.c_str(), data.size())};
            return decode_body(version, packet_id, reader);
        },
        nb::arg("packet_id"), nb::arg("data"), "Reads a packet body, its class chosen by `packet_id`.");
    m.def(
        "decode_packet",
        [version](nb::bytes data) {
            BinaryReader reader{std::string_view(data.c_str(), data.size())};
            auto header = Serializer<PacketHeader>::deserialize(reader);
            if (!header) {
                throw_decode_error("PacketHeader", reader, header.error().message());
            }
            nb::object packet = decode_body(version, header->packet_id, reader);
            return nb::make_tuple(*header, packet);
        },
        nb::arg("data"), "Reads a header and the body it names: `(PacketHeader, packet)`.");
    m.def("encode", &encode_body, nb::arg("packet"), "The packet body, without its header.");
    m.def("encode_packet", &encode_framed, nb::arg("packet"), nb::arg("recipient_sub_id") = 0,
          nb::arg("sender_sub_id") = 0, "Header and body, the bytes a batch length-prefixes.");
}

}  // namespace

void bind_versions(nb::module_ &parent)
{
    bind_type<PacketHeader>(parent, nullptr);
    for (const auto &binding : version_bindings()) {
        auto module = parent.def_submodule(std::format("v{}", binding.number).c_str());
        auto legacy = module.def_submodule("legacy", "The pre-cereal shapes, where one name has two encodings.");
        module.attr("nbt") = parent.attr("nbt");
        Version version{.number = binding.number, .module = module, .legacy = legacy};
        for (auto *bind_file : binding.files) {
            bind_file(version);
        }
        binding.check(version);
        bind_version_api(version);
    }
    for (const auto &[cls, annotations] : annotators()) {
        cls.attr("__annotations__") = annotations();
    }
}

}  // namespace bedrock::protocol::python

NB_MODULE(_native, m)
{
    namespace bpy = bedrock::protocol::python;
    m.doc() = "Bedrock packet codecs generated by bpc.";
    m.attr("LATEST_PROTOCOL") = bedrock::protocol::latest_version;
    bpy::bind_nbt(m);
    bpy::bind_versions(m);
}
