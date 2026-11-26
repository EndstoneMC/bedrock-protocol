from collections.abc import Mapping
from typing import Protocol, override

from bedrock_protocol_compiler import expression
from bedrock_protocol_compiler.descriptor import Binary, CompilerError, Expression, Len
from bedrock_protocol_compiler.expression import BOOL, INT64, Num, Term, common
from bedrock_protocol_compiler.java.value import convert, java_of, literal
from bedrock_protocol_compiler.schema import Encoding, Schema


class Operand(expression.Operand, Protocol):
    label: str
    member: str
    suffix: str


class Renderer(expression.Renderer[Operand]):
    backend = "Java"

    def __init__(self, schema: Schema, encoding: Encoding, operands: Mapping[str, Operand], receiver: str) -> None:
        super().__init__(schema, encoding, operands)
        self.receiver = receiver

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

    @override
    def label(self, operand: Operand) -> str:
        return operand.label

    @override
    def access(self, operand: Operand) -> str:
        return f"{self.receiver}{operand.member}{operand.suffix}"

    @override
    def length(self, operand: Operand) -> str:
        return f"(long) {self.receiver}{operand.member}.size()"

    @override
    def test(self, operand: Operand, bit: int) -> str:
        return f"{self.receiver}{operand.member}.get({bit})"

    @override
    def choice(self, test: str, first: str, second: str) -> str:
        return f"({test} ? {first} : {second})"

    @override
    def counted(self, code: str) -> str:
        return f"({code} ? 1 : 0)"

    @override
    def nonzero(self, code: str) -> str:
        return f"({code}) != 0"

    @override
    def constant(self, value: int, cls: Num) -> str:
        return literal(value, cls)

    @override
    def cast(self, code: str, source: Num, target: Num) -> str:
        return convert(code, java_of(source), source, target, java_of(target))

    @override
    def widened(self, code: str, source: Num) -> str:
        return code

    @override
    def binary(self, operator: str, first: Term, second: Term, cls: Num) -> Term:
        if operator in ("<", "<=") and not cls.signed:
            boxed = "Long" if cls.bits == 64 else "Integer"
            return Term(
                f"{boxed}.compareUnsigned({self.spell(first, cls)}, {self.spell(second, cls)}) {operator} 0",
                BOOL,
            )
        return super().binary(operator, first, second, cls)
