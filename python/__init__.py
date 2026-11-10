"""Bedrock packets and codecs: the bare names are the latest protocol, `v<N>` pins one."""

from importlib import import_module

from ._native import LATEST_PROTOCOL

_latest = import_module(f".v{LATEST_PROTOCOL}", __name__)
globals().update({name: getattr(_latest, name) for name in dir(_latest) if not name.startswith("_")})
del import_module, _latest
