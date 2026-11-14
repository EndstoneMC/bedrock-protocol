import re

from bedrock_protocol_compiler.java import names
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import Schema

STRING_LITERAL = re.compile(r'"(?:[^"\\]|\\.)*"')


def write(schema: Schema, out: Printer, package: str, body: Printer) -> None:
    text = STRING_LITERAL.sub('""', body.text)
    found = sorted(
        spelled
        for name, spelled in names.imports(schema).items()
        if spelled.rpartition(".")[0] != package and re.search(rf"(?<![\w.]){name}\b", text)
    )
    out.emit("package $package$;", package=package)
    out.emit("")
    for spelled in found:
        out.emit("import $spelled$;", spelled=spelled)
    if found:
        out.emit("")
    lines = body.lines
    for index, line in enumerate(lines):
        following = lines[index + 1] if index + 1 < len(lines) else ""
        if line or (following and not out.lines[-1].endswith("{") and not following.lstrip().startswith("}")):
            out.lines.append(line)
