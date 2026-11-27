import json
from collections import Counter
from typing import override

from bedrock_protocol_compiler.descriptor import CompilerError, Primitive
from bedrock_protocol_compiler.expression import BOOL, CLASSES, Num, wrap
from bedrock_protocol_compiler.java.names import atom
from bedrock_protocol_compiler.printer import Printer

JAVA = {"bool": "boolean", "float": "float", "double": "double", "str": "String", "bytes": "byte[]"}
BOXED = {"boolean": "Boolean", "int": "Integer", "long": "Long", "float": "Float", "double": "Double"}
DEFAULTS = {
    "boolean": "false",
    "int": "0",
    "long": "0L",
    "float": "0.0f",
    "double": "0.0",
    "String": '""',
    "byte[]": "new byte[0]",
}
HASHES = {"boolean": "Boolean", "int": "Integer", "long": "Long", "float": "Float", "double": "Double"}
READS = {
    "bool": ("ByteBufCodec.readBoolean(buf)", "boolean"),
    "int8": ("ByteBufCodec.readByte(buf)", "byte"),
    "uint8": ("ByteBufCodec.readUnsignedByte(buf)", "int"),
    "int16": ("ByteBufCodec.readShortLE(buf)", "short"),
    "uint16": ("ByteBufCodec.readUnsignedShortLE(buf)", "int"),
    "int32": ("ByteBufCodec.readIntLE(buf)", "int"),
    "uint32": ("ByteBufCodec.readIntLE(buf)", "int"),
    "int64": ("ByteBufCodec.readLongLE(buf)", "long"),
    "uint64": ("ByteBufCodec.readLongLE(buf)", "long"),
    "varint32": ("ByteBufCodec.readVarInt(buf)", "int"),
    "uvarint32": ("ByteBufCodec.readUnsignedVarInt(buf)", "int"),
    "varint64": ("ByteBufCodec.readVarLong(buf)", "long"),
    "uvarint64": ("ByteBufCodec.readUnsignedVarLong(buf)", "long"),
    "float": ("ByteBufCodec.readFloatLE(buf)", "float"),
    "double": ("ByteBufCodec.readDoubleLE(buf)", "double"),
    "str": ("ByteBufCodec.readString(buf)", "String"),
    "bytes": ("ByteBufCodec.readByteArray(buf)", "byte[]"),
}
BIG_READS = {"int32": ("ByteBufCodec.readInt(buf)", "int"), "uint32": ("ByteBufCodec.readInt(buf)", "int")}
WRITES = {
    "bool": "buf.writeBoolean({});",
    "int8": "buf.writeByte({});",
    "uint8": "buf.writeByte({});",
    "int16": "buf.writeShortLE({});",
    "uint16": "buf.writeShortLE({});",
    "int32": "buf.writeIntLE({});",
    "uint32": "buf.writeIntLE({});",
    "int64": "buf.writeLongLE({});",
    "uint64": "buf.writeLongLE({});",
    "varint32": "ByteBufCodec.writeVarInt(buf, {});",
    "uvarint32": "ByteBufCodec.writeUnsignedVarInt(buf, {});",
    "varint64": "ByteBufCodec.writeVarLong(buf, {});",
    "uvarint64": "ByteBufCodec.writeUnsignedVarLong(buf, {});",
    "float": "buf.writeFloatLE({});",
    "double": "buf.writeDoubleLE({});",
    "str": "ByteBufCodec.writeString(buf, {});",
    "bytes": "ByteBufCodec.writeByteArray(buf, {});",
}
BIG_WRITES = {"int32": "buf.writeInt({});", "uint32": "buf.writeInt({});"}
LIST_COUNTS = {
    "uvarint32": "ByteBufCodec.readUvarint32Count(buf)",
    "uint32": "ByteBufCodec.readUint32Count(buf)",
    "uint16": "ByteBufCodec.readUint16Count(buf)",
    "varint32": "ByteBufCodec.readVarint32Count(buf)",
}


def java_of(cls: Num) -> str:
    if cls.kind == "int":
        return "long" if cls.bits == 64 else "int"
    return JAVA[cls.kind]


def widened(code: str, java: str, rep: str) -> str:
    if rep == "int" and java in ("byte", "short"):
        return f"(int) {atom(code)}"
    if rep == "long" and java in ("byte", "short", "int"):
        return f"(long) {atom(code)}"
    return code


