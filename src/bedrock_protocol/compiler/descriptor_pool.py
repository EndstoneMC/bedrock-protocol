"""`DescriptorPool` — protoc analog of `descriptor.{h,cc}`'s pool half.

protoc splits a schema in two: `FileDescriptorProto` is what the parser emits,
pure data; `FileDescriptor` is what `DescriptorPool::BuildFile` returns, with its
cross-file references resolved. We mirror that pair as `File` and `ResolvedFile`,
and this is the pool that turns one into the other.

`build_file` is protoc's `DescriptorPool::BuildFile`: it resolves a file's imports
first, then runs the equivalent of `DescriptorBuilder` over it -- classify which
types are versioned, order them topologically, and project each versioned type
into per-snapshot views. Built files are memoised here, in the pool, the way
protoc keeps them in `DescriptorPool::Tables`; a descriptor holds a back-reference
to its pool (`ResolvedFile.pool`, protoc's `FileDescriptor::pool()`) rather than
carrying the cache itself.

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


class DescriptorPool:
    """Builds `ResolvedFile` descriptors from the parser's `File` protos, and owns
    them once built. protoc's `DescriptorPool`."""

    def __init__(self, file_set: FileSet) -> None:
        self._file_set = file_set
        self._built: dict[str, ResolvedFile] = {}

    @property
    def file_set(self) -> FileSet:
        return self._file_set

    def find_file_by_name(self, name: str) -> ResolvedFile | None:
        """An already-built descriptor, or None. protoc's
        `DescriptorPool::FindFileByName`, minus the on-demand build: a file's
        imports are always built before it, so a lookup during a build finds them."""
        return self._built.get(name)

    def build_all(self) -> tuple[ResolvedFile, ...]:
        """Every output file, in `file_set.outputs` order."""
        return tuple(self.build_file(name) for name in self._file_set.outputs)

    def build_file(self, name: str, _visiting: frozenset[str] = frozenset()) -> ResolvedFile:
        """protoc's `DescriptorPool::BuildFile`: cross-reference one file and hand
        back its descriptor, building its imports first."""
        built = self._built.get(name)
        if built is not None:
            return built
        resolved = self._build(self._file_set.files[name], _visiting)
        self._built[name] = resolved
        return resolved

    def _build(self, file: File, _visiting: frozenset[str]) -> ResolvedFile:
        file_set = self._file_set
        # Build imports first so cross-file lookups find their snapshot info
        # already in the pool. Skip an import already being built higher up the
        # stack (an import cycle): recursing would never terminate.
        deeper = _visiting | {file.name}
        for imp in file.imports:
            if imp in file_set.files and imp not in deeper:
                self.build_file(imp, deeper)

        all_types: tuple[Enum | Struct, ...] = (*file.enums, *file.structs)
        by_name: dict[str, Enum | Struct] = {t.name: t for t in all_types}
        # Source declaration order, not enums-then-structs -- the C++ layout depends on it.
        types: tuple[Enum | Struct, ...] = tuple(by_name[n] for n in file.declaration_order if n in by_name)
        own = frozenset(by_name)

        versioned = _versioned_types(types, file, self)
        order = _topo_order(types, own)
        snapshots = _snapshot_points(types, versioned, file, self)
        snapshots_by_type = _plan_snapshots(types, by_name, versioned, order, snapshots, file, self)

        return ResolvedFile(
            file=file,
            pool=self,
            declaration_order=tuple(order),
            versioned_types=versioned,
            snapshots=tuple(snapshots),
            snapshots_by_type=snapshots_by_type,
        )


# --- versioned classification -------------------------------------------------


def _versioned_types(types: tuple[Enum | Struct, ...], file: File, pool: DescriptorPool) -> frozenset[str]:
    """Names that are versioned by their own change points or by a transitive
    reference to a versioned type. Folds in versioned names from resolved
    imports so a reference to an imported versioned type propagates back."""
    versioned: set[str] = {t.name for t in types if t.change_points}
    for imp in file.imports:
        other = pool.find_file_by_name(imp)
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
    pool: DescriptorPool,
) -> list[int]:
    points = {0}
    for t in types:
        if t.name in versioned:
            points |= t.change_points
    for imp in file.imports:
        other = pool.find_file_by_name(imp)
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
    pool: DescriptorPool,
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
            other = pool.find_file_by_name(imp)
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
        since = getattr(t, "since", None)
        until = getattr(t, "until", None)
        for i, s in enumerate(snapshots):
            present = (since is None or s >= since) and (until is None or s < until)
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
        values = tuple(v for v in t.values if v.present_at(snapshot))
        key = tuple((v.name, v.number) for v in values)
        return Enum(t.name, values, t.underlying), None, key
    narrowed: list[Field] = []
    key_parts: list[Any] = []
    for f in t.fields:
        version = f.version_at(snapshot)
        if version is None:
            continue
        narrowed.append(Field(f.name, (version,)))
        key_parts.append((f.name, version.type))
    return None, replace(t, fields=tuple(narrowed)), tuple(key_parts)
