import ast
import keyword
from collections.abc import Callable
from dataclasses import dataclass
from functools import reduce

from bedrock_protocol_compiler.descriptor import (
    Binary,
    Bitset,
    CompilerError,
    Expression,
    Field,
    FieldRef,
    Int,
    Len,
    List,
    Map,
    MemberRef,
    Not,
    Range,
    Test,
)


@dataclass
class Lambda:
    param: str
    body: ast.expr
    earlier: list[Field]
    range: Range
    versions: tuple[int, ...]
    member_of: Callable[[ast.expr], MemberRef]
    error: Callable[[ast.expr, str], CompilerError]


def field_name(identifier: str) -> str:
    if identifier.endswith("_") and keyword.iskeyword(identifier[:-1]):
        return identifier[:-1]
    return identifier


def read_lambda(
    node: ast.expr,
    earlier: list[Field],
    range: Range,
    versions: tuple[int, ...],
    member_of: Callable[[ast.expr], MemberRef],
    error: Callable[[ast.expr, str], CompilerError],
) -> Lambda:
    if not (
        isinstance(node, ast.Lambda)
        and len(node.args.args) == 1
        and not (node.args.posonlyargs or node.args.kwonlyargs or node.args.vararg or node.args.kwarg)
    ):
        raise error(node, "is not a lambda of one argument")
    return Lambda(node.args.args[0].arg, node.body, earlier, range, versions, member_of, error)


def earlier_field(context: Lambda, node: ast.expr) -> Field:
    if not (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == context.param):
        raise context.error(node, f"{ast.unparse(node)} is not {context.param}.<field>")
    name = field_name(node.attr)
    declared = [earlier for earlier in context.earlier if earlier.name == name]
    for version in context.versions:
        if declared and context.range.contains(version) and not any(each.range.contains(version) for each in declared):
            raise context.error(node, f"{ast.unparse(node)} is absent at {version}")
    for earlier in declared:
        if any(context.range.contains(version) and earlier.range.contains(version) for version in context.versions):
            return earlier
    raise context.error(node, f"{ast.unparse(node)} is not an earlier field")


def parse_count(context: Lambda) -> Expression:
    return count_of(context, context.body)


def count_of(context: Lambda, node: ast.expr) -> Expression:
    match node:
        case ast.BinOp(op=ast.Mult(), left=left, right=right):
            return Binary("*", count_of(context, left), count_of(context, right))
        case ast.Call(func=ast.Name(id="len"), args=[argument], keywords=[]):
            counted = earlier_field(context, argument)
            if not isinstance(counted.type, List | Map):
                raise context.error(argument, "len is given something other than a list or map")
            return Len(counted.name)
        case ast.Attribute():
            return FieldRef(earlier_field(context, node).name)
    raise context.error(node, "is not a field, len(field) or a product")


def parse_predicate(context: Lambda) -> Expression:
    return predicate_of(context, context.body)


def predicate_of(context: Lambda, node: ast.expr) -> Expression:
    match node:
        case ast.BoolOp(op=op, values=values):
            operator = "and" if isinstance(op, ast.And) else "or"
            operands = [predicate_of(context, value) for value in values]
            return reduce(lambda left, right: Binary(operator, left, right), operands)
        case ast.UnaryOp(op=ast.Not(), operand=operand):
            return Not(predicate_of(context, operand))
        case ast.BinOp(op=ast.BitAnd(), left=left, right=right):
            return Binary("&", predicate_of(context, left), predicate_of(context, right))
        case ast.Compare(left=left, ops=[ast.In()], comparators=[ast.Set(elts=elements)]):
            tested = predicate_of(context, left)
            operands = [Binary("==", tested, predicate_of(context, element)) for element in elements]
            return reduce(lambda first, second: Binary("or", first, second), operands)
        case ast.Compare(left=left, ops=[ast.Eq() | ast.NotEq() | ast.Lt() as op], comparators=[right]):
            operator = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<"}[type(op)]
            return Binary(operator, predicate_of(context, left), predicate_of(context, right))
        case ast.Call(func=ast.Attribute(value=receiver, attr="test"), args=[bit], keywords=[]):
            bits = earlier_field(context, receiver)
            if not isinstance(bits.type, Bitset):
                raise context.error(receiver, "test is given something other than a bitset")
            return Test(bits.name, context.member_of(bit))
        case ast.Attribute(value=ast.Name(id=name)) if name == context.param:
            return FieldRef(earlier_field(context, node).name)
        case ast.Attribute():
            return context.member_of(node)
        case ast.Constant() | ast.UnaryOp(op=ast.USub()):
            try:
                value = ast.literal_eval(node)
            except (ValueError, TypeError):
                value = None
            if type(value) is not int:
                raise context.error(node, "is not a literal int")
            return Int(value)
    raise context.error(node, "is not a predicate")
