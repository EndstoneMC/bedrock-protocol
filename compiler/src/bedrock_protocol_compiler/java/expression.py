from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from bedrock_protocol_compiler.descriptor import (
    Binary,
    CompilerError,
    Expression,
    FieldRef,
    Int,
    Len,
    MemberRef,
    Not,
    Test,
)
from bedrock_protocol_compiler.java.value import BOOL, CLASSES, Num, convert, java_of, literal
from bedrock_protocol_compiler.schema import EnumShape, Schema

INT32 = CLASSES["int32"]
UINT32 = CLASSES["uint32"]
INT64 = CLASSES["int64"]
UINT64 = CLASSES["uint64"]
OPERATORS = {"and": "&&", "or": "||"}


class Operand(Protocol):
    label: str
    member: str
    term: Num | None
    suffix: str
    bitset: bool
    sized: bool


@dataclass(frozen=True)
class Term:
    code: str | None
    cls: Num
    value: int = 0


def enum_class(shape: EnumShape) -> Num:
    underlying = CLASSES[shape.underlying.name]
    return Num("int", False, 8) if underlying == BOOL else underlying


def common(a: Num, b: Num) -> Num:
    if a.signed == b.signed:
        return a if a.bits >= b.bits else b
    unsigned, signed = (a, b) if not a.signed else (b, a)
    return unsigned if unsigned.bits >= signed.bits else signed


class Renderer:
    def __init__(self, schema: Schema, version: int, operands: Mapping[str, Operand], receiver: str) -> None:
        self.schema = schema
        self.version = version
        self.operands = operands
        self.receiver = receiver

    def predicate(self, expression: Expression) -> str:
        term = self.term(expression)
        if term.cls == BOOL and term.code is not None:
            return term.code
        return f"({self.spell(term, term.cls)}) != 0"

    def count(self, expression: Expression) -> str:
        match expression:
            case Binary(operator="*", left=left, right=right):
                return f"ByteBufCodec.countProduct(buf, {self.count(left)}, {self.count(right)})"
            case Len(field=name):
                operand = self.operands[name]
                if not operand.sized:
                    raise CompilerError(f"{operand.label}: is not a list or a map")
                return f"ByteBufCodec.countValue(buf, {self.receiver}{operand.member}.size())"
        widest = self.promoted(self.term(expression))
        return f"ByteBufCodec.countValue(buf, {self.spell(widest, common(widest.cls, INT64))})"

    def member(self, member: MemberRef) -> Term:
        shape = self.schema.shape_at(member.enum, self.version)
        if not isinstance(shape, EnumShape):
            raise CompilerError(f"{member.enum.name}.{member.name}: is not an enum member")
        return Term(None, enum_class(shape), shape.numbers[member.name])

    def term(self, expression: Expression) -> Term:
        match expression:
            case FieldRef(name=name):
                operand = self.operands[name]
                if operand.term is None:
                    raise CompilerError(f"{operand.label}: is not an integer, a bool or an enum")
                return Term(f"{self.receiver}{operand.member}{operand.suffix}", operand.term)
            case MemberRef():
                return self.member(expression)
            case Int(value=value):
                if -(1 << 31) <= value < 1 << 31:
                    return Term(None, INT32, value)
                return Term(None, INT64 if -(1 << 63) <= value < 1 << 63 else UINT64, value)
            case Test(field=name, member=member):
                operand = self.operands[name]
                if not operand.bitset:
                    raise CompilerError(f"{operand.label}: is not a bitset")
                return Term(f"{self.receiver}{operand.member}.get({self.member(member).value})", BOOL)
            case Not(operand=operand):
                return Term(f"!({self.predicate(operand)})", BOOL)
            case Binary(operator="and" | "or" as operator, left=left, right=right):
                spelled = f"({self.predicate(left)}) {OPERATORS[operator]} ({self.predicate(right)})"
                return Term(spelled, BOOL)
            case Binary(operator=operator, left=left, right=right):
                first = self.promoted(self.term(left))
                second = self.promoted(self.term(right))
                cls = common(first.cls, second.cls)
                if operator in ("==", "!="):
                    for constant, other in ((first, second), (second, first)):
                        if constant.code is None and other.cls == UINT32 and 0 <= constant.value < 1 << 32:
                            cls = UINT32
                a = self.spell(first, cls)
                b = self.spell(second, cls)
                if operator == "<" and not cls.signed:
                    boxed = "Long" if cls.bits == 64 else "Integer"
                    return Term(f"{boxed}.compareUnsigned({a}, {b}) < 0", BOOL)
                return Term(f"({a}) {operator} ({b})", BOOL if operator in ("==", "!=", "<") else cls)
        raise CompilerError(f"{expression}: is not a predicate the Java backend renders")

    def promoted(self, term: Term) -> Term:
        if term.cls == BOOL:
            return Term(f"({term.code} ? 1 : 0)", INT32)
        if term.cls.bits < 32:
            return Term(term.code, INT32, term.value)
        return term

    def spell(self, term: Term, cls: Num) -> str:
        if term.code is None:
            return literal(term.value, cls)
        return convert(term.code, java_of(term.cls), term.cls, cls, java_of(cls))
