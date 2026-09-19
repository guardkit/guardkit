"""B9 acceptance corrections, Lane B (revision of 19 September 2026) — the
top-level ``scenario_owners:`` map.

WHY THE KEY MOVED. The first cut of this lane asked the plan writer for an
``owner_task:`` inside each ``scenarios:`` entry. Eight sessions with the real
local planner seat that afternoon showed why that could not work: on a FIRST
answer the planner writes no ``scenarios:`` map at all (0 of 4 with the rule in
its prompt, 0 of 2 without it). That map is minted LATER by the stamp normaliser,
from the approved feature files — so ownership carried inside it was written by
nobody at the moment it was supposed to be written, and a planner-written
``verifier:`` stamp would have outranked the normaliser's own rules.

Ownership therefore lives in its own top-level key the planner writes on its
first answer::

    scenario_owners:
      "<approved scenario title, verbatim>": TASK-XXXX-00N

GuardKit's part of that is small and is all that is pinned here:

* the ``Feature`` model carries the key instead of silently dropping it
  (``extra="ignore"`` means an unthreaded key is inert — how ``evidence_repos``
  was once inert);
* a value naming a task the feature does not contain is a LOUD load error, in
  the same voice as an unknown ``owner_task``;
* absent is allowed, so every feature written before the key existed loads
  unchanged;
* the keys are NOT compared with the ``.feature`` here — the plan-side check
  owns that, where the approved specification is in hand and a violation can
  still be repaired by one re-ask;
* the stamp normaliser's splice leaves the block alone, key for key and byte
  for byte, so ownership survives the round that mints ``scenarios:``;
* ``guardkit feature validate`` accepts a feature that declares it.

NEW file (edits no existing test).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureLoader,
    FeatureValidationError,
)
from guardkit.orchestrator.stamp_normalizer import write_stamps

_TITLE = "Requesting the report returns one row per day"
_OTHER = "Requesting the report with no data returns an empty list"


def _write_feature(
    tmp_path: Path,
    *,
    scenario_owners: dict | None = None,
    scenarios: dict | None = None,
    feature_id: str = "FEAT-DBE3",
) -> Path:
    """A minimal two-task feature whose task docs exist on disk."""
    features_dir = tmp_path / ".guardkit" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir = tmp_path / "tasks" / "backlog" / "daily-report"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    data: dict = {
        "id": feature_id,
        "name": "Daily report",
        "status": "planned",
        "tasks": [],
        "orchestration": {"parallel_groups": [["TASK-DBE3-002", "TASK-DBE3-003"]]},
    }
    if scenarios is not None:
        data["scenarios"] = scenarios
    if scenario_owners is not None:
        data["scenario_owners"] = scenario_owners
    for task_id, title in (
        ("TASK-DBE3-002", "Count the rows per day"),
        ("TASK-DBE3-003", "Add the report surface"),
    ):
        rel = f"tasks/backlog/daily-report/{task_id}.md"
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


# ---------------------------------------------------------------------------
# 1. The model carries the key
# ---------------------------------------------------------------------------


class TestTheModelCarriesTheKey:
    def test_scenario_owners_is_a_field_of_feature(self) -> None:
        assert "scenario_owners" in Feature.model_fields

    def test_it_defaults_to_empty(self) -> None:
        feature = Feature(id="FEAT-X", name="X")
        assert feature.scenario_owners == {}

    def test_a_non_mapping_is_refused_loudly(self) -> None:
        """NEGATIVE CONTROL: extra="ignore" would otherwise swallow it."""
        with pytest.raises(Exception) as exc:
            Feature(id="FEAT-X", name="X", scenario_owners=["TASK-X-001"])
        assert "scenario_owners" in str(exc.value)

    def test_an_empty_owner_value_is_refused(self) -> None:
        with pytest.raises(Exception) as exc:
            Feature(id="FEAT-X", name="X", scenario_owners={_TITLE: ""})
        assert "scenario_owners" in str(exc.value)

    def test_a_non_string_owner_value_is_refused(self) -> None:
        with pytest.raises(Exception) as exc:
            Feature(id="FEAT-X", name="X", scenario_owners={_TITLE: 3})
        assert "scenario_owners" in str(exc.value)


# ---------------------------------------------------------------------------
# 2. Loading
# ---------------------------------------------------------------------------


class TestFeatureLoaderAndTheOwnershipMap:
    def test_a_known_owner_loads_and_is_carried(self, tmp_path: Path) -> None:
        """POSITIVE CONTROL: the declared ownership survives the load."""
        features_dir = _write_feature(
            tmp_path, scenario_owners={_TITLE: "TASK-DBE3-003"}
        )
        feature = FeatureLoader.load_feature(
            "FEAT-DBE3", repo_root=tmp_path, features_dir=features_dir
        )
        assert feature.scenario_owners == {_TITLE: "TASK-DBE3-003"}

    def test_an_absent_map_still_loads(self, tmp_path: Path) -> None:
        """POSITIVE CONTROL: every feature written before the key existed."""
        features_dir = _write_feature(tmp_path)
        feature = FeatureLoader.load_feature(
            "FEAT-DBE3", repo_root=tmp_path, features_dir=features_dir
        )
        assert feature.scenario_owners == {}

    def test_an_owner_that_is_not_a_task_fails_the_load(self, tmp_path: Path) -> None:
        """NEGATIVE CONTROL: a typo'd owner leaves the scenario unowned behind a
        map that looks complete."""
        features_dir = _write_feature(
            tmp_path, scenario_owners={_TITLE: "TASK-DBE3-009"}
        )
        with pytest.raises(FeatureValidationError) as exc:
            FeatureLoader.load_feature(
                "FEAT-DBE3", repo_root=tmp_path, features_dir=features_dir
            )
        message = str(exc.value)
        assert "TASK-DBE3-009" in message
        assert _TITLE in message
        assert "TASK-DBE3-003" in message  # the tasks it could have named

    def test_a_title_the_feature_file_does_not_stamp_is_not_a_load_error(
        self, tmp_path: Path
    ) -> None:
        """The keys belong to the approved specification, not to guardkit: a
        title guardkit has never seen is the plan-side check's business, and by
        load time the repair round is gone."""
        features_dir = _write_feature(
            tmp_path,
            scenario_owners={_TITLE: "TASK-DBE3-003", _OTHER: "TASK-DBE3-003"},
        )
        feature = FeatureLoader.load_feature(
            "FEAT-DBE3", repo_root=tmp_path, features_dir=features_dir
        )
        assert set(feature.scenario_owners) == {_TITLE, _OTHER}

    def test_the_two_ownership_homes_coexist(self, tmp_path: Path) -> None:
        """A plan may still carry the stamp-level ``owner_task`` (nothing
        requires it any more); the top-level map is read either way."""
        features_dir = _write_feature(
            tmp_path,
            scenarios={_TITLE: {"verifier": "hurl", "owner_task": "TASK-DBE3-003"}},
            scenario_owners={_TITLE: "TASK-DBE3-003"},
        )
        feature = FeatureLoader.load_feature(
            "FEAT-DBE3", repo_root=tmp_path, features_dir=features_dir
        )
        assert feature.scenario_owners == {_TITLE: "TASK-DBE3-003"}
        assert feature.scenarios[_TITLE].owner_task == "TASK-DBE3-003"


# ---------------------------------------------------------------------------
# 3. Round trip through feature_to_dict
# ---------------------------------------------------------------------------


class TestSerialisation:
    def test_the_map_survives_feature_to_dict(self, tmp_path: Path) -> None:
        features_dir = _write_feature(
            tmp_path, scenario_owners={_TITLE: "TASK-DBE3-003"}
        )
        feature = FeatureLoader.load_feature(
            "FEAT-DBE3", repo_root=tmp_path, features_dir=features_dir
        )
        data = FeatureLoader._feature_to_dict(feature)
        assert data["scenario_owners"] == {_TITLE: "TASK-DBE3-003"}

    def test_an_empty_map_is_not_sprouted_into_every_file(
        self, tmp_path: Path
    ) -> None:
        """The missing-key-equals-empty law every other optional block follows."""
        features_dir = _write_feature(tmp_path)
        feature = FeatureLoader.load_feature(
            "FEAT-DBE3", repo_root=tmp_path, features_dir=features_dir
        )
        assert "scenario_owners" not in FeatureLoader._feature_to_dict(feature)


# ---------------------------------------------------------------------------
# 4. The stamp normaliser leaves it alone
# ---------------------------------------------------------------------------


_YAML_WITH_OWNERS = """id: FEAT-DBE3
name: Daily report
status: planned
scenario_owners:
  "Requesting the report returns one row per day": TASK-DBE3-003
  "Requesting the report with no data returns an empty list": TASK-DBE3-003
