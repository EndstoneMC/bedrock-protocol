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

void init_versions(nb::module_ &parent)
{
    nb::enum_<SerializationMode>(parent, "SerializationMode", nb::is_arithmetic())
        .value("DEFAULT", SerializationMode::Default)
        .value("CEREAL", SerializationMode::Cereal)
        .value("MANUAL", SerializationMode::Manual);
    static std::array<CodecTable, versions.size()> tables;
    const nb::object names = nb::module_::import_("types").attr("SimpleNamespace");
    std::vector<Scope> bound;
    for (std::size_t i = 0; i < versions.size(); ++i) {
        auto module = parent.def_submodule(std::format("v{}", versions[i]).c_str());
        bound.push_back({.number = versions[i], .module = module, .codecs = &tables[i], .names = names()});
    }
    init_types(parent, bound);
    const nb::object read_only = nb::module_::import_("types").attr("MappingProxyType");
    for (const Scope &scope : bound) {
        auto m = nb::borrow<nb::module_>(scope.module);
        m.attr("_T") = nb::type_var("_T");
        nb::dict modes;
        for (auto [cls, by_mode] : scope.modes) {
            modes[cls] = read_only(by_mode);
        }
        m.attr("encodings") = read_only(scope.encodings);
        m.attr("packets") = read_only(scope.packets);
        m.attr("modes") = read_only(modes);
        m.def(
            "encode",
            [codecs = scope.codecs, number = scope.number](nb::handle value, SerializationMode mode) {
                const Codec &codec = resolve(*codecs, number, value.type(), mode, "value");
                if (!nb::inst_ready(value)) {
                    throw nb::type_error(
                        std::format("value: {} instance is not initialized", nb::repr(value.type()).c_str()).c_str());
                }
                std::string buffer;
                BinaryWriter writer{buffer};
                if (auto written = codec.encode(writer, value); !written) {
                    throw_encode_error(written.error());
                }
                return nb::bytes(buffer.data(), buffer.size());
            },
            nb::arg("value"), nb::kw_only(), nb::arg("mode") = SerializationMode::Default,
            nb::sig("def encode(value: object, *, mode: bedrock_protocol.SerializationMode = ...) -> bytes"),
            "The encoded form at this protocol.");
        m.def(
            "decode",
            [codecs = scope.codecs, number = scope.number](nb::handle cls, const nb::bytes &data,
                                                           SerializationMode mode) {
                const Codec &codec = resolve(*codecs, number, cls, mode, "cls");
                BinaryReader reader{std::string_view(data.c_str(), data.size())};
                return codec.decode(reader);
            },
            nb::arg("cls"), nb::arg("data"), nb::kw_only(), nb::arg("mode") = SerializationMode::Default,
            nb::sig("def decode(cls: type[_T], data: bytes, *, mode: bedrock_protocol.SerializationMode = ...) -> _T"),
            "Reads one `cls` at this protocol that must span all of `data`.");
        nb::list all;
        for (nb::handle name : m.attr("__dict__")) {
            const std::string_view text = nb::borrow<nb::str>(name).c_str();
            if (!text.starts_with('_')) {
                all.append(name);
            }
        }
        m.attr("__all__") = all;
    }
}

}  // namespace bedrock::protocol::python
