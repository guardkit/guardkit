"""Tests for the hermetic task-level DCL oracle (Phase D, design §1 / D1).

``run_dcl_for_task`` compiles + derives (never runs live assertions). These
tests exercise the real vendored WASM checker, so they require node.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from guardkit.qa.dcl.oracle import (
    STATUS_COMPILE_ERROR,
    STATUS_DERIVATION_ERROR,
    STATUS_PASS,
    run_dcl_for_task,
)

from .conftest import requires_node

TASK_ID = "TASK-STAT-001"


def _make_repo(
    tmp_path: Path,
    capability_dcl: Path,
    binding_file: Path,
    *,
    with_binding: bool = True,
    dcl_src: Path | None = None,
) -> Path:
    """Build a repo with a @task-tagged .dcl under features/ + a binding table."""
    repo = tmp_path / "repo"
    feat_dir = repo / "features" / "stats-endpoint"
    feat_dir.mkdir(parents=True, exist_ok=True)
    body = (dcl_src or capability_dcl).read_text(encoding="utf-8")
    # Prepend the @task marker discovery keys on (the spike source uses "// Task:").
    tagged = f"// @task:{TASK_ID}\n{body}"
    (feat_dir / "stats-endpoint.dcl").write_text(tagged, encoding="utf-8")
    if with_binding:
        bind_dir = repo / "qa" / "dcl"
        bind_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(binding_file, bind_dir / "binding.yaml")
    return repo


def test_no_tagged_dcl_returns_none(tmp_path: Path):
    """Absence discipline: no @task-tagged .dcl → None (not-applicable)."""
    repo = tmp_path / "repo"
    (repo / "features").mkdir(parents=True)
    assert run_dcl_for_task(TASK_ID, repo) is None


def test_no_features_dir_returns_none(tmp_path: Path):
    assert run_dcl_for_task(TASK_ID, tmp_path / "repo") is None


@requires_node
def test_clean_compile_and_derivation_passes(
    tmp_path: Path, capability_dcl: Path, binding_file: Path
):
    repo = _make_repo(tmp_path, capability_dcl, binding_file)
    result = run_dcl_for_task(TASK_ID, repo)
    assert result is not None
    assert result.status == STATUS_PASS
    assert result.compile_ok is True
    assert result.error_count == 0
    assert result.run_ids  # a non-empty derived RUN set
    assert result.feature == "stats-endpoint"
    # Receipt + assertion set were written to the repo (design §2 paths).
    assert (repo / "qa" / "dcl" / "derived" / "stats-endpoint.yaml").is_file()
    assert (repo / "qa" / "dcl" / "derivation-stats-endpoint.yaml").is_file()
    # to_dict carries the pass payload.
    d = result.to_dict()
    assert d["status"] == "pass"
    assert d["run_ids"] == result.run_ids
    assert "errors" not in d


@requires_node
def test_broken_dcl_is_compile_error(
    tmp_path: Path, capability_dcl: Path, binding_file: Path, broken_dcl: Path
):
    repo = _make_repo(
        tmp_path, capability_dcl, binding_file, dcl_src=broken_dcl
    )
    result = run_dcl_for_task(TASK_ID, repo)
    assert result is not None
    assert result.status == STATUS_COMPILE_ERROR
    assert result.compile_ok is False
    assert result.error_count > 0
    assert result.errors  # loud diagnostics, never silent
    d = result.to_dict()
    assert d["status"] == "compile_error"
    assert d["errors"]


@requires_node
def test_missing_binding_is_derivation_error(
    tmp_path: Path, capability_dcl: Path, binding_file: Path
):
    repo = _make_repo(
        tmp_path, capability_dcl, binding_file, with_binding=False
    )
    result = run_dcl_for_task(TASK_ID, repo)
    assert result is not None
    assert result.status == STATUS_DERIVATION_ERROR
    assert result.compile_ok is True
    assert result.derivation_error is not None
