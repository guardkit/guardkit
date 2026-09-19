"""B9 corrections, Lane B (guardkit half) — 19 September 2026.

Two gaps this file pins, both measured on the B9 build:

1. ``assumption_confidence_checker`` globbed the LITERAL name
   ``_assumptions.yaml``. The specification writer emits the SLUGGED name
   (``user-creation-analytics_assumptions.yaml``), so every manifest the
   factory actually wrote was scanned zero times and the gate reported a
   clean ``files_scanned: 0`` over a directory full of unconfirmed rows. A
   file nobody can read is now named in ``malformed`` instead of vanishing
   into a skipped count.

2. A scenario had no owner. Five tasks each passed their own checks while
   the endpoint the person asked for was wrong, because a correct helper and
   a wrong route both counted as done. ``ScenarioStamp.owner_task`` says
   which task owes the promise at the surface the person uses, and the
   loader refuses a value naming a task the feature does not contain.

NEW file (edits no existing test).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from guardkit.orchestrator.feature_loader import (
    FeatureLoader,
    FeatureValidationError,
)
from guardkit.orchestrator.quality_gates.assumption_confidence_checker import (
    check_unconfirmed_low_confidence_assumptions,
)
from guardkit.orchestrator.verifier_stamp import (
    ScenarioStamp,
    parse_scenario_stamp,
)


# ---------------------------------------------------------------------------
# 1. Assumptions discovery
# ---------------------------------------------------------------------------

_UNCONFIRMED_ROWS = """\
assumptions:
  - id: ASSUM-001
    scenario: Requesting the last 7 days returns exactly 7 entries
    assumption: The window ends yesterday
    confidence: low
    basis: not stated in input
    human_response: deferred
"""

_CONFIRMED_ROWS = """\
assumptions:
  - id: ASSUM-001
    scenario: Requesting the last 7 days returns exactly 7 entries
    assumption: The window ends yesterday
    confidence: low
    basis: not stated in input
    human_response: confirmed
