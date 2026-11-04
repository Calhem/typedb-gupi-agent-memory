"""Phase 6D manifests are versioned and never overwritten; the runner refuses any mismatch."""

import json

import pytest

from gupi.benchmarks.e2e import __main__ as runner, manifest


def test_version_1_is_built_exactly_as_before():
    m = manifest.build(1)
    assert "manifest_version" not in m and "supplementary_code" not in m
    assert set(m["code"]) == set(manifest.CODE)


def test_a_new_manifest_matches_until_its_code_changes(tmp_path):
    path = manifest.write(tmp_path / "m.json", 2)
    assert manifest.check(path) == []
    frozen = json.loads(path.read_text())
    assert frozen["manifest_version"] == 2 and frozen["commit"] and set(frozen["supplementary_code"]) == set(manifest.SUPPLEMENTARY)
    frozen["supplementary_code"]["extraction contract (SchemaInfo)"]["sha256"] = "0" * 64
    path.write_text(json.dumps(frozen))
    assert manifest.check(path) == ["supplementary_code"]


def test_a_frozen_manifest_is_never_overwritten(tmp_path):
    path = manifest.write(tmp_path / "m.json", 2)
    with pytest.raises(FileExistsError):
        manifest.write(path, 2)
    assert manifest.main(["--write", "--path", str(path), "--version", "2"]) == 1


def test_the_runner_refuses_a_mismatching_manifest_and_writes_nothing(tmp_path):
    path = manifest.write(tmp_path / "m.json", 2)
    frozen = json.loads(path.read_text())
    frozen["code"]["validation"]["sha256"] = "0" * 64
    path.write_text(json.dumps(frozen))
    label = "test-refused-run"
    assert runner.main(["--label", label, "--parts", "world", "--manifest", str(path)]) == 1
    assert not (runner.OUT / label).exists()
