from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from bedrock_protocol_compiler.descriptor import (
    Binary,
    Choice,
    CompilerError,
    Expression,
    FieldRef,
    Int,
    MemberRef,
    Not,
    Test,
)
from bedrock_protocol_compiler.schema import Encoding, EnumModel, Schema


@dataclass(frozen=True)
class Num:
    kind: str
    signed: bool = True
    bits: int = 0


BOOL = Num("bool")
FLOAT = Num("float")
DOUBLE = Num("double")
STR = Num("str")
BYTES = Num("bytes")
CLASSES = {
    "bool": BOOL,
    "float": FLOAT,
    "double": DOUBLE,
    "str": STR,
    "bytes": BYTES,
    "int8": Num("int", True, 8),
    "uint8": Num("int", False, 8),
    "int16": Num("int", True, 16),
    "uint16": Num("int", False, 16),
    "int32": Num("int", True, 32),
    "varint32": Num("int", True, 32),
    "uint32": Num("int", False, 32),
    "uvarint32": Num("int", False, 32),
    "int64": Num("int", True, 64),
    "varint64": Num("int", True, 64),
    "uint64": Num("int", False, 64),
    "uvarint64": Num("int", False, 64),
}
INT32 = CLASSES["int32"]
UINT32 = CLASSES["uint32"]
INT64 = CLASSES["int64"]
UINT64 = CLASSES["uint64"]
LOGICAL = {"and": "&&", "or": "||"}
COMPARISONS = ("==", "!=", "<")


class Operand(Protocol):
    term: Num | None
    bitset: bool
    sized: bool


@dataclass(frozen=True)
class Term:
    code: str | None
    cls: Num
    value: int = 0


def enum_class(enum_type: EnumModel) -> Num:
    underlying = CLASSES[enum_type.underlying.name]
    return Num("int", False, 8) if underlying == BOOL else underlying


def common(a: Num, b: Num) -> Num:
    if a.signed == b.signed:
        return a if a.bits >= b.bits else b
    unsigned, signed = (a, b) if not a.signed else (b, a)
    return unsigned if unsigned.bits >= signed.bits else signed


def wrap(value: int | bool, cls: Num) -> int:
    wrapped = int(value) % (1 << cls.bits)
    if cls.signed and wrapped >= 1 << (cls.bits - 1):
        wrapped -= 1 << cls.bits
    return wrapped


class Renderer[O: Operand]:
    """Types an expression as C++ promotes it, leaving each backend to spell its terms."""

    backend = ""

    def __init__(self, schema: Schema, encoding: Encoding, operands: Mapping[str, O]) -> None:
        self.schema = schema
        self.encoding = encoding
        self.operands = operands

    def label(self, operand: O) -> str:
        raise NotImplementedError

    def access(self, operand: O) -> str:
        raise NotImplementedError

    def test(self, operand: O, bit: int) -> str:
        raise NotImplementedError

    def choice(self, test: str, first: str, second: str) -> str:
        raise NotImplementedError

    def counted(self, code: str) -> str:
        raise NotImplementedError

    def nonzero(self, code: str) -> str:
        raise NotImplementedError

    def constant(self, value: int, cls: Num) -> str:
        raise NotImplementedError

    def cast(self, code: str, source: Num, target: Num) -> str:
        raise NotImplementedError

    def widened(self, code: str, source: Num) -> str:
        return self.cast(code, source, INT32)

    def binary(self, operator: str, first: Term, second: Term, cls: Num) -> Term:
        spelled = f"({self.spell(first, cls)}) {operator} ({self.spell(second, cls)})"
        return Term(spelled, BOOL if operator in COMPARISONS else cls)

    def predicate(self, expression: Expression) -> str:
        term = self.term(expression)
        if term.cls == BOOL and term.code is not None:
            return term.code
        return self.nonzero(self.spell(term, term.cls))

    def copies(self, expression: Expression) -> str:
        return self.spell(self.promoted(self.term(expression)), INT32)

    def member(self, member: MemberRef) -> Term:
        enum_type = self.schema.enum_type(member.enum, self.encoding.since)
        resolved = self.schema.resolve(member, self.encoding.since)
        value = self.schema.enumerators(enum_type).get(resolved.name)
        if value is None:
            value = self.schema.number(self.encoding, member)
        return Term(None, enum_class(enum_type), value)

    def term(self, expression: Expression) -> Term:
        match expression:
            case FieldRef(name=name):
                operand = self.operands[name]
                if operand.term is None:
                    raise CompilerError(f"{self.label(operand)}: is not an integer, a bool or an enum")
                return Term(self.access(operand), operand.term)
            case MemberRef():
                return self.member(expression)
            case Int(value=value):
                if -(1 << 31) <= value < 1 << 31:
                    return Term(None, INT32, value)
                return Term(None, INT64 if -(1 << 63) <= value < 1 << 63 else UINT64, value)
            case Test(field=name, member=member):
                operand = self.operands[name]
                if not operand.bitset:
                    raise CompilerError(f"{self.label(operand)}: is not a bitset")
                return Term(self.test(operand, self.schema.number(self.encoding, member)), BOOL)
            case Not(operand=operand):
                return Term(f"!({self.predicate(operand)})", BOOL)
            case Choice(test=test, when_true=when_true, when_false=when_false):
                first = self.promoted(self.term(when_true))
                second = self.promoted(self.term(when_false))
                cls = common(first.cls, second.cls)
                return Term(self.choice(self.predicate(test), self.spell(first, cls), self.spell(second, cls)), cls)
            case Binary(operator="and" | "or" as operator, left=left, right=right):
                return Term(f"({self.predicate(left)}) {LOGICAL[operator]} ({self.predicate(right)})", BOOL)
            case Binary(operator=operator, left=left, right=right):
                first = self.promoted(self.term(left))
                second = self.promoted(self.term(right))
                cls = common(first.cls, second.cls)
                if operator in ("==", "!="):
                    for constant, other in ((first, second), (second, first)):
                        if constant.code is None and other.cls == UINT32 and 0 <= constant.value < 1 << 32:
                            cls = UINT32
                return self.binary(operator, first, second, cls)
        raise CompilerError(f"{expression}: is not a predicate the {self.backend} backend renders")

    def promoted(self, term: Term) -> Term:
        if term.cls == BOOL and term.code is not None:
            return Term(self.counted(term.code), INT32)
        if term.cls.bits < 32:
            return Term(None if term.code is None else self.widened(term.code, term.cls), INT32, term.value)
        return term

    def spell(self, term: Term, cls: Num) -> str:
        if term.code is None:
            return self.constant(term.value, cls)
        return self.cast(term.code, term.cls, cls)
