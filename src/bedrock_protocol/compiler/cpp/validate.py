"""C++-only pre-codegen validation.

Constraints that aren't backend-agnostic — a name-coded nested enum, a
cross-module reference to a versioned type — live here. The frontend
remains language-agnostic; the C++ generator runs these checks before
emitting anything.
"""

from __future__ import annotations

from ...descriptor import (
    CompilerError,
    CondType,
    Enum,
    EnumType,
    OptionalType,
    ResolvedFile,
    Struct,
)


def check(resolved: ResolvedFile) -> None:
    _check_no_string_coded_nested_enums(resolved)
    _check_no_cross_module_versioned_references(resolved)


def _check_no_string_coded_nested_enums(resolved: ResolvedFile) -> None:
    """C++ codec for name-coded enums emits `Serializer<Enum>` specializations
    at namespace scope, which is awkward for a nested enum. Reject it here."""
    file = resolved.file
    for struct in file.structs:
        nested = frozenset(e.name for e in struct.nested_enums)
        if not nested:
            continue
        for f in struct.fields:
            for version in f.versions:
                t = version.type
                while isinstance(t, (OptionalType, CondType)):
                    t = t.inner
                if isinstance(t, EnumType) and t.name in nested and t.scalar is None:
                    raise CompilerError(
                        f"{struct.name}.{f.name}: a nested enum cannot be "
                        f"string-coded (field(type=str)) -- use an integer wire "
                        f"primitive, or lift the enum to module scope"
                    )


def _check_no_cross_module_versioned_references(
    resolved: ResolvedFile,
) -> None:
    """Cross-module references to a versioned type would need both headers'
    snapshot sets aligned — unsupported. Plain (unversioned) cross-module
    references like `Vec3` are fine."""
    file = resolved.file
    dep_versioned: set[str] = set()
    for dep in file.imports:
        other = resolved.file_set.files.get(dep)
        if other is None:
            continue
        other_types: tuple[Enum | Struct, ...] = (
            *other.enums, *other.structs,
        )
        for t in other_types:
            if t.change_points:
                dep_versioned.add(t.name)
    if not dep_versioned:
        return
    for struct in file.structs:
        roots = frozenset(r.split(".", 1)[0] for r in struct.referenced)
        bad = roots & dep_versioned
        if bad:
            raise CompilerError(
                f"{struct.name}: references versioned type(s) {sorted(bad)} "
                f"from another module -- cross-module versioning is unsupported"
            )
