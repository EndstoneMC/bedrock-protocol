"""Build and execute generated native regressions with CMake, Ninja and nanobind 3.1.0.

python tests/compiler/native/run.py --work-dir <private-build-dir>
On Windows, run from a Visual Studio developer shell; pass
--cmake-arg=-DCMAKE_CXX_COMPILER=clang-cl to select clang-cl.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    fixture = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=fixture.parents[2])
    parser.add_argument("--cmake-arg", action="append", default=[])
    args = parser.parse_args()
    source, work = args.source_root.resolve(), args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONPATH=str(source / "src"), PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")

    def run(command, environment=env):
        subprocess.run(command, cwd=work, env=environment, check=True)

    schema = work / "input/protocol"
    schema.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source / "protocol/__init__.py", schema / "__init__.py")
    shutil.copyfile(fixture / "schema.py", schema / "schema.py")
    generated = work / "generated"
    for language, output in (("cpp", generated / "include/bedrock/protocol"), ("nanobind", generated / "native")):
        run(
            [
                sys.executable,
                "-m",
                "bedrock_protocol",
                "--language",
                language,
                "--out",
                output,
                "--import-path",
                schema.parent,
                schema / "schema.py",
            ],
        )
    (generated / "include/bedrock/protocol.hpp").write_text(
        "#pragma once\n#include <bedrock/protocol/schema.h>\n", encoding="utf-8"
    )
    package = work / "package/bedrock_protocol"
    package.mkdir(parents=True, exist_ok=True)
    for name in ("__init__.py", "_api.py"):
        shutil.copyfile(source / "src/bedrock_protocol" / name, package / name)
    for module in (generated / "native/bedrock_protocol").iterdir():
        shutil.copyfile(module, package / module.name)
    run(
        [
            "cmake",
            "-S",
            fixture,
            "-B",
            work / "build",
            "-G",
            "Ninja",
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DPython_EXECUTABLE={Path(sys.executable).as_posix()}",
            f"-DBPC_SOURCE_DIR={source.as_posix()}",
            f"-DFIXTURE_WORK_DIR={work.as_posix()}",
            *args.cmake_arg,
        ],
    )
    run(["cmake", "--build", work / "build", "--parallel", "2"])
    run(
        [sys.executable, "-m", "pytest", "-v", fixture / "check.py"],
        dict(env, PYTHONPATH=str(package.parent), BPC_NATIVE_FIXTURE_PACKAGE=str(package)),
    )


if __name__ == "__main__":
    main()