def convert(code: str, java: str, source: Num, target: Num, rep: str) -> str:
    """Spells `static_cast<target>(source)` over the Java representations, as a `rep`."""
    if BOOL in (source, target):
        if source == target:
            if java == rep:
                return code
            return f"({code} ? 1 : 0)" if java == "boolean" else f"{atom(code)} != 0"
        if target == BOOL:
            truth = code if java == "boolean" else f"{atom(code)} != 0"
            return truth if rep == "boolean" else f"({truth} ? 1 : 0)"
        if java == "boolean":
            return f"({code} ? 1L : 0L)" if rep == "long" else f"({code} ? 1 : 0)"
        return widened(code, java, rep)
    if source == target or source.kind != "int":
        return widened(code, java, rep)
    if target.bits == 64:
        if source.bits == 64:
            return code
        if source.bits == 32 and not source.signed:
            return f"Integer.toUnsignedLong({code})"
        return f"(long) {atom(code)}"
    if target.bits == 32:
        return f"(int) {atom(code)}" if source.bits == 64 else widened(code, java, rep)
    if source.bits < target.bits and (target.signed or not source.signed):
        return widened(code, java, rep)
    if not target.signed:
        masked = f"{atom(code)} & {'0xFF' if target.bits == 8 else '0xFFFF'}"
        return f"(int) ({masked})" if java == "long" else masked
    return f"(int) ({'byte' if target.bits == 8 else 'short'}) {atom(code)}"


def bits(code: str, java: str, source: Num, target: Num) -> str:
    """Spells the argument a ByteBuf write takes for `static_cast<target>(source)`."""
    if target == BOOL:
        return code if java == "boolean" else f"{atom(code)} != 0"
    if target.kind != "int":
        return code
    if java == "boolean":
        return f"({code} ? 1L : 0L)" if target.bits == 64 else f"({code} ? 1 : 0)"
    if target.bits < 64:
        return f"(int) {atom(code)}" if java == "long" else code
    if java != "long" and source.kind == "int" and source.bits == 32 and not source.signed:
        return f"Integer.toUnsignedLong({code})"
    return code


def literal(value: int | bool, cls: Num) -> str:
    if cls == BOOL:
        return "true" if value else "false"
    wrapped = wrap(value, cls)
    suffix = "L" if cls.bits == 64 else ""
    if cls.bits >= 32 and wrapped >= 1 << (cls.bits - 1):
        return f"0x{wrapped:X}{suffix}"
    return f"{wrapped}{suffix}"


class Body:
    def __init__(self, p: Printer) -> None:
        self.p = p
        self.counts: Counter[str] = Counter()

    def fresh(self, stem: str) -> str:
        name = f"{stem}{self.counts[stem]}"
        self.counts[stem] += 1
        return name

    def line(self, code: str) -> None:
        self.p.emit("$code$", code=code)

    def fail(self, condition: str, factory: str) -> None:
        self.p.emit(
            """
            if ($condition$) {
                throw DecodeException.$factory$(buf.readerIndex());
            }
            """,
            condition=condition,
            factory=factory,
        )

    def reject(self, condition: str, message: str) -> None:
        self.p.emit(
            """
            if ($condition$) {
                throw new IllegalArgumentException($message$);
            }
            """,
            condition=condition,
            message=message,
        )


class Value:
    java: str
    label: str
    mutable = False
    trivial = True
    enum: str | None = None
    number: Num | None = None

    @property
    def boxed(self) -> str:
        return BOXED.get(self.java, self.java)

    def annotated(self, nullable: bool = False) -> str:
        if self.java in BOXED:
            return self.java
        mark = "@Nullable" if nullable else "@NotNull"
        if self.java.endswith("[]"):
            return f"{self.java[:-2]} {mark} []"
        return f"{mark} {self.java}"

    def default(self) -> str:
        raise NotImplementedError

    def read(self, body: Body) -> str:
        raise NotImplementedError

    def write(self, body: Body, value: str) -> None:
        raise NotImplementedError

    def adopt(self, body: Body, value: str) -> str:
        raise NotImplementedError

    def copy(self, value: str) -> str:
        return value

    def unboxed(self, value: str) -> str:
        return f"({self.java}) {value}" if self.java in BOXED else value

    def equal(self, a: str, b: str) -> str:
        return f"{a}.equals({b})"

    def hash(self, a: str) -> str:
        return f"{a}.hashCode()"

    def nullable_equal(self, a: str, b: str) -> str:
        return f"Objects.equals({a}, {b})"

    def nullable_hash(self, a: str) -> str:
        return f"Objects.hashCode({a})"

    def comparator(self) -> str | None:
        raise CompilerError(f"{self.label}: a {self.java} is not a map key")


