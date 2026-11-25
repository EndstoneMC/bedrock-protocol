from pathlib import Path

from bedrock_protocol_compiler.printer import Printer


class GeneratorContext:
    def __init__(self, out: Path, owned: tuple[str, ...] = ("*",)) -> None:
        self.out = out
        self.owned = owned
        self.printers: dict[Path, Printer] = {}

    def open(self, path: str) -> Printer:
        printer = self.printers[Path(path)] = Printer()
        return printer

    def commit(self) -> None:
        for relative, printer in self.printers.items():
            target = self.out / relative
            text = printer.text.encode()
            if not target.is_file() or target.read_bytes() != text:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(text)
        for root in {relative.parts[0] for relative in self.printers}:
            for pattern in self.owned:
                for stale in (self.out / root).rglob(pattern):
                    if stale.is_file() and stale.relative_to(self.out) not in self.printers:
                        stale.unlink()
