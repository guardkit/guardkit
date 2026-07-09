"""Tests for seam-check config + feature-base anti-tamper (WS3-S3 §1.3)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator.seam_checks import (
    detect_config_tamper,
    feature_base_path,
    load_feature_base_config,
    load_working_tree_config,
    record_feature_base,
    resolve_feature_base,
)

_CONFIG = """version: 1
composition_roots:
  - path: src/pkg/main.py
exclusions:
  - generated/
boot_smoke:
  - id: serve-boots
    kind: serve
    target: "pkg.main:serve"
    readiness:
      kind: http
      url: "http://127.0.0.1:${PORT}/healthz"
      timeout_s: 30
    env_required: [".env"]
  - id: app-constructs
    kind: construct
    target: "pkg.main:create_app"
    expect_type: "pkg.app:App"
"""


def _run(args, cwd):
    subprocess.run(args, cwd=str(cwd), check=True, capture_output=True)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    _run(["git", "init", "-q"], tmp_path)
    _run(["git", "config", "user.email", "t@t"], tmp_path)
    _run(["git", "config", "user.name", "t"], tmp_path)
    (tmp_path / ".guardkit").mkdir()
    (tmp_path / _cfg_rel(tmp_path)).write_text(_CONFIG)
    _run(["git", "add", "-A"], tmp_path)
    _run(["git", "commit", "-qm", "base"], tmp_path)
    _run(["git", "branch", "-M", "main"], tmp_path)
    return tmp_path


def _cfg_rel(root: Path) -> str:
    return ".guardkit/seam-checks.yaml"


# --- config parsing --------------------------------------------------------


def test_parse_config(tmp_path: Path) -> None:
    (tmp_path / ".guardkit").mkdir()
    (tmp_path / _cfg_rel(tmp_path)).write_text(_CONFIG)
    cfg = load_working_tree_config(tmp_path)
    assert cfg.present is True
    assert cfg.composition_roots == ["src/pkg/main.py"]
    assert cfg.exclusions == ["generated/"]
    assert len(cfg.boot_smoke) == 2
    serve, construct = cfg.boot_smoke
    assert serve.kind == "serve" and serve.env_required == [".env"]
    assert serve.is_hermetic is False  # has env_required
    assert construct.kind == "construct" and construct.expect_type == "pkg.app:App"
    assert construct.is_hermetic is True


def test_absent_config(tmp_path: Path) -> None:
    cfg = load_working_tree_config(tmp_path)
    assert cfg.present is False
    assert cfg.has_boot_smoke is False


# --- feature-base pin ------------------------------------------------------


def test_record_and_resolve_feature_base(git_repo: Path) -> None:
    sha = record_feature_base(git_repo, "FEAT-X", git_repo, "main")
    assert sha and len(sha) == 40
    assert feature_base_path(git_repo, "FEAT-X").exists()
    assert resolve_feature_base(git_repo, "FEAT-X") == sha


def test_resolve_falls_back_to_merge_base(git_repo: Path) -> None:
    # No feature_base.json recorded → merge-base HEAD main (== HEAD here).
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(git_repo),
                          capture_output=True, text=True).stdout.strip()
    assert resolve_feature_base(git_repo, "FEAT-X", "main") == head


def test_feature_base_config_reads_committed_copy(git_repo: Path) -> None:
    sha = record_feature_base(git_repo, "FEAT-X", git_repo, "main")
    # Now tamper the working-tree config (Player edit mid-run).
    (git_repo / _cfg_rel(git_repo)).write_text("version: 1\nboot_smoke: []\n")
    base_cfg = load_feature_base_config(git_repo, sha)
    # Baseline copy still governs — 2 boot-smoke entries, not the tampered 0.
    assert len(base_cfg.boot_smoke) == 2


# --- CONFIG_TAMPER ---------------------------------------------------------


def test_config_tamper_working_tree(git_repo: Path) -> None:
    sha = resolve_feature_base(git_repo, "FEAT-X", "main")
    (git_repo / _cfg_rel(git_repo)).write_text("version: 1\nboot_smoke: []\n")
    findings = detect_config_tamper(git_repo, sha)
    assert any(f["locus"] == "working_tree" for f in findings)


def test_config_tamper_committed_wave(git_repo: Path) -> None:
    sha = resolve_feature_base(git_repo, "FEAT-X", "main")
    (git_repo / _cfg_rel(git_repo)).write_text("version: 1\nboot_smoke: []\n")
    _run(["git", "add", "-A"], git_repo)
    _run(["git", "commit", "-qm", "wave-1 tampered config"], git_repo)
    findings = detect_config_tamper(git_repo, sha)
    loci = {f["locus"] for f in findings}
    assert "committed_wave" in loci
    committed = [f for f in findings if f["locus"] == "committed_wave"][0]
    assert committed["commits"]


def test_no_tamper_when_unchanged(git_repo: Path) -> None:
    sha = resolve_feature_base(git_repo, "FEAT-X", "main")
    assert detect_config_tamper(git_repo, sha) == []
