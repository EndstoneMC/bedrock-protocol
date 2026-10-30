"""Check independently installed distributions."""

import argparse
import ast
import importlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path


def literal(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"missing {name}")


def declarations(tree, module):
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            value = getattr(module, node.name)
            declarations(node, value)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    getattr(module, target.id)
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and not node.target.id.startswith("_")
        ):
            getattr(module, node.target.id)


def installed(schema):
    import bedrock_protocol as bp

    package = Path(bp.__file__).resolve().parent
    assert package.is_relative_to(Path(sys.prefix).resolve()), package
    assert (package / "py.typed").is_file()
    expected = literal(ast.parse(schema.read_text(encoding="utf-8")), "__supported_versions__")
    assert bp.SUPPORTED_VERSIONS == expected
    versions = [f"v{version}" for version in expected]
    assert [name for name in bp.__all__ if name.startswith("v") and name[1:].isdigit()] == versions
    stub = ast.parse((package / "__init__.pyi").read_text(encoding="utf-8"))
    assert bp.__all__ == literal(stub, "__all__")
    for name in bp.__all__:
        getattr(bp, name)
    for name in [*versions, "wire"]:
        module = importlib.import_module(f"bedrock_protocol.{name}")
        assert getattr(bp, name) is module
        stub = ast.parse((package / f"{name}.pyi").read_text(encoding="utf-8"))
        declarations(stub, module)
    print(f"Installed consumer: {package}; {len(expected)} versions, stubs and exports passed")


def compiler(schema, workspace):
    import bedrock_protocol as bp

    package = Path(bp.__file__).resolve().parent
    assert package.is_relative_to(Path(sys.prefix).resolve()), package
    assert not workspace.is_relative_to(Path(__file__).resolve().parents[2]), workspace
    assert not workspace.exists(), workspace
    launcher = Path(sysconfig.get_path("scripts")) / ("bpc.exe" if os.name == "nt" else "bpc")
    assert launcher.is_file(), launcher
    inputs = workspace / "protocol"
    inputs.mkdir(parents=True)
    shutil.copyfile(schema, inputs / "__init__.py")
    (inputs / "installed.py").write_text(
        "from protocol import packet, uint32\n\n"
        "@packet(id=1)\nclass InstalledPacket:\n    value: uint32\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    subprocess.run(
        [str(launcher), "--language", "cpp", "--out", "generated", "--import-path", ".", "protocol/installed.py"],
        cwd=workspace,
        env=env,
        check=True,
    )
    header = workspace / "generated/installed.h"
    source = workspace / "generated/installed.cpp"
    assert "struct InstalledPacket" in header.read_text(encoding="utf-8")
    assert "Serializer<" in source.read_text(encoding="utf-8")
    print(json.dumps({
        "launcher": str(launcher), "cwd": str(workspace), "package": str(package),
        "outputs": [str(header), str(source)],
    }, indent=2))


def payloads():
    pure = importlib.metadata.distribution("bedrock-protocol")
    native = importlib.metadata.distribution("bedrock-protocol-native")
    pure_files = {str(path) for path in pure.files if str(path).startswith("bedrock_protocol/")}
    native_files = {str(path) for path in native.files if str(path).startswith("bedrock_protocol/")}
    assert pure_files and native_files
    assert not pure_files.intersection(native_files), pure_files.intersection(native_files)
    assert all(Path(path).name.startswith(("_native.", "v")) for path in native_files), native_files
    assert "bedrock-protocol==0.5.0.dev0" in native.requires, native.requires
    print(f"Disjoint package payloads: pure={len(pure_files)}, native={len(native_files)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("installed").add_argument("schema", type=Path)
    commands.add_parser("payloads")
    command = commands.add_parser("compiler")
    command.add_argument("schema", type=Path)
    command.add_argument("workspace", type=Path)
    args = parser.parse_args()
    if args.command == "installed":
        installed(args.schema)
    elif args.command == "compiler":
        compiler(args.schema.resolve(), args.workspace.resolve())
    elif args.command == "payloads":
        payloads()
