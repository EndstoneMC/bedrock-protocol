import importlib
import pkgutil
import types


def pytest_make_parametrize_id(val):
    if isinstance(val, types.ModuleType):
        return val.__name__.rpartition(".")[2]
    return None


def pytest_generate_tests(metafunc):
    if "protocol" in metafunc.fixturenames:
        import bedrock_protocol

        names = sorted(
            (
                module.name
                for module in pkgutil.iter_modules(bedrock_protocol.__path__)
                if module.name.startswith("v") and module.name[1:].isdigit()
            ),
            key=lambda name: int(name[1:]),
        )
        versions = [importlib.import_module(f"bedrock_protocol.{name}") for name in names]
        metafunc.parametrize("protocol", versions, ids=names)
