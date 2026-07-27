"""Unit tests for the FEAT-SCG (SCG-001) mechanical spec-conformance guard.

Covers the pydantic rule schema (loud on unknown type / typo), the pure
executor for every rule type incl. the absent/crash paths, the ac_paths flag,
and the task-load snapshot round-trip (including the CV4M bypass-resistance
property: a Player editing the live authority cannot change the verdict).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from guardkit.orchestrator.quality_gates.spec_conformance import (
    AssertCommandRule,
    ByteParityRule,
    ConformanceBlock,
    TokenCoverageRule,
    evaluate,
    evaluate_from_snapshot,
    load_snapshot,
    parse_conformance_block,
    snapshot_paths,
    snapshot_task_conformance,
)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class TestSchema:
    def test_absent_defaults(self) -> None:
        block = parse_conformance_block({})
        assert block.ac_paths is False
        assert block.rules == []

    def test_all_three_rule_types_parse(self) -> None:
        block = parse_conformance_block(
            {
                "ac_paths": True,
                "rules": [
                    {
                        "id": "R-1",
                        "type": "byte_parity",
                        "authority": "docs/spec/golden.txt",
                        "subject": "src/foo.py",
                        "subject_region": {"start": "BEGIN", "end": "END"},
                    },
                    {
                        "id": "R-2",
                        "type": "token_coverage",
                        "paths": ["src/coach.py"],
                        "require_tokens": ["config.yaml"],
                        "unique_token": {
                            "token": "RESOLVER",
                            "max_count": 1,
                            "paths": ["src/**/*.py"],
                        },
                        "require_test_tokens": {
                            "paths": ["tests/**/*.py"],
                            "tokens": ["config-only tier"],
                        },
                    },
                    {
                        "id": "R-3",
                        "type": "assert_command",
                        "command": "true",
                        "expected_exit": 0,
                        "timeout": 30,
                    },
                ],
            }
        )
        assert block.ac_paths is True
        assert isinstance(block.rules[0], ByteParityRule)
        assert isinstance(block.rules[1], TokenCoverageRule)
        assert isinstance(block.rules[2], AssertCommandRule)
        assert block.rules[0].subject_region.start == "BEGIN"

    def test_unknown_type_is_loud(self) -> None:
        with pytest.raises(ValueError):
            parse_conformance_block(
                {"rules": [{"id": "R", "type": "not_a_type"}]}
            )

    def test_typo_key_is_loud(self) -> None:
        with pytest.raises(ValueError):
            parse_conformance_block(
                {
                    "rules": [
                        {
                            "id": "R",
                            "type": "byte_parity",
                            "authorit": "x",  # typo
                            "subject": "s.py",
                        }
                    ]
                }
            )

    def test_extra_top_level_key_is_loud(self) -> None:
        with pytest.raises(ValueError):
            parse_conformance_block({"ac_path": True})  # typo of ac_paths

    def test_subject_region_extra_key_is_loud(self) -> None:
        with pytest.raises(ValueError):
            parse_conformance_block(
                {
                    "rules": [
                        {
                            "id": "R",
                            "type": "byte_parity",
                            "authority": "a",
                            "subject": "s.py",
                            "subject_region": {
                                "start": "S",
                                "end": "E",
                                "middle": "?",  # unknown
                            },
                        }
                    ]
                }
            )


# ---------------------------------------------------------------------------
# Executor — absence
# ---------------------------------------------------------------------------


class TestAbsence:
    def test_no_block_is_absent(self, tmp_path: Path) -> None:
        result = evaluate(None, {}, tmp_path)
        assert result["status"] == "absent"
        assert result["failures"] == []

    def test_empty_block_is_absent(self, tmp_path: Path) -> None:
        result = evaluate(ConformanceBlock(), {}, tmp_path)
        assert result["status"] == "absent"

    def test_missing_authority_snapshot_is_absent(self, tmp_path: Path) -> None:
        (tmp_path / "s.py").write_text("hello")
        block = parse_conformance_block(
            {
                "rules": [
                    {
                        "id": "R-1",
                        "type": "byte_parity",
                        "authority": "a.txt",
                        "subject": "s.py",
                    }
                ]
            }
        )
        # authority_bytes intentionally empty -> cannot verify -> absent.
        result = evaluate(block, {}, tmp_path)
        assert result["status"] == "absent"

    def test_executor_crash_degrades_to_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        block = parse_conformance_block(
            {
                "rules": [
                    {"id": "R-3", "type": "assert_command", "command": "true"}
                ]
            }
        )
        import guardkit.orchestrator.quality_gates.spec_conformance as scg

        def _boom(*_a, **_k):
            raise RuntimeError("injected")

        monkeypatch.setattr(scg, "_evaluate_assert_command", _boom)
        result = evaluate(block, {}, tmp_path)
        assert result["status"] == "absent"


# ---------------------------------------------------------------------------
# Executor — byte_parity
# ---------------------------------------------------------------------------


class TestByteParity:
    def _block(self, **extra) -> ConformanceBlock:
        rule = {
            "id": "R-1",
            "type": "byte_parity",
            "authority": "docs/golden.txt",
            "subject": "src/foo.py",
        }
        rule.update(extra)
        return parse_conformance_block({"rules": [rule]})

    def test_whole_file_match_passes(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "foo.py").write_text("exact match\n")
        block = self._block()
        result = evaluate(block, {"R-1": b"exact match\n"}, tmp_path)
        assert result["status"] == "passed"

    def test_whole_file_mismatch_fails_with_diff(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "foo.py").write_text("drifted line\n")
        block = self._block()
        result = evaluate(block, {"R-1": b"authoritative line\n"}, tmp_path)
        assert result["status"] == "failed"
        (failure,) = result["failures"]
        assert failure["rule_id"] == "R-1"
        assert failure["kind"] == "byte_parity"
        assert "authoritative line" in failure["detail"]
        assert "drifted line" in failure["detail"]
        assert "@@" in failure["detail"]  # unified diff hunk header

    def test_missing_subject_fails(self, tmp_path: Path) -> None:
        block = self._block()
        result = evaluate(block, {"R-1": b"x"}, tmp_path)
        assert result["status"] == "failed"
        assert "not found" in result["failures"][0]["detail"]

    def test_crlf_subject_identical_to_crlf_authority_passes(
        self, tmp_path: Path
    ) -> None:
        """Identical CRLF bytes on both sides must PASS.

        Regression pin: ``Path.read_text`` universal-newlines translation on
        the subject side (\\r\\n -> \\n) made identical CRLF files false-FAIL
        against their own untranslated authority bytes.
        """
        crlf = b"line one\r\nline two\r\n"
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "foo.py").write_bytes(crlf)
        block = self._block()
        result = evaluate(block, {"R-1": crlf}, tmp_path)
        assert result["status"] == "passed"

    def test_crlf_subject_fails_against_lf_authority(
        self, tmp_path: Path
    ) -> None:
        """A CRLF-divergent subject must FAIL an LF authority.

        Regression pin: newline translation masked this real byte divergence
        (the subject normalized to LF before comparison and falsely passed).
        """
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "foo.py").write_bytes(b"line one\r\nline two\r\n")
        block = self._block()
        result = evaluate(block, {"R-1": b"line one\nline two\n"}, tmp_path)
        assert result["status"] == "failed"
        assert result["failures"][0]["kind"] == "byte_parity"

    def test_region_extraction_match(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "foo.py").write_text(
            'PREFIX BEGIN keep this END SUFFIX'
        )
        block = self._block(subject_region={"start": "BEGIN", "end": "END"})
        result = evaluate(block, {"R-1": b" keep this "}, tmp_path)
        assert result["status"] == "passed"

    def test_region_extraction_mismatch(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "foo.py").write_text("BEGIN drifted END")
        block = self._block(subject_region={"start": "BEGIN", "end": "END"})
        result = evaluate(block, {"R-1": b" expected "}, tmp_path)
        assert result["status"] == "failed"
        assert "region" in result["failures"][0]["detail"].lower()

    def test_region_markers_absent_fails(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "foo.py").write_text("no markers here")
        block = self._block(subject_region={"start": "BEGIN", "end": "END"})
        result = evaluate(block, {"R-1": b"anything"}, tmp_path)
        assert result["status"] == "failed"
        assert "marker" in result["failures"][0]["detail"].lower()


# ---------------------------------------------------------------------------
# Executor — token_coverage
# ---------------------------------------------------------------------------


class TestTokenCoverage:
    def test_require_tokens_present_passes(self, tmp_path: Path) -> None:
        (tmp_path / "coach.py").write_text("reads config.yaml for the coach")
        block = parse_conformance_block(
            {
                "rules": [
                    {
                        "id": "R-2",
                        "type": "token_coverage",
                        "paths": ["coach.py"],
                        "require_tokens": ["config.yaml", "coach"],
                    }
                ]
            }
        )
        assert evaluate(block, {}, tmp_path)["status"] == "passed"

    def test_require_tokens_missing_fails(self, tmp_path: Path) -> None:
        (tmp_path / "coach.py").write_text("only env resolver here")
        block = parse_conformance_block(
            {
                "rules": [
                    {
                        "id": "R-2",
                        "type": "token_coverage",
                        "paths": ["coach.py"],
                        "require_tokens": ["config.yaml"],
                    }
                ]
            }
        )
        result = evaluate(block, {}, tmp_path)
        assert result["status"] == "failed"
        assert "config.yaml" in result["failures"][0]["detail"]

    def test_no_matching_files_reports_missing(self, tmp_path: Path) -> None:
        # The CMIR omission class: the tier never built, no file to search.
        block = parse_conformance_block(
            {
                "rules": [
                    {
                        "id": "R-2",
                        "type": "token_coverage",
                        "paths": ["does_not_exist.py"],
                        "require_tokens": ["config.yaml"],
                    }
                ]
            }
        )
        result = evaluate(block, {}, tmp_path)
        assert result["status"] == "failed"
        assert "No files matched" in result["failures"][0]["detail"]

    def test_unique_token_over_cap_fails(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("RESOLVER = 1")
        (tmp_path / "b.py").write_text("RESOLVER = 2")
        block = parse_conformance_block(
            {
                "rules": [
                    {
                        "id": "R-2",
                        "type": "token_coverage",
                        "paths": ["*.py"],
                        "unique_token": {
                            "token": "RESOLVER",
                            "max_count": 1,
                            "paths": ["*.py"],
                        },
                    }
                ]
            }
        )
        result = evaluate(block, {}, tmp_path)
        assert result["status"] == "failed"
        assert "2 time" in result["failures"][0]["detail"]

    def test_unique_token_within_cap_passes(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("RESOLVER = 1")
        block = parse_conformance_block(
            {
                "rules": [
                    {
                        "id": "R-2",
                        "type": "token_coverage",
                        "paths": ["*.py"],
                        "unique_token": {
                            "token": "RESOLVER",
                            "max_count": 1,
                            "paths": ["*.py"],
                        },
                    }
                ]
            }
        )
        assert evaluate(block, {}, tmp_path)["status"] == "passed"

    def test_require_test_tokens_missing_fails(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "t.py").write_text("def test_something(): pass")
        block = parse_conformance_block(
            {
                "rules": [
                    {
                        "id": "R-2",
                        "type": "token_coverage",
                        "paths": ["tests/**/*.py"],
                        "require_test_tokens": {
                            "paths": ["tests/**/*.py"],
                            "tokens": ["config-only tier"],
                        },
                    }
                ]
            }
        )
        result = evaluate(block, {}, tmp_path)
        assert result["status"] == "failed"
        assert "config-only tier" in result["failures"][0]["detail"]

    def test_require_test_tokens_present_passes(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "t.py").write_text("# config-only tier test")
        block = parse_conformance_block(
            {
                "rules": [
                    {
                        "id": "R-2",
                        "type": "token_coverage",
                        "paths": ["tests/**/*.py"],
                        "require_test_tokens": {
                            "paths": ["tests/**/*.py"],
                            "tokens": ["config-only tier"],
                        },
                    }
                ]
            }
        )
        assert evaluate(block, {}, tmp_path)["status"] == "passed"


# ---------------------------------------------------------------------------
# Executor — assert_command
# ---------------------------------------------------------------------------


class TestAssertCommand:
    def test_exit_zero_passes(self, tmp_path: Path) -> None:
        block = parse_conformance_block(
            {"rules": [{"id": "R-3", "type": "assert_command", "command": "exit 0"}]}
        )
        assert evaluate(block, {}, tmp_path)["status"] == "passed"

    def test_nonzero_exit_fails_with_tail(self, tmp_path: Path) -> None:
        block = parse_conformance_block(
            {
                "rules": [
                    {
                        "id": "R-3",
                        "type": "assert_command",
                        "command": "echo boom-detail; exit 3",
                    }
                ]
            }
        )
        result = evaluate(block, {}, tmp_path)
        assert result["status"] == "failed"
        detail = result["failures"][0]["detail"]
        assert "exited 3" in detail
        assert "boom-detail" in detail

    def test_expected_nonzero_exit_passes(self, tmp_path: Path) -> None:
        block = parse_conformance_block(
            {
                "rules": [
                    {
                        "id": "R-3",
                        "type": "assert_command",
                        "command": "exit 7",
                        "expected_exit": 7,
                    }
                ]
            }
        )
        assert evaluate(block, {}, tmp_path)["status"] == "passed"

    def test_timeout_fails(self, tmp_path: Path) -> None:
        block = parse_conformance_block(
            {
                "rules": [
                    {
                        "id": "R-3",
                        "type": "assert_command",
                        "command": f"{sys.executable} -c 'import time; time.sleep(5)'",
                        "timeout": 1,
                    }
                ]
            }
        )
        result = evaluate(block, {}, tmp_path)
        assert result["status"] == "failed"
        assert "timed out" in result["failures"][0]["detail"]

    def test_command_runs_in_subject_root(self, tmp_path: Path) -> None:
        (tmp_path / "marker.flag").write_text("x")
        block = parse_conformance_block(
            {
                "rules": [
                    {
                        "id": "R-3",
                        "type": "assert_command",
                        "command": "test -f marker.flag",
                    }
                ]
            }
        )
        assert evaluate(block, {}, tmp_path)["status"] == "passed"


# ---------------------------------------------------------------------------
# Executor — ac_paths
# ---------------------------------------------------------------------------


class TestAcPaths:
    def _block(self) -> ConformanceBlock:
        return parse_conformance_block({"ac_paths": True})

    def test_missing_cited_path_fails(self, tmp_path: Path) -> None:
        acs = [{"id": "AC-1", "text": "adds `src/pkg/new_module.py`"}]
        result = evaluate(
            self._block(), {}, tmp_path, acceptance_criteria=acs
        )
        assert result["status"] == "failed"
        f = result["failures"][0]
        assert f["kind"] == "ac_paths"
        assert "src/pkg/new_module.py" in f["detail"]

    def test_present_cited_path_passes(self, tmp_path: Path) -> None:
        (tmp_path / "src" / "pkg").mkdir(parents=True)
        (tmp_path / "src" / "pkg" / "new_module.py").write_text("x")
        acs = [{"id": "AC-1", "text": "adds src/pkg/new_module.py"}]
        result = evaluate(
            self._block(), {}, tmp_path, acceptance_criteria=acs
        )
        assert result["status"] == "passed"

    def test_bare_basename_is_not_flagged(self, tmp_path: Path) -> None:
        # A basename without a directory is skipped (false-positive guard).
        acs = [{"id": "AC-1", "text": "modify consumer.py in the usual place"}]
        result = evaluate(
            self._block(), {}, tmp_path, acceptance_criteria=acs
        )
        assert result["status"] == "passed"

    def test_no_acs_passes(self, tmp_path: Path) -> None:
        result = evaluate(self._block(), {}, tmp_path, acceptance_criteria=None)
        assert result["status"] == "passed"

    def test_glob_token_is_ignored(self, tmp_path: Path) -> None:
        acs = [{"id": "AC-1", "text": "touches src/**/*.py broadly"}]
        result = evaluate(
            self._block(), {}, tmp_path, acceptance_criteria=acs
        )
        assert result["status"] == "passed"


# ---------------------------------------------------------------------------
# Snapshot round-trip (item 3 + CV4M bypass-resistance)
# ---------------------------------------------------------------------------


def _write_task_file(
    repo_root: Path, task_id: str, frontmatter_yaml: str
) -> Path:
    task_dir = repo_root / "tasks" / "backlog"
    task_dir.mkdir(parents=True, exist_ok=True)
    task_file = task_dir / f"{task_id}.md"
    task_file.write_text(
        f"---\n{frontmatter_yaml}---\n\n# {task_id}\n\nBody.\n"
    )
    return task_file


class TestSnapshotRoundTrip:
    def _worktree_shaped(self, repo_root: Path, task_id: str) -> Path:
        """A realistic worktree root under <repo>/.guardkit/worktrees/<id>."""
        wt = repo_root / ".guardkit" / "worktrees" / task_id
        wt.mkdir(parents=True, exist_ok=True)
        return wt

    def test_no_conformance_block_writes_nothing(self, tmp_path: Path) -> None:
        task_id = "TASK-SCG-NB"
        _write_task_file(tmp_path, task_id, "task_type: FEATURE\n")
        wt = self._worktree_shaped(tmp_path, task_id)
        out = snapshot_task_conformance(task_id, wt, tmp_path)
        assert out is None
        assert not snapshot_paths(task_id, wt)["dir"].exists()

    def test_snapshot_captures_block_and_authority(
        self, tmp_path: Path
    ) -> None:
        task_id = "TASK-SCG-01"
        # Authority lives in the repo, captured pre-build.
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "golden.txt").write_text("AUTHORITATIVE\n")
        _write_task_file(
            tmp_path,
            task_id,
            "task_type: FEATURE\n"
            "conformance:\n"
            "  rules:\n"
            "    - id: R-1\n"
            "      type: byte_parity\n"
            "      authority: docs/golden.txt\n"
            "      subject: src/foo.py\n",
        )
        wt = self._worktree_shaped(tmp_path, task_id)
        # Subject in the worktree matches the authority initially.
        (wt / "src").mkdir(parents=True)
        (wt / "src" / "foo.py").write_text("AUTHORITATIVE\n")

        snap = snapshot_task_conformance(task_id, wt, tmp_path)
        assert snap is not None
        # The snapshot must live OUTSIDE the worktree (SBHO containment).
        assert ".guardkit/worktrees" not in str(snap)

        loaded = load_snapshot(snap)
        assert loaded is not None
        block, authority_bytes = loaded
        assert authority_bytes["R-1"] == b"AUTHORITATIVE\n"

        # Green while the subject matches.
        assert evaluate_from_snapshot(snap, wt)["status"] == "passed"

    def test_player_editing_live_authority_cannot_flip_verdict(
        self, tmp_path: Path
    ) -> None:
        """CV4M bypass-resistance: editing BOTH sides in the worktree still fails."""
        task_id = "TASK-SCG-02"
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "golden.txt").write_text("AUTHORITATIVE\n")
        _write_task_file(
            tmp_path,
            task_id,
            "conformance:\n"
            "  rules:\n"
            "    - id: R-1\n"
            "      type: byte_parity\n"
            "      authority: docs/golden.txt\n"
            "      subject: src/foo.py\n",
        )
        wt = self._worktree_shaped(tmp_path, task_id)
        (wt / "src").mkdir(parents=True)
        (wt / "src" / "foo.py").write_text("AUTHORITATIVE\n")
        # Also give the worktree a live copy of the authority the Player can reach.
        (wt / "docs").mkdir()
        (wt / "docs" / "golden.txt").write_text("AUTHORITATIVE\n")

        snap = snapshot_task_conformance(task_id, wt, tmp_path)
        assert snap is not None

        # The Player drifts the subject AND edits the live authority to match.
        (wt / "src" / "foo.py").write_text("DRIFTED\n")
        (wt / "docs" / "golden.txt").write_text("DRIFTED\n")

        # The executor reads the SNAPSHOT authority, so it still fails.
        result = evaluate_from_snapshot(snap, wt)
        assert result["status"] == "failed"
        assert "AUTHORITATIVE" in result["failures"][0]["detail"]

    def test_malformed_block_degrades_to_none(self, tmp_path: Path) -> None:
        task_id = "TASK-SCG-BAD"
        _write_task_file(
            tmp_path,
            task_id,
            "conformance:\n"
            "  rules:\n"
            "    - id: R-1\n"
            "      type: not_a_real_type\n",
        )
        wt = self._worktree_shaped(tmp_path, task_id)
        out = snapshot_task_conformance(task_id, wt, tmp_path)
        assert out is None

    def test_missing_authority_file_still_snapshots_block(
        self, tmp_path: Path
    ) -> None:
        task_id = "TASK-SCG-NOAUTH"
        _write_task_file(
            tmp_path,
            task_id,
            "conformance:\n"
            "  rules:\n"
            "    - id: R-1\n"
            "      type: byte_parity\n"
            "      authority: docs/missing.txt\n"
            "      subject: src/foo.py\n",
        )
        wt = self._worktree_shaped(tmp_path, task_id)
        snap = snapshot_task_conformance(task_id, wt, tmp_path)
        assert snap is not None
        # Block captured, but authority bytes absent -> executor degrades absent.
        result = evaluate_from_snapshot(snap, wt)
        assert result["status"] == "absent"

    def test_evaluate_from_snapshot_absent_when_no_snapshot(
        self, tmp_path: Path
    ) -> None:
        result = evaluate_from_snapshot(tmp_path / "nope", tmp_path)
        assert result["status"] == "absent"
