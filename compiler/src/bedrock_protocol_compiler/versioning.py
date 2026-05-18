"""Version-snapshot planning.

Turns a module's version-gated griffe classes into a concrete emission plan:
each generated type becomes a plain (non-template) `struct` / `enum class` in a
version-snapshot namespace `bedrock::protocol::v{N}`. A type whose definition
does not change between two snapshots is emitted as a `using` alias to the
earlier snapshot, so it is literally the same type -- no extra template
instantiation, one shared `Serializer`. A `detail::XXX_<V>` traits template plus
a `XXX_<V>` alias template restore the `XXX_<V>` spelling for callers.

A type is *versioned* only if it has a real version change-point, or transitively
references one. Types that never vary stay a single plain definition in
`bedrock::protocol` (like `Vec3`).
"""

import click
import inflection

from .filters import (
    class_has_field_since,
    enum_members,
    field_serialize_kind,
    nested_enums,
    referenced_names,
    reject_versioned_nested_enums,
    string_coded_enums,
)
from .parse import (
    class_packet_id,
    class_since,
    is_int_enum,
    since_kwarg,
)
from .types import resolve_type


def _camel(name: str) -> str:
    """`THROW_ITEM` -> `ThrowItem` -- the C++ enumerator spelling."""
    return inflection.camelize(name.lower())


def _field_since(attr) -> int | None:
    return since_kwarg(attr.value, "field") if attr.value is not None else None


def _enum_change_points(cls) -> set[int]:
    points: set[int] = set()
    cs = class_since(cls)
    if cs is not None:
        points.add(cs)
    for _, _, since, until in enum_members(cls)["entries"]:
        if since is not None:
            points.add(since)
        if until is not None:
            points.add(until)
    return points


def _change_points(cls) -> set[int]:
    """Intrinsic version change-points of one class -- the versions at which its
    own definition gains or loses something."""
    if is_int_enum(cls):
        return _enum_change_points(cls)
    return {
        s
        for _, attr in cls.attributes.items()
        if (s := _field_since(attr)) is not None
    }


def _has_change_point(cls) -> bool:
    return bool(_change_points(cls))


def compute_versioned_types(classes) -> set[str]:
    """Names of types that must be version-snapshotted.

    A type is versioned iff it has an intrinsic change-point, or transitively
    references a versioned type. Fixed-point iteration over the field-reference
    graph. Unlike the old "templated" notion this seeds with enums that actually
    vary -- a referenced-but-never-gated enum no longer drags its packets into
    the version machinery.
    """
    versioned: set[str] = {c.name for c in classes if _has_change_point(c)}
    while True:
        changed = False
        for c in classes:
            if is_int_enum(c) or c.name in versioned:
                continue
            for _, attr in c.attributes.items():
                if referenced_names(attr.annotation) & versioned:
                    versioned.add(c.name)
                    changed = True
                    break
        if not changed:
            return versioned


def _module_snapshots(classes, versioned: set[str]) -> list[int]:
    """Sorted snapshot versions for the module: 0 plus every change-point of
    every versioned type. Ranges are `[s_i, s_{i+1})`."""
    points = {0}
    for c in classes:
        if c.name in versioned:
            points |= _change_points(c)
    return sorted(points)


def _topo_order(classes, own_names: set[str]) -> list[str]:
    """Type names ordered so a referenced type precedes the type that uses it.
    Stable: ties keep declaration order. The protocol graph is acyclic."""
    decl = [c.name for c in classes]
    decl_index = {n: i for i, n in enumerate(decl)}
    deps: dict[str, set[str]] = {}
    for c in classes:
        d: set[str] = set()
        for _, attr in c.attributes.items():
            d |= referenced_names(attr.annotation) & own_names
        deps[c.name] = d - {c.name}

    order: list[str] = []
    state: dict[str, int] = {}

    def visit(n: str) -> None:
        if state.get(n):
            return
        state[n] = 1
        for m in sorted(deps[n], key=lambda x: decl_index[x]):
            visit(m)
        state[n] = 2
        order.append(n)

    for n in decl:
        visit(n)
    return order


def _guard_cross_module(own_classes, dep_classes, own_names: set[str]) -> None:
    """Cross-module references to a *versioned* type are not supported -- the
    snapshot sets of the two headers would have to be aligned. All current
    cross-module references target unversioned types (`Vec3`, primitives)."""
    dep_versioned = {c.name for c in dep_classes if _has_change_point(c)}
    if not dep_versioned:
        return
    for c in own_classes:
        for _, attr in c.attributes.items():
            bad = referenced_names(attr.annotation) & dep_versioned
            if bad:
                raise click.ClickException(
                    f"{c.name}: references versioned type(s) {sorted(bad)} from "
                    f"another module -- cross-module versioning is unsupported"
                )