class Scalar(Value):
    def __init__(
        self,
        stored: str,
        encoded: str,
        endian: str | None,
        label: str,
        enum: str | None = None,
        numbering: tuple[str, int] | None = None,
    ) -> None:
        self.stored = CLASSES[stored]
        self.numbering = numbering
        self.encoded_name = encoded
        self.encoded = CLASSES[encoded]
        self.label = label
        self.enum = enum
        self.java = "int" if enum is not None and self.stored == BOOL else java_of(self.stored)
        self.number = Num("int", False, 8) if self.java == "int" and self.stored == BOOL else self.stored
        self.mutable = self.java == "byte[]"
        self.trivial = self.narrow("value") is None and not self.mutable
        reads, writes = (BIG_READS, BIG_WRITES) if endian else (READS, WRITES)
        if encoded not in reads:
            raise CompilerError(f"{label}: ByteBufCodec has no big-endian {encoded}")
        self.raw, self.raw_java = reads[encoded]
        self.call = writes[encoded]

    def narrow(self, value: str) -> str | None:
        if self.java == "int" and self.stored == BOOL:
            return f"({value} & ~1) != 0"
        if self.stored.kind != "int" or self.stored.bits >= 32:
            return None
        if self.stored.signed:
            return f"{value} != ({'byte' if self.stored.bits == 8 else 'short'}) {value}"
        return f"({value} & ~{'0xFF' if self.stored.bits == 8 else '0xFFFF'}) != 0"

    @override
    def default(self) -> str:
        return DEFAULTS[self.java]

    @override
    def read(self, body: Body) -> str:
        widens = self.stored.kind == self.encoded.kind == "int" and self.stored.bits >= self.encoded.bits
        if self.stored == self.encoded or widens:
            stored = convert(self.raw, self.raw_java, self.encoded, self.stored, self.java)
        else:
            local = "int" if self.raw_java in ("byte", "short") else self.raw_java
            read = body.fresh("v")
            stored = body.fresh("s")
            body.line(f"{local} {read} = {self.raw};")
            body.line(f"{self.java} {stored} = {convert(read, local, self.encoded, self.stored, self.java)};")
            body.fail(f"{convert(stored, self.java, self.stored, self.encoded, local)} != {read}", "outOfRange")
        if self.numbering is None:
            return stored
        helper, since = self.numbering
        number = body.fresh("n")
        body.line(f"int {number} = {stored};")
        body.fail(f"!{helper}.decodes({since}, {number})", "unknownValue")
        return f"{helper}.fromNumber({since}, {number})"

    @override
    def write(self, body: Body, value: str) -> None:
        if self.numbering is not None:
            value = f"{self.numbering[0]}.toNumber({self.numbering[1]}, {value})"
        if self.encoded.bits >= self.stored.bits:
            body.line(self.call.format(bits(value, self.java, self.stored, self.encoded)))
            return
        if self.numbering is not None:
            number = body.fresh("n")
            body.line(f"{self.java} {number} = {value};")
            value = number
        rep = java_of(self.encoded)
        written = body.fresh("w")
        body.line(f"{rep} {written} = {convert(value, self.java, self.stored, self.encoded, rep)};")
        body.reject(
            f"{convert(written, rep, self.encoded, self.stored, self.java)} != {value}",
            f'"{self.label}: " + {value} + " is out of range"',
        )
        body.line(self.call.format(bits(written, rep, self.encoded, self.encoded)))

    @override
    def adopt(self, body: Body, value: str) -> str:
        condition = self.narrow(value)
        if condition is not None:
            body.reject(condition, f'"{self.label}: cannot hold " + {value}')
        if self.java == "String":
            return f"Objects.requireNonNull({value})"
        return self.copy(value)

    @override
    def copy(self, value: str) -> str:
        return f"{value}.clone()" if self.mutable else value

    @override
    def equal(self, a: str, b: str) -> str:
        if self.java == "float":
            return f"Float.floatToIntBits({a}) == Float.floatToIntBits({b})"
        if self.java == "double":
            return f"Double.doubleToLongBits({a}) == Double.doubleToLongBits({b})"
        if self.java in BOXED:
            return f"{a} == {b}"
        if self.mutable:
            return f"Arrays.equals({a}, {b})"
        return super().equal(a, b)

    @override
    def hash(self, a: str) -> str:
        if self.java in HASHES:
            return f"{HASHES[self.java]}.hashCode({a})"
        if self.mutable:
            return f"Arrays.hashCode({a})"
        return super().hash(a)

    @override
    def nullable_equal(self, a: str, b: str) -> str:
        return f"Arrays.equals({a}, {b})" if self.mutable else super().nullable_equal(a, b)

    @override
    def nullable_hash(self, a: str) -> str:
        return f"Arrays.hashCode({a})" if self.mutable else super().nullable_hash(a)

    @override
    def comparator(self) -> str | None:
        if self.enum is not None:
            raise CompilerError(f"{self.label}: an integer-coded enum is not a map key")
        if self.java == "String":
            return "ByteBufCodec.STR_ORDER"
        if self.java in ("float", "double"):
            return "(a, b) -> a < b ? -1 : b < a ? 1 : 0"
        if self.stored.kind == "int" and self.stored.bits >= 32 and not self.stored.signed:
            return "Long::compareUnsigned" if self.stored.bits == 64 else "Integer::compareUnsigned"
        if self.mutable:
            return super().comparator()
        return None


