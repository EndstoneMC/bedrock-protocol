"""Version-snapshot analysis + dependency resolution.

Analog of protoc's `DescriptorBuilder` step inside `DescriptorPool::Add`.
Takes the raw `File` the parser emitted, validates that every type
reference resolves (against the file or its imports), classifies which
types are versioned, computes a topological order, and projects each
versioned type into per-snapshot views.

A versioned type is one whose definition gains or loses something at a
known protocol version, transitively. Each versioned type splits into
snapshots `[s_i, s_{i+1})`; each snapshot either holds a fresh definition
or, when nothing has changed, reuses an earlier one. A backend reads the
resulting `VersionSnapshot.is_fresh` to decide whether to emit a definition
or a `using` alias.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable

from ..descriptor import (
    BitsetType,
    CompilerError,
    CondType,
    Enum,
    Field,
    FieldType,
    FieldVersion,
    File,
    FileSet,
    MappingType,
    OptionalType,
    RepeatedType,
    ResolvedFile,
    Struct,
    VariantType,
    VersionSnapshot,
)


def resolve_all(file_set: FileSet) -> tuple[ResolvedFile, ...]:
    """Resolve every output file in `file_set`, in `file_set.outputs` order."""
    return tuple(resolve(file_set.files[name], file_set) for name in file_set.outputs)


def resolve(file: File, file_set: FileSet) -> ResolvedFile:
    all_types: tuple[Enum | Struct, ...] = (
        *file.enums, *file.structs,
    )
    by_name: dict[str, Enum | Struct] = {
        t.name: t for t in all_types
    }
    # Source declaration order, not enums-then-structs — the layout the C++
    # backend emits depends on this.
    types: tuple[Enum | Struct, ...] = tuple(
        by_name[n] for n in file.declaration_order if n in by_name
    )
    own = frozenset(by_name)

    versioned = _versioned_types(types)
    order = _topo_order(types, own)
    snapshots = _snapshot_points(types, versioned)
    snapshots_by_type = _plan_snapshots(types, by_name, versioned, order, snapshots)

    return ResolvedFile(
        file=file,
        file_set=file_set,
        declaration_order=tuple(order),
        versioned_types=versioned,
        snapshots=tuple(snapshots),
        snapshots_by_type=snapshots_by_type,
    )


# --- versioned classification -------------------------------------------------


def _versioned_types(
    types: tuple[Enum | Struct, ...],
) -> frozenset[str]:
    """Names that are versioned, either by their own change points or by a
    transitive reference to a versioned type."""
    versioned: set[str] = {t.name for t in types if t.change_points}
    while True:
        grew = False
        for t in types:
            if isinstance(t, Enum) or t.name in versioned:
                continue
            if t.referenced & versioned:
                versioned.add(t.name)
                grew = True
        if not grew:
            return frozenset(versioned)


# --- topological order --------------------------------------------------------


def _topo_order(
    types: tuple[Enum | Struct, ...],
    own: frozenset[str],
) -> list[str]:
    """Names ordered so a referenced type precedes its user. Ties keep
    declaration order; the reference graph is acyclic."""
    decl = [t.name for t in types]
    rank = {n: i for i, n in enumerate(decl)}
    deps = {
        t.name: (t.referenced & own) - {t.name} for t in types
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


# --- snapshots ----------------------------------------------------------------


def _snapshot_points(
    types: tuple[Enum | Struct, ...],
    versioned: frozenset[str],
) -> list[int]:
    points = {0}
    for t in types:
        if t.name in versioned:
            points |= t.change_points
    return sorted(points)


def _plan_snapshots(
    types: tuple[Enum | Struct, ...],
    by_name: dict[str, Enum | Struct],
    versioned: frozenset[str],
    order: Iterable[str],
    snapshots: list[int],
) -> dict[str, tuple[VersionSnapshot, ...]]:
    """One `VersionSnapshot` tuple per versioned type, in snapshot order."""
    result: dict[str, tuple[VersionSnapshot, ...]] = {}
    # Identity keys per (name, snapshot) — for deciding when a definition is
    # fresh vs. a re-use of the previous snapshot.
    keys: dict[str, dict[int, tuple[Any, ...]]] = {}
    # The snapshot whose definition (name, snapshot) resolves to.
    concrete: dict[str, dict[int, int]] = {}

    for name in order:
        if name not in versioned:
            continue
        t = by_name[name]
        deps = (t.referenced & versioned) - {name}
        keys[name] = {}
        concrete[name] = {}
        out: list[VersionSnapshot] = []
        previous: int | None = None
        for i, s in enumerate(snapshots):
            present = t.since is None or s >= t.since
            if not present:
                continue
            enum_view, struct_view, key = _snapshot_view(t, s)
            keys[name][s] = key
            if previous is None:
                fresh = True
                conc = s
            else:
                own_changed = key != keys[name][previous]
                dep_changed = any(
                    concrete[d].get(s) != concrete[d].get(previous)
                    for d in deps
                )
                fresh = own_changed or dep_changed
                conc = s if fresh else concrete[name][previous]
            concrete[name][s] = conc
            hi = snapshots[i + 1] if i + 1 < len(snapshots) else None
            out.append(VersionSnapshot(
                lo=s,
                hi=hi,
                is_fresh=fresh,
                concrete=conc,
                enum=enum_view,
                struct=struct_view,
            ))
            previous = s
        result[name] = tuple(out)
    return result


def _snapshot_view(
    t: Enum | Struct, snapshot: int
) -> tuple[Enum | None, Struct | None, tuple[Any, ...]]:
    """A narrowed-to-snapshot view of `t`, plus an identity key that
    determines whether two snapshots share one definition."""
    if isinstance(t, Enum):
        values = _narrow_enum_values(t.values, snapshot)
        view = Enum(t.name, values, t.since)
        key = _enum_key(values)
        return view, None, key
    narrowed_enums: list[Enum] = []
    nested_values: dict[str, dict[str, int]] = {}
    enum_key_parts: list[Any] = []
    for e in t.nested_enums:
        ev = _narrow_enum_values(e.values, snapshot)
        narrowed_enums.append(Enum(e.name, ev, e.since))
        nested_values[e.name] = {v.name: v.number for v in ev}
        enum_key_parts.append((e.name, _enum_key(ev)))
    narrowed: list[Field] = []
    key_parts: list[Any] = []
    for f in t.fields:
        version = f.version_at(snapshot)
        if version is None:
            continue
        rebound = _rebind_bitsets(version.type, nested_values)
        if rebound is not version.type:
            version = replace(version, type=rebound)
        narrowed.append(Field(f.name, (version,)))
        key_parts.append((f.name, version.type))
    view_s = replace(
        t, fields=tuple(narrowed), nested_enums=tuple(narrowed_enums),
    )
    return None, view_s, tuple(key_parts) + (tuple(enum_key_parts),)


def _rebind_bitsets(
    t: FieldType | None,
    nested: dict[str, dict[str, int]],
) -> FieldType | None:
    """Walk a field-type tree, replacing `BitsetType(size=..., enum_member=X)`
    with `BitsetType(size=N)` where N is the snapshot value of the enum
    member. Anything without a symbolic ref or whose enum/member isn't in the
    snapshot's nested-enum map is left untouched.
    """
    if t is None:
        return None
    if isinstance(t, BitsetType):
        if t.enum_member is None:
            return t
        enum_name, member_name = t.enum_member
        members = nested.get(enum_name)
        if members is None or member_name not in members:
            return t
        new_size = members[member_name]
        if new_size == t.size:
            return t
        return replace(t, size=new_size)
    if isinstance(t, OptionalType):
        inner = _rebind_bitsets(t.inner, nested)
        return replace(t, inner=inner) if inner is not t.inner else t
    if isinstance(t, RepeatedType):
        inner = _rebind_bitsets(t.inner, nested)
        return replace(t, inner=inner) if inner is not t.inner else t
    if isinstance(t, MappingType):
        key = _rebind_bitsets(t.key, nested)
        val = _rebind_bitsets(t.value, nested)
        if key is t.key and val is t.value:
            return t
        return replace(t, key=key, value=val)
    if isinstance(t, VariantType):
        new_cases = tuple(_rebind_bitsets(c, nested) for c in t.cases)
        if new_cases == t.cases:
            return t
        return replace(t, cases=new_cases)
    if isinstance(t, CondType):
        inner = _rebind_bitsets(t.inner, nested)
        return replace(t, inner=inner) if inner is not t.inner else t
    return t


def _enum_key(values: tuple[Any, ...]) -> tuple[Any, ...]:
    """Identity key for a narrowed enum view: name, number, and whether the
    value carries deprecation at this snapshot. Two snapshots that differ
    only in which members are `[[deprecated]]` get separate definitions."""
    return tuple(
        (v.name, v.number, v.deprecated is not None) for v in values
    )


def _narrow_enum_values(
    values: tuple[Any, ...], snapshot: int
) -> tuple[Any, ...]:
    """Filter enum values to those present at `snapshot`, suppress the
    `deprecated` marker on members whose deprecation version hasn't kicked
    in yet, then re-resolve every sentinel as one past the highest
    non-sentinel member of the narrowed set."""
    from dataclasses import replace as _replace
    present: list[Any] = []
    for v in values:
        if v.since is not None and v.since > snapshot:
            continue
        if v.until is not None and snapshot >= v.until:
            continue
        dep = v.deprecated if (
            v.deprecated is not None and snapshot >= v.deprecated
        ) else None
        present.append(_replace(v, deprecated=dep))
    if any(v.sentinel for v in present):
        non_sentinel = [v.number for v in present if not v.sentinel]
        if non_sentinel:
            high = max(non_sentinel) + 1
            present = [
                _replace(v, number=high) if v.sentinel else v
                for v in present
            ]
    return tuple(present)
