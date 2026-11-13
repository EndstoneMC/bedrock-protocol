"""Writes bedrock_protocol's stubs with nanobind's stubgen, plus the forms it cannot derive from a name."""

import sys
from importlib import import_module
from pathlib import Path
from types import ModuleType, UnionType
from typing import Any, get_args

from nanobind.stubgen import StubGen, create_subdirectory_for_module, load_pattern_file


class BindingStubGen(StubGen):
    def put_type(self, tp: Any, name: str | None) -> None:
        if name and tp.__module__ != self.module.__name__ and "." in tp.__qualname__:
            alias = self.import_object("typing", "TypeAlias")
            self.write_ln(f"{name}: {alias} = {self.simplify_types(f'{tp.__module__}.{tp.__qualname__}')}\n")
        else:
            super().put_type(tp, name)

    def put_property(self, prop: property, name: str | None) -> None:
        if "property" not in vars(self.stack[-2]):
            super().put_property(prop, name)
            return
        self.import_object("builtins", None)
        self.write_ln("@builtins.property")
        self.put(prop.fget, name=name)
        if prop.fset:
            self.write_ln(f"@{name}.setter")
            self.put(prop.fset, name=name)

    def type_str(self, tp: Any) -> str:
        if isinstance(tp, UnionType):
            return " | ".join(self.type_str(arg) for arg in get_args(tp))
        return super().type_str(tp)

    def put_value(self, value: object, name: str, parent: object | None = None, abbrev: bool = True) -> None:
        if name == "__all__":
            self.write_ln(f"__all__ = {self.expr_str(value, abbrev=False)}\n")
        elif name == "__hash__" and value is None:
            self.write_ln(f"__hash__: {self.import_object('typing', 'ClassVar')}[None]  # type: ignore[assignment]\n")
        else:
            super().put_value(value, name, parent, abbrev)


stage, output, pattern_file = sys.argv[1:]
sys.path.insert(0, stage)
patterns = load_pattern_file(pattern_file)
pending = [(import_module("bedrock_protocol"), Path(output, "__init__.pyi"))]
while pending:
    module, path = pending.pop()
    stub = BindingStubGen(module, include_private=True, patterns=patterns)
    stub.put(module)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stub.get(), encoding="utf-8")
    for name, child in vars(module).items():
        if isinstance(child, ModuleType) and child.__name__ == f"{module.__name__}.{name}":
            nested = create_subdirectory_for_module(child)
            pending.append((child, path.parent / name / "__init__.pyi" if nested else path.parent / f"{name}.pyi"))
Path(output, "py.typed").touch()
