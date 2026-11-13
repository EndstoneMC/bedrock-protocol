import importlib
import json
import types
from pathlib import Path

import cereal
import pytest

GOLDENS = Path(__file__).parent / "goldens"
CASES = {path: json.loads(path.read_text()) for path in sorted(GOLDENS.glob("*/*.json"))}


def pytest_make_parametrize_id(val):
    if isinstance(val, types.ModuleType):
        return val.__name__.rpartition(".")[2]
    return None


def pytest_generate_tests(metafunc):
    if "protocol" in metafunc.fixturenames:
        import bedrock_protocol

        names = [f"v{version}" for version in bedrock_protocol.versions]
        versions = [importlib.import_module(f"bedrock_protocol.{name}") for name in names]
        metafunc.parametrize("protocol", versions, ids=names)

    if "cls" in metafunc.fixturenames and "loadable" in metafunc.fixturenames:
        params = [
            pytest.param(
                importlib.import_module(f"bedrock_protocol.{path.parent.name}").packets[int(path.stem[:3])],
                case,
                id=f"{path.parent.name}/{path.stem}/{case['id']}",
            )
            for path, cases in CASES.items()
            for case in cases
            if not cereal.loses_arms(
                importlib.import_module(f"bedrock_protocol.{path.parent.name}").packets[int(path.stem[:3])],
                case["value"],
                bytes.fromhex(case["bytes"]),
            )
        ]
        metafunc.parametrize("cls, loadable", params)

    if "cls" in metafunc.fixturenames and "case" in metafunc.fixturenames:
        params = [
            pytest.param(
                importlib.import_module(f"bedrock_protocol.{path.parent.name}").packets[int(path.stem[:3])],
                case,
                id=f"{path.parent.name}/{path.stem}/{case['id']}",
            )
            for path, cases in CASES.items()
            for case in cases
        ]
        metafunc.parametrize("cls, case", params)

    if "case_file" in metafunc.fixturenames:
        metafunc.parametrize("case_file", list(CASES), ids=[f"{path.parent.name}/{path.stem}" for path in CASES])