tasks:
  - id: TASK-DBE3-003
    title: Add the report surface
    file_path: tasks/backlog/daily-report/TASK-DBE3-003.md
"""


class TestTheStampNormaliserDoesNotDropIt:
    def test_the_block_survives_a_stamp_write_byte_for_byte(
        self, tmp_path: Path
    ) -> None:
        """THE ROUND THAT MATTERS: ``scenarios:`` is minted after the plan is
        written, so ownership has to come through that write untouched."""
        path = tmp_path / "FEAT-DBE3.yaml"
        path.write_text(_YAML_WITH_OWNERS, encoding="utf-8")

        write_stamps(path, {_TITLE: {"verifier": "hurl"}})

        after = path.read_text(encoding="utf-8")
        block_start = _YAML_WITH_OWNERS.index("scenario_owners:")
        block_end = _YAML_WITH_OWNERS.index("tasks:")
        block = _YAML_WITH_OWNERS[block_start:block_end]
        assert block in after, after

        parsed = yaml.safe_load(after)
        assert parsed["scenario_owners"] == {
            _TITLE: "TASK-DBE3-003",
            _OTHER: "TASK-DBE3-003",
        }
        assert parsed["scenarios"][_TITLE] == {"verifier": "hurl"}

    def test_a_file_with_no_owners_is_unchanged_in_that_respect(
        self, tmp_path: Path
    ) -> None:
        """POSITIVE CONTROL: the normaliser's existing behaviour is untouched."""
        path = tmp_path / "FEAT-DBE3.yaml"
        without = _YAML_WITH_OWNERS.replace(
            _YAML_WITH_OWNERS[
                _YAML_WITH_OWNERS.index("scenario_owners:") : _YAML_WITH_OWNERS.index(
                    "tasks:"
                )
            ],
            "",
        )
        path.write_text(without, encoding="utf-8")
        write_stamps(path, {_TITLE: {"verifier": "hurl"}})
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "scenario_owners" not in parsed
        assert parsed["scenarios"][_TITLE] == {"verifier": "hurl"}