def plan_module(
    mod,
    own_classes,
    dep_classes,
    class_names: set[str],
    enum_names: set[str],
    alias_wires: dict[str, dict],
):
    """Build the full render model for one output header.

    Returns a dict the templates consume directly: unversioned defs, per-snapshot
    namespaces (fresh defs or `using` aliases), `detail` traits ranges,
    topologically ordered `Serializer` specializations, and latest-version
    aliases.
    """
    type_aliases = set(alias_wires)
    name_to_cls = {c.name: c for c in own_classes}
    own_names = set(name_to_cls)
    decl_order = [c.name for c in own_classes]

    for c in own_classes:
        if not is_int_enum(c):
            reject_versioned_nested_enums(c, nested_enums(c))

    _guard_cross_module(own_classes, dep_classes, own_names)

    versioned = compute_versioned_types(own_classes)
    snapshots = _module_snapshots(own_classes, versioned)
    order = _topo_order(own_classes, own_names)
    str_enums = string_coded_enums(mod, enum_names)

    # --- per (versioned type, snapshot): present / fresh / concrete / visible.
    present: dict[str, dict[int, bool]] = {}
    fresh: dict[str, dict[int, bool]] = {}
    concrete: dict[str, dict[int, int]] = {}
    vis: dict[str, dict[int, tuple]] = {}  # snapshot -> (key, data)

    for name in order:
        if name not in versioned:
            continue
        cls = name_to_cls[name]
        is_enum = is_int_enum(cls)
        deps = set()
        for _, attr in cls.attributes.items():
            deps |= referenced_names(attr.annotation)
        deps = (deps & versioned) - {name}

        present[name], fresh[name], concrete[name], vis[name] = {}, {}, {}, {}
        prev: int | None = None
        for s in snapshots:
            if is_enum:
                cs = class_since(cls)
                here = cs is None or s >= cs
            else:
                here = True
            present[name][s] = here
            if not here:
                continue
            if is_enum:
                data = [
                    (n, v)
                    for n, v, since, until in enum_members(cls)["entries"]
                    if (since is None or since <= s)
                    and (until is None or s < until)
                ]
                key = tuple(data)
            else:
                data = [
                    (fn, attr)
                    for fn, attr in cls.attributes.items()
                    if _field_since(attr) is None or _field_since(attr) <= s
                ]
                key = tuple(fn for fn, _ in data)
            vis[name][s] = (key, data)
            if prev is None:
                is_fresh = True
            else:
                own_changed = key != vis[name][prev][0]
                dep_changed = any(
                    concrete[d].get(s) != concrete[d].get(prev) for d in deps
                )
                is_fresh = own_changed or dep_changed
            fresh[name][s] = is_fresh
            concrete[name][s] = s if is_fresh else concrete[name][prev]
            prev = s

    def fresh_snapshots(name: str) -> list[int]:
        return [s for s in snapshots if present[name].get(s) and fresh[name][s]]

    # --- record builders.
    def build_enum_def(name: str, members) -> dict:
        return {
            "kind": "enum",
            "name": name,
            "members": [(_camel(n), v) for n, v in members],
        }

    def build_struct_def(name: str, fields) -> dict:
        cls = name_to_cls[name]
        nested = nested_enums(cls)
        nested_names = set(nested)
        constants = []
        pid = class_packet_id(cls)
        if pid is not None:
            constants.append(("Id", "int", str(pid)))
        nested_defs = [
            (
                ename,
                [(_camel(n), v) for n, v, _, _ in enum_members(ecls)["entries"]],
            )
            for ename, ecls in nested.items()
        ]
        field_dicts = []
        unmapped = False
        for fname, attr in fields:
            ctype = (
                resolve_type(
                    attr.annotation,
                    class_names,
                    enum_names,
                    nested_names,
                    type_aliases,
                )
                if attr.annotation is not None
                else None
            )
            if ctype is None:
                unmapped = True
                break
            field_dicts.append({"name": fname, "ctype": ctype})
        return {
            "kind": "struct",
            "name": name,
            "nested_enums": nested_defs,
            "constants": constants,
            "fields": [] if unmapped else field_dicts,
            "unmapped": unmapped,
        }

    def build_def(name: str, data) -> dict:
        if is_int_enum(name_to_cls[name]):
            return build_enum_def(name, data)
        return build_struct_def(name, data)

    def _annotate(info: dict, owner_qual: str, qualify) -> None:
        kind = info["kind"]
        if kind == "enum":
            tn = info["type_name"]
            if info.get("nested"):
                info["value_cast"] = f"{owner_qual}::{tn}"
                info["ser_type"] = f"{owner_qual}::{tn}"
            else:
                spelled = qualify(tn) + tn
                info["value_cast"] = spelled
                info["ser_type"] = spelled
        elif kind == "struct":
            tn = info["type_name"]
            info["ser_type"] = qualify(tn) + tn
        elif kind in ("optional", "optional_variant"):
            _annotate(info["inner"], owner_qual, qualify)

    def serializer_fields(name: str, snap: int | None, fields):
        cls = name_to_cls[name]
        nested_names = set(nested_enums(cls))
        owner_qual = f"v{snap}::{name}" if name in versioned else name

        def qualify(tn: str) -> str:
            if tn in versioned:
                return f"v{concrete[tn][snap]}::"
            return ""

        out = []
        serializable = True
        for fname, attr in fields:
            info = field_serialize_kind(
                attr, class_names, enum_names, alias_wires, nested_names
            ) or {"kind": "unknown"}
            if info["kind"] == "unknown" or (
                info.get("inner", {}).get("kind") == "unknown"
            ):
                serializable = False
            ctype = resolve_type(
                attr.annotation, class_names, enum_names, nested_names, type_aliases
            )
            _annotate(info, owner_qual, qualify)
            out.append({"name": fname, "ctype": ctype, **info})
        return out, serializable

    def struct_serializer(name: str, snap: int | None):
        cls = name_to_cls[name]
        if name in versioned:
            fields = vis[name][snap][1]
            qualified = f"v{snap}::{name}"
        else:
            fields = list(cls.attributes.items())
            qualified = name
        field_recs, serializable = serializer_fields(name, snap, fields)
        if not serializable:
            return None
        return {"enum": False, "qualified": qualified, "fields": field_recs}

    def enum_serializer(name: str, snap: int | None):
        cls = name_to_cls[name]
        if name in versioned:
            members = vis[name][snap][1]
            qualified = f"v{snap}::{name}"
        else:
            members = [(n, v) for n, v, _, _ in enum_members(cls)["entries"]]
            qualified = name
        return {
            "enum": True,
            "qualified": qualified,
            "members": [(_camel(n), n.lower().replace("_", "")) for n, _ in members],
        }

    # --- assemble the model.
    unversioned_defs = []
    for name in order:
        if name in versioned:
            continue
        cls = name_to_cls[name]
        if is_int_enum(cls):
            members = [(n, v) for n, v, _, _ in enum_members(cls)["entries"]]
            unversioned_defs.append(build_enum_def(name, members))
        else:
            unversioned_defs.append(
                build_struct_def(name, list(cls.attributes.items()))
            )

    namespaces = []
    for s in snapshots:
        entries = []
        for name in order:
            if name not in versioned or not present[name].get(s):
                continue
            if fresh[name][s]:
                entries.append(
                    {"alias": False, "def": build_def(name, vis[name][s][1])}
                )
            else:
                entries.append(
                    {
                        "alias": True,
                        "name": name,
                        "target": f"v{concrete[name][s]}",
                    }
                )
        namespaces.append({"version": s, "entries": entries})

    traits = []
    for name in order:
        if name not in versioned:
            continue
        fs = fresh_snapshots(name)
        ranges = [
            (lo, fs[i + 1] if i + 1 < len(fs) else None)
            for i, lo in enumerate(fs)
        ]
        traits.append({"name": name, "ranges": ranges})

    serializers = []
    for name in order:
        cls = name_to_cls[name]
        if is_int_enum(cls):
            if name not in str_enums:
                continue
            snaps = fresh_snapshots(name) if name in versioned else [None]
            for snap in snaps:
                serializers.append(enum_serializer(name, snap))
        else:
            snaps = fresh_snapshots(name) if name in versioned else [None]
            for snap in snaps:
                rec = struct_serializer(name, snap)
                if rec is not None:
                    serializers.append(rec)

    return {
        "has_versioned": bool(versioned),
        "has_serializers": bool(serializers),
        "unversioned": unversioned_defs,
        "namespaces": namespaces,
        "traits": traits,
        "serializers": serializers,
        "latest_aliases": [n for n in decl_order if n in versioned],
    }
