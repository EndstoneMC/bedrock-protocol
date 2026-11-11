import pytest

from bedrock_protocol_compiler.printer import Printer


def test_emit_dedents_the_template_and_substitutes_variables():
    p = Printer()
    p.emit(
        """
        struct $name$ {
            int $field$;
        };
        """,
        name="Boss",
        field="id",
    )
    assert p.text == "struct Boss {\n    int id;\n};\n"


def test_emit_formats_an_int_variable():
    p = Printer()
    p.emit("static constexpr int Id = $id$;", id=74)
    assert p.text == "static constexpr int Id = 74;\n"


def test_emit_fails_on_a_missing_variable():
    with pytest.raises(ValueError, match=r"\$name\$: no such variable"):
        Printer().emit("struct $name$;")


def test_indent_nests_and_restores():
    p = Printer()
    p.emit("a")
    with p.indent():
        p.emit("b")
        with p.indent():
            p.emit("c")
        p.emit("d")
    p.emit("e")
    assert p.text == "a\n    b\n        c\n    d\ne\n"


def test_emit_leaves_blank_lines_empty_inside_an_indent():
    p = Printer()
    with p.indent():
        p.emit(
            """
            a

            b
            """
        )
    assert p.text == "    a\n\n    b\n"


def test_a_callable_inherits_the_indent_of_its_line():
    p = Printer()
    with p.indent():
        p.emit(
            """
            if (ok) {
                $body$
            }
            """,
            body=lambda: p.emit("return;"),
        )
    assert p.text == "    if (ok) {\n        return;\n    }\n"


def test_a_callable_may_emit_several_lines_and_indent_further():
    p = Printer()

    def body():
        p.emit("a")
        with p.indent():
            p.emit("b")

    p.emit(
        """
        {
            $body$
        }
        """,
        body=body,
    )
    assert p.text == "{\n    a\n        b\n}\n"


def test_a_callable_beside_other_text_is_rejected():
    with pytest.raises(ValueError, match=r"\$body\$: a callable must be alone on its line"):
        Printer().emit("x = $body$;", body=lambda: None)


def test_a_string_alone_on_its_line_is_substituted_at_that_indent():
    p = Printer()
    p.emit(
        """
        {
            $statement$
        }
        """,
        statement="return;",
    )
    assert p.text == "{\n    return;\n}\n"


def test_every_marker_on_a_line_is_substituted():
    p = Printer()
    p.emit("$type$ $name${};", type="int", name="id")
    assert p.text == "int id{};\n"
