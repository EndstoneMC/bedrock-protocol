"""Parse griffe Expr nodes for DSL constructs (`field`, `value`, `@enum`)."""

import griffe


def as_int(x) -> int | None:
    """Coerce a griffe literal (raw `str` from source) to int, or None."""
    if isinstance(x, str):
        try:
            return int(x)
        except ValueError:
            return None
    return None


def since_kwarg(expr, fn_name: str) -> int | None:
    """Return `N` if `expr` is the call `fn_name(..., since=N)`, else None."""
    if not (
        isinstance(expr, griffe.ExprCall)
        and isinstance(expr.function, griffe.ExprName)
        and expr.function.name == fn_name
    ):
        return None
    for arg in expr.arguments:
        if isinstance(arg, griffe.ExprKeyword) and arg.name == "since":
            return as_int(arg.value)
    return None


def parse_member_value(value) -> tuple[int, int | None] | None:
    """Parse `0` or `value(N, since=V)`. Returns (int_value, since_or_None)."""
    direct = as_int(value)
    if direct is not None:
        return direct, None
    if not (
        isinstance(value, griffe.ExprCall)
        and isinstance(value.function, griffe.ExprName)
        and value.function.name == "value"
        and value.arguments
    ):
        return None
    ivalue = as_int(value.arguments[0])
    if ivalue is None:
        return None
    return ivalue, since_kwarg(value, "value")


def class_since(cls) -> int | None:
    """Read `@enum(since=N)` from a class's decorators. Returns N or None."""
    for dec in cls.decorators:
        since = since_kwarg(dec.value, "enum")
        if since is not None:
            return since
    return None


def is_int_enum(cls) -> bool:
    """True if `cls` declares `IntEnum` as a base."""
    return any(
        isinstance(b, griffe.ExprName) and b.name == "IntEnum" for b in cls.bases
    )
