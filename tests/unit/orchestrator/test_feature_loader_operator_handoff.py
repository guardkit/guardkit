"""FeatureLoader accepts operator_handoff tasks with runtime-shaped ACs.

Pins AC-FPTC-004-02 and AC-FPTC-004-03: a feature whose only task carries
``task_type: operator_handoff`` and 7 of 8 runtime-shaped acceptance
criteria (modelled on TASK-GR-SEED) loads cleanly via
``FeatureLoader.validate_feature`` returning no errors.

The FeatureLoader does not parse acceptance criteria from task markdown
in the first place — its validation pipeline only checks structural
metadata (file existence, dependency graph, parallel-group sanity,
``task_type`` enum membership). This test pins that property so a future
refactor introducing AC-presence checks would have to consciously
exclude ``operator_handoff`` to remain compliant with TASK-FPTC-004.

Coverage Target: >=85%
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureLoader,
    FeatureOrchestration,
    FeatureTask,
)


# Seven runtime-shaped acceptance criteria modelled on TASK-GR-SEED.
# Each is a procedural step a human operator performs, with no
# automated/coach-verifiable signal. Loaded into the task markdown as
# the ``## Acceptance Criteria`` section to exercise the realistic
# shape ``operator_handoff`` tasks adopt.
_RUNTIME_SHAPED_ACS = [
    "AC-1 — Operator runs `./scripts/seed-graphiti.sh` and observes "
    "exit code 0.",
    "AC-2 — Operator inspects the FalkorDB browser at "
    "`http://whitestocks:6379` and confirms the new group_id appears.",
    "AC-3 — Operator runs `guardkit graphiti search 'seed'` and "
    "confirms at least one node is returned.",
    "AC-4 — Operator opens the seeded ADR file and confirms the "
    "rationale section is present.",
    "AC-5 — Operator triggers a downstream `/task-create` and confirms "
    "the seeded knowledge surfaces in Phase 1.7.",
    "AC-6 — Operator runs `docker logs graphiti-mcp --tail 50` and "
    "confirms no extraction errors fired during the seed run.",
    "AC-7 — Operator records the seed timestamp in the runbook for "
    "audit-trail purposes.",
]


def _write_operator_handoff_task(
    repo_root: Path,
    rel_path: str,
    task_id: str,
) -> Path:
    """Write an operator_handoff task markdown with 7 runtime-shaped ACs."""
    task_file = repo_root / rel_path
    task_file.parent.mkdir(parents=True, exist_ok=True)

    ac_block = "\n".join(f"- [ ] {ac}" for ac in _RUNTIME_SHAPED_ACS)
    task_file.write_text(
        dedent(
            f"""\
            ---
            id: {task_id}
            title: "Seed graphiti knowledge base (operator handoff)"
            status: backlog
            task_type: operator_handoff
            ---

            # Task: Seed graphiti knowledge base

            ## Description

            Seed the Graphiti knowledge graph with the bootstrap ADR set.
            This step requires runtime access to the FalkorDB instance
            and the seed scripts on the operator's workstation, so it
            cannot be automated by the Player.

            ## Acceptance Criteria

            {ac_block}

            ## Implementation Notes

            Operator follow-up — no automated implementation possible.
            """
        )
    )
    return task_file


class TestFeatureLoaderAcceptsOperatorHandoffTask:
    """AC-FPTC-004-03: feature with operator_handoff task validates clean."""

    def test_validate_feature_returns_no_errors(self, tmp_path: Path) -> None:
        """A feature with one operator_handoff task validates with no errors.

        Verifies that 7 runtime-shaped ACs in the task markdown do not
        cause any FeatureLoader validation errors — neither at parse
        time (``_parse_feature``) nor at validate time
        (``validate_feature``).
        """
        rel_path = "tasks/in_progress/TASK-FPTC-OP-SEED.md"
        _write_operator_handoff_task(tmp_path, rel_path, "TASK-FPTC-OP-SEED")

        feature = Feature(
            id="FEAT-OPHANDOFF",
            name="Operator handoff fixture feature",
            description=(
                "Single-task feature whose only deliverable is an "
                "operator-handoff seeding step."
            ),
            tasks=[
                FeatureTask(
                    id="TASK-FPTC-OP-SEED",
                    name="Seed graphiti knowledge base",
                    file_path=Path(rel_path),
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[["TASK-FPTC-OP-SEED"]],
            ),
        )

        errors = FeatureLoader.validate_feature(feature, tmp_path)

        assert errors == [], (
            f"Expected validate_feature to return [] for an operator_handoff "
            f"task with runtime-shaped ACs, got: {errors}"
        )

    def test_validate_feature_does_not_parse_ac_content(
        self, tmp_path: Path
    ) -> None:
        """The validator does not surface AC-content errors.

        Pins the implementation note from TASK-FPTC-004:

            ``FeatureLoader._parse_feature`` may already accept tasks
            without enforcing AC presence — verify by reading the
            existing parser before assuming an edit is needed.

        We feed in a deliberately malformed AC block (empty bullets,
        inline ``[skip]`` markers) and confirm validate_feature still
        returns no errors.
        """
        rel_path = "tasks/in_progress/TASK-FPTC-OP-MALFORMED.md"
        task_file = tmp_path / rel_path
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(
            dedent(
                """\
                ---
                id: TASK-FPTC-OP-MALFORMED
                title: "Operator handoff with malformed ACs"
                status: backlog
                task_type: operator_handoff
                ---

                # Task: Operator handoff with malformed ACs

                ## Acceptance Criteria

                - [ ]
                - [ ] [skip] not a real AC
                - [x] runtime step already done
                """
            )
        )

        feature = Feature(
            id="FEAT-OPHANDOFF-MALFORMED",
            name="Operator handoff with malformed ACs",
            tasks=[
                FeatureTask(
                    id="TASK-FPTC-OP-MALFORMED",
                    file_path=Path(rel_path),
                ),
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[["TASK-FPTC-OP-MALFORMED"]],
            ),
        )

        errors = FeatureLoader.validate_feature(feature, tmp_path)

        # No AC-related errors: validator only checks structural metadata.
        assert errors == [], (
            "FeatureLoader.validate_feature must remain a no-op for AC "
            f"content, even when the AC block is malformed. Got: {errors}"
        )
