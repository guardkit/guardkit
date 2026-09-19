"""A malformed assumptions manifest is visible in the Coach's warnings.

B9 (2026-09-19). The assumptions producer now names every manifest it could
not read or parse in ``malformed``. Before this consumer change a
malformed-only scan returned no issue at all, so the unreadable manifest was
invisible to the person reviewing the build. Warn-mode is kept on purpose:
these are warnings, never a block.
"""

from __future__ import annotations

from pathlib import Path

from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


def _validator(tmp_path: Path) -> CoachValidator:
    return CoachValidator(str(tmp_path), task_id="TASK-B9-MALFORMED")


def test_a_malformed_only_scan_is_a_visible_warning(tmp_path: Path) -> None:
    issues = _validator(tmp_path)._check_unconfirmed_assumptions(
        {
            "unconfirmed_low_confidence_assumptions": {
                "status": "warning",
                "unconfirmed": [],
                "malformed": ["features/orders/orders_assumptions.yaml"],
                "files_scanned": 1,
                "files_skipped": 1,
            }
        }
    )
    assert len(issues) == 1
    issue = issues[0]
    assert issue["severity"] == "warning"
    assert issue["category"] == "malformed_assumptions_manifest"
    assert "features/orders/orders_assumptions.yaml" in issue["description"]
    assert issue["details"]["malformed"] == ["features/orders/orders_assumptions.yaml"]


def test_unconfirmed_rows_and_a_malformed_file_are_both_reported(tmp_path: Path) -> None:
    issues = _validator(tmp_path)._check_unconfirmed_assumptions(
        {
            "unconfirmed_low_confidence_assumptions": {
                "status": "warning",
                "unconfirmed": [
                    {
                        "file": "features/a/a_assumptions.yaml",
                        "id": "ASSUM-001",
                        "scenario": "s",
                        "assumption": "a",
                        "human_response": "deferred",
                    }
                ],
                "malformed": ["features/b/b_assumptions.yaml"],
                "files_scanned": 2,
            }
        }
    )
    categories = sorted(issue["category"] for issue in issues)
    assert categories == [
        "malformed_assumptions_manifest",
        "unconfirmed_low_confidence_assumptions",
    ]
    assert all(issue["severity"] == "warning" for issue in issues)


def test_a_clean_scan_and_an_old_block_shape_stay_silent(tmp_path: Path) -> None:
    validator = _validator(tmp_path)
    assert validator._check_unconfirmed_assumptions(
        {"unconfirmed_low_confidence_assumptions": {"status": "ok", "unconfirmed": [], "malformed": []}}
    ) == []
    # A block written before the producer knew the word "malformed".
    assert validator._check_unconfirmed_assumptions(
        {"unconfirmed_low_confidence_assumptions": {"status": "warning", "unconfirmed": []}}
    ) == []
