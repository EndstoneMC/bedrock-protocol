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


def int_kwarg(expr, fn_name: str, kw: str) -> int | None:
    """Return `N` if `expr` is the call `fn_name(..., kw=N)`, else None."""
    if not (
        isinstance(expr, griffe.ExprCall)
        and isinstance(expr.function, griffe.ExprName)
        and expr.function.name == fn_name
    ):
        return None
    for arg in expr.arguments:
        if isinstance(arg, griffe.ExprKeyword) and arg.name == kw:
            return as_int(arg.value)
    return None


def since_kwarg(expr, fn_name: str) -> int | None:
    """Return `N` if `expr` is the call `fn_name(..., since=N)`, else None."""
    return int_kwarg(expr, fn_name, "since")


def name_kwarg(expr, fn_name: str, kw: str) -> str | None:
    """If `expr` is `fn_name(..., kw=X)` and X is an identifier, return X."""
    if not (
        isinstance(expr, griffe.ExprCall)
        and isinstance(expr.function, griffe.ExprName)
        and expr.function.name == fn_name
    ):
        return None
    for arg in expr.arguments:
        if (
            isinstance(arg, griffe.ExprKeyword)
            and arg.name == kw
            and isinstance(arg.value, griffe.ExprName)
        ):
            return arg.value.name
    return None


def str_kwarg(expr, fn_name: str, kw: str) -> str | None:
    """If `expr` is `fn_name(..., kw="X")` and X is a string literal, return X.

    griffe surfaces a literal as its raw source text, so a string keeps its
    surrounding quotes (`'"big"'`) -- those are stripped here. Returns None
    for a missing kwarg or a non-string value.
    """
    if not (
        isinstance(expr, griffe.ExprCall)
        and isinstance(expr.function, griffe.ExprName)
        and expr.function.name == fn_name
    ):
        return None
    for arg in expr.arguments:
        if not (isinstance(arg, griffe.ExprKeyword) and arg.name == kw):
            continue
        v = arg.value
        if isinstance(v, str) and len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]:
            return v[1:-1]
    return None


def parse_member_value(value) -> tuple[int, int | None, int | None] | None:
    """Parse `0` or `value(N, since=V, until=U)`. Returns (int_value, since, until)."""
    direct = as_int(value)
    if direct is not None:
        return direct, None, None
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
    return ivalue, since_kwarg(value, "value"), int_kwarg(value, "value", "until")


def class_since(cls) -> int | None:
    """Read `@enum(since=N)` from a class's decorators. Returns N or None."""
    for dec in cls.decorators:
        since = since_kwarg(dec.value, "enum")
        if since is not None:
            return since
    return None


def class_packet_id(cls) -> int | None:
    """Read `@packet(id=N)` from a class's decorators. Returns N or None."""
    for dec in cls.decorators:
        pid = int_kwarg(dec.value, "packet", "id")
        if pid is not None:
            return pid
    return None


def is_int_enum(cls) -> bool:
    """True if `cls` declares `IntEnum` as a base."""
    return any(
        isinstance(b, griffe.ExprName) and b.name == "IntEnum" for b in cls.bases
    )
