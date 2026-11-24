import re
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from bedrock_protocol_compiler.descriptor import CompilerError, Range
from bedrock_protocol_compiler.java.names import OBJECT, OBJECT_METHODS, bounds
from bedrock_protocol_compiler.printer import Printer

METHOD = re.compile(r"[^=]*?\b(?P<name>[a-z]\w*)\((?P<parameters>[^()]*)\) \{")
FIELD = re.compile(r"[\w.<>?,@\[\] ]+ (?P<name>\w+)(?: = .+)?;")
TYPE_ARGUMENTS = re.compile(r"<[^<>]*>")


@dataclass
class Scope:
    where: str
    name: str
    indent: str
    start: int
    end: int = 0


class Members:
    """Checks the members each class declares, read back from the lines its emitters printed."""

    def __init__(self, p: Printer) -> None:
        self.p = p
        self.scopes: list[Scope] = []
        self.origins: list[tuple[int, int, str]] = []

    @contextmanager
    def scope(self, where: str, name: str) -> Iterator[None]:
        scope = Scope(where, name, self.p.prefix, len(self.p.lines))
        yield
        scope.end = len(self.p.lines)
        self.scopes.append(scope)

    @contextmanager
    def origin(self, name: str) -> Iterator[None]:
        start = len(self.p.lines)
        yield
        self.origins.append((start, len(self.p.lines), name))

    def check(self) -> None:
        for scope in sorted(self.scopes, key=lambda each: each.start):
            methods = dict.fromkeys(OBJECT_METHODS, OBJECT)
            fields: dict[str, str] = {}
            for index in range(scope.start, scope.end):
                line = self.p.lines[index]
                declaration = line[len(scope.indent) :]
                if not line.startswith(scope.indent) or not declaration[:1].strip():
                    continue
                method = METHOD.fullmatch(declaration)
                field = FIELD.fullmatch(declaration)
                spans = [
                    (start, -end, name) for start, end, name in self.origins if scope.start <= start <= index < end
                ]
                origin = max(spans)[2] if spans else scope.name
                if method is not None:
                    parameters = method["parameters"]
                    while TYPE_ARGUMENTS.search(parameters):
                        parameters = TYPE_ARGUMENTS.sub("", parameters)
                    arity = parameters.count(",") + 1 if parameters.strip() else 0
                    first = methods.setdefault((method["name"], arity), origin)
                    clash = method["name"]
                elif field is not None:
                    first = fields.setdefault(field["name"], origin)
                    clash = field["name"]
                else:
                    continue
                if first != origin:
                    raise CompilerError(f"{scope.where}.{clash}: is generated for both {first} and {origin}")


def check_names(where: str, names: Iterable[tuple[str, str]]) -> None:
    seen: dict[str, str] = {}
    for name, origin in names:
        first = seen.setdefault(name, origin)
        if first != origin:
            raise CompilerError(f"{where}.{name}: is generated for both {first} and {origin}")


def equals(p: Printer, name: str, comparisons: list[str]) -> None:
    if not comparisons:
        p.emit(
            """
            @Override
            public boolean equals(@Nullable Object obj) {
                return obj instanceof $name$;
            }

            """,
            name=name,
        )
        return
    p.emit(
        """
        @Override
        public boolean equals(@Nullable Object obj) {
            if (obj == this) {
                return true;
            }
            if (!(obj instanceof $name$ other)) {
                return false;
            }
            $body$
        }

        """,
        name=name,
        body=lambda: conjunction(p, comparisons),
    )


def conjunction(p: Printer, comparisons: list[str]) -> None:
    end = ";" if len(comparisons) == 1 else ""
    p.emit("return $first$$end$", first=comparisons[0], end=end)
    with p.indent(), p.indent():
        for index, comparison in enumerate(comparisons[1:], 2):
            p.emit("&& $comparison$$end$", comparison=comparison, end=";" if index == len(comparisons) else "")


def hash_code(p: Printer, hashes: list[str]) -> None:
    p.emit(
        """
        @Override
        public int hashCode() {
            $body$
        }

        """,
        body=lambda: combine(p, hashes),
    )


def combine(p: Printer, hashes: list[str]) -> None:
    if not hashes:
        p.emit("return 1;")
        return
    p.emit("int hash = 1;")
    for each in hashes:
        p.emit("hash = 31 * hash + $each$;", each=each)
    p.emit("return hash;")


def ladder(p: Printer, entries: list[tuple[list[Range], Callable[[], None]]], absent: str) -> None:
    for runs, body in entries:
        clauses = [" && ".join(bounds(run.since, run.until, "protocol")) for run in runs]
        if "" in clauses:
            body()
            return
        clause = clauses[0] if len(clauses) == 1 else " || ".join(f"({each})" for each in clauses)
        p.emit(
            """
            if ($clause$) {
                $body$
            }
            """,
            clause=clause,
            body=body,
        )
    p.emit("throw new IllegalArgumentException($absent$ + protocol);", absent=absent)


def enum_getter(p: Printer, enum: str, name: str, number: str, index: str = "") -> None:
    p.emit(
        """
        public @NotNull $enum$ get$name$($index$) {
            $enum$ result = $enum$.forNumber($number$);
            return result == null ? $enum$.UNRECOGNIZED : result;
        }

        """,
        enum=enum,
        name=name,
        index=index,
        number=number,
    )


def enum_setter(p: Printer, enum: str, name: str) -> None:
    p.emit(
        """
        public @NotNull Builder set$name$(@NotNull $enum$ value) {
            return set$name$Value(value.getNumber());
        }

        """,
        name=name,
        enum=enum,
    )


def codec(
    p: Printer,
    registry: Members,
    where: str,
    name: str,
    message: str,
    exported: bool,
    constants: Callable[[], None],
    writes: Callable[[], None],
    reads: Callable[[], None],
) -> None:
    modifiers = "public static final" if exported else "static final"
    p.emit("$modifiers$ class $name$ implements Codec<$message$> {", modifiers=modifiers, name=name, message=message)
    with p.indent(), registry.scope(f"{where}.{name}", name):
        p.emit("$modifiers$ @NotNull $name$ INSTANCE = new $name$();", modifiers=modifiers, name=name)
        p.emit("")
        constants()
        p.emit("")
        p.emit(
            """
            private $name$() {}

            @Override
            public void encode(@NotNull $message$ value, @NotNull ByteBuf buf) {
                $writes$
            }

            @Override
            public @NotNull $message$ decode(@NotNull ByteBuf buf) {
                Builder out = new Builder();
                $reads$
                return out.build();
            }
            """,
            name=name,
            message=message,
            writes=writes,
            reads=reads,
        )
    p.emit("}")
    p.emit("")


def statics(p: Printer, name: str) -> None:
    p.emit(
        """
        public static @NotNull $name$ getDefaultInstance() {
            return DEFAULT_INSTANCE;
        }

        public static @NotNull Builder newBuilder() {
            return new Builder();
        }

        public @NotNull Builder toBuilder() {
            return new Builder(this);
        }

        """,
        name=name,
    )
