"""C++-specific render model.

The Jinja templates iterate over these dataclasses; they carry no logic of
their own. C++-only concerns — required `#include`s, namespace layout,
trait requires-clauses — live here, not in the shared IR.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RenderEnum:
    name: str
    members: list[tuple[str, int]]
    kind: str = "enum"


@dataclass
class RenderStruct:
    name: str
    nested_enums: list[RenderEnum]
    constants: list[tuple[str, str, str]]    # (name, ctype, literal)
    fields: list[tuple[str, str]]            # (ctype, name)
    kind: str = "struct"


@dataclass
class RenderEntry:
    """One member of a snapshot namespace: a fresh definition or a `using`
    alias back to an earlier snapshot."""
    alias: bool
    name: str = ""
    target: str = ""
    definition: RenderEnum | RenderStruct | None = None


@dataclass
class RenderNamespace:
    name: str
    entries: list[RenderEntry]


@dataclass
class RenderTrait:
    name: str
    ranges: list[tuple[str, str]]            # (requires-clause, namespace)


@dataclass
class RenderSerializer:
    qualified: str
    param: str
    serialize: list[str]
    deserialize: list[str]


@dataclass
class RenderedFile:
    package: str | None
    dep_includes: list[str]
    primitive_aliases: list[tuple[str, str]]   # `enum X : ctype {}` lines
    type_aliases: list[tuple[str, str]]        # `using X = ctype` lines
    unversioned: list[RenderEnum | RenderStruct]
    namespaces: list[RenderNamespace]
    traits: list[RenderTrait]
    serializers: list[RenderSerializer]
    latest_aliases: list[str]
    latest_version: int
    uses_uuid: bool
    uses_nbt: bool