class NamedScalar(Scalar):
    def __init__(self, stored: str, label: str, enum: str, since: str) -> None:
        super().__init__(stored, stored, None, label, enum)
        self.since = since

    @override
    def read(self, body: Body) -> str:
        return f"{self.enum}.decode({self.since}buf).getNumber()"

    @override
    def write(self, body: Body, value: str) -> None:
        constant = f"Objects.requireNonNullElse({self.enum}.forNumber({value}), {self.enum}.UNRECOGNIZED)"
        body.line(f"{constant}.encode({self.since}buf);")


class Reference(Value):
    def __init__(
        self,
        java: str,
        default: str,
        read: str,
        write: str,
        label: str,
        copy: str | None = None,
        number: Num | None = None,
    ) -> None:
        self.java = java
        self.initial = default
        self.decode = read
        self.encode = write
        self.label = label
        self.duplicate = copy
        self.mutable = copy is not None
        self.number = number
        self.trivial = copy is None and number is None

    @override
    def default(self) -> str:
        return self.initial

    @override
    def read(self, body: Body) -> str:
        return self.decode

    @override
    def write(self, body: Body, value: str) -> None:
        body.line(self.encode.format(value))

    @override
    def adopt(self, body: Body, value: str) -> str:
        if self.number is not None:
            body.reject(
                f"Objects.requireNonNull({value}) == {self.java}.UNRECOGNIZED",
                f'"{self.label}: cannot hold " + {value}',
            )
            return value
        if self.duplicate is not None:
            return self.duplicate.format(value)
        return f"Objects.requireNonNull({value})"

    @override
    def copy(self, value: str) -> str:
        return value if self.duplicate is None else self.duplicate.format(value)

    @override
    def equal(self, a: str, b: str) -> str:
        return f"{a} == {b}" if self.number is not None else super().equal(a, b)

    @override
    def comparator(self) -> str | None:
        if self.number is None:
            return super().comparator()
        if self.number.bits == 32 and not self.number.signed:
            return "(a, b) -> Integer.compareUnsigned(a.getNumber(), b.getNumber())"
        return f"Comparator.comparingInt({self.java}::getNumber)"


class PackedColor(Reference):
    """A struct of four floats coded as one 32-bit value, `channels` naming its members from the top byte."""

    def __init__(self, java: str, channels: list[str], encoded: str, label: str) -> None:
        read, write = READS[encoded][0], WRITES[encoded]
        if encoded == "str":
            read = "ByteBufCodec.parseColor(ByteBufCodec.readByteArray(buf))"
            write = write.format('"#" + Integer.toHexString({})')
        super().__init__(java, f"{java}.getDefaultInstance()", read, write, label)
        self.channels = channels

    @override
    def read(self, body: Body) -> str:
        packed = body.fresh("packed")
        body.line(f"int {packed} = {self.decode};")
        shifted = (f"{packed} >>> 24", f"{packed} >>> 16 & 0xFF", f"{packed} >>> 8 & 0xFF", f"{packed} & 0xFF")
        setters = "".join(
            f".set{member}(({channel}) / 255.0f)" for member, channel in zip(self.channels, shifted, strict=True)
        )
        return f"{self.java}.newBuilder(){setters}.build()"

    @override
    def write(self, body: Body, value: str) -> None:
        channels = ", ".join(f"{value}.get{member}()" for member in self.channels)
        body.line(self.encode.format(f"ByteBufCodec.packColor({channels}, {json.dumps(self.label)})"))


