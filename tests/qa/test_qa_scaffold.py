"""``guardkit init`` qa/ scaffold: installs stubs, never clobbers, stubs validate."""

from __future__ import annotations

from pathlib import Path

import pytest

from guardkit.qa.formats import validate_instance
from guardkit.templates.qa_scaffold import install_qa_scaffold

STUB_KINDS = [
    ("pass-bar", "pass-bar-TASK-0000.yaml"),
    ("known-failures", "known-failures.yaml"),
    ("leak-sweep", "leak-sweep.yaml"),
    ("gate-registry", "gates/registry.yaml"),
]


@pytest.fixture()
def scaffolded(tmp_path: Path) -> Path:
    copied = install_qa_scaffold(tmp_path)
    assert copied, "scaffold copied nothing — common/qa template dir missing?"
    return tmp_path


def test_scaffold_installs_expected_files(scaffolded: Path) -> None:
    assert (scaffolded / "qa" / "README.md").is_file()
    for _, rel in STUB_KINDS:
        assert (scaffolded / "qa" / rel).is_file(), rel


def test_scaffolded_stubs_validate(scaffolded: Path) -> None:
    for kind, rel in STUB_KINDS:
        validate_instance(kind, scaffolded / "qa" / rel)


def test_scaffold_is_idempotent(scaffolded: Path) -> None:
    assert install_qa_scaffold(scaffolded) == []


def test_scaffold_never_clobbers_existing_instance(tmp_path: Path) -> None:
    ledger = tmp_path / "qa" / "known-failures.yaml"
    ledger.parent.mkdir(parents=True)
    ledger.write_text("# the repo's real ledger\n")
    copied = install_qa_scaffold(tmp_path)
    assert "known-failures.yaml" not in copied
    assert ledger.read_text() == "# the repo's real ledger\n"
