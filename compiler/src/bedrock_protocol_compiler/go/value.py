from collections import Counter
from typing import override

from bedrock_protocol_compiler.descriptor import CompilerError, Primitive
from bedrock_protocol_compiler.expression import BOOL, CLASSES, UINT32, Num, wrap
from bedrock_protocol_compiler.go import names
from bedrock_protocol_compiler.printer import Printer

KINDS = {"bool": "bool", "float": "float32", "double": "float64", "str": "string", "bytes": "[]byte"}
ZEROS = {"bool": "false", "string": '""', "[]byte": "nil"}
COUNTS = ("uvarint32", "uint32", "uint16", "varint32")
FLOATS = {"float": 32, "double": 64}


def go_of(cls: Num) -> str:
    if cls.kind == "int":
        return f"{'' if cls.signed else 'u'}int{cls.bits}"
    return KINDS[cls.kind]


def atom(code: str) -> str:
    depth = 0
    for char in code:
        depth += char in "([{"
        depth -= char in ")]}"
        if depth == 0 and char in " !&|<>=+-*/^%":
            return f"({code})"
    return code


def convert(code: str, source: Num, target: Num) -> str:
    """Spells `static_cast<target>(source)` over the Go types of the two classes."""
    if source == target:
        return code
    if target == BOOL:
        return f"{atom(code)} != 0"
    if source == BOOL:
        return f"numberOf[{go_of(target)}]({code})"
    return f"{go_of(target)}({code})"


def literal(value: int | bool, cls: Num) -> str:
    if cls == BOOL:
        return "true" if value else "false"
    return str(wrap(value, cls))


class Body:
    def __init__(self, p: Printer, stream: str) -> None:
        self.p = p
        self.stream = stream
        self.counts: Counter[str] = Counter()

    def fresh(self, stem: str) -> str:
        name = f"{stem}{self.counts[stem]}"
        self.counts[stem] += 1
        return name

    def line(self, code: str) -> None:
        self.p.emit("$code$", code=code)

    def fail(self, condition: str, reason: str) -> None:
        self.p.emit(
            """
            if $condition$ {
                $stream$.Fail(stream.$reason$)
            }
            """,
            condition=condition,
            stream=self.stream,
            reason=reason,
        )


class Value:
    go: str
    zero: str
    nilable = False
    fallible = False

    def read(self, body: Body) -> str:
        raise NotImplementedError

    def write(self, body: Body, value: str) -> None:
        raise NotImplementedError

    def case(self, value: str) -> str:
        raise NotImplementedError


class Scalar(Value):
    def __init__(
        self,
        stored: Num,
        encoded: str,
        endian: str | None,
        label: str,
        printed: Num | None = None,
        enum: str | None = None,
        numbering: tuple[str, int] | None = None,
    ) -> None:
        if endian and encoded != "int32":
            raise CompilerError(f"{label}: stream has no big-endian {encoded}")
        self.stored = stored
        self.encoded = CLASSES[encoded]
        self.method = names.method(encoded, endian)
        self.printed = printed or self.encoded
        self.enum = enum
        self.numbering = numbering
        self.go = enum or go_of(stored)
        self.zero = "0" if enum is not None else ZEROS.get(self.go, "0")
        self.narrows = self.encoded.bits < self.stored.bits
        self.fallible = self.narrows or numbering is not None

    def number(self, value: str) -> str:
        return value if self.enum is None else f"{go_of(self.stored)}({value})"

    @override
    def read(self, body: Body) -> str:
        raw = f"r.Read{self.method}()"
        widens = self.stored.kind == self.encoded.kind == "int" and self.stored.bits >= self.encoded.bits
        if self.stored == self.encoded or widens:
            stored = convert(raw, self.encoded, self.stored)
        else:
            read = body.fresh("v")
            stored = body.fresh("s")
            body.line(f"{read} := {raw}")
            body.line(f"{stored} := {convert(read, self.encoded, self.stored)}")
            body.fail(f"{convert(stored, self.stored, self.encoded)} != {read}", "ErrOutOfRange")
        if self.enum is None:
            return stored
        if self.numbering is None:
            return f"{self.enum}({stored})"
        helper, since = self.numbering
        value = body.fresh("e")
        placed = body.fresh("ok")
        body.line(f"{value}, {placed} := {helper}FromNumber({since}, {stored})")
        body.fail(f"!{placed}", "ErrUnknownValue")
        return value

    @override
    def write(self, body: Body, value: str) -> None:
        if self.numbering is not None:
            helper, since = self.numbering
            number = body.fresh("n")
            placed = body.fresh("ok")
            body.line(f"{number}, {placed} := {helper}ToNumber({since}, {value})")
            body.fail(f"!{placed}", "ErrUnknownValue")
            value = number
        else:
            value = self.number(value)
        if not self.narrows:
            body.line(f"w.Write{self.method}({convert(value, self.stored, self.encoded)})")
            return
        written = body.fresh("w")
        body.line(f"{written} := {convert(value, self.stored, self.encoded)}")
        body.fail(f"{convert(written, self.encoded, self.stored)} != {value}", "ErrOutOfRange")
        body.line(f"w.Write{self.method}({written})")

    @override
    def case(self, value: str) -> str:
        if self.stored.kind in FLOATS:
            return f"caseFloat{FLOATS[self.stored.kind]}({value})"
        if self.stored.kind == "str":
            return f"caseString({value})"
        if self.stored.kind == "bytes":
            return f"caseBytes({value})"
        if self.numbering is not None:
            helper, since = self.numbering
            return f"caseNumber({helper}ToNumber({since}, {value}))"
        return convert(self.number(value), self.stored, self.printed)


