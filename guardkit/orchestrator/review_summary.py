"""Review summary generator for autobuild feature orchestration.

TASK-ABE-003: Generates structured human-readable markdown summaries from
FeatureOrchestrationResult data after feature_orchestrator.orchestrate() completes.

The generator reads existing data structures without modifying them and writes
a self-contained markdown file alongside the autobuild output directory.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from guardkit.orchestrator.feature_orchestrator import (
        FeatureOrchestrationResult,
        TaskExecutionResult,
    )

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class TaskSummaryRow:
    """Single row in the per-task outcome table."""

    task_id: str
    wave: int
    outcome: str  # "passed" | "failed"
    turns: int
    final_decision: str
    sdk_invocations: int
    sdk_ceiling_hits: int
    error: Optional[str] = None


@dataclass
class ReviewSummaryResult:
    """Result of summary generation."""

    success: bool
    output_path: Optional[Path] = None
    error: Optional[str] = None


# ============================================================================
# ReviewSummaryGenerator
# ============================================================================


class ReviewSummaryGenerator:
    """Generate a structured markdown review summary from autobuild execution data.

    Accepts a FeatureOrchestrationResult and writes a markdown file to the
    specified output directory.

    Parameters
    ----------
    output_dir : Path
        Directory where the summary file is written.
    """

    FILENAME = "review-summary.md"

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)

    def generate(self, result: FeatureOrchestrationResult) -> ReviewSummaryResult:
        """Generate and write the review summary markdown file.

        Parameters
        ----------
        result : FeatureOrchestrationResult
            Complete orchestration result to summarise.

        Returns
        -------
        ReviewSummaryResult
            Success flag and path to the written file, or error detail.
        """
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.output_dir / self.FILENAME
            content = self._render(result)
            output_path.write_text(content, encoding="utf-8")
            logger.info("Review summary written to %s", output_path)
            return ReviewSummaryResult(success=True, output_path=output_path)
        except OSError as exc:
            logger.warning("Failed to write review summary: %s", exc)
            return ReviewSummaryResult(success=False, error=str(exc))

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render(self, result: FeatureOrchestrationResult) -> str:
        sections = [
            self._render_header(result),
            self._render_feature_metrics(result),
            self._render_task_table(result),
            self._render_quality_metrics(result),
            self._render_turn_efficiency(result),
            self._render_key_findings(result),
        ]
        return "\n\n".join(sections) + "\n"

    def _render_header(self, result: FeatureOrchestrationResult) -> str:
        status_badge = "COMPLETED" if result.success else result.status.upper()
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
        return (
            f"# Autobuild Review Summary: {result.feature_id}\n\n"
            f"**Status:** {status_badge}  \n"
            f"**Generated:** {generated_at}"
        )

    def _render_feature_metrics(self, result: FeatureOrchestrationResult) -> str:
        all_tasks = self._flatten_task_results(result)
        total_turns = sum(r.total_turns for r in all_tasks)
        avg_turns = total_turns / len(all_tasks) if all_tasks else 0.0
        first_attempt_pass = sum(
            1 for r in all_tasks if r.success and r.total_turns == 1
        )
        first_attempt_rate = (
            first_attempt_pass / len(all_tasks) * 100 if all_tasks else 0.0
        )

        lines = [
            "## Metrics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total tasks | {result.total_tasks} |",
            f"| Total turns | {total_turns} |",
            f"| Avg turns/task | {avg_turns:.2f} |",
            f"| Waves executed | {len(result.wave_results)} |",
            f"| First-attempt pass rate | {first_attempt_rate:.0f}% |",
        ]
        return "\n".join(lines)

    def _render_task_table(self, result: FeatureOrchestrationResult) -> str:
        rows = self._build_task_rows(result)
        lines = [
            "## Per-Task Outcomes",
            "",
            "| Task | Wave | Turns | Outcome | Decision | Notes |",
            "|------|------|-------|---------|----------|-------|",
        ]
        for row in rows:
            outcome = "PASSED" if row.outcome == "passed" else "FAILED"
            notes = row.error or ""
            if row.sdk_ceiling_hits > 0:
                notes = f"ceiling hits: {row.sdk_ceiling_hits}" + (
                    f"; {notes}" if notes else ""
                )
            lines.append(
                f"| {row.task_id} | {row.wave} | {row.turns} "
                f"| {outcome} | {row.final_decision} | {notes} |"
            )
        return "\n".join(lines)

    def _render_quality_metrics(self, result: FeatureOrchestrationResult) -> str:
        all_tasks = self._flatten_task_results(result)
        total = len(all_tasks)
        success_rate = result.tasks_completed / total * 100 if total else 0.0
        first_turn_approvals = sum(
            1 for r in all_tasks if r.success and r.total_turns == 1
        )
        total_ceiling = sum(r.sdk_ceiling_hits for r in all_tasks)

        lines = [
            "## Quality Metrics",
            "",
            f"- Task success rate: {success_rate:.0f}%",
            f"- First-turn approvals: {first_turn_approvals}/{total}",
            f"- SDK ceiling hits: {total_ceiling}",
        ]
        return "\n".join(lines)

    def _render_turn_efficiency(self, result: FeatureOrchestrationResult) -> str:
        all_tasks = self._flatten_task_results(result)
        if not all_tasks:
            return "## Turn Efficiency\n\nNo task data available."

        turns_list = [r.total_turns for r in all_tasks]
        avg_turns = sum(turns_list) / len(turns_list)
        single_turn = sum(1 for t in turns_list if t == 1)
        multi_turn = sum(1 for t in turns_list if t > 1)

        all_sdk_turns: List[int] = []
        for r in all_tasks:
            all_sdk_turns.extend(r.sdk_turns_per_invocation)
        avg_sdk = sum(all_sdk_turns) / len(all_sdk_turns) if all_sdk_turns else 0.0

        lines = [
            "## Turn Efficiency",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Avg turns/task | {avg_turns:.1f} |",
            f"| Single-turn tasks | {single_turn} |",
            f"| Multi-turn tasks | {multi_turn} |",
            f"| Avg SDK turns/invocation | {avg_sdk:.1f} |",
        ]
        return "\n".join(lines)

    def _render_key_findings(self, result: FeatureOrchestrationResult) -> str:
        findings: List[str] = []
        all_tasks = self._flatten_task_results(result)

        total_ceiling = sum(r.sdk_ceiling_hits for r in all_tasks)
        if total_ceiling > 0:
            findings.append(
                f"{total_ceiling} SDK ceiling hit(s) detected — "
                "consider raising max_turns or splitting complex tasks."
            )

        multi_turn_failures = [
            r for r in all_tasks if not r.success and r.total_turns > 1
        ]
        if multi_turn_failures:
            ids = ", ".join(r.task_id for r in multi_turn_failures)
            findings.append(
                f"Tasks required multiple turns before failing: {ids}. "
                "Review coach feedback logs for recurring patterns."
            )

        single_turn_failures = [
            r for r in all_tasks if not r.success and r.total_turns == 1
        ]
        if single_turn_failures:
            ids = ", ".join(r.task_id for r in single_turn_failures)
            findings.append(f"Tasks failed on first turn: {ids}.")

        recovery_tasks = [r for r in all_tasks if r.recovery_count > 0]
        if recovery_tasks:
            ids = ", ".join(
                f"{r.task_id} ({r.recovery_count}x)" for r in recovery_tasks
            )
            findings.append(f"State recovery used: {ids}.")

        if result.success and total_ceiling == 0 and not multi_turn_failures:
            findings.append("All tasks completed cleanly with no issues.")

        if not findings:
            findings.append("No notable findings.")

        bullet_lines = "\n".join(f"- {f}" for f in findings)
        return f"## Key Findings\n\n{bullet_lines}"

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _flatten_task_results(
        self, result: FeatureOrchestrationResult
    ) -> List[TaskExecutionResult]:
        return [r for wave in result.wave_results for r in wave.results]

    def _build_task_rows(
        self, result: FeatureOrchestrationResult
    ) -> List[TaskSummaryRow]:
        rows: List[TaskSummaryRow] = []
        for wave in result.wave_results:
            for task_result in wave.results:
                rows.append(
                    TaskSummaryRow(
                        task_id=task_result.task_id,
                        wave=wave.wave_number,
                        outcome="passed" if task_result.success else "failed",
                        turns=task_result.total_turns,
                        final_decision=task_result.final_decision,
                        sdk_invocations=task_result.sdk_total_invocations,
                        sdk_ceiling_hits=task_result.sdk_ceiling_hits,
                        error=task_result.error,
                    )
                )
        return rows


__all__ = [
    "ReviewSummaryGenerator",
    "ReviewSummaryResult",
    "TaskSummaryRow",
]
