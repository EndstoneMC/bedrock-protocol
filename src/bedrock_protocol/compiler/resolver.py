"""Version-snapshot analysis + dependency resolution.

Analog of protoc's `DescriptorBuilder` step inside `DescriptorPool::Add`. Takes
the raw `File` the parser emitted, classifies which types are versioned,
computes a topological order, and projects each versioned type into
per-snapshot views.

A versioned type is one whose definition changes at a known protocol version,
transitively. Each versioned type splits into snapshots `[s_i, s_{i+1})`; each
either holds a fresh definition or reuses an earlier one. A backend reads
`VersionSnapshot.is_fresh` to decide between a definition and a `using` alias.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable

from bedrock_protocol.descriptor import (
    Enum,
    Field,
    File,
    FileSet,
    ResolvedFile,
    Struct,
    VersionSnapshot,
)


def resolve_all(file_set: FileSet) -> tuple[ResolvedFile, ...]:
    """Resolve every output file in `file_set`, in `file_set.outputs` order."""
    return tuple(resolve(file_set.files[name], file_set) for name in file_set.outputs)


def resolve(file: File, file_set: FileSet, _visiting: frozenset[str] = frozenset()) -> ResolvedFile:
    cached = file_set.resolved.get(file.name)
    if cached is not None:
        return cached

    # Resolve imports first so cross-file lookups find their snapshot info
    # already cached. Skip an import already being resolved higher up the stack
    # (an import cycle): recursing would never terminate.
    deeper = _visiting | {file.name}
    for imp in file.imports:
        other = file_set.files.get(imp)
        if other is not None and imp not in deeper:
            resolve(other, file_set, deeper)

    all_types: tuple[Enum | Struct, ...] = (*file.enums, *file.structs)
    by_name: dict[str, Enum | Struct] = {t.name: t for t in all_types}
    # Source declaration order, not enums-then-structs -- the C++ layout depends on it.
    types: tuple[Enum | Struct, ...] = tuple(by_name[n] for n in file.declaration_order if n in by_name)
    own = frozenset(by_name)

    versioned = _versioned_types(types, file, file_set)
    order = _topo_order(types, own)
    snapshots = _snapshot_points(types, versioned, file, file_set)
    snapshots_by_type = _plan_snapshots(types, by_name, versioned, order, snapshots, file, file_set)

    resolved = ResolvedFile(
        file=file,
        file_set=file_set,
        declaration_order=tuple(order),
        versioned_types=versioned,
        snapshots=tuple(snapshots),
        snapshots_by_type=snapshots_by_type,
    )
    file_set.resolved[file.name] = resolved
    return resolved


# --- versioned classification -------------------------------------------------


def _versioned_types(types: tuple[Enum | Struct, ...], file: File, file_set: FileSet) -> frozenset[str]:
    """Names that are versioned by their own change points or by a transitive
    reference to a versioned type. Folds in versioned names from resolved
    imports so a reference to an imported versioned type propagates back."""
    versioned: set[str] = {t.name for t in types if t.change_points}
    for imp in file.imports:
        other = file_set.resolved.get(imp)
        if other is not None:
            versioned |= other.versioned_types
    while True:
        grew = False
        for t in types:
            if isinstance(t, Enum) or t.name in versioned:
                continue
            refs = frozenset(_root_of(r) for r in t.referenced)
            if refs & versioned:
                versioned.add(t.name)
                grew = True
        if not grew:
            return frozenset(versioned)


def _root_of(ref: str) -> str:
    return ref.split(".", 1)[0]


# --- topological order --------------------------------------------------------


def _topo_order(types: tuple[Enum | Struct, ...], own: frozenset[str]) -> list[str]:
    """Names ordered so a referenced type precedes its user. Ties keep
    declaration order; the reference graph is acyclic."""
    decl = [t.name for t in types]
    rank = {n: i for i, n in enumerate(decl)}
    deps = {t.name: (frozenset(_root_of(r) for r in t.referenced) & own) - {t.name} for t in types}
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


# --- snapshots ----------------------------------------------------------------


def _snapshot_points(
    types: tuple[Enum | Struct, ...],
    versioned: frozenset[str],
    file: File,
    file_set: FileSet,
) -> list[int]:
    points = {0}
    for t in types:
        if t.name in versioned:
            points |= t.change_points
    for imp in file.imports:
        other = file_set.resolved.get(imp)
        if other is not None:
            points |= set(other.snapshots)
    return sorted(points)


def _plan_snapshots(
    types: tuple[Enum | Struct, ...],
    by_name: dict[str, Enum | Struct],
    versioned: frozenset[str],
    order: Iterable[str],
    snapshots: list[int],
    file: File,
    file_set: FileSet,
) -> dict[str, tuple[VersionSnapshot, ...]]:
    """One `VersionSnapshot` tuple per versioned type, in snapshot order."""
    result: dict[str, tuple[VersionSnapshot, ...]] = {}
    keys: dict[str, dict[int, tuple[Any, ...]]] = {}
    concrete: dict[str, dict[int, int]] = {}

    def dep_concrete(name: str, snapshot: int) -> int | None:
        own = concrete.get(name)
        if own is not None:
            view = own.get(snapshot)
            if view is not None:
                return view
        for imp in file.imports:
            other = file_set.resolved.get(imp)
            if other is None:
                continue
            snap = other.present_at(name, snapshot)
            if snap is not None:
                return snap.concrete
        return None

    for name in order:
        if name not in versioned:
            continue
        t = by_name[name]
        deps = (frozenset(_root_of(r) for r in t.referenced) & versioned) - {name}
        keys[name] = {}
        concrete[name] = {}
        out: list[VersionSnapshot] = []
        previous: int | None = None
        until = getattr(t, "until", None)
        for i, s in enumerate(snapshots):
            present = (t.since is None or s >= t.since) and (until is None or s < until)
            if not present:
                continue
            enum_view, struct_view, key = _snapshot_view(t, s)
            keys[name][s] = key
            if previous is None:
                fresh = True
                conc = s
            else:
                own_changed = key != keys[name][previous]
                dep_changed = any(dep_concrete(d, s) != dep_concrete(d, previous) for d in deps)
                fresh = own_changed or dep_changed
                conc = s if fresh else concrete[name][previous]
            concrete[name][s] = conc
            hi = snapshots[i + 1] if i + 1 < len(snapshots) else None
            out.append(VersionSnapshot(lo=s, hi=hi, is_fresh=fresh, concrete=conc, enum=enum_view, struct=struct_view))
            previous = s
        result[name] = tuple(out)
    return result


def _snapshot_view(t: Enum | Struct, snapshot: int) -> tuple[Enum | None, Struct | None, tuple[Any, ...]]:
    """A narrowed-to-snapshot view of `t`, plus an identity key that determines
    whether two snapshots share one definition."""
    if isinstance(t, Enum):
        key = tuple((v.name, v.number) for v in t.values)
        return Enum(t.name, t.values), None, key
    narrowed: list[Field] = []
    key_parts: list[Any] = []
    for f in t.fields:
        version = f.version_at(snapshot)
        if version is None:
            continue
        narrowed.append(Field(f.name, (version,)))
        key_parts.append((f.name, version.type))
    return None, replace(t, fields=tuple(narrowed)), tuple(key_parts)