class Named(Value):
    def __init__(self, enum: str, helper: str, since: int, stored: Num) -> None:
        self.go = enum
        self.zero = "0"
        self.helper = helper
        self.since = since
        self.stored = stored
        self.fallible = True

    def number(self, value: str) -> str:
        return f"{go_of(self.stored)}({value})"

    @override
    def read(self, body: Body) -> str:
        value = body.fresh("e")
        placed = body.fresh("ok")
        body.line(f"{value}, {placed} := {self.helper}FromName({self.since}, stream.FoldASCII(r.ReadString()))")
        body.fail(f"!{placed}", "ErrUnknownValue")
        return value

    @override
    def write(self, body: Body, value: str) -> None:
        name = body.fresh("name")
        placed = body.fresh("ok")
        body.line(f"{name}, {placed} := {self.helper}Name({self.since}, {value})")
        body.fail(f"!{placed}", "ErrUnknownValue")
        body.line(f"w.WriteString({name})")

    @override
    def case(self, value: str) -> str:
        return f"caseName({self.helper}Name({self.since}, {value}))"


class Reference(Value):
    def __init__(self, go: str, codec: str, cased: str, bound: str | None = None, argument: str = "") -> None:
        self.type = go
        self.bound = bound
        self.go = f"*{go}"
        self.zero = "nil"
        self.nilable = True
        self.fallible = True
        self.codec = codec
        self.cased = cased
        self.argument = argument

    @override
    def read(self, body: Body) -> str:
        value = body.fresh("m")
        body.line(f"{value} := new({self.type})")
        body.line(f"{value}.decode{self.codec}(r{self.argument})")
        return value

    @override
    def write(self, body: Body, value: str) -> None:
        body.line(f"{atom(value)}.encode{self.codec}(w{self.argument})")

    @override
    def case(self, value: str) -> str:
        return f"{atom(value)}.case{self.cased}()"


class ColorValue(Reference):
    """A struct of four float channels packed a byte each, `channels` naming its members from the highest byte."""

    def __init__(self, go: str, cased: str, bound: str, channels: tuple[str, ...], encoded: str) -> None:
        super().__init__(go, cased, cased, bound)
        self.channels = channels
        self.encoded = encoded
        self.method = names.method(encoded)

    @override
    def read(self, body: Body) -> str:
        raw = f"r.Read{self.method}()"
        packed = f"parseColor({raw})" if self.encoded == "str" else convert(raw, CLASSES[self.encoded], UINT32)
        read = [body.fresh("c") for _ in self.channels]
        body.line(f"{', '.join(read)} := unpackColor({packed})")
        members = ", ".join(f"{member}: {channel}" for member, channel in zip(self.channels, read, strict=True))
        return f"&{self.type}{{{members}}}"

    @override
    def write(self, body: Body, value: str) -> None:
        packed = body.fresh("p")
        placed = body.fresh("ok")
        channels = ", ".join(f"{atom(value)}.Get{member}()" for member in self.channels)
        body.line(f"{packed}, {placed} := packColor({channels})")
        body.fail(f"!{placed}", "ErrOutOfRange")
        written = f"formatColor({packed})" if self.encoded == "str" else convert(packed, UINT32, CLASSES[self.encoded])
        body.line(f"w.Write{self.method}({written})")


