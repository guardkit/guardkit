"""GuardKitVsVanillaRunner — orchestrates the guardkit_vs_vanilla eval type.

Runs two arms sequentially from identical starting state:
  Arm A: full GuardKit pipeline (feature-spec → system-plan → feature-plan → autobuild)
  Arm B: vanilla Claude Code (no GuardKit config, same codebase)

Both arms receive the same resolved input text.
Results are compared by MetricsExtractor and EvalJudge.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from eval_agent_invoker import EvalAgentInvoker, EvalAgentError, Trajectory
from eval_workspace import ForkedWorkspace

logger = logging.getLogger(__name__)


# ============================================================================
# Input resolution
# ============================================================================


class InputResolutionError(Exception):
    """Raised when the eval input cannot be resolved."""
    pass


class InputResolver:
    """Resolves eval input to a plain text string.

    Handles three sources:
      - text: use directly
      - file: read from path
      - linear_ticket: fetch via Linear MCP or web fetch
    """

    async def resolve(self, input_config: dict) -> str:
        """Resolve input to plain text. Raises InputResolutionError on failure."""
        source = input_config.get("source", "text")

        if source == "text":
            text = input_config.get("text", "").strip()
            if not text:
                raise InputResolutionError("Input source is 'text' but 'text' field is empty")
            return text

        elif source == "file":
            path = Path(input_config.get("file_path", ""))
            if not path.exists():
                raise InputResolutionError(f"Input file not found: {path}")
            return path.read_text(encoding="utf-8").strip()

        elif source == "linear_ticket":
            url = input_config.get("linear_ticket_url", "")
            if not url:
                raise InputResolutionError("Input source is 'linear_ticket' but 'linear_ticket_url' is empty")
            return await self._fetch_linear_ticket(url)

        else:
            raise InputResolutionError(f"Unknown input source: '{source}'. Must be text, file, or linear_ticket.")

    async def _fetch_linear_ticket(self, url: str) -> str:
        """Fetch Linear ticket content.

        Tries Linear MCP first, falls back to plain web fetch.
        Returns formatted plain text of the ticket.
        """
        logger.info(f"Fetching Linear ticket: {url}")
        try:
            return await self._fetch_via_web(url)
        except Exception as e:
            raise InputResolutionError(
                f"Could not fetch Linear ticket from {url}: {e}\n"
                f"Tip: use 'source: text' and paste the ticket content directly."
            ) from e

    @staticmethod
    async def _fetch_via_web(url: str) -> str:
        """Basic web fetch of a Linear ticket URL."""
        import urllib.request
        import html
        import re

        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            raise ValueError(f"HTTP fetch failed: {e}") from e

        # Extract meaningful text from Linear's HTML
        # Linear renders ticket title in <title> and description in og:description
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", content, re.IGNORECASE)
        desc_match = re.search(r'og:description["\s]+content="([^"]+)"', content, re.IGNORECASE)

        title = html.unescape(title_match.group(1)) if title_match else url
        desc = html.unescape(desc_match.group(1)) if desc_match else ""

        if not desc:
            raise ValueError("Could not extract ticket description from page content")

        return f"Title: {title.strip()}\n\nDescription:\n{desc.strip()}"


# ============================================================================
# Metrics extraction
# ============================================================================


@dataclass
class ArmMetrics:
    """Measured metrics from one arm's workspace after agent run."""
    arm: str
    turns_total: int = -1
    files_created: list[str] = field(default_factory=list)
    test_coverage_pct: float = -1.0     # -1 = not measurable
    lint_violations: int = -1           # -1 = not measurable
    assumptions_explicit: int = 0
    runnable: bool = False
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "turns_total": self.turns_total,
            "files_created": self.files_created,
            "test_coverage_pct": self.test_coverage_pct,
            "lint_violations": self.lint_violations,
            "assumptions_explicit": self.assumptions_explicit,
            "runnable": self.runnable,
            **({"error": self.error} if self.error else {}),
        }


