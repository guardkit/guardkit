"""Findings are task-shaped records that do NOT block (advisory in v1)."""

from __future__ import annotations

from guardkit.orchestrator.qa_stages import Finding, write_findings


def test_finding_markdown_is_task_shaped_and_marked_non_blocking():
    f = Finding(
        kind="mutation-survivor",
        subject="TASK-XXX-YYYY",
        site="authclient.py:27",
        summary="delete verb auth header unpinned",
        evidence="suite stayed green",
        suggested_pin="assert the header",
    )
    md = f.to_markdown(date="2026-07-09")
    assert "# QA finding (mutation-survivor)" in md
    assert "**Blocking:** no" in md  # advisory, never blocks
    assert "authclient.py:27" in md
    assert "## Suggested pin" in md


def test_write_findings_is_non_blocking_and_returns_paths(tmp_path):
    findings = [
        Finding("boundary-leak", "deploy-envelope", "proxy-nested-error", "raw TypeError escaped"),
        Finding("mutation-survivor", "TASK-XXX-YYYY", "m.py:1", "coverage hole"),
    ]
    paths = write_findings(findings, tmp_path, date="2026-07-09")
    assert len(paths) == 2
    assert all(p.exists() for p in paths)
    assert all(p.parent == tmp_path / "qa" / "findings" for p in paths)
    assert all(p.name.startswith("2026-07-09-") for p in paths)


def test_write_findings_same_slug_overwrites_not_piles(tmp_path):
    f = Finding("boundary-leak", "seam-a", "empty-bytes", "leak")
    write_findings([f], tmp_path, date="2026-07-09")
    write_findings([f], tmp_path, date="2026-07-09")
    files = list((tmp_path / "qa" / "findings").glob("*.md"))
    assert len(files) == 1  # same-day same-slug is idempotent


def test_slug_is_filesystem_safe():
    f = Finding("boundary-leak", "deploy/env:x", "in put/label", "s")
    slug = f.slug()
    assert "/" not in slug and ":" not in slug and " " not in slug
