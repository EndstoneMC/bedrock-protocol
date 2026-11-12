import importlib
import types


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