@dataclass
class ComparisonMetrics:
    """Metrics from both arms, with computed deltas."""
    guardkit: ArmMetrics
    vanilla: ArmMetrics

    def coverage_delta(self) -> Optional[float]:
        """Positive = GuardKit better. None = not measurable."""
        if self.guardkit.test_coverage_pct < 0 or self.vanilla.test_coverage_pct < 0:
            return None
        return self.guardkit.test_coverage_pct - self.vanilla.test_coverage_pct

    def lint_delta(self) -> Optional[int]:
        """Negative = GuardKit better (fewer violations). None = not measurable."""
        if self.guardkit.lint_violations < 0 or self.vanilla.lint_violations < 0:
            return None
        return self.guardkit.lint_violations - self.vanilla.lint_violations

    def assumption_delta(self) -> int:
        """Positive = GuardKit surfaced more assumptions explicitly."""
        return self.guardkit.assumptions_explicit - self.vanilla.assumptions_explicit

    def to_graphiti_fields(self) -> dict:
        """Fields for Graphiti episode storage."""
        cov = self.coverage_delta()
        lint = self.lint_delta()
        return {
            "guardkit_arm": self.guardkit.to_dict(),
            "vanilla_arm": self.vanilla.to_dict(),
            "deltas": {
                "coverage": f"{cov:+.1f}pp" if cov is not None else "not measurable",
                "lint": f"{lint:+d} violations" if lint is not None else "not measurable",
                "assumptions_surfaced": f"{self.assumption_delta():+d}",
            },
        }


class MetricsExtractor:
    """Reads per-arm evidence files and computes ComparisonMetrics."""

    def extract(
        self,
        guardkit_ws: ForkedWorkspace,
        vanilla_ws: ForkedWorkspace,
        guardkit_error: Optional[str] = None,
        vanilla_error: Optional[str] = None,
    ) -> ComparisonMetrics:
        gk = self._extract_arm(guardkit_ws, "guardkit", guardkit_error)
        van = self._extract_arm(vanilla_ws, "vanilla", vanilla_error)
        return ComparisonMetrics(guardkit=gk, vanilla=van)

    def _extract_arm(
        self, ws: ForkedWorkspace, arm: str, error: Optional[str]
    ) -> ArmMetrics:
        m = ArmMetrics(arm=arm, error=error)
        evidence_dir = ws.path / ".eval" / "evidence"

        # c1.txt: "assumptions_surfaced={N}" or list of silent assumptions
        c1 = self._read_evidence(evidence_dir / "c1.txt")
        if c1:
            if "assumptions_surfaced=" in c1:
                try:
                    m.assumptions_explicit = int(c1.split("assumptions_surfaced=")[1].split()[0])
                except (ValueError, IndexError):
                    pass
            elif arm == "guardkit":
                # Guardkit writes count; count lines as proxy
                m.assumptions_explicit = max(0, c1.count("\n"))

        # c2.txt: "coverage={N}%"
        c2 = self._read_evidence(evidence_dir / "c2.txt")
        if c2 and "coverage=" in c2:
            try:
                pct_str = c2.split("coverage=")[1].split("%")[0].strip()
                m.test_coverage_pct = float(pct_str)
            except (ValueError, IndexError):
                pass

        # c3.txt: "violations={N}"
        c3 = self._read_evidence(evidence_dir / "c3.txt")
        if c3 and "violations=" in c3:
            try:
                m.lint_violations = int(c3.split("violations=")[1].split()[0])
            except (ValueError, IndexError):
                pass

        # c5.txt: "runnable={yes|no}"
        c5 = self._read_evidence(evidence_dir / "c5.txt")
        if c5:
            m.runnable = "yes" in c5.lower()

        return m

    @staticmethod
    def _read_evidence(path: Path) -> Optional[str]:
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        return None


# ============================================================================
# Per-arm agent instructions
# ============================================================================

