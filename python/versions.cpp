#include <array>
#include <cstddef>
#include <format>
#include <string>
#include <string_view>
#include <tuple>
#include <utility>
#include <vector>

#include <nanobind/nanobind.h>
#include <nanobind/typing.h>

#include "_core.h"
#include "bedrock/protocol/serializer.hpp"
#include "bedrock/protocol/stream.hpp"
#include "bedrock/protocol/version.hpp"

namespace bedrock::protocol::python {

namespace {

const Codec &resolve(const CodecTable &codecs, int number, nb::handle type, SerializationMode mode,
                     const char *argument)
{
    const auto entry = codecs.find(type.ptr());
    if (entry == codecs.end()) {
        throw nb::type_error(
            std::format("{}: {} is not a type at protocol {}", argument, nb::repr(type).c_str(), number).c_str());
    }
    if (const Codec *codec = entry->second[std::to_underlying(mode)]) {
        return *codec;
    }
    if (mode != SerializationMode::Default) {
        throw nb::type_error(std::format("{}: {} has no {} mode at protocol {}", argument, nb::repr(type).c_str(),
                                         nb::cast<std::string>(nb::cast(mode).attr("name").attr("lower")()), number)
                                 .c_str());
    }
    std::string available;
    for (std::size_t i = 0; i < mode_count; ++i) {
        if (entry->second[i] != nullptr) {
            available += std::format("{}mode=SerializationMode.{}", available.empty() ? "" : " or ",
                                     nb::cast<std::string>(nb::cast(static_cast<SerializationMode>(i)).attr("name")));
        }
    }
    throw nb::type_error(std::format("{}: {} has no default mode at protocol {}; pass {}", argument,
                                     nb::repr(type).c_str(), number, available)
                             .c_str());
}

const Codec &resolve_packet(const Scope &scope, nb::handle type, const char *argument)
{
    if (!scope.packets.get(nb::getattr(type, "ID", nb::none()), nb::none()).is(type)) {
        throw nb::type_error(
            std::format("{}: {} is not a packet at protocol {}", argument, nb::repr(type).c_str(), scope.number)
                .c_str());
    }
    return resolve(*scope.codecs, scope.number, type, SerializationMode::Default, argument);
}

const CodecTable &codecs_at(const std::array<CodecTable, detail::versions.size()> &tables, int protocol)
{
    for (std::size_t i = 0; i < detail::versions.size(); ++i) {
        if (detail::versions[i] == protocol) {
            return tables[i];
        }
    }
    throw nb::value_error(std::format("protocol: {} is not a modelled protocol", protocol).c_str());
}

const EnumNumbering &resolve_enum(const Scope &scope, nb::handle type, const char *argument)
{
    const auto entry = scope.enums->find(type.ptr());
    if (entry == scope.enums->end()) {
        throw nb::type_error(std::format("{}: {} is not an enum", argument, nb::repr(type).c_str()).c_str());
    }
    return *entry->second;
}

const EnumNaming &resolve_naming(const Scope &scope, nb::handle type, const char *argument)
{
    const auto entry = scope.namings->find(type.ptr());
    if (entry == scope.namings->end()) {
        throw nb::type_error(std::format("{}: {} is not a name-coded enum", argument, nb::repr(type).c_str()).c_str());
    }
    return *entry->second;
}

nb::bytes encode_with(const Codec &codec, nb::handle value, const char *argument)
{
    if (!nb::inst_ready(value)) {
        throw nb::type_error(
            std::format("{}: {} instance is not initialized", argument, nb::repr(value.type()).c_str()).c_str());
    }
    std::string buffer;
    BinaryWriter writer{buffer};
    if (auto written = codec.encode(writer, value); !written) {
        throw_encode_error(written.error());
    }
    return nb::bytes(buffer.data(), buffer.size());
}

}  // namespace

std::tuple<nb::object, nb::object, std::string_view> claim_owner(const Scope &scope, nb::handle home,
                                                                 std::string_view declared, std::string_view label,
                                                                 bool create)
{
    std::string_view path = label.empty() ? declared : label;
    nb::object owner = scope.names;
    for (auto pos = path.find("::"); pos != std::string_view::npos; pos = path.find("::")) {
        owner = owner.attr(std::string(path.substr(0, pos)).c_str());
        path.remove_prefix(pos + 2);
    }
    nb::object parent = owner.is(scope.names) ? nb::borrow(home) : owner;
    const std::string name(declared.substr(declared.rfind(':') + 1));
    if (create && nb::hasattr(parent, name.c_str())) {
        std::string dotted(declared);
        for (auto pos = dotted.find("::"); pos != std::string::npos; pos = dotted.find("::", pos + 1)) {
            dotted.replace(pos, 2, ".");
        }
        throw nb::value_error(std::format("{}: is already bound at protocol {}", dotted, scope.number).c_str());
    }
    return {owner, parent, path};
}

void register_mode(const Scope &scope, nb::handle cls, SerializationMode mode, int since, const Codec *codec)
{
    (*scope.codecs)[cls.ptr()][std::to_underlying(mode)] = codec;
    nb::borrow<nb::dict>(scope.modes.attr("setdefault")(cls, nb::dict()))[nb::cast(mode)] = nb::int_(since);
    if (mode == SerializationMode::Default) {
        scope.encodings[cls] = nb::int_(since);
    }
}

void bind_name(nb::handle owner, std::string_view leaf, nb::handle cls)
{
    owner.attr(std::string(leaf).c_str()) = cls;
}

void register_packet(const Scope &scope, int id, nb::handle cls)
{
    scope.packets[nb::int_(id)] = cls;
}

void init_versions(nb::module_ &core, nb::module_ &package)
{
    nb::enum_<SerializationMode>(core, "SerializationMode", nb::is_arithmetic())
        .value("DEFAULT", SerializationMode::Default)
        .value("CEREAL", SerializationMode::Cereal)
        .value("MANUAL", SerializationMode::Manual);
    static std::array<CodecTable, detail::versions.size()> tables;
    static std::array<EnumTable, detail::versions.size()> enums;
    static std::array<NamingTable, detail::versions.size()> namings;
    const nb::object names = nb::module_::import_("types").attr("SimpleNamespace");
    std::vector<Scope> bound;
    for (std::size_t i = 0; i < detail::versions.size(); ++i) {
        auto module = package.def_submodule(std::format("v{}", detail::versions[i]).c_str());
        bound.push_back({.number = detail::versions[i],
                         .module = module,
                         .codecs = &tables[i],
                         .enums = &enums[i],
                         .namings = &namings[i],
                         .names = names()});
    }
    init_types(package, bound);
    const nb::object read_only = nb::module_::import_("types").attr("MappingProxyType");
    nb::dict encodings;
    nb::dict modes;
    for (const Scope &scope : bound) {
        auto m = nb::borrow<nb::module_>(scope.module);
        m.attr("_T") = nb::type_var("_T");
        m.attr("VERSION") = scope.number;
        m.attr("packets") = read_only(scope.packets);
        nb::dict by_class;
        for (auto [cls, by_mode] : scope.modes) {
            by_class[cls] = read_only(by_mode);
        }
        encodings[nb::int_(scope.number)] = read_only(scope.encodings);
        modes[nb::int_(scope.number)] = read_only(by_class);
        m.def(
            "encode",
            [scope](nb::handle packet) {
                return encode_with(resolve_packet(scope, packet.type(), "packet"), packet, "packet");
            },
            nb::arg("packet"), "The encoded form of a packet at this protocol.");
        m.def(
            "decode",
            [scope](nb::handle cls, const nb::bytes &data) {
                const Codec &codec = resolve_packet(scope, cls, "cls");
                BinaryReader reader{std::string_view(data.c_str(), data.size())};
                return codec.decode(reader);
            },
            nb::arg("cls"), nb::arg("data"), nb::sig("def decode(cls: type[_T], data: bytes) -> _T"),
            "Reads one packet `cls` at this protocol that must span all of `data`.");
        m.def(
            "enum_integer",
            [scope](nb::handle value) { return resolve_enum(scope, value.type(), "value").integer(value); },
            nb::arg("value"), nb::sig("def enum_integer(value: enum.Enum) -> int | None"),
            "The number this protocol writes for an enum value, or None where it cannot encode it.");
        m.def(
            "enum_name", [scope](nb::handle value) { return resolve_naming(scope, value.type(), "value").name(value); },
            nb::arg("value"), nb::sig("def enum_name(value: enum.Enum) -> str | None"),
            "The name this protocol writes for an enum value, or None where it cannot name it.");
        m.def(
            "enum_cast",
            [scope](nb::handle cls, const std::string &name) { return resolve_naming(scope, cls, "cls").cast(name); },
            nb::arg("cls"), nb::arg("name"), nb::sig("def enum_cast(cls: type[_T], name: str) -> _T | None"),
            "The value this protocol reads for `name` of enum `cls`, folding case.");
        m.def(
            "enum_cast",
            [scope](nb::handle cls, nb::handle number) { return resolve_enum(scope, cls, "cls").cast(number); },
            nb::arg("cls"), nb::arg("number"), nb::sig("def enum_cast(cls: type[_T], number: int) -> _T | int | None"),
            "The value this protocol reads for `number` of enum `cls`, an int where no member holds it.");
        m.def(
            "enum_contains",
            [scope](nb::handle value) { return !resolve_enum(scope, value.type(), "value").integer(value).is_none(); },
            nb::arg("value"), nb::sig("def enum_contains(value: enum.Enum) -> bool"),
            "Whether this protocol can encode an enum value.");
        m.def(
            "enum_contains",
            [scope](nb::handle cls, const std::string &name) {
                return !resolve_naming(scope, cls, "cls").cast(name).is_none();
            },
            nb::arg("cls"), nb::arg("name"), nb::sig("def enum_contains(cls: type, name: str) -> bool"),
            "Whether this protocol can decode `name` of enum `cls`.");
        m.def(
            "enum_contains",
            [scope](nb::handle cls, nb::handle number) {
                return !resolve_enum(scope, cls, "cls").cast(number).is_none();
            },
            nb::arg("cls"), nb::arg("number"), nb::sig("def enum_contains(cls: type, number: int) -> bool"),
            "Whether this protocol can decode `number` of enum `cls`.");
        m.def(
            "enum_values", [scope](nb::handle cls) { return resolve_enum(scope, cls, "cls").values(); }, nb::arg("cls"),
            nb::sig("def enum_values(cls: type[_T]) -> tuple[_T, ...]"),
            "The distinct values of enum `cls` this protocol can encode, in declaration order.");
        m.def(
            "enum_count", [scope](nb::handle cls) { return nb::len(resolve_enum(scope, cls, "cls").values()); },
            nb::arg("cls"), nb::sig("def enum_count(cls: type) -> int"),
            "How many values of enum `cls` this protocol can encode.");
        m.def(
            "enum_names", [scope](nb::handle cls) { return resolve_naming(scope, cls, "cls").names(); }, nb::arg("cls"),
            nb::sig("def enum_names(cls: type) -> tuple[str, ...]"),
            "The names this protocol writes for enum `cls`, in declaration order.");
        m.def(
            "enum_entries", [scope](nb::handle cls) { return resolve_naming(scope, cls, "cls").entries(); },
            nb::arg("cls"), nb::sig("def enum_entries(cls: type[_T]) -> tuple[tuple[_T, str], ...]"),
            "Each value of enum `cls` this protocol writes by name, with that name, in declaration order.");
        nb::list all;
        for (nb::handle name : m.attr("__dict__")) {
            const std::string_view text = nb::borrow<nb::str>(name).c_str();
            if (!text.starts_with('_')) {
                all.append(name);
            }
        }
        m.attr("__all__") = all;
    }
    package.attr("encode") = bound.back().module.attr("encode");
    package.attr("decode") = bound.back().module.attr("decode");
    core.attr("encodings") = read_only(encodings);
    core.attr("modes") = read_only(modes);
    core.attr("_T") = nb::type_var("_T");
    core.def(
        "encode",
        [](int protocol, nb::handle value, SerializationMode mode) {
            return encode_with(resolve(codecs_at(tables, protocol), protocol, value.type(), mode, "value"), value,
                               "value");
        },
        nb::arg("protocol"), nb::arg("value"), nb::kw_only(), nb::arg("mode") = SerializationMode::Default,
        nb::sig("def encode(protocol: int, value: object, *, mode: SerializationMode = ...) -> bytes"),
        "The encoded form of any bound value at `protocol`.");
    core.def(
        "decode",
        [](int protocol, nb::handle cls, const nb::bytes &data, SerializationMode mode) {
            const Codec &codec = resolve(codecs_at(tables, protocol), protocol, cls, mode, "cls");
            BinaryReader reader{std::string_view(data.c_str(), data.size())};
            return codec.decode(reader);
        },
        nb::arg("protocol"), nb::arg("cls"), nb::arg("data"), nb::kw_only(),
        nb::arg("mode") = SerializationMode::Default,
        nb::sig("def decode(protocol: int, cls: type[_T], data: bytes, *, mode: SerializationMode = ...) -> _T"),
        "Reads one bound `cls` at `protocol` that must span all of `data`.");
}

}  // namespace bedrock::protocol::python
