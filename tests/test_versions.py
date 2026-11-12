import pathlib
import re

import pytest

import bedrock_protocol


@pytest.mark.parametrize(("number", "snapshot"), [(2169, 2168), (860, 859)], ids=["2169", "860"])
def test_a_number_that_changes_no_shape_decodes_with_the_snapshot_below_it(number, snapshot):
    assert bedrock_protocol.protocol_version(number).snapshot == snapshot


@pytest.mark.parametrize(
    ("release", "number"),
    [("1.26.42", 2168), ("1.21.124", 860), ("1.26.0", 924)],
    ids=["1.26.42", "1.21.124", "1.26.0"],
)
def test_a_release_finds_the_number_that_reports_it(release, number):
    assert bedrock_protocol.protocol_version(release).number == number


def test_the_newest_entry_reaches_its_last_release():
    newest = bedrock_protocol.releases[-1]
    assert bedrock_protocol.protocol_version(newest.last).number == newest.number


def test_a_number_no_release_reported_has_no_entry():
    assert bedrock_protocol.protocol_version(2170) is None


def test_a_preview_build_has_no_entry():
    assert bedrock_protocol.protocol_version("1.26.60.30") is None


def test_the_table_starts_at_the_oldest_snapshot():
    assert bedrock_protocol.releases[0].number == bedrock_protocol.versions[0]


def test_the_bound_versions_ascend():
    assert list(bedrock_protocol.versions) == sorted(bedrock_protocol.versions)


def test_python_cannot_build_an_entry():
    with pytest.raises(TypeError, match="constructor"):
        bedrock_protocol.ProtocolVersion()


def test_the_readme_lists_every_release():
    readme = pathlib.Path(__file__).parent.parent.joinpath("README.md").read_text()
    section = readme.split("## Supported Protocols")[1].split("\n## ")[0]
    rows = {int(number): text for number, text in re.findall(r"^\| (\d+) \| (.+) \|$", section, re.M)}
    assert rows == {entry.number: entry.name.replace("-", " to ") for entry in bedrock_protocol.releases}