GUARDKIT_AGENT_INSTRUCTIONS = """
You are evaluating the GuardKit pipeline against a given requirement.

The input requirement is in: ./input.txt

Execute the full GuardKit pipeline in order:

1. Run: guardkit feature-spec --from ./input.txt
   Document: did it produce assumptions.md? How many assumptions were listed?

2. Run: guardkit system-plan

3. Run: guardkit feature-plan

4. Run: guardkit autobuild
   Document: total turns, Coach feedback cycles, any blocking issues.

After EACH command, append to ./guardkit-run-log.md:
  ## After [command name]
  - Status: [success / failed / blocked]
  - Key outputs: [files created, notable decisions]
  - Turns used: [N if applicable]
  - Coach feedback cycles: [N if applicable]

When all commands are complete:
- Run the test suite and note the coverage percentage
- Run the linter (ruff, pylint, or tsc --noEmit as appropriate) and count violations

Write evidence files:
  .eval/evidence/c1.txt  →  "assumptions_surfaced={N}" (count entries in assumptions.md, or 0)
  .eval/evidence/c2.txt  →  "coverage={N}%" (from test output, or "coverage=unknown")
  .eval/evidence/c3.txt  →  "violations={N}" (from linter, or "violations=unknown")
  .eval/evidence/c5.txt  →  "runnable=yes" or "runnable=no"

Write SUMMARY.md with sections:
  ## Objective
  ## Steps Executed  
  ## What Was Surfaced (assumptions, design decisions made explicit)
  ## Output Quality
  ## Assessment
""".strip()

VANILLA_AGENT_INSTRUCTIONS = """
You are evaluating vanilla Claude Code against a given requirement.

The input requirement is in: ./input.txt

Execute vanilla Claude Code — use ONLY the bare claude command:

1. Run: claude "$(cat ./input.txt)"

   IMPORTANT RULES:
   - Do NOT use any guardkit commands
   - Do NOT create CLAUDE.md or .guardkit/ directories
   - Do NOT add any system prompts or methodology
   - Let Claude Code proceed entirely on its own with just the requirement

2. Observe what Claude Code does:
   - Did it ask clarifying questions or proceed on assumptions?
   - What did it implement vs what it left out?
   - What implicit assumptions are visible in the code?

When Claude Code finishes:
- Run the test suite and note the coverage percentage
- Run the linter and count violations
- Inspect the output code for silent assumptions (things Claude Code decided
  without surfacing them — e.g. error response format, caching strategy, auth)

Write evidence files:
  .eval/evidence/c1.txt  →  List of silent assumptions you observed in the vanilla output
                             (one per line, e.g. "Assumed 404 response has no body")
  .eval/evidence/c2.txt  →  "coverage={N}%" (from test output, or "coverage=unknown")
  .eval/evidence/c3.txt  →  "violations={N}" (from linter, or "violations=unknown")
  .eval/evidence/c5.txt  →  "runnable=yes" or "runnable=no"

Write SUMMARY.md with sections:
  ## Objective
  ## Steps Executed
  ## What Claude Code Assumed Silently (list each assumption with evidence)
  ## Output Quality
  ## Assessment
""".strip()


# ============================================================================
# Runner
# ============================================================================


