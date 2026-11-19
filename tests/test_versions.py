import pathlib
import re

import pytest

from bedrock_protocol import ProtocolVersion, _core

README = pathlib.Path(__file__).parent.parent.joinpath("README.md").read_text()
SUPPORTED_PROTOCOLS = README.split("## Supported Protocols")[1].split("\n## ")[0]
ROWS = {int(number): text for number, text in re.findall(r"^\| (\d+) \| (.+) \|$", SUPPORTED_PROTOCOLS, re.M)}


def test_a_number_finds_the_supported_version_itself():
    assert ProtocolVersion.get(2225) is ProtocolVersion.MAXIMUM_VERSION


def test_a_version_is_named_for_its_first_release():
    assert ProtocolVersion.get(2193).name == "1.26.50"


def test_a_number_that_changes_no_shape_is_a_supported_version_of_its_own():
    assert ProtocolVersion.get(2169).name == "1.26.45"


def test_a_number_no_release_reported_has_no_version():
    assert ProtocolVersion.get(2170) is None


def test_the_supported_versions_run_from_the_minimum_to_the_maximum():
    assert ProtocolVersion.SUPPORTED_VERSIONS[0] is ProtocolVersion.MINIMUM_VERSION
    assert ProtocolVersion.SUPPORTED_VERSIONS[-1] is ProtocolVersion.MAXIMUM_VERSION


def test_the_minimum_version_is_the_oldest_modelled_protocol():
    assert ProtocolVersion.MINIMUM_VERSION.protocol == min(_core.modes)


def test_the_supported_versions_ascend():
    numbers = [version.protocol for version in ProtocolVersion.SUPPORTED_VERSIONS]
    assert numbers == sorted(set(numbers))


def test_a_version_shows_its_protocol_and_name():
    assert repr(ProtocolVersion.get(2169)) == "ProtocolVersion(protocol=2169, name='1.26.45')"


def test_python_cannot_build_a_version():
    with pytest.raises(TypeError, match="constructor"):
        ProtocolVersion()


def test_the_readme_lists_every_supported_version():
    assert ROWS.keys() == {version.protocol for version in ProtocolVersion.SUPPORTED_VERSIONS}


@pytest.mark.parametrize(
    "version",
    ProtocolVersion.SUPPORTED_VERSIONS,
    ids=[str(version.protocol) for version in ProtocolVersion.SUPPORTED_VERSIONS],
)
def test_the_readme_row_of_a_version_starts_at_its_name(version):
    assert ROWS[version.protocol].split(" to ")[0].replace("x", "0") == version.name


def test_a_protocol_holds_its_number(protocol):
    assert protocol.__name__ == f"bedrock_protocol.v{protocol.VERSION}"
