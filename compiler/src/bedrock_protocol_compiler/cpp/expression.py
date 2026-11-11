from bedrock_protocol_compiler.cpp import names
from bedrock_protocol_compiler.descriptor import Binary, Expression, FieldRef, Int, Len, MemberRef, Not, Test
from bedrock_protocol_compiler.schema import Schema

OPERATORS = {"and": "&&", "or": "||"}


def render(schema: Schema, version: int, expression: Expression, receiver: str) -> str:
    match expression:
        case FieldRef(name=name):
            return f"{receiver}.{name}"
        case MemberRef():
            return names.enumerator(schema, expression, version)
        case Int(value=value):
            return str(value)
        case Len(field=name):
            return f"{receiver}.{name}.size()"
        case Test(field=name, member=member):
            return f"{receiver}.{name}.test(static_cast<std::size_t>({names.enumerator(schema, member, version)}))"
        case Not(operand=operand):
            return f"!({render(schema, version, operand, receiver)})"
        case Binary(operator=operator, left=left, right=right):
            spelled = OPERATORS.get(operator, operator)
            return f"({render(schema, version, left, receiver)}) {spelled} ({render(schema, version, right, receiver)})"
    raise AssertionError(expression)


def render_count(schema: Schema, version: int, expression: Expression, receiver: str) -> str:
    match expression:
        case Binary(operator="*", left=left, right=right):
            left_count = render_count(schema, version, left, receiver)
            right_count = render_count(schema, version, right, receiver)
            return f"detail::countProduct({left_count}, {right_count})"
    return f"detail::countValue({render(schema, version, expression, receiver)})"