# ---------------------------------------------------------------------------
# 5. `guardkit feature validate` accepts it
# ---------------------------------------------------------------------------


class TestTheValidateCommand:
    def test_feature_validate_accepts_a_declared_ownership_map(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from click.testing import CliRunner

        from guardkit.cli.feature import validate

        _write_feature(tmp_path, scenario_owners={_TITLE: "TASK-DBE3-003"})
        monkeypatch.chdir(tmp_path)
        result = CliRunner().invoke(validate, ["FEAT-DBE3", "--json"])
        assert result.exit_code == 0, result.output
        assert '"valid": true' in result.output

    def test_feature_validate_refuses_an_owner_that_is_not_a_task(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """NEGATIVE CONTROL through the SAME oracle forge's pre-commit runs.

        The command does not exit 0. It surfaces a load-time
        ``FeatureValidationError`` as an exception rather than a formatted
        error list — which is what it already does for a routing-law rejection
        and for an unknown ``owner_task``; this test pins the existing shape
        rather than changing it.
        """
        from click.testing import CliRunner

        from guardkit.cli.feature import validate

        _write_feature(tmp_path, scenario_owners={_TITLE: "TASK-DBE3-009"})
        monkeypatch.chdir(tmp_path)
        result = CliRunner().invoke(validate, ["FEAT-DBE3", "--json"])
        assert result.exit_code != 0
        assert isinstance(result.exception, FeatureValidationError)
        assert "TASK-DBE3-009" in str(result.exception)
