import importlib
import json
import types
from pathlib import Path

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

    if "cases" in metafunc.fixturenames:
        metafunc.parametrize("cases", list(CASES.values()), ids=[f"{path.parent.name}/{path.stem}" for path in CASES])

    if "cls" in metafunc.fixturenames and "case" in metafunc.fixturenames:
        params = []
        for path, cases in CASES.items():
            packets = importlib.import_module(f"bedrock_protocol.v{path.parent.name}").packets
            params.extend(
                pytest.param(packets[int(path.stem[:3])], case, id=f"{path.parent.name}/{path.stem}/{case['id']}")
                for case in cases
            )
        metafunc.parametrize("cls, case", params)
