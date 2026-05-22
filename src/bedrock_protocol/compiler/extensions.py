"""A griffe extension underpinning the protocol DSL's version machinery.

griffe keeps class and module members in a name-keyed mapping, so a redeclared
name collapses to its last declaration; and griffe has no model for a `with`
block in a class body. This extension recovers the three things the DSL needs:

* **Redeclared attributes** -- a field whose type or wire shape changed across
  protocol versions, declared once per era. `on_attribute_instance` fires once
  per declaration (even the overwritten ones); the ordered list is reattached
  to the surviving member, where `Frontend` reads it back.
* **Redeclared classes** -- a whole struct redeclared once per era via
  `@type(since=, until=)`. Captured the same way and reattached to the
  surviving class.
* **`with field(when=...)` guards** -- a block grouping fields under a shared
  `when=` predicate. griffe does not model `with`, so the class AST is
  rewritten before it is visited: each guarded field is hoisted straight into
  the class body, with the guard predicate merged into its `field(...)` call
  as a `_group_when=` keyword.
"""

import ast
import copy
from typing import Any

import griffe

#: `extra` namespace, and the keys under which the ordered redeclaration lists
#: of an attribute / a class are stored on the surviving member.
EXTRA_NAMESPACE = "bpc"
REDECLARATIONS = "redeclarations"
CLASS_REDECLARATIONS = "class_redeclarations"


class RedeclarationExtension(griffe.Extension):
    """Recovers redeclared attributes, redeclared classes, and `with`-guarded
    field groups -- declarations griffe would otherwise lose or cannot model."""

    def __init__(self) -> None:
        # id(class)  -> {attribute name -> declarations in source order}
        self._pending: dict[int, dict[str, list[griffe.Attribute]]] = {}
        # id(module) -> {class name     -> declarations in source order}
        self._pending_classes: dict[int, dict[str, list[griffe.Class]]] = {}

    # --- with-guard hoisting: rewrite the class AST before it is visited -----

    def on_class_node(self, *, node: Any, **kwargs: Any) -> None:
        """Hoist every `with field(when=...)` block's fields into the class
        body, merging the guard predicate into each as `_group_when=` and the
        block's index as `_group_id=` -- the index keeps the hoisted fields
        identifiable as one block once the `with` is gone."""
        if not isinstance(node, ast.ClassDef):
            return
        new_body: list[ast.stmt] = []
        group = 0
        for stmt in node.body:
            guard = self._field_guard(stmt)
            if guard is None:
                new_body.append(stmt)
                continue
            block, predicate = guard
            for inner in block.body:
                self._merge_group_when(inner, predicate, group)
                new_body.append(inner)
            group += 1
        node.body = new_body

    @staticmethod
    def _field_guard(stmt: ast.stmt) -> tuple[ast.With, ast.expr] | None:
        """A `with field(when=...):` block paired with its `when=` predicate,
        or None when `stmt` is not such a guard block."""
        if not isinstance(stmt, ast.With) or len(stmt.items) != 1:
            return None
        ctx = stmt.items[0].context_expr
        if not (
            isinstance(ctx, ast.Call)
            and isinstance(ctx.func, ast.Name)
            and ctx.func.id == "field"
        ):
            return None
        for kw in ctx.keywords:
            if kw.arg == "when":
                return stmt, kw.value
        return None

    @staticmethod
    def _merge_group_when(stmt: ast.stmt, predicate: ast.expr, group: int) -> None:
        """Merge a guard into a hoisted field as `field(_group_when=, _group_id=)`:
        the shared predicate, and the index of the `with` block it came from so
        the block survives hoisting and a backend can re-form it. A field with
        no `field(...)` call gains one; an existing call gains the keywords.
        Statements that are not annotated assignments are left untouched."""
        if not isinstance(stmt, ast.AnnAssign):
            return
        keywords = [
            ast.keyword(arg="_group_when", value=copy.deepcopy(predicate)),
            ast.keyword(arg="_group_id", value=ast.Constant(value=group)),
        ]
        if stmt.value is None:
            stmt.value = ast.Call(
                func=ast.Name(id="field", ctx=ast.Load()), args=[], keywords=keywords
            )
        elif isinstance(stmt.value, ast.Call):
            stmt.value.keywords.extend(keywords)
        else:
            return
        ast.copy_location(stmt.value, stmt)
        ast.fix_missing_locations(stmt)

    # --- redeclared attributes ----------------------------------------------

    def on_attribute_instance(self, *, attr: griffe.Attribute, **kwargs: Any) -> None:
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

    # --- redeclared classes -------------------------------------------------

    def on_class_instance(self, *, cls: griffe.Class, **kwargs: Any) -> None:
        parent = cls.parent
        if parent is None or not parent.is_module:
            return
        by_name = self._pending_classes.setdefault(id(parent), {})
        by_name.setdefault(cls.name, []).append(cls)

    def on_module_members(self, *, mod: griffe.Module, **kwargs: Any) -> None:
        for name, decls in self._pending_classes.pop(id(mod), {}).items():
            if len(decls) < 2:
                continue
            survivor = mod.members.get(name)
            if isinstance(survivor, griffe.Class):
                survivor.extra[EXTRA_NAMESPACE][CLASS_REDECLARATIONS] = list(decls)
