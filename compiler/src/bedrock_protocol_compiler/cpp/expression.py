from bedrock_protocol_compiler.cpp import names
from bedrock_protocol_compiler.descriptor import Binary, Choice, Expression, FieldRef, Int, Len, MemberRef, Not, Test
from bedrock_protocol_compiler.schema import Encoding, Schema

OPERATORS = {"and": "&&", "or": "||"}


def render(schema: Schema, encoding: Encoding, expression: Expression, receiver: str) -> str:
    match expression:
        case FieldRef(name=name):
            return f"{receiver}.{name}"
        case MemberRef():
            return names.spelled_member(schema, schema.resolve(expression, encoding.since), encoding)
        case Int(value=value):
            return str(value)
        case Len(field=name):
            return f"{receiver}.{name}.size()"
        case Test(field=name, member=member):
            return f"{receiver}.{name}.test(static_cast<std::size_t>({names.numbered(schema, member, encoding)}))"
        case Not(operand=operand):
            return f"!({render(schema, encoding, operand, receiver)})"
        case Choice(test=test, when_true=when_true, when_false=when_false):
            return (
                f"({render(schema, encoding, test, receiver)}) ? ({render(schema, encoding, when_true, receiver)}) "
                f": ({render(schema, encoding, when_false, receiver)})"
            )
        case Binary(operator=operator, left=left, right=right):
            spelled = OPERATORS.get(operator, operator)
            return (
                f"({render(schema, encoding, left, receiver)}) {spelled} ({render(schema, encoding, right, receiver)})"
            )
    raise AssertionError(expression)


def render_count(schema: Schema, encoding: Encoding, expression: Expression, receiver: str) -> str:
    match expression:
        case Binary(operator="*", left=left, right=right):
            left_count = render_count(schema, encoding, left, receiver)
            right_count = render_count(schema, encoding, right, receiver)
            return f"detail::countProduct({left_count}, {right_count})"
    return f"detail::countValue({render(schema, encoding, expression, receiver)})"