class GuardKitVsVanillaRunner:
    """Orchestrates a guardkit_vs_vanilla eval — two arms, one comparison."""

    def __init__(self) -> None:
        self.resolver = InputResolver()
        self.extractor = MetricsExtractor()

    async def run(
        self,
        brief,   # GuardKitVsVanillaBrief or EvalBrief with type=guardkit_vs_vanilla
        js,      # NATS JetStream context
    ) -> tuple[Trajectory, Trajectory, ComparisonMetrics]:
        """Run both arms and return trajectories + metrics for judging.

        Returns (guardkit_trajectory, vanilla_trajectory, comparison_metrics).
        """
        eval_id = brief.eval_id

        # 1. Resolve input — same text for both arms
        logger.info(f"[{eval_id}] Resolving input")
        input_text = await self.resolver.resolve(
            brief.input if hasattr(brief, "input") else {"source": "text", "text": brief.objective}
        )
        logger.info(f"[{eval_id}] Input resolved ({len(input_text)} chars)")

        # 2. Provision workspaces
        gk_template = getattr(brief, "guardkit_arm_template", "guardkit-project")
        van_template = getattr(brief, "vanilla_arm_template", "plain-project")

        gk_ws, van_ws = await ForkedWorkspace.__class__.create_forked_pair.__func__(
            ForkedWorkspace, eval_id, gk_template, van_template
        )
        # Simpler: just instantiate directly
        from eval_workspace import EvalWorkspace
        gk_ws_obj, van_ws_obj = await EvalWorkspace.create_forked_pair(
            eval_id, gk_template, van_template
        )

        gk_error: Optional[str] = None
        van_error: Optional[str] = None
        gk_trajectory: Optional[Trajectory] = None
        van_trajectory: Optional[Trajectory] = None

        try:
            # Write input.txt to both workspaces
            gk_ws_obj.write_input(input_text)
            van_ws_obj.write_input(input_text)

            # 3. Run Arm A — GuardKit
            await self._publish_status(js, eval_id, "arm_a_running", "GuardKit pipeline")
            logger.info(f"[{eval_id}] === Arm A: GuardKit pipeline ===")
            try:
                gk_invoker = EvalAgentInvoker(
                    workspace_path=gk_ws_obj.path,
                    timeout_seconds=brief.setup.timeout_minutes * 60 // 2,
                )
                gk_brief = self._build_arm_brief(brief, "guardkit", GUARDKIT_AGENT_INSTRUCTIONS)
                gk_trajectory = await gk_invoker.invoke(gk_brief)
                logger.info(f"[{eval_id}] Arm A complete: {gk_trajectory.num_turns} turns")
            except EvalAgentError as e:
                logger.error(f"[{eval_id}] Arm A (GuardKit) failed: {e}")
                gk_error = str(e)
                gk_trajectory = Trajectory(eval_id=eval_id)  # empty

            # 4. Run Arm B — Vanilla
            await self._publish_status(js, eval_id, "arm_b_running", "Vanilla Claude Code")
            logger.info(f"[{eval_id}] === Arm B: Vanilla Claude Code ===")
            try:
                van_invoker = EvalAgentInvoker(
                    workspace_path=van_ws_obj.path,
                    timeout_seconds=brief.setup.timeout_minutes * 60 // 2,
                )
                van_brief = self._build_arm_brief(brief, "vanilla", VANILLA_AGENT_INSTRUCTIONS)
                van_trajectory = await van_invoker.invoke(van_brief)
                logger.info(f"[{eval_id}] Arm B complete: {van_trajectory.num_turns} turns")
            except EvalAgentError as e:
                logger.error(f"[{eval_id}] Arm B (Vanilla) failed: {e}")
                van_error = str(e)
                van_trajectory = Trajectory(eval_id=eval_id)

            # 5. Extract metrics
            await self._publish_status(js, eval_id, "extracting_metrics")
            metrics = self.extractor.extract(gk_ws_obj, van_ws_obj, gk_error, van_error)
            logger.info(
                f"[{eval_id}] Metrics:"
                f"\n  GuardKit: coverage={metrics.guardkit.test_coverage_pct}%"
                f" lint={metrics.guardkit.lint_violations}"
                f" assumptions={metrics.guardkit.assumptions_explicit}"
                f"\n  Vanilla:  coverage={metrics.vanilla.test_coverage_pct}%"
                f" lint={metrics.vanilla.lint_violations}"
                f" assumptions={metrics.vanilla.assumptions_explicit}"
            )

            return gk_trajectory, van_trajectory, metrics

        finally:
            await gk_ws_obj.teardown()
            await van_ws_obj.teardown()

    def _build_arm_brief(self, brief, arm: str, instructions: str):
        """Build a minimal brief-like object for the arm's EvalAgentInvoker."""
        from types import SimpleNamespace
        return SimpleNamespace(
            eval_id=f"{brief.eval_id}-{arm}",
            title=f"{brief.title} [{arm}]",
            objective=brief.objective,
            agent_instructions=instructions,
            criteria=brief.criteria,
        )

    @staticmethod
    async def _publish_status(js, eval_id: str, phase: str, detail: str = "") -> None:
        import json
        payload = json.dumps({"eval_id": eval_id, "phase": phase, "detail": detail}).encode()
        try:
            await js.publish(f"eval.status.{eval_id}", payload)
        except Exception:
            pass
