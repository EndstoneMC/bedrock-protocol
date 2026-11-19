"""The package version: CMakeLists.txt's project version at its tag, else its PEP 440 dev release."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_root = Path(__file__).resolve().parent.parent
_pkg_info = _root / "PKG-INFO"

if _pkg_info.is_file():
    __version__ = re.findall(r"^Version: (\S+)$", _pkg_info.read_text(encoding="utf-8"), re.MULTILINE)[0]
else:
    _cmake = (_root / "CMakeLists.txt").read_text(encoding="utf-8")
    _release = re.findall(r"project\(bedrock-protocol VERSION (\S+)", _cmake)[0]
    try:
        _tags = subprocess.run(
            ["git", "tag", "--points-at", "HEAD"], cwd=_root, capture_output=True, text=True, check=False
        ).stdout.split()
    except FileNotFoundError:
        _tags = []
    __version__ = _release if f"v{_release}" in _tags else f"{_release}.dev0"


def dynamic_metadata(_settings: Mapping[str, Any], _project: Mapping[str, Any]) -> dict[str, str]:
    return {"version": __version__}