class BitsetValue(Value):
    def __init__(self, width: int, label: str) -> None:
        self.java = "BitSet"
        self.width = width
        self.label = label
        self.mutable = True
        self.trivial = False

    @override
    def default(self) -> str:
        return "new BitSet()"

    @override
    def read(self, body: Body) -> str:
        return f"ByteBufCodec.readBitSet(buf, {self.width})"

    @override
    def write(self, body: Body, value: str) -> None:
        body.line(f"ByteBufCodec.writeBitSet(buf, {value}, {self.width}, {json.dumps(self.label)});")

    @override
    def adopt(self, body: Body, value: str) -> str:
        body.reject(f"{value}.length() > {self.width}", f'"{self.label}: cannot hold bit " + ({value}.length() - 1)')
        return self.copy(value)

    @override
    def copy(self, value: str) -> str:
        return f"(BitSet) {value}.clone()"


class ListValue(Value):
    def __init__(self, element: Value, prefix: Primitive | None, size: int | None, label: str) -> None:
        if element.mutable:
            raise CompilerError(f"{label}: a {element.java} inside a list or array is not supported")
        self.element = element
        self.prefix = prefix
        self.counted = None if prefix is None else LIST_COUNTS[prefix.name]
        self.size = size
        self.label = label
        self.java = f"List<{element.boxed}>"
        self.trivial = False

    @override
    def default(self) -> str:
        if self.size is None:
            return "List.of()"
        return f"Collections.nCopies({self.size}, {self.element.default()})"

    def read_into(self, body: Body, count: str | None = None) -> str:
        elements = body.fresh("list")
        index = body.fresh("i")
        if self.size is None:
            total = body.fresh("count")
            body.line(f"int {total} = ByteBufCodec.toCount(buf, {self.counted if count is None else count});")
            body.line(
                f"List<{self.element.boxed}> {elements} = new ArrayList<>(ByteBufCodec.initialCapacity({total}));"
            )
        else:
            total = str(self.size)
            body.line(f"List<{self.element.boxed}> {elements} = new ArrayList<>({total});")
        body.p.emit(
            """
            for (int $index$ = 0; $index$ < $total$; $index$++) {
                try {
                    $element$
                } catch (DecodeException e) {
                    throw e.prepend($index$);
                }
            }
            """,
            index=index,
            total=total,
            element=lambda: body.line(f"{elements}.add({self.element.read(body)});"),
        )
        return elements

    @override
    def read(self, body: Body) -> str:
        return f"Collections.unmodifiableList({self.read_into(body)})"

    @override
    def write(self, body: Body, value: str) -> None:
        if self.prefix is not None:
            prefix = CLASSES[self.prefix.name]
            body.line(WRITES[self.prefix.name].format(bits(f"{value}.size()", "int", CLASSES["int32"], prefix)))
        element = body.fresh("element")
        body.p.emit(
            """
            for ($type$ $element$ : $value$) {
                $body$
            }
            """,
            type=self.element.java,
            element=element,
            value=value,
            body=lambda: self.element.write(body, element),
        )

    @override
    def adopt(self, body: Body, value: str) -> str:
        elements = body.fresh("list")
        if self.element.trivial:
            body.line(f"List<{self.element.boxed}> {elements} = List.copyOf({value});")
            adopted = elements
        else:
            element = body.fresh("element")
            body.line(f"List<{self.element.boxed}> {elements} = new ArrayList<>();")
            body.p.emit(
                """
                for ($type$ $element$ : $value$) {
                    $body$
                }
                """,
                type=self.element.java,
                element=element,
                value=value,
                body=lambda: body.line(f"{elements}.add({self.element.adopt(body, element)});"),
            )
            adopted = f"Collections.unmodifiableList({elements})"
        if self.size is not None:
            body.reject(
                f"{elements}.size() != {self.size}", f'"{self.label}: cannot hold " + {elements}.size() + " elements"'
            )
        return adopted
