from bedrock_protocol_compiler.cpp import names
from bedrock_protocol_compiler.cpp.field import PrimitiveField
from bedrock_protocol_compiler.descriptor import Alias
from bedrock_protocol_compiler.printer import Printer


class AliasGenerator:
    def __init__(self, alias: Alias) -> None:
        self.alias = alias
        self.underlying = names.PRIMITIVES[alias.primitive.name]

    def includes(self) -> set[str]:
        return {"<compare>", names.runtime("detail/reflect"), *PrimitiveField(self.alias.primitive).includes()}

    def definition(self, p: Printer) -> None:
        p.emit(
            """
            struct $name$ {
                constexpr $name$() = default;
                explicit constexpr $name$($underlying$ value) : value_(value) {}
                constexpr operator $underlying$() const { return value_; }
                friend constexpr bool operator==(const $name$ &, const $name$ &) = default;
                friend constexpr auto operator<=>(const $name$ &, const $name$ &) = default;

              private:
                $underlying$ value_{};
            };

            """,
            name=self.alias.name,
            underlying=self.underlying,
        )

    def trait(self, p: Printer) -> None:
        p.emit(
            """
            template <>
            struct primitive_alias<$name$> { using type = $underlying$; };

            """,
            name=self.alias.name,
            underlying=self.underlying,
        )
