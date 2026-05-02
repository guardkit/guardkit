"""Contract tests for installer/core/commands/feature-plan.md prompt content.

These tests pin specific subsections in the /feature-plan prompt so they
cannot silently regress. The Plan agent reads this file at runtime; if a
required rule disappears, the agent loses it without warning. Pinning the
prompt content here is the cheapest way to catch that.

Currently pinned:

- TASK-FPSG-001 — "Path verification — REQUIRED" subsection sits above
  the smoke_gates "Non-goals" block, requires the agent to verify any
  path written into ``smoke_gates.command`` (or per-task notes) against
  the *target* repo's actual ``tests/`` tree before authoring, and
  references the TASK-REV-DEA8 forge incident by name.
- TASK-FPSG-001 (refinement, 2026-05-02) — same subsection also
  contains an ``after_wave`` temporal-sequencing rule citing the
  study-tutor FEAT-FD32 Run 2 chicken-and-egg incident
  (TASK-GR-SMOK / AC-SMOK-01).
"""

from pathlib import Path

import pytest


_PROMPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "installer"
    / "core"
    / "commands"
    / "feature-plan.md"
)


@pytest.fixture(scope="module")
def prompt_text() -> str:
    assert _PROMPT_PATH.exists(), (
        f"Expected /feature-plan prompt at {_PROMPT_PATH}; not found"
    )
    return _PROMPT_PATH.read_text(encoding="utf-8")


class TestPathVerificationRule:
    """TASK-FPSG-001 — smoke-gate path verification rule."""

    def test_subsection_heading_present(self, prompt_text: str) -> None:
        assert "**Path verification — REQUIRED before authoring.**" in prompt_text, (
            "Path verification subsection heading missing from /feature-plan "
            "prompt — see TASK-FPSG-001"
        )

    def test_must_verify_language_present(self, prompt_text: str) -> None:
        # Either spelling — "MUST be verified" or "MUST verify" — counts
        # as the load-bearing imperative the AC asks for.
        assert (
            "MUST be verified" in prompt_text
            or "MUST verify" in prompt_text
        ), (
            "Path-verification rule must contain a verbatim 'MUST be "
            "verified' / 'MUST verify' imperative — see TASK-FPSG-001"
        )

    def test_references_prior_incident(self, prompt_text: str) -> None:
        assert "TASK-REV-DEA8" in prompt_text, (
            "Path-verification rule must reference TASK-REV-DEA8 by name "
            "as the prior incident — see TASK-FPSG-001"
        )

    def test_subsection_sits_above_smoke_gates_non_goals(
        self, prompt_text: str
    ) -> None:
        # Anchor on the smoke-gates Non-goals block specifically (the prompt
        # contains other "Non-goals" sections for unrelated steps). The
        # canonical anchor inside that block is the "do not auto-generate
        # smoke-gate commands" line.
        heading = "**Path verification — REQUIRED before authoring.**"
        smoke_gates_anchor = "Do not auto-generate smoke-gate commands."
        h_idx = prompt_text.find(heading)
        anchor_idx = prompt_text.find(smoke_gates_anchor)
        assert h_idx != -1, "Path-verification heading not found"
        assert anchor_idx != -1, (
            "smoke_gates non-goals anchor 'Do not auto-generate smoke-gate "
            "commands.' not found"
        )
        assert h_idx < anchor_idx, (
            "Path-verification subsection must appear ABOVE the smoke_gates "
            "'Non-goals' block (TASK-FPSG-001 AC)"
        )
        # And it should be a co-located rule, not on the other side of the
        # file — pin to within a reasonable proximity (a few KB).
        assert anchor_idx - h_idx < 4000, (
            "Path-verification subsection should sit immediately above the "
            "smoke_gates 'Non-goals' block, not elsewhere in the prompt"
        )

    def test_temporal_sequencing_rule_present(self, prompt_text: str) -> None:
        # TASK-FPSG-001 refinement: the same subsection must also pin the
        # after_wave temporal-sequencing rule (Class B — does the path
        # exist by the time the gate fires?), not just the spatial Class A
        # rule (does the path exist now?).
        assert (
            "`after_wave` temporal-sequencing — REQUIRED" in prompt_text
        ), (
            "Path-verification subsection must pin an "
            "'`after_wave` temporal-sequencing — REQUIRED' rule heading "
            "(TASK-FPSG-001 refinement)"
        )

    def test_temporal_sequencing_must_be_ge_creating_wave(
        self, prompt_text: str
    ) -> None:
        # The load-bearing constraint: after_wave must be >= the wave
        # that creates the path. Pin the imperative wording.
        assert "must be ≥ that creation task's wave" in prompt_text, (
            "Temporal-sequencing rule must state the after_wave >= "
            "creating-wave constraint verbatim (TASK-FPSG-001 refinement)"
        )

    def test_temporal_sequencing_references_feat_fd32(
        self, prompt_text: str
    ) -> None:
        # The rule cites a concrete prior incident, same shape as the
        # Class A rule citing TASK-REV-DEA8.
        for marker in ("FEAT-FD32", "TASK-GR-SMOK", "AC-SMOK-01"):
            assert marker in prompt_text, (
                f"Temporal-sequencing rule must reference {marker!r} as "
                "the prior incident (TASK-FPSG-001 refinement)"
            )

    def test_temporal_sequencing_sits_inside_path_verification_subsection(
        self, prompt_text: str
    ) -> None:
        # The temporal rule must be co-located inside the existing
        # "Path verification — REQUIRED" subsection, not floating
        # elsewhere in the prompt.
        path_heading = "**Path verification — REQUIRED before authoring.**"
        temporal_heading = "**`after_wave` temporal-sequencing — REQUIRED.**"
        smoke_gates_anchor = "Do not auto-generate smoke-gate commands."
        path_idx = prompt_text.find(path_heading)
        temporal_idx = prompt_text.find(temporal_heading)
        anchor_idx = prompt_text.find(smoke_gates_anchor)
        assert path_idx != -1, "Path-verification heading not found"
        assert temporal_idx != -1, "Temporal-sequencing heading not found"
        assert anchor_idx != -1, "smoke_gates non-goals anchor not found"
        assert path_idx < temporal_idx < anchor_idx, (
            "Temporal-sequencing rule must sit BETWEEN the "
            "'Path verification' heading and the smoke_gates 'Non-goals' "
            "block (TASK-FPSG-001 refinement)"
        )

    def test_canonical_smoke_gates_schema_unchanged(self, prompt_text: str) -> None:
        # AC: "Schema reference unchanged — the canonical smoke_gates
        # schema example block remains exactly as-is". Pin the load-bearing
        # lines so a future edit can't quietly drift the schema.
        for fragment in (
            "smoke_gates:",
            "after_wave: [2, 3]",
            "pytest tests/smoke -x",
            "expected_exit: 0",
            "timeout: 120",
        ):
            assert fragment in prompt_text, (
                f"Canonical smoke_gates schema fragment missing: {fragment!r}"
            )
