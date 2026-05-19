"""A griffe extension that preserves redeclared class attributes.

griffe's `Class.members` is name-keyed, so declaring the same attribute name
several times in a class body collapses to the last declaration. The protocol
DSL relies on redeclaration to model a field whose type or wire shape changed
across protocol versions -- one declaration per version era. This extension
captures every declaration as the visitor creates it (`on_attribute_instance`
fires once per declaration, even the overwritten ones) and, once a class is
fully visited, reattaches the ordered list to the surviving member's `extra`,
where `Frontend` reads it back.
"""

from typing import Any

import griffe

#: `extra` namespace and key under which the ordered list of an attribute's
#: redeclarations (two or more) is stored on the surviving `Attribute`.
EXTRA_NAMESPACE = "bpc"
REDECLARATIONS = "redeclarations"


class RedeclarationExtension(griffe.Extension):
    """Collects same-named class attributes that griffe would otherwise
    collapse and reattaches them, in source order, to the survivor."""

    def __init__(self) -> None:
        # id(class) -> {attribute name -> declarations in source order}
        self._pending: dict[int, dict[str, list[griffe.Attribute]]] = {}

    def on_attribute_instance(
        self, *, attr: griffe.Attribute, **kwargs: Any
    ) -> None:
        parent = attr.parent
        if parent is None or not parent.is_class:
            return
        by_name = self._pending.setdefault(id(parent), {})
        by_name.setdefault(attr.name, []).append(attr)

    def on_class_members(self, *, cls: griffe.Class, **kwargs: Any) -> None:
        for name, decls in self._pending.pop(id(cls), {}).items():
            if len(decls) < 2:
                continue
            survivor = cls.members.get(name)
            if isinstance(survivor, griffe.Attribute):
                survivor.extra[EXTRA_NAMESPACE][REDECLARATIONS] = list(decls)
