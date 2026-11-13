import importlib
import json
import types
from pathlib import Path

import pytest

GOLDENS = Path(__file__).parent / "goldens"
CASES = {path: json.loads(path.read_text()) for path in sorted(GOLDENS.glob("*/*.json"))}


LOST_ARM = "BDS keeps the first variant arm that loads cleanly (doLoadPlainVariant 0x8162900)"
LOST_ARMS = {
    "v2168/030_inventory_transaction/inventory_mismatch_with_legacy_slots",
    "v2168/065_legacy_telemetry_event/composter_used_event",
    "v2168/097_book_edit/add_page_arm",
    "v2168/328_primitive_shapes/sphere_text_cylinder_pyramid_payloads",
    "v2168/328_primitive_shapes/arrow_box_line_ellipsoid_cone_payloads_with_absent_fields",
    "v2168/348_clientbound_update_sound_data/resume_in_every_slot",
    "v2168/348_clientbound_update_sound_data/pause_in_every_slot",
}


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

    if "cls" in metafunc.fixturenames and ("case" in metafunc.fixturenames or "round_trip" in metafunc.fixturenames):
        rows = [
            (
                importlib.import_module(f"bedrock_protocol.{path.parent.name}").packets[int(path.stem[:3])],
                case,
                f"{path.parent.name}/{path.stem}/{case['id']}",
            )
            for path, cases in CASES.items()
            for case in cases
        ]
        if "round_trip" in metafunc.fixturenames:
            params = [
                pytest.param(
                    cls,
                    case,
                    id=name,
                    marks=pytest.mark.xfail(strict=True, reason=LOST_ARM) if name in LOST_ARMS else [],
                )
                for cls, case, name in rows
            ]
            metafunc.parametrize("cls, round_trip", params)
        else:
            metafunc.parametrize("cls, case", [pytest.param(cls, case, id=name) for cls, case, name in rows])

    if "case_file" in metafunc.fixturenames:
        metafunc.parametrize("case_file", list(CASES), ids=[f"{path.parent.name}/{path.stem}" for path in CASES])
