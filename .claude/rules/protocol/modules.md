---
paths:
  - "protocol/**"
---
# Modules

## Placement

- Name every schema module after a BDS game-tree folder, and open it with a docstring naming what it holds and what it deliberately excludes.
- Settle placement by grepping the docstrings (`head -qn 4 protocol/*.py`, `grep -n "^Not " protocol/*.py`), never by re-deriving the taxonomy.
- Change a module's docstring in the same commit that adds a declaration it excludes.
- Place a declaration by its BDS header's domain folder:
  - a reusable type goes to its domain's module;
  - a wire-only type under `network/packet/types/<path>/` goes to the module mirroring `<path>`;
  - a payload declared in the packet's own header nests in the `@packet`;
  - a subdirectory merges into its parent unless it can stand alone.
- Where the folder cannot decide (it appears at two depths, or holds over 100 headers or under 3), fall back in order to the module declaring most of the packet's referenced types, then the packet family, then leave the declaration where it is.
- Never create a module because of size; a lookup table lives with its subject.
- Keep the schema's import graph acyclic.

## Order

- Order a module live-first: classes live at `__version__` on top, then the dead ones, newest `until=` first, with no banner between them.
- Keep a redeclaration chain together in ascending order; it moves to the tail only when its last declaration carries `until=`.
- Treat declaration order as meaningless beyond that layout.
