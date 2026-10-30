#pragma once

#include <span>

#include "views.h"

namespace bedrock::protocol::python {
inline constexpr std::size_t maxPacketBytes = 4 * 1024 * 1024;

enum class Recoverability { fatal, packet_body };

struct NativeError {
    std::string reason;
    std::size_t offset = 0;
    int packet_id = -1;
    Recoverability recoverability = Recoverability::fatal;
};

inline NativeError bodyError(std::error_code error, const bp::BinaryReader &reader)
{
    // These are the malformed-body codes emitted by the audited serializers.
    // value_too_large also represents limits; the sticky budget state takes priority.
    const bool malformed = error == std::errc::message_size || error == std::errc::illegal_byte_sequence ||
                           error == std::errc::value_too_large;
    return {error.message(), reader.getReadPointer(), -1,
            malformed && !reader.resourceFailure() ? Recoverability::packet_body : Recoverability::fatal};
}

struct PacketHeader {
    int packet_id;
    int sender_subclient_id;
    int target_subclient_id;
};

struct NativePacket {
    std::shared_ptr<const void> value;
    nb::object (*expose)(std::shared_ptr<const void>, int);
    void (*write)(bp::BinaryWriter &, const void *);
};

struct DecodedPacket {
    int protocol;
    PacketHeader header;
    NativePacket payload;
};

struct EncodedPacket {
    std::string bytes;
    int protocol;
    int packet_id;
};

struct UnknownPacket : Packet {
    int packet_id;
    std::shared_ptr<const std::string> body;
    int protocol = 0;
    UnknownPacket(int packet_id, std::shared_ptr<const std::string> body, int protocol = 0)
        : packet_id(packet_id), body(std::move(body)), protocol(protocol)
    {
    }
};

struct PacketEntry {
    int id;
    std::expected<NativePacket, NativeError> (*read)(bp::BinaryReader &);
    bool (*accepts)(nb::handle);
    NativePacket (*snapshot)(nb::handle);
};

template <class T>
NativePacket nativePacket(std::shared_ptr<const T> value)
{
    return {std::move(value),
            [](std::shared_ptr<const void> value, int protocol) {
                return Record<T>::get(std::static_pointer_cast<const T>(std::move(value)), protocol);
            },
            [](bp::BinaryWriter &writer, const void *value) {
                bp::serialize(writer, *static_cast<const T *>(value));
            }};
}

template <class T>
constexpr PacketEntry packetEntry(int id)
{
    return {id,
            [](bp::BinaryReader &reader) -> std::expected<NativePacket, NativeError> {
                if (auto result = reader.account(1, sizeof(T), false); !result) {
                    return std::unexpected(NativeError{"decoded_storage_limit", reader.getReadPointer()});
                }
                auto result = bp::deserialize<T>(reader);
                if (!result) {
                    return std::unexpected(bodyError(result.error(), reader));
                }
                return nativePacket(std::make_shared<const T>(std::move(*result)));
            },
            [](nb::handle object) { return nb::isinstance<View<T>>(object); },
            [](nb::handle object) {
                return nativePacket(nb::cast<const View<T> &>(object).value);
            }};
}

std::span<const PacketEntry *const> packetEntries(int protocol);
std::span<const int> supportedPacketIds(int protocol);
std::span<const int> supportedVersions();
void bindGenerated(nb::module_ &module);

class Codec {
public:
    Codec(int protocol, bp::DecodeLimits limits = {});
    int protocol() const { return protocol_; }
    const bp::DecodeLimits &limits() const { return limits_; }
    std::expected<DecodedPacket, NativeError> decode(std::string_view data, bp::DecodeBudget &budget) const;
    // The caller has validated the header and positioned the full-frame reader at its body.
    std::expected<DecodedPacket, NativeError> decodeBody(bp::BinaryReader &reader, const PacketHeader &header) const;
    std::pair<int, NativePacket> snapshot(nb::handle packet) const;
    std::string encode(int packet_id, const NativePacket &packet, int sender = 0, int target = 0) const;

private:
    int protocol_;
    bp::DecodeLimits limits_;
};

std::expected<PacketHeader, NativeError> readHeader(bp::BinaryReader &reader);
[[noreturn]] void fail(const char *kind, int protocol, int packet_id, const std::string &reason,
                       std::optional<std::size_t> offset = {});
void bindCodec(nb::module_ &module);
void bindWire(nb::module_ &module);
}  // namespace bedrock::protocol::python
