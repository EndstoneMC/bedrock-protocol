from collections.abc import Mapping
from typing import Protocol, override

from bedrock_protocol_compiler import expression
from bedrock_protocol_compiler.descriptor import Binary, CompilerError, Expression, Len
from bedrock_protocol_compiler.expression import INT64, Num
from bedrock_protocol_compiler.go.value import convert, go_of, literal
from bedrock_protocol_compiler.schema import Encoding, Schema


class Operand(expression.Operand, Protocol):
    name: str

    def access(self) -> str: ...

    def operand(self) -> str: ...


class Renderer(expression.Renderer[Operand]):
    backend = "Go"

    def __init__(self, schema: Schema, encoding: Encoding, operands: Mapping[str, Operand], where: str) -> None:
        super().__init__(schema, encoding, operands)
        self.where = where

    def count(self, expression: Expression) -> str:
        match expression:
            case Binary(operator="*", left=left, right=right):
                return f"r.CountProduct({self.count(left)}, {self.count(right)})"
            case Len(field=name):
                operand = self.operands[name]
                if not operand.sized:
                    raise CompilerError(f"{self.label(operand)}: is not a list or a map")
                return f"int64(len({operand.access()}))"
        return self.spell(self.promoted(self.term(expression)), INT64)

    @override
    def label(self, operand: Operand) -> str:
        return f"{self.where}.{operand.name}"

    @override
    def access(self, operand: Operand) -> str:
        return operand.operand()

    @override
    def test(self, operand: Operand, bit: int) -> str:
        return f"{operand.access()}.Test({bit})"

    @override
    def choice(self, test: str, first: str, second: str) -> str:
        return f"choose({test}, {first}, {second})"

    @override
    def counted(self, code: str) -> str:
        return f"numberOf[int32]({code})"

    @override
    def nonzero(self, code: str) -> str:
        return f"{code} != 0"

    @override
    def constant(self, value: int, cls: Num) -> str:
        return f"{go_of(cls)}({literal(value, cls)})"

    @override
    def cast(self, code: str, source: Num, target: Num) -> str:
        return convert(code, source, target)