class BuiltinValue(Value):
    def __init__(self, stem: str, name: str, zero: str, nilable: bool) -> None:
        self.go = f"{stem}.{name}"
        self.stem = stem
        self.name = name
        self.zero = zero
        self.nilable = nilable
        self.fallible = True

    @override
    def read(self, body: Body) -> str:
        return f"{self.stem}.Read{self.name}(r)"

    @override
    def write(self, body: Body, value: str) -> None:
        body.line(f"{self.stem}.Write{self.name}(w, {value})")

    @override
    def case(self, value: str) -> str:
        return f"case{self.name}({value})"


class BitsetValue(Value):
    go = "Bitset"
    zero = "Bitset{}"
    fallible = True

    def __init__(self, width: int) -> None:
        self.width = width

    @override
    def read(self, body: Body) -> str:
        return f"readBitset(r, {self.width})"

    @override
    def write(self, body: Body, value: str) -> None:
        body.line(f"writeBitset(w, {value}, {self.width})")

    @override
    def case(self, value: str) -> str:
        return f"caseBitset({value})"


class ListValue(Value):
    def __init__(self, element: Value, prefix: Primitive | None, size: int | None, label: str, blob: bool) -> None:
        if prefix is not None and prefix.name not in COUNTS:
            raise CompilerError(f"{label}: a list prefixed by {prefix.name} is not supported")
        self.element = element
        self.prefix = prefix
        self.size = size
        self.blob = blob
        self.go = f"[]{element.go}" if size is None else f"[{size}]{element.go}"
        self.zero = "nil" if size is None else f"{self.go}{{}}"
        self.nilable = size is None
        self.fallible = element.fallible

    def read_into(self, body: Body, count: str | None = None) -> str:
        elements = body.fresh("list")
        index = body.fresh("i")
        if self.size is None:
            total = body.fresh("count")
            if count is not None:
                body.line(f"{total} := r.Count({count})")
            elif self.prefix is not None:
                body.line(f"{total} := r.Read{names.method(self.prefix.name)}Count()")
            else:
                raise CompilerError(f"{self.go}: a list needs a prefix or a count")
            body.line(f"{elements} := make({self.go}, 0, stream.InitialCapacity({total}))")
            loop = f"for {index} := 0; {index} < {total}; {index}++ {{"
            store = f"{elements} = append({elements}, $element$)"
        else:
            body.line(f"var {elements} {self.go}")
            loop = f"for {index} := range {elements} {{"
            store = f"{elements}[{index}] = $element$"
        body.p.emit(loop)
        with body.p.indent():
            body.p.emit(store, element=self.element.read(body))
            body.p.emit(
                """
                if r.Failed() {
                    r.PrependIndex($index$)
                    break
                }
                """,
                index=index,
            )
        body.p.emit("}")
        return elements

    @override
    def read(self, body: Body) -> str:
        return self.read_into(body)

    @override
    def write(self, body: Body, value: str) -> None:
        if self.prefix is not None:
            prefix = CLASSES[self.prefix.name]
            body.line(f"w.Write{names.method(self.prefix.name)}({go_of(prefix)}(len({value})))")
        index = body.fresh("i") if self.element.fallible else "_"
        element = body.fresh("e")
        body.p.emit(f"for {index}, {element} := range {value} {{")
        with body.p.indent():
            self.element.write(body, element)
            if self.element.fallible:
                body.p.emit(
                    """
                    if w.Failed() {
                        w.PrependIndex($index$)
                        break
                    }
                    """,
                    index=index,
                )
        body.p.emit("}")

    @override
    def case(self, value: str) -> str:
        if self.blob:
            return f"caseBytes({atom(value)}[:])"
        return f"caseList({atom(value)}[:], func(v {self.element.go}) any {{ return {self.element.case('v')} }})"
