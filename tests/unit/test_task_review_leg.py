"""Tests for the headless review leg (``guardkit task-review``).

The model call is faked at the ``run_specialist`` seam — the real-seat run is
the coordinator's replay, not this suite's job. Everything else runs for real:
the task loader, the context resolver, the artefact admission filter, the
consistency check, the marker renderer and the receipt writer.

Covers, per the design pass ``leg-invocation-design-pass-2026-08-02.md``:

* CLI registration, the union flag set, unknown-flag exit 2;
* the Phase-0 id-form refusal (no task file → exit 2);
* the M0 fence, both ways, including the ``openai:``-by-route refinement;
* marker-block emission cross-checked against **copies of forge's own scrape
  regexes** (``forge/src/forge/adapters/guardkit/parser.py:36-61``);
* the stem-collision guard (§e.4) — a ``TASK-…-review-report`` stem matches the
  fix-task regex and must never reach ``## Artefacts``;
* the internal consistency check, both ways (§c.1);
* the receipt shape including the phases-not-run list;
* ``--nats`` on stderr, never stdout;
* ``--context`` both payload kinds, and an unreadable value never failing;
* the internal budget expiring → written partial + exit 2.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from guardkit.cli.main import cli
from guardkit.cli.task_review import FRONTIER_ESCAPE_ENV, resolve_m0_violation, task_review
from guardkit.orchestrator import review_runner


# ===========================================================================
# Copies of forge's scrape regexes — the cross-check
# ===========================================================================
# Verbatim from forge/src/forge/adapters/guardkit/parser.py:36-61. If the leg's
# emission and these ever diverge, this suite fails rather than the pipeline
# silently reading an empty result.

FORGE_ARTEFACTS_SECTION_RE = re.compile(
    r"^##\s+Artefacts\s*$([\s\S]*?)(?=^##\s+|\Z)", re.MULTILINE
)
FORGE_ARTEFACT_LINE_RE = re.compile(r"^\s*-\s+(\S.*?)\s*$", re.MULTILINE)
FORGE_COACH_SCORE_RE = re.compile(
    r"^\s*coach_score\s*:\s*([+-]?\d+(?:\.\d+)?)\s*$", re.MULTILINE
)
FORGE_DETECTION_FINDINGS_SECTION_RE = re.compile(
    r"^##\s+Detection\s+Findings\s*$([\s\S]*?)(?=^##\s+|\Z)", re.MULTILINE
)
FORGE_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.MULTILINE)

# forge/src/forge/cli/_serve_deps_stage_log.py:398
FORGE_FIX_TASK_ID_RE = re.compile(r"^TASK-[A-Z0-9]{3,12}(?:-[A-Za-z0-9]+)*$")


def forge_extract_artefacts(stdout: str) -> list[str]:
    section = FORGE_ARTEFACTS_SECTION_RE.search(stdout)
    if section is None:
        return []
    return [m.group(1) for m in FORGE_ARTEFACT_LINE_RE.finditer(section.group(1))]


def forge_extract_findings(stdout: str):
    section = FORGE_DETECTION_FINDINGS_SECTION_RE.search(stdout)
    if section is None:
        return None
    fence = FORGE_JSON_FENCE_RE.search(section.group(1))
    if fence is None:
        return None
    parsed = json.loads(fence.group(1).strip())
    return [i for i in parsed if isinstance(i, dict)] if isinstance(parsed, list) else None


def forge_extract_fix_tasks(artefact_paths) -> tuple[str, ...]:
    seen: list[str] = []
    for raw in artefact_paths:
        stem = Path(str(raw)).stem
        if FORGE_FIX_TASK_ID_RE.match(stem) and stem not in seen:
            seen.append(stem)
    return tuple(seen)


# ===========================================================================
# Fixtures / fakes
# ===========================================================================

TASK_ID = "TASK-REV-A1B2C3"

SAMPLE_FINDING = {
    "id": "F1",
    "severity": "high",
    "title": "Unguarded attribute access",
    "file": "src/parser.py",
    "line": 88,
    "detail": "match.group(1) dereferenced without a None check.",
}


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Keep the fleet-memory CLI tier off: these tests are network-free."""
    monkeypatch.setenv("GUARDKIT_REVIEW_MEMORY_CLI", "0")
    monkeypatch.delenv(FRONTIER_ESCAPE_ENV, raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A minimal repo with the review task on disk; cwd is set to it."""
    task_dir = tmp_path / "tasks" / "in_progress"
    task_dir.mkdir(parents=True)
    (task_dir / f"{TASK_ID}.md").write_text(
        "---\n"
        f"id: {TASK_ID}\n"
        "title: Review the header parser\n"
        "status: in_progress\n"
        "task_type: review\n"
        "---\n\n"
        "# Review the header parser\n\n"
        "## Requirements\n\nAssess src/parser.py.\n\n"
        "## Acceptance Criteria\n\n- [ ] Header path assessed\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


class _FakeSpecialistResult:
    def __init__(self, status="passed", error=None):
        self.specialist_name = "code-reviewer"
        self.phase = "5"
        self.status = status
        self.duration_seconds = 1.0
        self.result_file = None
        self.error = error


def install_fake_specialist(
    monkeypatch,
    repo_root: Path,
    *,
    report_body: str | None = None,
    findings_payload=None,
    status: str = "passed",
    error: str | None = None,
    recorder: dict | None = None,
):
    """Fake the model call **at the ``run_specialist`` seam**."""

    async def _fake_run_specialist(
        specialist_name,
        worktree_path,
        task_id,
        sdk_timeout,
        prompt,
        allowed_tools,
        agent_invoker,
        **kwargs,
    ):
        if recorder is not None:
            recorder.update(
                {
                    "specialist_name": specialist_name,
                    "worktree_path": Path(worktree_path),
                    "task_id": task_id,
                    "sdk_timeout": sdk_timeout,
                    "prompt": prompt,
                    "allowed_tools": list(allowed_tools),
                    "agent_invoker": agent_invoker,
                }
            )
        if report_body is not None:
            report = repo_root / ".claude" / "reviews" / f"{task_id}-review-report.md"
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(report_body, encoding="utf-8")
        if findings_payload is not None:
            findings = (
                repo_root / ".guardkit" / "autobuild" / task_id / "review_findings.json"
            )
            findings.parent.mkdir(parents=True, exist_ok=True)
            findings.write_text(json.dumps(findings_payload), encoding="utf-8")
        return _FakeSpecialistResult(status=status, error=error)

    monkeypatch.setattr(review_runner, "run_specialist", _fake_run_specialist)
    monkeypatch.setattr(
        review_runner, "_build_agent_invoker", lambda **kwargs: object()
    )


def install_fake_producer(monkeypatch, repo_root: Path, filenames):
    """Fake the fix-task producer; writes real files where the real one does."""

    def _producer(review_task, review_report_path):
        target = repo_root / "tasks" / "backlog" / "header-parser"
        target.mkdir(parents=True, exist_ok=True)
        for name in filenames:
            (target / name).write_text(
                f"---\nid: {Path(name).stem}\nparent_review: {review_task['id']}\n---\n",
                encoding="utf-8",
            )

    monkeypatch.setattr(review_runner, "_import_producer", lambda: _producer)


def clean_report(task_id: str = TASK_ID) -> str:
    return (
        f"# Review Report — {task_id}\n\n"
        "## Summary\n\nRead src/parser.py end to end.\n\n"
        "## Context Used\n\n- clarification: defaults applied (unattended)\n\n"
        f"## Findings\n\n{review_runner.CLEAN_REVIEW_LINE}\n\n"
        "## Recommendations\n\nNone — the review is clean.\n"
    )


def findings_report(task_id: str = TASK_ID) -> str:
    return (
        f"# Review Report — {task_id}\n\n"
        "## Summary\n\nOne defect found.\n\n"
        "## Context Used\n\n- clarification: defaults applied (unattended)\n\n"
        "## Findings\n\n### F1 — Unguarded attribute access\n\nsrc/parser.py:88\n\n"
        "## Recommendations\n\n"
        "1. Add a null guard to parse_header() in src/parser.py.\n"
    )


@pytest.fixture
def runner():
    return CliRunner()


# ===========================================================================
# 1. CLI registration + flag union + unknown flag
# ===========================================================================


class TestCliSurface:
    def test_task_review_is_registered(self):
        """The pipeline spawns the literal verb `task-review`."""
        assert "task-review" in cli.commands

    @pytest.mark.parametrize(
        "flag",
        [
            "--task-id",
            "--build-id",
            "--correlation-id",
            "--feature-yaml",
            "--context",
            "--nats",
            "--mode",
            "--depth",
            "--model",
            "--sdk-timeout",
        ],
    )
    def test_union_flag_set_is_accepted(self, runner, flag):
        result = runner.invoke(task_review, ["--help"])
        assert result.exit_code == 0
        assert flag in result.stdout

    def test_task_id_is_required(self, runner):
        result = runner.invoke(task_review, [])
        assert result.exit_code == 2

    def test_unknown_flag_exits_2(self, runner):
        result = runner.invoke(task_review, ["--task-id", TASK_ID, "--not-a-flag"])
        assert result.exit_code == 2

    def test_sdk_timeout_defaults_under_the_dispatch_cap(self):
        """480s internal budget sits under the dispatcher's 600s SIGKILL."""
        assert review_runner.DEFAULT_SDK_TIMEOUT_SECONDS == 480
        assert review_runner.DEFAULT_SDK_TIMEOUT_SECONDS < 600


# ===========================================================================
# 2. Phase-0 REFUSED — id-form only
# ===========================================================================


class TestIdFormRefusal:
    def test_missing_task_file_exits_2(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(task_review, ["--task-id", "TASK-NOPE-001"])
        assert result.exit_code == 2
        assert "REFUSED" in result.stderr
        assert "TASK-NOPE-001" in result.stderr

    def test_missing_task_file_never_prints_markers(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(task_review, ["--task-id", "TASK-NOPE-001"])
        assert "## Artefacts" not in result.stdout


# ===========================================================================
# 3. The M0 fence, both ways
# ===========================================================================


class TestM0Fence:
    @pytest.mark.parametrize(
        "model",
        [
            "anthropic:claude-opus-4",
            "anthropic/claude-sonnet-4-5",
            "google_genai:gemini-2.5-pro",
            "bedrock:anthropic.claude-v2",
            "xai:grok-4",
            "mistralai:mistral-large",
        ],
    )
    def test_frontier_prefix_is_a_violation(self, model):
        violation = resolve_m0_violation(model)
        assert violation is not None
        assert model in violation

    @pytest.mark.parametrize(
        "model", [None, "", "qwen36-workhorse", "gemma4-coach", "claude-sonnet-4-5"]
    )
    def test_local_seat_is_not_a_violation(self, model):
        assert resolve_m0_violation(model) is None

    def test_openai_prefix_without_base_url_is_a_violation(self, monkeypatch):
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        assert resolve_m0_violation("openai:gpt-5") is not None

    def test_openai_prefix_against_the_vendor_host_is_a_violation(self, monkeypatch):
        monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        assert resolve_m0_violation("openai:gpt-5") is not None

    def test_openai_prefix_against_a_fleet_seat_is_allowed(self, monkeypatch):
        """The fleet's own route IS openai:<alias> against a local base URL."""
        monkeypatch.setenv("OPENAI_BASE_URL", "http://gb10.local:8000/v1")
        assert resolve_m0_violation("openai:qwen36-workhorse") is None

    def test_cli_refuses_a_frontier_model_with_exit_2(self, runner, repo, monkeypatch):
        install_fake_specialist(
            monkeypatch, repo, report_body=clean_report(), findings_payload={"findings": []}
        )
        result = runner.invoke(
            task_review, ["--task-id", TASK_ID, "--model", "anthropic:claude-opus-4"]
        )
        assert result.exit_code == 2
        assert "M0 fence" in result.stderr
        assert "anthropic:claude-opus-4" in result.stderr
        assert "## Artefacts" not in result.stdout

    def test_escape_hatch_lets_a_frontier_model_through(
        self, runner, repo, monkeypatch
    ):
        monkeypatch.setenv(FRONTIER_ESCAPE_ENV, "1")
        install_fake_specialist(
            monkeypatch, repo, report_body=clean_report(), findings_payload={"findings": []}
        )
        result = runner.invoke(
            task_review, ["--task-id", TASK_ID, "--model", "anthropic:claude-opus-4"]
        )
        assert result.exit_code == 0
        assert "Proceeding because" in result.stderr
        assert "## Artefacts" in result.stdout


# ===========================================================================
# 4. Marker emission, cross-checked against forge's parser
# ===========================================================================


class TestMarkerEmission:
    def test_clean_review_emits_an_empty_artefact_section(
        self, runner, repo, monkeypatch
    ):
        install_fake_specialist(
            monkeypatch,
            repo,
            report_body=clean_report(),
            findings_payload={"clean": True, "findings": []},
        )
        result = runner.invoke(task_review, ["--task-id", TASK_ID])
        assert result.exit_code == 0
        assert forge_extract_artefacts(result.stdout) == []
        assert forge_extract_findings(result.stdout) == []

    def test_findings_review_emits_fix_task_paths_forge_can_read(
        self, runner, repo, monkeypatch
    ):
        install_fake_producer(
            monkeypatch, repo, ["TASK-HPR-001-add-null-guard.md"]
        )
        install_fake_specialist(
            monkeypatch,
            repo,
            report_body=findings_report(),
            findings_payload={"clean": False, "findings": [SAMPLE_FINDING]},
        )
        result = runner.invoke(task_review, ["--task-id", TASK_ID])
        assert result.exit_code == 0, result.stderr

        artefacts = forge_extract_artefacts(result.stdout)
        assert len(artefacts) == 1
        assert artefacts[0].endswith("TASK-HPR-001-add-null-guard.md")
        assert Path(artefacts[0]).is_file()

        # And the pipeline's own fix-task extractor recovers a typed id.
        assert forge_extract_fix_tasks(artefacts) == ("TASK-HPR-001-add-null-guard",)

        findings = forge_extract_findings(result.stdout)
        assert findings == [SAMPLE_FINDING]

    def test_coach_score_line_is_emitted_only_when_supplied(
        self, runner, repo, monkeypatch
    ):
        install_fake_specialist(
            monkeypatch,
            repo,
            report_body=clean_report(),
            findings_payload={"clean": True, "findings": [], "coach_score": 0.91},
        )
        result = runner.invoke(task_review, ["--task-id", TASK_ID])
        assert result.exit_code == 0
        match = FORGE_COACH_SCORE_RE.search(result.stdout)
        assert match is not None
        assert float(match.group(1)) == 0.91

    def test_coach_score_omitted_when_absent(self, runner, repo, monkeypatch):
        install_fake_specialist(
            monkeypatch,
            repo,
            report_body=clean_report(),
            findings_payload={"clean": True, "findings": []},
        )
        result = runner.invoke(task_review, ["--task-id", TASK_ID])
        assert FORGE_COACH_SCORE_RE.search(result.stdout) is None

    def test_coach_score_is_not_mistaken_for_an_artefact_line(self):
        """The score sits outside the artefact section, by construction."""
        block = review_runner.render_marker_block(
            fix_task_paths=["/tmp/TASK-ABC-001.md"], findings=[], coach_score=0.5
        )
        assert forge_extract_artefacts(block) == ["/tmp/TASK-ABC-001.md"]

    def test_no_coach_breakdown_is_fabricated(self, runner, repo, monkeypatch):
        """The review leg has no coach; inventing a table would be a fake gate."""
        install_fake_specialist(
            monkeypatch,
            repo,
            report_body=clean_report(),
            findings_payload={"clean": True, "findings": []},
        )
        result = runner.invoke(task_review, ["--task-id", TASK_ID])
        assert "## Coach Breakdown" not in result.stdout


# ===========================================================================
# 5. §e.4 — the stem-collision guard
# ===========================================================================


class TestStemCollisionGuard:
    def test_the_report_stem_really_does_match_forges_fix_task_regex(self):
        """The hazard is real: this is why the guard exists."""
        assert FORGE_FIX_TASK_ID_RE.match(f"{TASK_ID}-review-report")
        assert review_runner.FIX_TASK_STEM_RE.match(f"{TASK_ID}-review-report")

    def test_report_is_never_admitted_as_an_artefact(self, tmp_path):
        report = tmp_path / ".claude" / "reviews" / f"{TASK_ID}-review-report.md"
        report.parent.mkdir(parents=True)
        report.write_text("x", encoding="utf-8")
        fix_task = tmp_path / "TASK-HPR-001-fix.md"
        fix_task.write_text("x", encoding="utf-8")

        admitted, rejected = review_runner.admit_fix_task_paths(
            [report, fix_task],
            written_this_run=[report, fix_task],
            report_path=report,
        )
        assert admitted == [str(fix_task.resolve())]
        assert any("review report" in r["reason"] for r in rejected)

    def test_report_never_reaches_stdout_artefacts_end_to_end(
        self, runner, repo, monkeypatch
    ):
        install_fake_producer(monkeypatch, repo, ["TASK-HPR-001-fix.md"])
        install_fake_specialist(
            monkeypatch,
            repo,
            report_body=findings_report(),
            findings_payload={"findings": [SAMPLE_FINDING]},
        )
        result = runner.invoke(task_review, ["--task-id", TASK_ID])
        assert result.exit_code == 0
        artefacts = forge_extract_artefacts(result.stdout)
        assert all("review-report" not in a for a in artefacts)
        assert forge_extract_fix_tasks(artefacts) == ("TASK-HPR-001-fix",)


class TestArtefactDiscipline:
    def test_path_not_written_this_run_is_rejected(self, tmp_path):
        stranger = tmp_path / "TASK-XYZ-001-stranger.md"
        stranger.write_text("x", encoding="utf-8")
        admitted, rejected = review_runner.admit_fix_task_paths(
            [stranger], written_this_run=[], report_path=tmp_path / "report.md"
        )
        assert admitted == []
        assert rejected[0]["reason"] == "not written by this leg in this run"

    def test_path_that_does_not_exist_is_rejected(self, tmp_path):
        ghost = tmp_path / "TASK-XYZ-001-ghost.md"
        admitted, rejected = review_runner.admit_fix_task_paths(
            [ghost], written_this_run=[ghost], report_path=tmp_path / "report.md"
        )
        assert admitted == []
        assert rejected[0]["reason"] == "does not exist on disk"

    def test_stem_the_pipeline_would_drop_is_rejected_loudly(self, tmp_path):
        """A 2-char prefix fails forge's `[A-Z0-9]{3,12}` head and is dropped."""
        short = tmp_path / "TASK-FW-001-too-short-a-prefix.md"
        short.write_text("x", encoding="utf-8")
        assert not FORGE_FIX_TASK_ID_RE.match(short.stem)
        admitted, rejected = review_runner.admit_fix_task_paths(
            [short], written_this_run=[short], report_path=tmp_path / "report.md"
        )
        assert admitted == []
        assert "would drop it silently" in rejected[0]["reason"]


# ===========================================================================
# 6. The internal consistency check, both ways
# ===========================================================================


class TestConsistencyCheck:
    def test_findings_with_no_fix_tasks_fails(self):
        verdict, reason = review_runner.evaluate_consistency(
            findings=[SAMPLE_FINDING], fix_task_paths=[]
        )
        assert verdict == "FAILED"
        assert "clean-looking success" in reason

    def test_findings_with_fix_tasks_passes(self):
        verdict, reason = review_runner.evaluate_consistency(
            findings=[SAMPLE_FINDING], fix_task_paths=["/tmp/TASK-ABC-001.md"]
        )
        assert (verdict, reason) == ("PASSED", None)

    def test_clean_with_no_fix_tasks_passes(self):
        assert review_runner.evaluate_consistency(findings=[], fix_task_paths=[])[0] == (
            "PASSED"
        )

    def test_fix_tasks_without_findings_fails(self):
        verdict, reason = review_runner.evaluate_consistency(
            findings=[], fix_task_paths=["/tmp/TASK-ABC-001.md"]
        )
        assert verdict == "FAILED"
        assert "claims clean while producing work" in reason

    def test_end_to_end_findings_but_producer_wrote_nothing_exits_2(
        self, runner, repo, monkeypatch
    ):
        install_fake_producer(monkeypatch, repo, [])  # producer writes nothing
        install_fake_specialist(
            monkeypatch,
            repo,
            report_body=findings_report(),
            findings_payload={"findings": [SAMPLE_FINDING]},
        )
        result = runner.invoke(task_review, ["--task-id", TASK_ID])
        assert result.exit_code == 2
        assert "refusing to print a clean-looking success" in result.stderr
        assert "## Artefacts" not in result.stdout

    def test_a_clean_review_must_be_positively_clean(self, runner, repo, monkeypatch):
        """Empty findings + no explicit clean line = exit 2, not a quiet pass."""
        install_fake_specialist(
            monkeypatch,
            repo,
            report_body="# Review Report\n\n## Findings\n\nnothing much\n",
            findings_payload={"findings": []},
        )
        result = runner.invoke(task_review, ["--task-id", TASK_ID])
        assert result.exit_code == 2
        assert "POSITIVELY" in result.stderr

    def test_missing_findings_file_exits_2(self, runner, repo, monkeypatch):
        install_fake_specialist(monkeypatch, repo, report_body=clean_report())
        result = runner.invoke(task_review, ["--task-id", TASK_ID])
        assert result.exit_code == 2
        assert "findings file not written" in result.stderr

    def test_missing_report_exits_2(self, runner, repo, monkeypatch):
        install_fake_specialist(monkeypatch, repo, findings_payload={"findings": []})
        result = runner.invoke(task_review, ["--task-id", TASK_ID])
        assert result.exit_code == 2
        assert "wrote no report" in result.stderr


# ===========================================================================
# 7. The per-leg receipt
# ===========================================================================


class TestReceipt:
    def _receipt(self, repo: Path) -> dict:
        path = review_runner.receipt_path_for(repo, TASK_ID)
        assert path.is_file(), f"receipt not written at {path}"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_receipt_mirrors_task_work_results_location(self, repo):
        assert review_runner.receipt_path_for(repo, TASK_ID) == (
            repo / ".guardkit" / "autobuild" / TASK_ID / "task_review_results.json"
        )

    def test_receipt_shape_on_a_findings_run(self, runner, repo, monkeypatch):
        install_fake_producer(monkeypatch, repo, ["TASK-HPR-001-fix.md"])
        install_fake_specialist(
            monkeypatch,
            repo,
            report_body=findings_report(),
            findings_payload={"findings": [SAMPLE_FINDING]},
        )
        result = runner.invoke(
            task_review,
            [
                "--task-id",
                TASK_ID,
                "--build-id",
                "BUILD-9",
                "--correlation-id",
                "CID-9",
                "--model",
                "qwen36-workhorse",
            ],
        )
        assert result.exit_code == 0, result.stderr
        receipt = self._receipt(repo)

        assert receipt["leg"] == "task-review"
        assert receipt["task_id"] == TASK_ID
        assert receipt["build_id"] == "BUILD-9"
        assert receipt["correlation_id"] == "CID-9"
        assert receipt["model"] == "qwen36-workhorse"
        assert receipt["status"] == "findings"
        assert receipt["exit_code"] == 0
        assert receipt["findings_count"] == 1
        assert receipt["consistency_check"] == "PASSED"
        assert isinstance(receipt["duration_seconds"], (int, float))
        assert len(receipt["fix_task_paths"]) == 1
        assert receipt["review_report_path"].endswith(
            f"{TASK_ID}-review-report.md"
        )
        # The report is pinned in the receipt, never in ## Artefacts.
        assert receipt["review_report_path"] not in receipt["fix_task_paths"]

    def test_receipt_carries_the_phases_not_run_list(self, runner, repo, monkeypatch):
        install_fake_specialist(
            monkeypatch,
            repo,
            report_body=clean_report(),
            findings_payload={"findings": []},
        )
        result = runner.invoke(task_review, ["--task-id", TASK_ID])
        assert result.exit_code == 0, result.stderr
        phases = self._receipt(repo)["phases_not_run"]

        by_checkpoint = {p["checkpoint"]: p for p in phases}
        assert len(phases) == 6
        dispositions = {p["checkpoint"]: p["disposition"] for p in phases}
        assert any(
            "Phase 0" in c and d == "REFUSED" for c, d in dispositions.items()
        )
        assert any(
            "1.6" in c and d == "AUTO-ANSWERED" for c, d in dispositions.items()
        )
        assert any(
            "MCP tier" in c and d == "DECLARED-ABSENT" for c, d in dispositions.items()
        )
        assert any(
            "CLI tier" in c and d == "ATTEMPTED-AND-RECORDED"
            for c, d in dispositions.items()
        )
        assert any(
            "4.5" in c and d == "DECLARED-ABSENT" for c, d in dispositions.items()
        )
        assert any(
            "Phase 5" in c and d == "RELOCATED" for c, d in dispositions.items()
        )
        # The auto-answer is recorded WITH the answer used (§c.1's law).
        clarification = next(p for p in phases if "1.6" in p["checkpoint"])
        assert clarification["answer_used"] == "defaults applied (unattended)"
        # Phase 5 names where the judgement went.
        assert "gate_decision" in by_checkpoint[
            next(c for c in by_checkpoint if "Phase 5" in c)
        ]["relocated_to"]

    def test_receipt_written_on_the_refusal_path_too(
        self, runner, repo, monkeypatch
    ):
        install_fake_producer(monkeypatch, repo, [])
        install_fake_specialist(
            monkeypatch,
            repo,
            report_body=findings_report(),
            findings_payload={"findings": [SAMPLE_FINDING]},
        )
        result = runner.invoke(task_review, ["--task-id", TASK_ID])
        assert result.exit_code == 2
        receipt = self._receipt(repo)
        assert receipt["status"] == "inconsistent"
        assert receipt["consistency_check"] == "FAILED"
        assert receipt["exit_code"] == 2


# ===========================================================================
# 8. --nats: accepted, stderr only
# ===========================================================================


class TestNatsFlag:
    def test_nats_notice_goes_to_stderr_not_stdout(self, runner, repo, monkeypatch):
        install_fake_specialist(
            monkeypatch,
            repo,
            report_body=clean_report(),
            findings_payload={"findings": []},
        )
        result = runner.invoke(task_review, ["--task-id", TASK_ID, "--nats"])
        assert result.exit_code == 0
        assert "streaming NOT BUILT" in result.stderr
        assert "NOT BUILT" not in result.stdout
        # The scrape is unaffected.
        assert forge_extract_artefacts(result.stdout) == []

    def test_nats_help_declares_it_is_not_built(self, runner):
        result = runner.invoke(task_review, ["--help"])
        assert "NOT BUILT" in result.stdout

    def test_no_notice_when_the_flag_is_absent(self, runner, repo, monkeypatch):
        install_fake_specialist(
            monkeypatch,
            repo,
            report_body=clean_report(),
            findings_payload={"findings": []},
        )
        result = runner.invoke(task_review, ["--task-id", TASK_ID])
        assert "streaming NOT BUILT" not in result.stderr


# ===========================================================================
# 9. --context, both payload kinds
# ===========================================================================


class TestContextFlag:
    def test_readable_file_is_read_as_a_document(self, tmp_path):
        doc = tmp_path / "contract.md"
        doc.write_text("# Contract\nbody", encoding="utf-8")
        payloads = review_runner.load_context_payloads(
            [str(doc)], repo_root=tmp_path
        )
        assert payloads[0].kind == "file"
        assert "body" in payloads[0].text

    def test_inline_json_failure_pack_is_recognised(self, tmp_path):
        blob = json.dumps({"failure_pack": {"stage": "build", "exit_code": 1}})
        payloads = review_runner.load_context_payloads([blob], repo_root=tmp_path)
        assert payloads[0].kind == "inline-json"
        assert payloads[0].parsed["failure_pack"]["stage"] == "build"

    def test_inline_text_is_kept_as_text(self, tmp_path):
        payloads = review_runner.load_context_payloads(
            ["the previous build failed on the header path"], repo_root=tmp_path
        )
        assert payloads[0].kind == "inline-text"
        assert payloads[0].parsed is None

    def test_unreadable_context_never_fails_the_leg(self, runner, repo, monkeypatch):
        """A leg stricter than its caller turns a warning into a dead journey."""
        install_fake_specialist(
            monkeypatch,
            repo,
            report_body=clean_report(),
            findings_payload={"findings": []},
        )
        result = runner.invoke(
            task_review,
            [
                "--task-id",
                TASK_ID,
                "--context",
                "/nonexistent/path/to/nowhere.md",
                "--context",
                '{"failure_pack": {"stage": "build"}}',
            ],
        )
        assert result.exit_code == 0, result.stderr
        receipt = json.loads(
            review_runner.receipt_path_for(repo, TASK_ID).read_text(encoding="utf-8")
        )
        kinds = [entry["kind"] for entry in receipt["context"]]
        # A path that does not exist is treated as inline text, never fatal.
        assert "inline-json" in kinds
        assert len(kinds) == 2

    def test_both_kinds_reach_the_prompt(self, runner, repo, monkeypatch):
        doc = repo / "contract.md"
        doc.write_text("CONTRACT-MARKER", encoding="utf-8")
        recorder: dict = {}
        install_fake_specialist(
            monkeypatch,
            repo,
            report_body=clean_report(),
            findings_payload={"findings": []},
            recorder=recorder,
        )
        result = runner.invoke(
            task_review,
            [
                "--task-id",
                TASK_ID,
                "--context",
                str(doc),
                "--context",
                '{"failure_pack": {"stage": "build"}}',
            ],
        )
        assert result.exit_code == 0, result.stderr
        assert "CONTRACT-MARKER" in recorder["prompt"]
        assert "failure_pack" in recorder["prompt"]


# ===========================================================================
# 10. Composition: the run_specialist seam
# ===========================================================================


class TestComposition:
    def test_seam_arguments(self, runner, repo, monkeypatch):
        recorder: dict = {}
        install_fake_specialist(
            monkeypatch,
            repo,
            report_body=clean_report(),
            findings_payload={"findings": []},
            recorder=recorder,
        )
        result = runner.invoke(
            task_review, ["--task-id", TASK_ID, "--sdk-timeout", "123"]
        )
        assert result.exit_code == 0, result.stderr
        assert recorder["specialist_name"] == "code-reviewer"
        assert recorder["allowed_tools"] == ["Read", "Grep", "Glob", "Write"]
        assert recorder["task_id"] == TASK_ID
        assert recorder["sdk_timeout"] == 123
        assert recorder["worktree_path"].resolve() == repo.resolve()

    def test_prompt_carries_every_disposition(self, runner, repo, monkeypatch):
        recorder: dict = {}
        install_fake_specialist(
            monkeypatch,
            repo,
            report_body=clean_report(),
            findings_payload={"findings": []},
            recorder=recorder,
        )
        runner.invoke(task_review, ["--task-id", TASK_ID])
        prompt = recorder["prompt"]
        for token in (
            "REFUSED",
            "AUTO-ANSWERED",
            "DECLARED-ABSENT",
            "RELOCATED",
            "clarification: defaults applied (unattended)",
            "handle_implement_option_sync",
        ):
            assert token in prompt, token

    def test_protocol_file_is_loadable_by_name(self):
        from guardkit.orchestrator.prompts import load_protocol

        body = load_protocol("task_review_protocol")
        assert "Phases Not Run" in body
        assert review_runner.CLEAN_REVIEW_LINE in body


# ===========================================================================
# 11. Budget expiry → written partial + exit 2
# ===========================================================================


class TestTimeout:
    def test_timeout_writes_a_partial_and_exits_2(self, runner, repo, monkeypatch):
        install_fake_specialist(
            monkeypatch,
            repo,
            status="failed",
            error="SDKTimeoutError: SDK invocation exceeded 480s",
        )
        result = runner.invoke(task_review, ["--task-id", TASK_ID])
        assert result.exit_code == 2
        assert "internal 480s budget" in result.stderr

        report = repo / ".claude" / "reviews" / f"{TASK_ID}-review-report.md"
        assert report.is_file()
        body = report.read_text(encoding="utf-8")
        assert "PARTIAL" in body
        assert "did not complete" in body
        assert "Phases Not Run" in body

        receipt = json.loads(
            review_runner.receipt_path_for(repo, TASK_ID).read_text(encoding="utf-8")
        )
        assert receipt["status"] == "timeout"
        assert receipt["exit_code"] == 2
        assert receipt["findings_count"] == 0

    def test_timeout_prints_no_markers(self, runner, repo, monkeypatch):
        install_fake_specialist(
            monkeypatch, repo, status="failed", error="timed out after 480s"
        )
        result = runner.invoke(task_review, ["--task-id", TASK_ID])
        assert "## Artefacts" not in result.stdout
        assert "## Detection Findings" not in result.stdout

    def test_non_timeout_failure_is_classified_separately(
        self, runner, repo, monkeypatch
    ):
        install_fake_specialist(
            monkeypatch, repo, status="failed", error="AgentInvocationError: boom"
        )
        result = runner.invoke(task_review, ["--task-id", TASK_ID])
        assert result.exit_code == 2
        receipt = json.loads(
            review_runner.receipt_path_for(repo, TASK_ID).read_text(encoding="utf-8")
        )
        assert receipt["status"] == "failed"
        assert "boom" in receipt["error"]

    def test_timeout_classifier(self):
        assert review_runner._looks_like_timeout("SDKTimeoutError", 1.0, 480)
        assert review_runner._looks_like_timeout(None, 479.0, 480)
        assert not review_runner._looks_like_timeout("boom", 1.0, 480)


# ===========================================================================
# 12. Findings-file tolerance
# ===========================================================================


class TestFindingsFile:
    def test_bare_array_is_accepted(self, tmp_path):
        path = tmp_path / "f.json"
        path.write_text(json.dumps([SAMPLE_FINDING]), encoding="utf-8")
        findings, score, error = review_runner.read_findings_file(path)
        assert findings == [SAMPLE_FINDING]
        assert (score, error) == (None, None)

    def test_non_dict_elements_are_dropped(self, tmp_path):
        path = tmp_path / "f.json"
        path.write_text(json.dumps(["oops", SAMPLE_FINDING, 3]), encoding="utf-8")
        findings, _, error = review_runner.read_findings_file(path)
        assert findings == [SAMPLE_FINDING]
        assert error is None

    def test_malformed_json_is_an_honest_error(self, tmp_path):
        path = tmp_path / "f.json"
        path.write_text("{not json", encoding="utf-8")
        findings, _, error = review_runner.read_findings_file(path)
        assert findings == []
        assert "malformed" in error

    def test_boolean_coach_score_is_not_a_float(self, tmp_path):
        path = tmp_path / "f.json"
        path.write_text(
            json.dumps({"findings": [], "coach_score": True}), encoding="utf-8"
        )
        _, score, _ = review_runner.read_findings_file(path)
        assert score is None


# ===========================================================================
# 13. The REAL fix-task producer — no fake at this seam
# ===========================================================================


class TestRealProducer:
    """Exercises ``implement_orchestrator.handle_implement_option_sync`` for real.

    The producer is the design's fourth win — "the fix-task artefact
    requirement is met by an **existing** producer" — so it gets a test that
    does not fake it. Network-free: the producer only parses markdown and
    writes files under ``tasks/backlog/``.
    """

    REPORT = (
        "# Review Report — TASK-REV-A1B2C3\n\n"
        "## Summary\n\nTwo defects.\n\n"
        "## Recommendations\n\n"
        "1. Add a null guard to parse_header() in src/parser.py.\n"
        "2. Cover the truncated-header path in tests/test_parser.py.\n"
    )

    def _run(self, tmp_path: Path, title: str):
        report = tmp_path / ".claude" / "reviews" / f"{TASK_ID}-review-report.md"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(self.REPORT, encoding="utf-8")
        cwd = Path.cwd()
        import os

        os.chdir(tmp_path)
        try:
            return (
                review_runner.produce_fix_tasks(
                    task_id=TASK_ID,
                    task={"frontmatter": {"title": title}},
                    report_path=report,
                    repo_root=tmp_path,
                ),
                report,
            )
        finally:
            os.chdir(cwd)

    def test_real_producer_writes_admissible_fix_tasks(self, tmp_path):
        (written, info), report = self._run(
            tmp_path, "Review header parser subsystem"
        )
        assert len(written) == 2, info
        admitted, rejected = review_runner.admit_fix_task_paths(
            written, written_this_run=written, report_path=report
        )
        assert len(admitted) == 2
        assert rejected == []
        # And the pipeline's own extractor recovers two typed fix-task ids.
        assert len(forge_extract_fix_tasks(admitted)) == 2

    def test_producer_stdout_narration_never_reaches_our_stdout(
        self, tmp_path, capsys
    ):
        """The producer prints a 10-step narration; stdout is a control surface."""
        capsys.readouterr()
        (written, info), _ = self._run(tmp_path, "Review header parser subsystem")
        captured = capsys.readouterr()
        assert "Step 1/10" not in captured.out
        assert "Step 1/10" in info["narration_tail"]

    def test_producer_failure_after_writing_is_recorded_not_swallowed(
        self, tmp_path
    ):
        """KNOWN PRE-EXISTING DEFECT, pinned so it cannot rot silently.

        ``guide_generator._calculate_wave_duration`` (installer/core/lib/
        guide_generator.py:164) sums ``estimated_effort_days`` across a wave,
        but the subtasks the review parser produces carry that field as a
        *string* — so the producer raises ``TypeError`` at step 9/10, **after**
        the fix-task files are already on disk at step 8. The leg must keep the
        real files and record the failure, never discard the work or claim a
        clean producer run.
        """
        (written, info), _ = self._run(tmp_path, "Review header parser subsystem")
        assert len(written) == 2
        assert info["ok"] is False
        assert "TypeError" in info["error"]

    def test_producer_sidecars_are_not_candidate_artefacts(self, monkeypatch, tmp_path):
        """README / IMPLEMENTATION-GUIDE land beside the fix tasks but are not one."""

        def _producer(review_task, review_report_path):
            target = tmp_path / "tasks" / "backlog" / "header-parser"
            target.mkdir(parents=True, exist_ok=True)
            for name in (
                "TASK-HPR-001-fix.md",
                "README.md",
                "IMPLEMENTATION-GUIDE.md",
            ):
                (target / name).write_text("x", encoding="utf-8")

        monkeypatch.setattr(review_runner, "_import_producer", lambda: _producer)
        report = tmp_path / ".claude" / "reviews" / f"{TASK_ID}-review-report.md"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(self.REPORT, encoding="utf-8")

        written, _info = review_runner.produce_fix_tasks(
            task_id=TASK_ID,
            task={"frontmatter": {"title": "Review header parser subsystem"}},
            report_path=report,
            repo_root=tmp_path,
        )
        assert [p.name for p in written] == ["TASK-HPR-001-fix.md"]
        admitted, rejected = review_runner.admit_fix_task_paths(
            written, written_this_run=written, report_path=report
        )
        assert len(admitted) == 1
        assert rejected == []

    def test_two_word_slug_produces_a_stem_the_pipeline_would_drop(self, tmp_path):
        """The producer/consumer stem mismatch, pinned as a live hazard.

        The producer's prefix is the slug's word initials, so a two-word
        feature slug yields ``TASK-FW-001-…`` — whose stem fails forge's
        ``TASK-[A-Z0-9]{3,12}`` head and is dropped **silently** by
        ``default_fix_tasks_extractor``. The leg's admission filter turns that
        silence into a named rejection, and the consistency check then exits 2.
        """
        (written, _info), report = self._run(tmp_path, "Review feature workflow")
        assert written, "producer wrote nothing"
        assert all(not FORGE_FIX_TASK_ID_RE.match(p.stem) for p in written)
        admitted, rejected = review_runner.admit_fix_task_paths(
            written, written_this_run=written, report_path=report
        )
        assert admitted == []
        assert all("would drop it silently" in r["reason"] for r in rejected)
        verdict, reason = review_runner.evaluate_consistency(
            findings=[SAMPLE_FINDING], fix_task_paths=admitted
        )
        assert verdict == "FAILED"
        assert "clean-looking success" in reason
