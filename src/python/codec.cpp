#include "codec.h"

#include <algorithm>
#include <vector>

namespace bedrock::protocol::python {

[[noreturn]] void fail(const char *kind, int protocol, int packet_id, const std::string &reason,
                       std::optional<std::size_t> offset)
{
    auto cls = nb::module_::import_("bedrock_protocol._api").attr(kind);
    auto error = cls(reason, nb::arg("protocol") = protocol,
                     nb::arg("packet_id") = packet_id < 0 ? nb::object(nb::none()) : nb::object(nb::int_(packet_id)),
                     nb::arg("offset") = offset ? nb::object(nb::int_(*offset)) : nb::object(nb::none()),
                     nb::arg("reason") = reason);
    PyErr_SetObject(cls.ptr(), error.ptr());
    throw nb::python_error();
}

Codec::Codec(int protocol, bp::DecodeLimits limits) : protocol_(protocol), limits_(limits)
{
    if (supportedPacketIds(protocol).empty()) {
        fail("UnsupportedVersionError", protocol, -1, "unsupported_protocol");
    }
    if (limits.max_depth > 128) {
        throw nb::value_error("max_depth cannot exceed 128");
    }
}

std::expected<PacketHeader, NativeError> readHeader(bp::BinaryReader &reader)
{
    auto raw = reader.readVarInt<std::uint32_t>();
    if (!raw) {
        return std::unexpected(NativeError{"invalid_packet_header", reader.getReadPointer()});
    }
    if ((*raw >> 14) != 0) {
        return std::unexpected(NativeError{"reserved_packet_header_bits", reader.getReadPointer()});
    }
    return PacketHeader{static_cast<int>(*raw & 0x3ff), static_cast<int>((*raw >> 10) & 3),
                        static_cast<int>((*raw >> 12) & 3)};
}

namespace {
std::span<const PacketEntry *const> packetEntries(int protocol)
{
    static const auto entries = [] {
        std::vector<std::pair<int, std::vector<const PacketEntry *>>> result;
        result.reserve(supportedVersions().size());
        for (const auto version : supportedVersions()) {
            std::vector<const PacketEntry *> packets;
            const auto packet_ids = supportedPacketIds(version);
            packets.reserve(packet_ids.size());
            for (const auto id : packet_ids) {
                packets.push_back(findPacket(version, id));
            }
            result.emplace_back(version, std::move(packets));
        }
        return result;
    }();
    for (const auto &[version, packets] : entries) {
        if (version == protocol) {
            return packets;
        }
    }
    return {};
}

NativePacket unknown(std::shared_ptr<const UnknownPacket> value)
{
    return {std::move(value),
            [](std::shared_ptr<const void> value, int protocol) {
                const auto &packet = *std::static_pointer_cast<const UnknownPacket>(value);
                return nb::cast(UnknownPacket{packet.packet_id, packet.body, protocol});
            },
            [](bp::BinaryWriter &writer, const void *value) {
                writer.writeRawBytes(*static_cast<const UnknownPacket *>(value)->body);
            }};
}

nb::tuple ids(std::span<const int> values)
{
    nb::list result;
    for (int value : values) {
        result.append(value);
    }
    return nb::tuple(result);
}

std::pair<int, std::string> encodePacket(const Codec &codec, nb::handle packet, int sender, int target)
{
    if (sender < 0 || sender > 3 || target < 0 || target > 3) {
        throw nb::value_error("subclient IDs must fit 2 bits");
    }
    auto [id, value] = codec.snapshot(packet);
    std::string bytes;
    try {
        nb::gil_scoped_release release;
        bytes = codec.encode(id, value, sender, target);
    }
    catch (const std::exception &error) {
        fail("EncodeError", codec.protocol(), id, error.what());
    }
    return {id, std::move(bytes)};
}
}  // namespace

std::expected<DecodedPacket, NativeError> Codec::decode(std::string_view data, bp::DecodeBudget &budget) const
{
    if (data.size() > maxPacketBytes) {
        return std::unexpected(NativeError{"packet_byte_limit"});
    }
    bp::BinaryReader reader(data, &budget);
    auto header = readHeader(reader);
    if (!header) {
        return std::unexpected(header.error());
    }
    return decodeBody(reader, *header);
}

std::expected<DecodedPacket, NativeError> Codec::decodeBody(bp::BinaryReader &reader, const PacketHeader &header) const
{
    const auto id = header.packet_id;
    const auto entries = packetEntries(protocol_);
    const auto found = std::lower_bound(entries.begin(), entries.end(), id,
                                        [](const PacketEntry *entry, int packet_id) { return entry->id < packet_id; });
    const auto *entry = found != entries.end() && (*found)->id == id ? *found : nullptr;
    if (!entry) {
        auto known = knownPacketIds(protocol_);
        if (std::binary_search(known.begin(), known.end(), id)) {
            return std::unexpected(NativeError{"packet_not_bound", reader.getReadPointer(), id,
                                                Recoverability::packet_body});
        }
        auto body = reader.readRemaining();
        if (!body) {
            return std::unexpected(NativeError{body.error().message(), reader.getReadPointer(), id});
        }
        auto packet =
            std::make_shared<const UnknownPacket>(id, std::make_shared<const std::string>(std::move(*body)), protocol_);
        return DecodedPacket{protocol_, header, unknown(std::move(packet))};
    }
    auto payload = entry->read(reader);
    if (!payload) {
        auto error = payload.error();
        error.packet_id = id;
        return std::unexpected(std::move(error));
    }
    if (reader.getUnreadLength()) {
        return std::unexpected(NativeError{"trailing_packet_data", reader.getReadPointer(), id,
                                            Recoverability::packet_body});
    }
    return DecodedPacket{protocol_, header, std::move(*payload)};
}

std::pair<int, NativePacket> Codec::snapshot(nb::handle packet) const
{
    if (nb::isinstance<UnknownPacket>(packet)) {
        const auto &value = nb::cast<const UnknownPacket &>(packet);
        auto known = knownPacketIds(protocol_);
        if (std::binary_search(known.begin(), known.end(), value.packet_id)) {
            fail("EncodeError", protocol_, value.packet_id, "known_packet_requires_typed_value");
        }
        return {value.packet_id, unknown(std::make_shared<const UnknownPacket>(value))};
    }
    for (const auto *entry : packetEntries(protocol_)) {
        if (entry->accepts(packet)) {
            return {entry->id, entry->snapshot(packet)};
        }
    }
    fail("EncodeError", protocol_, -1, "packet_type_unavailable");
}

std::string Codec::encode(int id, const NativePacket &packet, int sender, int target) const
{
    std::string bytes;
    bp::BinaryWriter writer(bytes);
    writer.writeVarInt<std::uint32_t>(static_cast<unsigned>(id) | (sender << 10) | (target << 12));
    packet.write(writer, packet.value.get());
    if (bytes.size() > maxPacketBytes) {
        throw std::length_error("packet_byte_limit");
    }
    return bytes;
}

void bindCodec(nb::module_ &module)
{
    nb::class_<bp::DecodeLimits>(module, "DecodeLimits")
        .def(nb::new_([](std::size_t elements, std::size_t bytes, std::size_t depth) {
                 if (depth > 128) {
                     throw nb::value_error("max_depth cannot exceed 128");
                 }
                 return bp::DecodeLimits{elements, bytes, depth};
             }),
             nb::kw_only(), nb::arg("max_decoded_elements") = 1'048'576,
             nb::arg("max_decoded_bytes") = 64 * 1024 * 1024, nb::arg("max_depth") = 128)
        .def_ro("max_decoded_elements", &bp::DecodeLimits::max_decoded_elements)
        .def_ro("max_decoded_bytes", &bp::DecodeLimits::max_decoded_bytes)
        .def_ro("max_depth", &bp::DecodeLimits::max_depth);
    nb::class_<PacketHeader>(module, "PacketHeader")
        .def_ro("packet_id", &PacketHeader::packet_id)
        .def_ro("sender_subclient_id", &PacketHeader::sender_subclient_id)
        .def_ro("target_subclient_id", &PacketHeader::target_subclient_id);
    nb::class_<DecodedPacket>(module, "DecodedPacket")
        .def_ro("protocol", &DecodedPacket::protocol)
        .def_ro("header", &DecodedPacket::header)
        .def_prop_ro("payload",
                     [](const DecodedPacket &self) { return self.payload.expose(self.payload.value, self.protocol); });
    nb::class_<EncodedPacket>(module, "EncodedPacket")
        .def_ro("protocol", &EncodedPacket::protocol)
        .def_ro("packet_id", &EncodedPacket::packet_id)
        .def("__len__", [](const EncodedPacket &self) { return self.bytes.size(); });
    nb::class_<UnknownPacket, Packet>(module, "UnknownPacket")
        .def(nb::new_([](int packet_id, nb::handle body) {
                 if (packet_id < 0 || packet_id > 1023) {
                     throw nb::value_error("packet_id must fit 10 bits");
                 }
                 auto copy = std::make_shared<const std::string>(snapshotBuffer(body, maxPacketBytes));
                 return UnknownPacket{packet_id, std::move(copy)};
             }),
             nb::kw_only(), nb::arg("packet_id"), nb::arg("body"))
        .def_ro("packet_id", &UnknownPacket::packet_id)
        .def_prop_ro("protocol", [](const UnknownPacket &self) { return provenance(self.protocol); })
        .def_prop_ro("body",
                     [](const UnknownPacket &self) {
                         return BinaryView{self.body, self.body->data(), self.body->size(), self.protocol};
                     })
        .def("copy",
             [](const UnknownPacket &self) {
                 return UnknownPacket{self.packet_id, std::make_shared<const std::string>(*self.body), self.protocol};
             })
        .def("wire_bytes", [](const UnknownPacket &self) { return nb::bytes(self.body->data(), self.body->size()); });
    nb::class_<Codec>(module, "Codec")
        .def(nb::init<int, bp::DecodeLimits>(), nb::arg("protocol"), nb::kw_only(),
             nb::arg("limits") = bp::DecodeLimits{})
        .def_prop_ro("protocol", &Codec::protocol)
        .def_prop_ro("limits", [](const Codec &self) { return self.limits(); })
        .def_prop_ro("known_packet_ids", [](const Codec &self) { return ids(knownPacketIds(self.protocol())); })
        .def_prop_ro("supported_packet_ids", [](const Codec &self) { return ids(supportedPacketIds(self.protocol())); })
        .def(
            "decode_packet",
            [](const Codec &self, nb::handle data) {
                std::string bytes;
                try {
                    bytes = snapshotBuffer(data, maxPacketBytes);
                }
                catch (const nb::builtin_exception &) {
                    fail("DecodeError", self.protocol(), -1, "packet_byte_limit");
                }
                bp::DecodeBudget budget(self.limits());
                std::expected<DecodedPacket, NativeError> result;
                {
                    nb::gil_scoped_release release;
                    result = self.decode(bytes, budget);
                }
                if (!result) {
                    fail("DecodeError", self.protocol(), result.error().packet_id, result.error().reason,
                         result.error().offset);
                }
                return std::move(*result);
            },
            nb::arg("data"))
        .def(
            "prepare_packet",
            [](const Codec &self, nb::handle packet, int sender, int target) {
                auto [id, bytes] = encodePacket(self, packet, sender, target);
                return EncodedPacket{std::move(bytes), self.protocol(), id};
            },
            nb::arg("packet"), nb::kw_only(), nb::arg("sender_subclient_id") = 0, nb::arg("target_subclient_id") = 0)
        .def(
            "encode_packet",
            [](const Codec &self, nb::handle packet, int sender, int target) {
                auto [id, bytes] = encodePacket(self, packet, sender, target);
                return nb::bytes(bytes.data(), bytes.size());
            },
            nb::arg("packet"), nb::kw_only(), nb::arg("sender_subclient_id") = 0, nb::arg("target_subclient_id") = 0);
    module.attr("SUPPORTED_VERSIONS") = ids(supportedVersions());
}
}  // namespace bedrock::protocol::python
