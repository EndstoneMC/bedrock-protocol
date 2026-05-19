"""Version-snapshot analysis -- language-agnostic.

A protocol type is *versioned* when its definition gains or loses something at
a known protocol version, or it transitively references such a type. For a
versioned type the timeline splits into snapshots `[s_i, s_{i+1})`; each
snapshot either holds a fresh definition or, when nothing changed, reuses an
earlier one. `VersionPlan` computes that structure; a backend decides how to
spell it (C++ namespaces, traits, ...).
"""

from dataclasses import replace
from typing import Any

from .schema import Enum, Field, Struct


class VersionPlan:
    def __init__(self, types: tuple[Enum | Struct, ...]):
        self._types = types
        self._by_name = {t.name: t for t in types}
        self._own = frozenset(self._by_name)
        self.versioned = self._versioned_types()
        self.order = self._topo_order()
        self.snapshots = self._compute_snapshots()
        self._present: dict[str, dict[int, bool]] = {}
        self._fresh: dict[str, dict[int, bool]] = {}
        self._concrete: dict[str, dict[int, int]] = {}
        self._visible: dict[str, dict[int, tuple[Any, ...]]] = {}
        self._keys: dict[str, dict[int, tuple[Any, ...]]] = {}
        self._plan_snapshots()

    # --- queries -------------------------------------------------------------

    def is_versioned(self, name: str) -> bool:
        return name in self.versioned

    def present(self, name: str, snapshot: int) -> bool:
        return self._present[name].get(snapshot, False)

    def fresh(self, name: str, snapshot: int) -> bool:
        return self._fresh[name][snapshot]

    def concrete(self, name: str, snapshot: int) -> int:
        """The snapshot whose definition `(name, snapshot)` resolves to."""
        return self._concrete[name][snapshot]

    def visible(self, name: str, snapshot: int) -> tuple[Any, ...]:
        """Fields (Struct) or members (Enum) present at `snapshot`."""
        return self._visible[name][snapshot]

    def fresh_snapshots(self, name: str) -> list[int]:
        return [
            s for s in self.snapshots
            if self._present[name].get(s) and self._fresh[name][s]
        ]

    def ranges(self, name: str) -> list[tuple[int, int | None]]:
        """Half-open `[lo, hi)` version ranges, one per fresh snapshot."""
        fresh = self.fresh_snapshots(name)
        return [
            (lo, fresh[i + 1] if i + 1 < len(fresh) else None)
            for i, lo in enumerate(fresh)
        ]

    # --- analysis ------------------------------------------------------------

    def _versioned_types(self) -> frozenset[str]:
        versioned = {t.name for t in self._types if t.change_points}
        while True:
            grew = False
            for t in self._types:
                if isinstance(t, Enum) or t.name in versioned:
                    continue
                if t.referenced & versioned:
                    versioned.add(t.name)
                    grew = True
            if not grew:
                return frozenset(versioned)

    def _topo_order(self) -> list[str]:
        """Names ordered so a referenced type precedes its user. Ties keep
        declaration order; the reference graph is acyclic."""
        decl = [t.name for t in self._types]
        rank = {n: i for i, n in enumerate(decl)}
        deps = {
            t.name: (t.referenced & self._own) - {t.name} for t in self._types
        }
        order: list[str] = []
        state: dict[str, int] = {}

        def visit(name: str) -> None:
            if state.get(name):
                return
            state[name] = 1
            for dep in sorted(deps[name], key=rank.__getitem__):
                visit(dep)
            state[name] = 2
            order.append(name)

        for name in decl:
            visit(name)
        return order

    def _compute_snapshots(self) -> list[int]:
        points = {0}
        for t in self._types:
            if t.name in self.versioned:
                points |= t.change_points
        return sorted(points)

    def _plan_snapshots(self) -> None:
        for name in self.order:
            if name not in self.versioned:
                continue
            t = self._by_name[name]
            deps = (t.referenced & self.versioned) - {name}
            self._present[name], self._fresh[name] = {}, {}
            self._concrete[name], self._visible[name], self._keys[name] = {}, {}, {}
            previous: int | None = None
            for s in self.snapshots:
                here = t.since is None or s >= t.since
                self._present[name][s] = here
                if not here:
                    continue
                data, key = self._snapshot_view(t, s)
                self._visible[name][s], self._keys[name][s] = data, key
                if previous is None:
                    fresh, concrete = True, s
                else:
                    own_changed = key != self._keys[name][previous]
                    dep_changed = any(
                        self._concrete[d].get(s) != self._concrete[d].get(previous)
                        for d in deps
                    )
                    fresh = own_changed or dep_changed
                    concrete = s if fresh else self._concrete[name][previous]
                self._fresh[name][s] = fresh
                self._concrete[name][s] = concrete
                previous = s

    @staticmethod
    def _snapshot_view(
        t: Enum | Struct, snapshot: int
    ) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
        """The (data, identity-key) of a type at one snapshot. Two snapshots
        with equal keys share a definition."""
        if isinstance(t, Enum):
            members = tuple(
                m for m in t.members
                if (m.since is None or m.since <= snapshot)
                and (m.until is None or snapshot < m.until)
            )
            return members, tuple((m.name, m.value) for m in members)
        # Each field contributes the arm active at `snapshot`, narrowed to a
        # single-arm Field. The key carries the arm's type and wire, so the
        # snapshot also splits when only a field's encoding changed.
        narrowed: list[Field] = []
        key: list[Any] = []
        for f in t.fields:
            arm = f.arm_at(snapshot)
            if arm is None:
                continue
            narrowed.append(replace(f, arms=(arm,)))
            key.append((f.name, arm.type, arm.wire))
        return tuple(narrowed), tuple(key)
