from pathlib import Path

from bedrock_protocol_compiler.descriptor import CompilerError
from bedrock_protocol_compiler.printer import Printer


class GeneratorContext:
    def __init__(self, out: Path) -> None:
        self.out = out
        self.printers: dict[Path, Printer] = {}

    def open(self, path: str) -> Printer:
        relative = Path(path)
        if relative.parts[:1] != ("bedrock",) or ".." in relative.parts:
            raise CompilerError(f"{path}: not under bedrock/")
        if relative in self.printers:
            raise CompilerError(f"{path}: already open")
        printer = self.printers[relative] = Printer()
        return printer

    def commit(self) -> None:
        for relative, printer in self.printers.items():
            target = self.out / relative
            text = printer.text.encode()
            if not target.is_file() or target.read_bytes() != text:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(text)
        for stale in (self.out / "bedrock").rglob("*"):
            if stale.is_file() and stale.relative_to(self.out) not in self.printers:
                stale.unlink()