"""


def _write(root: Path, rel: str, body: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


class TestAssumptionsDiscoveryGlob:
    def test_the_slugged_manifest_the_writer_actually_emits_is_found(
        self, tmp_path: Path
    ) -> None:
        """THE B9 DEFECT. The literal-name glob scanned this file zero times."""
        _write(
            tmp_path,
            "features/user-creation-analytics/"
            "user-creation-analytics_assumptions.yaml",
            _UNCONFIRMED_ROWS,
        )
        block = check_unconfirmed_low_confidence_assumptions(tmp_path)

        assert block["files_scanned"] == 1
        assert block["status"] == "warning"
        assert [row["id"] for row in block["unconfirmed"]] == ["ASSUM-001"]
        assert block["unconfirmed"][0]["file"].endswith(
            "user-creation-analytics_assumptions.yaml"
        )
        assert block["malformed"] == []

    def test_the_literal_name_still_matches(self, tmp_path: Path) -> None:
        """POSITIVE CONTROL: the name feature-spec.md declares is unchanged."""
        _write(
            tmp_path, "features/doc-upload/_assumptions.yaml", _UNCONFIRMED_ROWS
        )
        block = check_unconfirmed_low_confidence_assumptions(tmp_path)

        assert block["files_scanned"] == 1
        assert block["status"] == "warning"
        assert [row["id"] for row in block["unconfirmed"]] == ["ASSUM-001"]

    def test_a_confirmed_slugged_manifest_is_scanned_and_stays_ok(
        self, tmp_path: Path
    ) -> None:
        """POSITIVE CONTROL: finding the file must not invent a warning."""
        _write(
            tmp_path,
            "features/user-creation-analytics/"
            "user-creation-analytics_assumptions.yaml",
            _CONFIRMED_ROWS,
        )
        block = check_unconfirmed_low_confidence_assumptions(tmp_path)

        assert block["files_scanned"] == 1
        assert block["status"] == "ok"
        assert block["unconfirmed"] == []
        assert block["malformed"] == []

    def test_a_malformed_manifest_is_named_not_silently_skipped(
        self, tmp_path: Path
    ) -> None:
        """NEGATIVE CONTROL: unreadable is not the same as empty."""
        _write(
            tmp_path,
            "features/broken/broken_assumptions.yaml",
            "assumptions: [oh dear\n  - not: yaml\n",
        )
        block = check_unconfirmed_low_confidence_assumptions(tmp_path)

        assert block["status"] == "warning"
        assert block["files_scanned"] == 1
        assert block["files_skipped"] == 1
        assert block["malformed"] == ["features/broken/broken_assumptions.yaml"]
        assert block["unconfirmed"] == []

    def test_a_manifest_that_is_not_a_mapping_is_malformed_too(
        self, tmp_path: Path
    ) -> None:
        _write(
            tmp_path, "features/broken/list_assumptions.yaml", "- just\n- a list\n"
        )
        block = check_unconfirmed_low_confidence_assumptions(tmp_path)

        assert block["status"] == "warning"
        assert block["malformed"] == ["features/broken/list_assumptions.yaml"]

    def test_a_missing_features_directory_is_unchanged(
        self, tmp_path: Path
    ) -> None:
        """POSITIVE CONTROL: tasks that never touch features/ see no gate."""
        block = check_unconfirmed_low_confidence_assumptions(tmp_path)

        assert block["status"] == "ok"
        assert block["files_scanned"] == 0
        assert block["files_skipped"] == 0
        assert block["malformed"] == []
        assert block["unconfirmed"] == []

    def test_an_unrelated_yaml_beside_the_manifest_is_not_scanned(
        self, tmp_path: Path
    ) -> None:
        """The glob widened to the slug, not to every YAML under features/."""
        _write(
            tmp_path,
            "features/user-creation-analytics/"
            "user-creation-analytics_digest.yaml",
            _UNCONFIRMED_ROWS,
        )
        block = check_unconfirmed_low_confidence_assumptions(tmp_path)

        assert block["files_scanned"] == 0
        assert block["status"] == "ok"


# ---------------------------------------------------------------------------
# 2. Delivery ownership — ScenarioStamp.owner_task
# ---------------------------------------------------------------------------

_TITLE = "Requesting the last 7 days of user creation counts returns 7 entries"


class TestScenarioStampOwnerTask:
    def test_owner_task_is_accepted_on_a_stamp(self) -> None:
        stamp = parse_scenario_stamp(
            {"verifier": "hurl", "owner_task": "TASK-DBE3-003"}, scenario=_TITLE
        )
        assert stamp.owner_task == "TASK-DBE3-003"

    def test_owner_task_is_absent_by_default(self) -> None:
        assert ScenarioStamp(verifier="hurl").owner_task is None

    def test_an_unknown_key_is_still_rejected_and_the_message_lists_the_field(
        self,
    ) -> None:
        with pytest.raises(ValueError) as exc:
            parse_scenario_stamp(
                {"verifier": "hurl", "owner_tsak": "TASK-DBE3-003"},
                scenario=_TITLE,
            )
        assert "owner_task" in str(exc.value)

    def test_a_blank_owner_task_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            parse_scenario_stamp({"verifier": "hurl", "owner_task": ""})


def _write_feature(
    tmp_path: Path, scenarios: dict, *, feature_id: str = "FEAT-DBE3"
) -> Path:
    """A minimal two-task feature whose task docs exist on disk."""
    features_dir = tmp_path / ".guardkit" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir = tmp_path / "tasks" / "backlog" / "user-creation-analytics"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "id": feature_id,
        "name": "User creation analytics",
        "status": "planned",
        "tasks": [],
        "orchestration": {"parallel_groups": [["TASK-DBE3-002", "TASK-DBE3-003"]]},
        "scenarios": scenarios,
    }
    for task_id, title in (
        ("TASK-DBE3-002", "Implement analytics crud"),
        ("TASK-DBE3-003", "Add analytics router and endpoint"),
    ):
        rel = f"tasks/backlog/user-creation-analytics/{task_id}.md"
        (tmp_path / rel).write_text(f"# {title}\n", encoding="utf-8")
        data["tasks"].append(
            {
                "id": task_id,
                "title": title,
                "file_path": rel,
                "status": "pending",
                "complexity": 3,
            }
        )
    (features_dir / f"{feature_id}.yaml").write_text(
        yaml.safe_dump(data, sort_keys=False), encoding="utf-8"
    )
    return features_dir


class TestFeatureLoaderRefusesAnUnknownOwner:
    def test_an_owner_task_that_is_not_in_the_feature_fails_the_load(
        self, tmp_path: Path
    ) -> None:
        """NEGATIVE CONTROL: a scenario owned by a task that does not exist."""
        features_dir = _write_feature(
            tmp_path,
            {_TITLE: {"verifier": "hurl", "owner_task": "TASK-DBE3-009"}},
        )
        with pytest.raises(FeatureValidationError) as exc:
            FeatureLoader.load_feature(
                "FEAT-DBE3", repo_root=tmp_path, features_dir=features_dir
            )
        message = str(exc.value)
        assert "TASK-DBE3-009" in message
        assert _TITLE in message
        assert "TASK-DBE3-003" in message  # the tasks it could have named

    def test_a_known_owner_task_loads(self, tmp_path: Path) -> None:
        """POSITIVE CONTROL: the ownership that IS declared is carried."""
        features_dir = _write_feature(
            tmp_path,
            {_TITLE: {"verifier": "hurl", "owner_task": "TASK-DBE3-003"}},
        )
        feature = FeatureLoader.load_feature(
            "FEAT-DBE3", repo_root=tmp_path, features_dir=features_dir
        )
        assert feature.scenarios[_TITLE].owner_task == "TASK-DBE3-003"

    def test_an_absent_owner_task_still_loads(self, tmp_path: Path) -> None:
        """POSITIVE CONTROL: every historical feature loads unchanged."""
        features_dir = _write_feature(tmp_path, {_TITLE: {"verifier": "hurl"}})
        feature = FeatureLoader.load_feature(
            "FEAT-DBE3", repo_root=tmp_path, features_dir=features_dir
        )
        assert feature.scenarios[_TITLE].owner_task is None

    def test_the_bare_string_shorthand_still_loads(self, tmp_path: Path) -> None:
        features_dir = _write_feature(tmp_path, {_TITLE: "hurl"})
        feature = FeatureLoader.load_feature(
            "FEAT-DBE3", repo_root=tmp_path, features_dir=features_dir
        )
        assert feature.scenarios[_TITLE].verifier == "hurl"
        assert feature.scenarios[_TITLE].owner_task is None
