"""Stage native distribution build inputs in a new directory."""

import argparse
import fnmatch
import shutil
import tomllib
from pathlib import Path

BUILD_INPUTS = (
    "CMakeLists.txt",
    "conanfile.py",
    "pyproject.native.toml",
    "cmake",
    "include",
    "src",
    "protocol",
    "tests",
    "third_party",
    "LICENSE",
    "README.md",
    "docs/python.md",
)


def stage(source, destination):
    if destination.exists():
        raise FileExistsError(destination)
    for name in BUILD_INPUTS:
        if not (source / name).exists():
            raise FileNotFoundError(source / name)
    metadata = tomllib.loads((source / "pyproject.native.toml").read_text(encoding="utf-8"))
    exclusions = metadata["tool"]["conan-py-build"]["sdist"]["exclude"]

    def ignore(directory, names):
        return [
            name for name in names
            if any(
                fnmatch.fnmatch((Path(directory) / name).relative_to(source).as_posix(), pattern)
                or fnmatch.fnmatch(name, pattern)
                for pattern in exclusions
            )
        ]

    destination.mkdir(parents=True)
    for name in BUILD_INPUTS:
        original, target = source / name, destination / name
        if original.is_dir():
            shutil.copytree(original, target, ignore=ignore)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, target)
    shutil.copyfile(destination / "pyproject.native.toml", destination / "pyproject.toml")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    stage(args.source.resolve(), args.destination.resolve())
