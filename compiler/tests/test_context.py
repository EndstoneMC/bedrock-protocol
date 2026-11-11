import os

from bedrock_protocol_compiler.context import GeneratorContext


def write(out, path, text):
    context = GeneratorContext(out)
    context.open(path).emit(text)
    context.commit()


def test_commit_writes_every_opened_file(tmp_path):
    context = GeneratorContext(tmp_path)
    context.open("bedrock/protocol/boss.h").emit("boss")
    context.open("bedrock/protocol/version.hpp").emit("version")
    context.commit()
    assert (tmp_path / "bedrock/protocol/boss.h").read_text() == "boss\n"
    assert (tmp_path / "bedrock/protocol/version.hpp").read_text() == "version\n"


def test_commit_leaves_an_unchanged_file_untouched(tmp_path):
    write(tmp_path, "bedrock/protocol/boss.h", "boss")
    target = tmp_path / "bedrock/protocol/boss.h"
    os.utime(target, ns=(1, 1))
    write(tmp_path, "bedrock/protocol/boss.h", "boss")
    assert target.stat().st_mtime_ns == 1


def test_commit_rewrites_a_changed_file(tmp_path):
    write(tmp_path, "bedrock/protocol/boss.h", "boss")
    write(tmp_path, "bedrock/protocol/boss.h", "boss v2")
    assert (tmp_path / "bedrock/protocol/boss.h").read_text() == "boss v2\n"


def test_commit_deletes_every_other_file_under_bedrock(tmp_path):
    stale = tmp_path / "bedrock/protocol/old.h"
    stale.parent.mkdir(parents=True)
    stale.write_text("old")
    deeper = tmp_path / "bedrock/extra/deep/old.cpp"
    deeper.parent.mkdir(parents=True)
    deeper.write_text("old")
    write(tmp_path, "bedrock/protocol/boss.h", "boss")
    assert not stale.exists()
    assert not deeper.exists()


def test_commit_leaves_files_outside_bedrock_alone(tmp_path):
    other = tmp_path / "other.txt"
    other.write_text("keep")
    write(tmp_path, "bedrock/protocol/boss.h", "boss")
    assert other.read_text() == "keep"


def test_commit_creates_the_out_directory(tmp_path):
    write(tmp_path / "generated", "bedrock/protocol/boss.h", "boss")
    assert (tmp_path / "generated/bedrock/protocol/boss.h").is_file()

