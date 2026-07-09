"""Tests for ENVTAMPER-a bootstrap parity + resolution-origin (WS3-S3 §5.1).

The RENV-1 must-fire fixture: a Player vendors a fake ``nats_core/`` package
DIRECTORY (no sys.modules touch) — the cheapest route to the ABL-001 outcome.
A naive importability probe would succeed and suppress the advisory; the
resolution-origin check inverts that to ``vendored_stub_suspected``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("guardkitfactory.wiring.skip_guards")

from guardkit.orchestrator.env_parity import analyze_env_parity  # noqa: E402


def _write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_missing_skip_guarded_module_is_env_parity_gap(tmp_path: Path) -> None:
    _write(tmp_path, "tests/test_x.py",
           "import pytest\n"
           "pytest.importorskip('absent_dep_xyz_999')\n"
           "def test_it():\n    pass\n")
    r = analyze_env_parity(tmp_path, sys.executable)
    assert r.ran
    gaps = [f for f in r.findings if f.kind == "ENV_PARITY_GAP"]
    assert any(f.module == "absent_dep_xyz_999" for f in gaps)


def test_extras_mapping_names_the_extra(tmp_path: Path) -> None:
    # Use a dist that is definitely NOT installed so it registers as a gap.
    _write(tmp_path, "pyproject.toml",
           "[project]\n"
           "name = 'demo'\n"
           "version = '0'\n"
           "[project.optional-dependencies]\n"
           "memory = ['made-up-dist-zzz>=0.4,<1']\n")
    _write(tmp_path, "tests/test_m.py",
           "import pytest\n"
           "pytest.importorskip('made_up_dist_zzz')\n")
    r = analyze_env_parity(tmp_path, sys.executable)
    gap = [f for f in r.findings if f.module == "made_up_dist_zzz"]
    assert gap and gap[0].mapped_extra == "memory"
    assert "memory" in gap[0].detail


def test_vendored_stub_directory_renv1(tmp_path: Path) -> None:
    # The RENV-1 shape: a fake nats_core/ package DIRECTORY in the worktree.
    _write(tmp_path, "nats_core/__init__.py", "MAX = 1\n")
    _write(tmp_path, "tests/test_v.py",
           "import pytest\n"
           "pytest.importorskip('nats_core')\n")
    r = analyze_env_parity(tmp_path, sys.executable)
    vendored = [f for f in r.findings if f.kind == "vendored_stub_suspected"]
    assert any(f.module == "nats_core" for f in vendored), [f.to_dict() for f in r.findings]


def test_find_spec_guard_extracted(tmp_path: Path) -> None:
    _write(tmp_path, "tests/test_fs.py",
           "from importlib.util import find_spec\n"
           "_HAS = find_spec('absent_dep_abc_888') is not None\n")
    r = analyze_env_parity(tmp_path, sys.executable)
    assert any(f.module == "absent_dep_abc_888" for f in r.findings)


def test_no_skip_guards_is_absent(tmp_path: Path) -> None:
    _write(tmp_path, "tests/test_plain.py", "def test_it():\n    pass\n")
    r = analyze_env_parity(tmp_path, sys.executable)
    assert r.ran and r.findings == []


def test_never_hard_fails(tmp_path: Path) -> None:
    # Even a broken worktree must return a result, never raise.
    r = analyze_env_parity(tmp_path, "/nonexistent/python")
    assert isinstance(r.ran, bool)
