"""Two tasks that would work on the same area of the repository do not run
at the same time.

Why this rule exists (build ``build-FEAT-3EF3-20260911171802``, 2026-09-11):
one plan put "add the statistics schema" and "implement the statistics query"
into ONE wave. They ran together, which put the coach on its isolated-snapshot
path; that path could not start the repository's test command at all, so the
coder was told five turns running that its tests produced no signal, and while
chasing that it deleted two working functions from a module the schema task had
never mentioned. 79 tests of shipped behaviour went with them.

Two things this file is careful about:

* The rule reads DECLARED PATHS ONLY — it never opens a source file and never
  names a language. The cases below are written with TypeScript-shaped and
  Go-shaped paths as well as Python-shaped ones, so the suite itself proves
  nothing here is Python-shaped.
* The banner an operator reads must show the number the executor enforces. A
  banner that says two while one runs is how an operator learns to distrust
  the log.
"""

from __future__ import annotations

import json
import re
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from rich.console import Console

from guardkit.cli.display import WaveProgressDisplay
from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
from guardkit.orchestrator.parallel_strategy import (
    SAME_AREA_DEFAULT,
    SAME_AREA_ENV_VAR,
    SAME_AREA_OFF,
    SAME_AREA_POLICIES,
    SAME_AREA_SEQUENCE_ON_DECLARED_OVERLAP,
    SAME_AREA_SEQUENCE_WHEN_UNSURE,
    MaxParallelMode,
    ParallelConfig,
    collect_wave_task_paths,
    find_same_area_conflict,
    resolve_max_parallel,
    same_area_policy_from_env,
)


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", text)


def _config(static_value=4, same_area=SAME_AREA_DEFAULT, mode=MaxParallelMode.STATIC):
    return ParallelConfig(mode=mode, static_value=static_value, same_area=same_area)


# ============================================================================
# 1. The rule itself, in three languages' worth of path shapes
# ============================================================================


class TestSameFileSequencesTheWave:
    """Two tasks naming the same file run one at a time."""

    def test_typescript_same_file(self):
        decision = find_same_area_conflict(
            {
                "TASK-ROUTE-001": ["src/users/router.ts"],
                "TASK-ROUTE-002": ["src/users/router.ts"],
            }
        )
        assert decision.sequence is True
        assert "TASK-ROUTE-001" in decision.reason
        assert "TASK-ROUTE-002" in decision.reason
        assert "src/users/router.ts" in decision.reason

    def test_go_same_file(self):
        decision = find_same_area_conflict(
            {
                "TASK-GO-001": ["internal/users/crud.go"],
                "TASK-GO-002": ["internal/users/crud.go", "cmd/api/main.go"],
            }
        )
        assert decision.sequence is True
        assert "internal/users/crud.go" in decision.reason

    def test_python_same_file_is_the_observed_failure(self):
        decision = find_same_area_conflict(
            {
                "TASK-STAT-002": ["src/users/schemas.py", "src/users/crud.py"],
                "TASK-STAT-003": ["src/users/crud.py"],
            }
        )
        assert decision.sequence is True
        assert "src/users/crud.py" in decision.reason

    def test_resolver_returns_one(self):
        resolved = resolve_max_parallel(
            _config(static_value=4),
            wave_number=2,
            wave_size=2,
            wave_task_paths={
                "TASK-A": ["src/users/router.ts"],
                "TASK-B": ["src/users/router.ts"],
            },
        )
        assert resolved == 1

    def test_the_sentence_is_logged_once(self, caplog):
        with caplog.at_level("INFO"):
            resolve_max_parallel(
                _config(),
                wave_number=3,
                wave_size=2,
                wave_task_paths={
                    "TASK-A": ["internal/users/crud.go"],
                    "TASK-B": ["internal/users/crud.go"],
                },
            )
        messages = [r.getMessage() for r in caplog.records]
        assert any(
            "Wave 3" in m
            and "TASK-A and TASK-B" in m
            and "internal/users/crud.go" in m
            for m in messages
        ), messages

    def test_read_only_resolution_logs_nothing(self, caplog):
        with caplog.at_level("INFO"):
            resolve_max_parallel(
                _config(),
                wave_number=3,
                wave_size=2,
                log=False,
                wave_task_paths={
                    "TASK-A": ["src/users/router.ts"],
                    "TASK-B": ["src/users/router.ts"],
                },
            )
        assert not [r for r in caplog.records if "Wave 3" in r.getMessage()]


class TestSameDirectorySequencesTheWave:
    """A module is an area, not just a file: neighbouring files count."""

    def test_typescript_neighbouring_files(self):
        decision = find_same_area_conflict(
            {
                "TASK-TS-001": ["src/users/router.ts"],
                "TASK-TS-002": ["src/users/schemas.ts"],
            }
        )
        assert decision.sequence is True
        assert "src/users" in decision.reason

    def test_go_neighbouring_files(self):
        decision = find_same_area_conflict(
            {
                "TASK-GO-001": ["internal/users/crud.go"],
                "TASK-GO-002": ["internal/users/handler.go"],
            }
        )
        assert decision.sequence is True
        assert "internal/users" in decision.reason

    def test_resolver_returns_one(self):
        assert (
            resolve_max_parallel(
                _config(static_value=None),
                wave_size=2,
                wave_task_paths={
                    "TASK-A": ["src/users/schemas.py"],
                    "TASK-B": ["src/users/crud.py"],
                },
            )
            == 1
        )

    def test_two_top_level_files_share_the_repository_root(self):
        decision = find_same_area_conflict(
            {"TASK-A": ["package.json"], "TASK-B": ["tsconfig.json"]}
        )
        assert decision.sequence is True
        assert "repository root" in decision.reason


class TestDifferentAreasRunTogether:
    """Other waves are unaffected."""

    def test_typescript_different_directories(self):
        decision = find_same_area_conflict(
            {
                "TASK-TS-001": ["src/users/router.ts"],
                "TASK-TS-002": ["src/billing/router.ts"],
            }
        )
        assert decision.sequence is False
        assert decision.reason == ""

    def test_go_different_directories(self):
        decision = find_same_area_conflict(
            {
                "TASK-GO-001": ["internal/users/crud.go"],
                "TASK-GO-002": ["internal/billing/crud.go"],
            }
        )
        assert decision.sequence is False

    def test_nested_directory_is_not_its_parent(self):
        """``src/users/admin/x.ts`` is not the same area as ``src/users/y.ts``
        — the rule compares the IMMEDIATE parent only."""
        decision = find_same_area_conflict(
            {
                "TASK-A": ["src/users/admin/x.ts"],
                "TASK-B": ["src/users/y.ts"],
            }
        )
        assert decision.sequence is False

    def test_resolver_leaves_the_wave_alone(self):
        assert (
            resolve_max_parallel(
                _config(static_value=4),
                wave_size=2,
                wave_task_paths={
                    "TASK-A": ["internal/users/crud.go"],
                    "TASK-B": ["internal/billing/crud.go"],
                },
            )
            == 4
        )

    def test_unlimited_stays_unlimited(self):
        assert (
            resolve_max_parallel(
                _config(static_value=None),
                wave_size=2,
                wave_task_paths={
                    "TASK-A": ["src/a/one.ts"],
                    "TASK-B": ["src/b/two.ts"],
                },
            )
            is None
        )


class TestADeclaredDirectoryIsAnArea:
    """A task may name a whole directory instead of a file — a plan that says
    ``files_to_modify: - src/users/`` is an ordinary thing for a model to
    write. The trailing slash is the only signal that the entry means a
    directory, so it is kept and the directory is treated as the area. No
    extension is ever inspected, so this is language-free like the rest."""

    def test_typescript_directory_and_a_file_inside_it_sequence(self):
        decision = find_same_area_conflict(
            {"TASK-A": ["src/users/"], "TASK-B": ["src/users/crud.ts"]}
        )
        assert decision.sequence is True
        assert "src/users" in decision.reason

    def test_go_directory_and_a_file_inside_it_sequence(self):
        decision = find_same_area_conflict(
            {"TASK-A": ["internal/users/"], "TASK-B": ["internal/users/handler.go"]}
        )
        assert decision.sequence is True
        assert "internal/users" in decision.reason

    def test_a_file_deeper_inside_the_claimed_directory_sequences(self):
        """A directory claim covers everything beneath it, however deep — the
        task said it would work in there."""
        decision = find_same_area_conflict(
            {"TASK-A": ["src/users/"], "TASK-B": ["src/users/admin/handler.ts"]}
        )
        assert decision.sequence is True
        assert "src/users" in decision.reason

    def test_the_same_directory_twice_sequences_and_reads_as_an_area(self):
        decision = find_same_area_conflict(
            {"TASK-A": ["internal/users/"], "TASK-B": ["internal/users/"]}
        )
        assert decision.sequence is True
        assert "both work on files in internal/users" in decision.reason

    def test_a_directory_inside_another_claimed_directory_sequences(self):
        decision = find_same_area_conflict(
            {"TASK-A": ["src/"], "TASK-B": ["src/users/"]}
        )
        assert decision.sequence is True
        assert "both work on files in src" in decision.reason

    def test_sibling_directories_run_together(self):
        decision = find_same_area_conflict(
            {"TASK-A": ["src/users/"], "TASK-B": ["src/billing/"]}
        )
        assert decision.sequence is False

    def test_a_directory_and_a_file_outside_it_run_together(self):
        decision = find_same_area_conflict(
            {"TASK-A": ["src/users/"], "TASK-B": ["internal/billing/crud.go"]}
        )
        assert decision.sequence is False

    def test_a_directory_written_with_backslashes_is_still_a_directory(self):
        decision = find_same_area_conflict(
            {"TASK-A": ["src\\users\\"], "TASK-B": ["src/users/crud.ts"]}
        )
        assert decision.sequence is True
        assert "src/users" in decision.reason

    def test_resolver_returns_one_for_a_claimed_directory(self):
        assert (
            resolve_max_parallel(
                _config(static_value=4),
                wave_size=2,
                wave_task_paths={
                    "TASK-A": ["src/users/"],
                    "TASK-B": ["src/users/crud.ts"],
                },
            )
            == 1
        )

    def test_the_relaxed_setting_still_sequences_a_claimed_directory(self):
        decision = find_same_area_conflict(
            {"TASK-A": ["internal/users/"], "TASK-B": ["internal/users/crud.go"]},
            policy=SAME_AREA_SEQUENCE_ON_DECLARED_OVERLAP,
        )
        assert decision.sequence is True


class TestPathShapesAreNormalisedBeforeComparing:
    def test_leading_dot_slash_and_backslashes_still_match(self):
        decision = find_same_area_conflict(
            {
                "TASK-A": ["./src/users/router.ts"],
                "TASK-B": ["src\\users\\router.ts"],
            }
        )
        assert decision.sequence is True

    def test_backticks_are_stripped(self):
        decision = find_same_area_conflict(
            {"TASK-A": ["`internal/users/crud.go`"], "TASK-B": ["internal/users/crud.go"]}
        )
        assert decision.sequence is True

    def test_unusable_entries_count_as_nothing_declared(self):
        """A task whose only "paths" are junk has declared nothing, so the
        default sequences the wave rather than reading it as no overlap."""
        decision = find_same_area_conflict(
            {"TASK-A": ["   ", None], "TASK-B": ["src/billing/router.ts"]}
        )
        assert decision.sequence is True
        assert "TASK-A does not say" in decision.reason


# ============================================================================
# 2. When nothing is declared, fail safe
# ============================================================================


class TestNothingDeclaredFailsSafe:
    def test_default_sequences_the_wave(self):
        decision = find_same_area_conflict(
            {"TASK-A": None, "TASK-B": ["src/billing/router.ts"]}
        )
        assert decision.sequence is True
        assert "TASK-A does not say" in decision.reason

    def test_default_names_every_silent_task(self):
        decision = find_same_area_conflict({"TASK-A": None, "TASK-B": None})
        assert decision.sequence is True
        assert "TASK-A" in decision.reason and "TASK-B" in decision.reason

    def test_relaxed_setting_lets_undeclared_tasks_run_together(self):
        decision = find_same_area_conflict(
            {"TASK-A": None, "TASK-B": ["src/billing/router.ts"]},
            policy=SAME_AREA_SEQUENCE_ON_DECLARED_OVERLAP,
        )
        assert decision.sequence is False

    def test_relaxed_setting_still_sequences_a_declared_overlap(self):
        decision = find_same_area_conflict(
            {
                "TASK-A": None,
                "TASK-B": ["internal/users/crud.go"],
                "TASK-C": ["internal/users/handler.go"],
            },
            policy=SAME_AREA_SEQUENCE_ON_DECLARED_OVERLAP,
        )
        assert decision.sequence is True
        assert "internal/users" in decision.reason

    def test_resolver_sequences_under_the_default(self):
        assert (
            resolve_max_parallel(
                _config(static_value=4),
                wave_size=2,
                wave_task_paths={"TASK-A": None, "TASK-B": None},
            )
            == 1
        )

    def test_resolver_does_not_sequence_under_the_relaxed_setting(self):
        assert (
            resolve_max_parallel(
                _config(static_value=4, same_area=SAME_AREA_SEQUENCE_ON_DECLARED_OVERLAP),
                wave_size=2,
                wave_task_paths={"TASK-A": None, "TASK-B": None},
            )
            == 4
        )

    def test_no_mapping_at_all_leaves_todays_behaviour_unchanged(self):
        """A caller that passes nothing gets today's behaviour, because a
        one-entry-per-task mapping is how the wave is described."""
        assert (
            resolve_max_parallel(_config(static_value=4), wave_size=2) == 4
        )


# ============================================================================
# 3. The setting: three plain words, read from the environment
# ============================================================================


class TestTheSetting:
    def test_the_three_values_are_plain_words(self):
        assert SAME_AREA_POLICIES == (
            "sequence-when-unsure",
            "sequence-on-declared-overlap",
            "off",
        )
        assert SAME_AREA_DEFAULT == SAME_AREA_SEQUENCE_WHEN_UNSURE

    def test_unset_gives_the_safe_default(self):
        assert same_area_policy_from_env({}) == SAME_AREA_SEQUENCE_WHEN_UNSURE

    @pytest.mark.parametrize("value", SAME_AREA_POLICIES)
    def test_each_value_is_read(self, value):
        assert same_area_policy_from_env({SAME_AREA_ENV_VAR: value}) == value

    def test_case_and_spaces_are_forgiven(self):
        assert (
            same_area_policy_from_env({SAME_AREA_ENV_VAR: "  OFF "}) == SAME_AREA_OFF
        )

    def test_an_unrecognised_value_falls_back_and_says_so(self, caplog):
        with caplog.at_level("WARNING"):
            got = same_area_policy_from_env({SAME_AREA_ENV_VAR: "maybe"})
        assert got == SAME_AREA_DEFAULT
        assert any("maybe" in r.getMessage() for r in caplog.records)

    def test_config_reads_the_environment_the_way_it_reads_the_others(
        self, monkeypatch
    ):
        monkeypatch.setenv(SAME_AREA_ENV_VAR, SAME_AREA_OFF)
        assert ParallelConfig().same_area == SAME_AREA_OFF
        assert ParallelConfig.from_legacy(2).same_area == SAME_AREA_OFF

    def test_config_default_when_the_environment_is_silent(self, monkeypatch):
        monkeypatch.delenv(SAME_AREA_ENV_VAR, raising=False)
        assert ParallelConfig().same_area == SAME_AREA_DEFAULT


class TestRuleOffRestoresTodaysBehaviour:
    @pytest.mark.parametrize(
        "paths",
        [
            {"TASK-A": ["src/users/router.ts"], "TASK-B": ["src/users/router.ts"]},
            {"TASK-A": ["internal/users/crud.go"], "TASK-B": ["internal/users/x.go"]},
            {"TASK-A": None, "TASK-B": None},
        ],
    )
    def test_off_resolves_exactly_what_it_resolved_before(self, paths):
        config = _config(static_value=3, same_area=SAME_AREA_OFF)
        assert resolve_max_parallel(config, wave_size=2, wave_task_paths=paths) == 3
        # "exactly what it resolved before" = the same answer the resolver
        # gives when it is told nothing about the wave's tasks at all.
        assert resolve_max_parallel(config, wave_size=2) == 3

    def test_off_leaves_unlimited_unlimited(self):
        config = _config(static_value=None, same_area=SAME_AREA_OFF)
        assert (
            resolve_max_parallel(
                config,
                wave_size=2,
                wave_task_paths={"TASK-A": None, "TASK-B": None},
            )
            is None
        )


class TestWavesTheRuleDoesNotTouch:
    def test_a_one_task_wave_is_untouched(self):
        assert find_same_area_conflict({"TASK-ALONE": None}).sequence is False
        assert (
            resolve_max_parallel(
                _config(static_value=4),
                wave_size=1,
                wave_task_paths={"TASK-ALONE": None},
            )
            == 4
        )

    def test_an_empty_wave_is_untouched(self):
        assert find_same_area_conflict({}).sequence is False


class TestPerWaveOverrideStillWins:
    def test_override_beats_a_declared_overlap(self):
        config = _config(static_value=1, mode=MaxParallelMode.PER_WAVE)
        assert (
            resolve_max_parallel(
                config,
                wave_size=2,
                wave_override=3,
                wave_task_paths={
                    "TASK-A": ["src/users/router.ts"],
                    "TASK-B": ["src/users/router.ts"],
                },
            )
            == 3
        )

    def test_override_beats_an_undeclared_wave(self):
        config = _config(static_value=1, mode=MaxParallelMode.PER_WAVE)
        assert (
            resolve_max_parallel(
                config,
                wave_size=2,
                wave_override=2,
                wave_task_paths={"TASK-A": None, "TASK-B": None},
            )
            == 2
        )

    def test_without_an_override_the_rule_still_applies_in_per_wave_mode(self):
        config = _config(static_value=4, mode=MaxParallelMode.PER_WAVE)
        assert (
            resolve_max_parallel(
                config,
                wave_size=2,
                wave_override=None,
                wave_task_paths={
                    "TASK-A": ["internal/users/crud.go"],
                    "TASK-B": ["internal/users/handler.go"],
                },
            )
            == 1
        )


# ============================================================================
# 4. Reading what a task says it will touch — declared paths only
# ============================================================================


def _write_task(repo: Path, task_id: str, frontmatter: str = "", body: str = "") -> Path:
    task_file = repo / "tasks" / "backlog" / f"{task_id}.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        f"---\nid: {task_id}\ntitle: {task_id}\nstatus: pending\n"
        f"{frontmatter}---\n\n# {task_id}\n\n{body}\n",
        encoding="utf-8",
    )
    return task_file


def _write_plan(repo: Path, task_id: str, create=(), modify=()) -> None:
    state_dir = repo / "docs" / "state" / task_id
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "implementation_plan.json").write_text(
        json.dumps({"plan": {"files_to_create": list(create), "files_to_modify": list(modify)}}),
        encoding="utf-8",
    )


class TestCollectWaveTaskPaths:
    def test_frontmatter_lists_are_read(self, tmp_path):
        _write_task(
            tmp_path,
            "TASK-TS-001",
            frontmatter="files_to_create:\n  - src/users/router.ts\nfiles_to_modify:\n  - src/users/schemas.ts\n",
        )
        collected = collect_wave_task_paths(["TASK-TS-001"], tmp_path)
        assert collected["TASK-TS-001"] == [
            "src/users/router.ts",
            "src/users/schemas.ts",
        ]

    def test_the_implementation_plan_is_read(self, tmp_path):
        _write_task(tmp_path, "TASK-GO-001")
        _write_plan(tmp_path, "TASK-GO-001", modify=["internal/users/crud.go"])
        collected = collect_wave_task_paths(["TASK-GO-001"], tmp_path)
        assert collected["TASK-GO-001"] == ["internal/users/crud.go"]

    def test_the_task_document_text_is_the_last_resort(self, tmp_path):
        _write_task(
            tmp_path,
            "TASK-TS-002",
            body="Add the handler to `src/users/router.ts` and its test.",
        )
        collected = collect_wave_task_paths(["TASK-TS-002"], tmp_path)
        assert collected["TASK-TS-002"] == ["src/users/router.ts"]

    def test_a_task_that_says_nothing_maps_to_none(self, tmp_path):
        _write_task(tmp_path, "TASK-SILENT", body="Make the statistics work.")
        collected = collect_wave_task_paths(["TASK-SILENT"], tmp_path)
        assert collected["TASK-SILENT"] is None

    def test_a_missing_task_document_maps_to_none(self, tmp_path):
        collected = collect_wave_task_paths(["TASK-ABSENT"], tmp_path)
        assert collected["TASK-ABSENT"] is None

    def test_a_named_task_file_outside_the_standard_folders_is_read(self, tmp_path):
        task_file = tmp_path / "elsewhere" / "TASK-GO-009.md"
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(
            "---\nid: TASK-GO-009\n---\n\nEdit internal/users/handler.go here.\n",
            encoding="utf-8",
        )
        collected = collect_wave_task_paths(
            ["TASK-GO-009"], tmp_path, task_files={"TASK-GO-009": Path("elsewhere/TASK-GO-009.md")}
        )
        assert collected["TASK-GO-009"] == ["internal/users/handler.go"]

    def test_the_wave_reads_end_to_end_into_a_decision(self, tmp_path):
        """The observed failure, rebuilt from task documents: one task names
        the schema file, the other names the query file, both in one module."""
        _write_task(
            tmp_path,
            "TASK-STAT-002",
            frontmatter="files_to_modify:\n  - src/users/schemas.py\n",
        )
        _write_task(
            tmp_path,
            "TASK-STAT-003",
            frontmatter="files_to_modify:\n  - src/users/crud.py\n",
        )
        collected = collect_wave_task_paths(
            ["TASK-STAT-002", "TASK-STAT-003"], tmp_path
        )
        assert find_same_area_conflict(collected).sequence is True
        assert resolve_max_parallel(_config(4), wave_size=2, wave_task_paths=collected) == 1

    def test_the_order_of_the_wave_is_kept(self, tmp_path):
        _write_task(tmp_path, "TASK-B")
        _write_task(tmp_path, "TASK-A")
        collected = collect_wave_task_paths(["TASK-B", "TASK-A"], tmp_path)
        assert list(collected) == ["TASK-B", "TASK-A"]


# ============================================================================
# 5. The banner shows the number the executor enforces
# ============================================================================


def _write_feature_repo(repo_root: Path, task_frontmatter) -> None:
    """A two-task, one-wave feature whose tasks declare the given paths."""
    features_dir = repo_root / ".guardkit" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "id": "FEAT-AREA",
        "name": "Same-area test feature",
        "description": "Wave overlap fixture",
        "created": "2026-09-11T00:00:00Z",
        "status": "planned",
        "complexity": 3,
        "estimated_tasks": 2,
        "tasks": [
            {
                "id": task_id,
                "name": task_id,
                "file_path": f"tasks/backlog/{task_id}.md",
                "complexity": 2,
                "dependencies": [],
                "status": "pending",
                "implementation_mode": "task-work",
                "estimated_minutes": 30,
            }
            for task_id in task_frontmatter
        ],
        "orchestration": {
            "parallel_groups": [list(task_frontmatter)],
            "estimated_duration_minutes": 60,
        },
    }
    with open(features_dir / "FEAT-AREA.yaml", "w") as handle:
        yaml.dump(data, handle, sort_keys=False)
    for task_id, frontmatter in task_frontmatter.items():
        _write_task(repo_root, task_id, frontmatter=frontmatter)


@pytest.fixture
def mock_worktree_manager(tmp_path):
    from guardkit.worktrees import Worktree

    worktree_path = tmp_path / ".guardkit" / "worktrees" / "FEAT-AREA"
    worktree_path.mkdir(parents=True, exist_ok=True)
    worktree = Worktree(
        task_id="FEAT-AREA",
        branch_name="autobuild/FEAT-AREA",
        path=worktree_path,
        base_branch="main",
    )
    manager = MagicMock()
    manager.create.return_value = worktree
    manager.worktrees_dir = worktree_path.parent
    return manager


def _orchestrator(tmp_path, mock_worktree_manager, same_area=SAME_AREA_DEFAULT):
    orch = FeatureOrchestrator(
        repo_root=tmp_path,
        worktree_manager=mock_worktree_manager,
        quiet=True,
        skip_validation=True,
    )
    orch._parallel_config = ParallelConfig(
        mode=MaxParallelMode.STATIC, static_value=4, same_area=same_area
    )
    return orch


@patch(
    "guardkit.orchestrator.agent_invoker.detect_timeout_multiplier",
    return_value=1.0,
)
class TestBannerAgreesWithTheDecision:
    """The display resolution and the authoritative one read the same answer."""

    def _wave(self, tmp_path, mock_worktree_manager, task_frontmatter, same_area=SAME_AREA_DEFAULT):
        from guardkit.orchestrator.feature_loader import FeatureLoader

        _write_feature_repo(tmp_path, task_frontmatter)
        orch = _orchestrator(tmp_path, mock_worktree_manager, same_area=same_area)
        feature = FeatureLoader.load_feature("FEAT-AREA", repo_root=tmp_path)
        worktree = mock_worktree_manager.create.return_value
        # The worktree the tasks are read from is the repo itself here.
        worktree = type(worktree)(
            task_id=worktree.task_id,
            branch_name=worktree.branch_name,
            path=tmp_path,
            base_branch=worktree.base_branch,
        )
        task_ids = list(task_frontmatter)
        paths = orch._wave_task_paths(1, task_ids, feature, worktree)
        display_value = resolve_max_parallel(
            orch._parallel_config,
            wave_number=1,
            wave_size=len(task_ids),
            log=False,
            wave_task_paths=paths,
        )
        executor_value = resolve_max_parallel(
            orch._parallel_config,
            wave_number=1,
            wave_size=len(task_ids),
            wave_task_paths=paths,
        )
        return orch, task_ids, display_value, executor_value

    def test_overlapping_wave_banner_says_one(
        self, mock_detect, tmp_path, mock_worktree_manager
    ):
        orch, task_ids, display_value, executor_value = self._wave(
            tmp_path,
            mock_worktree_manager,
            {
                "TASK-TS-001": "files_to_modify:\n  - src/users/router.ts\n",
                "TASK-TS-002": "files_to_modify:\n  - src/users/schemas.ts\n",
            },
        )
        assert display_value == executor_value == 1

        output = StringIO()
        display = WaveProgressDisplay(
            total_waves=1, console=Console(file=output, force_terminal=True, width=80)
        )
        display.start_wave(1, task_ids, max_parallel=display_value)
        assert "(parallel: 1)" in strip_ansi(output.getvalue())

    def test_independent_wave_banner_says_what_the_executor_allows(
        self, mock_detect, tmp_path, mock_worktree_manager
    ):
        orch, task_ids, display_value, executor_value = self._wave(
            tmp_path,
            mock_worktree_manager,
            {
                "TASK-GO-001": "files_to_modify:\n  - internal/users/crud.go\n",
                "TASK-GO-002": "files_to_modify:\n  - internal/billing/crud.go\n",
            },
        )
        assert display_value == executor_value == 4

    def test_undeclared_wave_banner_says_one(
        self, mock_detect, tmp_path, mock_worktree_manager
    ):
        orch, task_ids, display_value, executor_value = self._wave(
            tmp_path,
            mock_worktree_manager,
            {"TASK-Q-001": "", "TASK-Q-002": ""},
        )
        assert display_value == executor_value == 1

    def test_the_wave_is_read_once_and_remembered(
        self, mock_detect, tmp_path, mock_worktree_manager
    ):
        """Both call sites get the identical answer object, so they cannot
        drift apart between the banner and the dispatch."""
        from guardkit.orchestrator.feature_loader import FeatureLoader

        frontmatter = {
            "TASK-TS-001": "files_to_modify:\n  - src/users/router.ts\n",
            "TASK-TS-002": "files_to_modify:\n  - src/users/schemas.ts\n",
        }
        _write_feature_repo(tmp_path, frontmatter)
        orch = _orchestrator(tmp_path, mock_worktree_manager)
        feature = FeatureLoader.load_feature("FEAT-AREA", repo_root=tmp_path)
        worktree = mock_worktree_manager.create.return_value
        worktree = type(worktree)(
            task_id=worktree.task_id,
            branch_name=worktree.branch_name,
            path=tmp_path,
            base_branch=worktree.base_branch,
        )
        first = orch._wave_task_paths(1, list(frontmatter), feature, worktree)
        second = orch._wave_task_paths(1, list(frontmatter), feature, worktree)
        assert first is second

    def test_a_task_the_feature_does_not_know_still_resolves(
        self, mock_detect, tmp_path, mock_worktree_manager
    ):
        """Nothing here may raise mid-wave: an unknown task simply counts as
        having declared nothing."""
        from guardkit.orchestrator.feature_loader import FeatureLoader

        _write_feature_repo(
            tmp_path, {"TASK-TS-001": "files_to_modify:\n  - src/users/router.ts\n"}
        )
        orch = _orchestrator(tmp_path, mock_worktree_manager)
        feature = FeatureLoader.load_feature("FEAT-AREA", repo_root=tmp_path)
        worktree = mock_worktree_manager.create.return_value
        worktree = type(worktree)(
            task_id=worktree.task_id,
            branch_name=worktree.branch_name,
            path=tmp_path,
            base_branch=worktree.base_branch,
        )
        paths = orch._wave_task_paths(
            1, ["TASK-TS-001", "TASK-NOT-IN-FEATURE"], feature, worktree
        )
        assert paths["TASK-NOT-IN-FEATURE"] is None
        assert (
            resolve_max_parallel(
                orch._parallel_config, wave_size=2, wave_task_paths=paths
            )
            == 1
        )


# ============================================================================
# 6. A RE-ENTERED wave's banner tells the same truth as the first pass
# ============================================================================
#
# Two gates can send a wave round again after its tasks have passed: the
# post-wave smoke gate and the post-wave wiring gate. Both re-print the wave
# banner before re-running it. Both used to print the wave size, which was
# harmless only while parallelism was unlimited; under this rule it would be a
# lie — "Wave 2/1: TASK-STAT-002, TASK-STAT-003 (parallel: 2)" above a wave
# the dispatcher runs one task at a time.


def _real_feature_and_worktree(tmp_path, mock_worktree_manager, task_frontmatter):
    """A loaded feature and a worktree pointing at the repository itself."""
    from guardkit.orchestrator.feature_loader import FeatureLoader

    _write_feature_repo(tmp_path, task_frontmatter)
    feature = FeatureLoader.load_feature("FEAT-AREA", repo_root=tmp_path)
    template = mock_worktree_manager.create.return_value
    worktree = type(template)(
        task_id=template.task_id,
        branch_name=template.branch_name,
        path=tmp_path,
        base_branch=template.base_branch,
    )
    return feature, worktree


def _wave_result(task_ids):
    from guardkit.orchestrator.feature_orchestrator import (
        TaskExecutionResult,
        WaveExecutionResult,
    )

    return WaveExecutionResult(
        wave_number=1,
        task_ids=list(task_ids),
        results=[
            TaskExecutionResult(
                task_id=task_id,
                success=True,
                total_turns=1,
                final_decision="approved",
            )
            for task_id in task_ids
        ],
        all_succeeded=True,
    )


def _smoke_result(passed: bool):
    from guardkit.orchestrator.smoke_gates import SmokeGateResult

    return SmokeGateResult(
        passed=passed,
        exit_code=0 if passed else 1,
        stdout="",
        stderr="" if passed else "TypeError: users_created_per_day() missing 1 argument",
        timed_out=False,
        command="npm run smoke",
        timeout=5,
        after_wave=1,
        gate_not_wired=False,
    )


def _banner_numbers(output: StringIO):
    """Every "(parallel: K)" the display has printed, in order."""
    return [int(n) for n in re.findall(r"parallel: (\d+)", strip_ansi(output.getvalue()))]


def _display_on(orch):
    output = StringIO()
    orch._wave_display = WaveProgressDisplay(
        total_waves=1,
        console=Console(file=output, force_terminal=True, width=100),
    )
    return output


def _authoritative(orch, task_ids, feature, worktree):
    """The number the dispatcher will enforce for this wave."""
    return resolve_max_parallel(
        orch._parallel_config,
        wave_number=1,
        wave_size=len(task_ids),
        wave_task_paths=orch._wave_task_paths(1, task_ids, feature, worktree),
    )


_OVERLAPPING = {
    "TASK-STAT-002": "files_to_modify:\n  - src/users/schemas.ts\n",
    "TASK-STAT-003": "files_to_modify:\n  - src/users/crud.ts\n",
}
_INDEPENDENT = {
    "TASK-GO-001": "files_to_modify:\n  - internal/users/crud.go\n",
    "TASK-GO-002": "files_to_modify:\n  - internal/billing/crud.go\n",
}


@patch(
    "guardkit.orchestrator.agent_invoker.detect_timeout_multiplier",
    return_value=1.0,
)
class TestTheSmokeGateRetryBannerAgrees:
    """The smoke gate re-enters the wave; its banner must not say two."""

    def _drive(self, tmp_path, mock_worktree_manager, frontmatter):
        from guardkit.orchestrator.feature_loader import SmokeGates

        feature, worktree = _real_feature_and_worktree(
            tmp_path, mock_worktree_manager, frontmatter
        )
        feature.smoke_gates = SmokeGates(
            after_wave=1, command="npm run smoke", expected_exit=0, timeout=5
        )
        task_ids = list(frontmatter)
        orch = _orchestrator(tmp_path, mock_worktree_manager)
        orch._smoke_gate_max_retries = 1
        output = _display_on(orch)
        wave_result = _wave_result(task_ids)

        with patch(
            "guardkit.orchestrator.feature_orchestrator.run_smoke_gate",
            side_effect=[_smoke_result(False), _smoke_result(True)],
        ), patch.object(
            orch, "_execute_wave", return_value=_wave_result(task_ids)
        ) as executed:
            outcome = orch._run_post_wave_smoke_gate(
                1, task_ids, feature, worktree, wave_result
            )

        assert executed.call_count == 1, "the wave must actually have been re-entered"
        assert outcome.terminate is False
        return orch, task_ids, feature, worktree, output

    def test_overlapping_wave_is_re_entered_one_at_a_time(
        self, mock_detect, tmp_path, mock_worktree_manager
    ):
        orch, task_ids, feature, worktree, output = self._drive(
            tmp_path, mock_worktree_manager, _OVERLAPPING
        )
        printed = _banner_numbers(output)
        assert printed == [1], printed
        assert printed[0] == _authoritative(orch, task_ids, feature, worktree)
        # The wave size is 2; printing it is exactly the old defect.
        assert printed[0] != len(task_ids)

    def test_independent_wave_still_runs_both_tasks_together(
        self, mock_detect, tmp_path, mock_worktree_manager
    ):
        """Not hard-wired to one: an independent wave is re-entered with both
        tasks running together, and the banner says so.

        The allowance here is 4 and the wave holds 2 tasks, so the honest
        number is 2 — the display shows the smaller of the allowance and the
        wave size, because that is the concurrency actually reached."""
        orch, task_ids, feature, worktree, output = self._drive(
            tmp_path, mock_worktree_manager, _INDEPENDENT
        )
        printed = _banner_numbers(output)
        assert printed == [2], printed
        allowance = _authoritative(orch, task_ids, feature, worktree)
        assert allowance == 4
        assert printed[0] == min(allowance, len(task_ids))


@patch(
    "guardkit.orchestrator.agent_invoker.detect_timeout_multiplier",
    return_value=1.0,
)
class TestTheWiringGateRetryBannerAgrees:
    """The wiring gate re-enters the wave; its banner must not say two either."""

    def _drive(self, tmp_path, mock_worktree_manager, frontmatter):
        import sys
        import types

        feature, worktree = _real_feature_and_worktree(
            tmp_path, mock_worktree_manager, frontmatter
        )
        task_ids = list(frontmatter)
        orch = _orchestrator(tmp_path, mock_worktree_manager)
        orch._wiring_gate_max_retries = 1
        output = _display_on(orch)
        wave_result = _wave_result(task_ids)

        finding = {
            "file": "tests/users/router.test.ts",
            "lineno": 7,
            "symbol": "UserService",
            "pattern": "MOCKED_SEAM",
            "authored_this_turn": True,
        }

        def _wiring(findings):
            return {
                "status": "complete",
                "mocked_seam": {
                    "status": "ran",
                    "findings": findings,
                    "external_mocks_ignored": [],
                },
                "ctor_arity": {"status": "ran", "findings": []},
            }

        answers = iter([_wiring([finding]), _wiring([])])

        # guardkitfactory is an optional extra and is absent here, so the gate
        # would skip itself. Stand a module in its place carrying the one
        # function the gate calls, so the RETRY PATH itself really runs.
        package = types.ModuleType("guardkitfactory")
        wiring_module = types.ModuleType("guardkitfactory.wiring")
        wiring_module.analyze_wiring = lambda **kwargs: next(answers)
        package.wiring = wiring_module

        with patch.dict(
            sys.modules,
            {"guardkitfactory": package, "guardkitfactory.wiring": wiring_module},
        ), patch.object(
            orch, "_wave_authored_files", return_value=["src/users/schemas.ts"]
        ), patch.object(
            orch, "_execute_wave", return_value=_wave_result(task_ids)
        ) as executed:
            outcome = orch._run_post_wave_wiring_gate(
                1, task_ids, feature, worktree, wave_result
            )

        assert executed.call_count == 1, "the wave must actually have been re-entered"
        assert outcome.terminate is False
        return orch, task_ids, feature, worktree, output

    def test_overlapping_wave_is_re_entered_one_at_a_time(
        self, mock_detect, tmp_path, mock_worktree_manager
    ):
        orch, task_ids, feature, worktree, output = self._drive(
            tmp_path, mock_worktree_manager, _OVERLAPPING
        )
        printed = _banner_numbers(output)
        assert printed == [1], printed
        assert printed[0] == _authoritative(orch, task_ids, feature, worktree)
        assert printed[0] != len(task_ids)

    def test_independent_wave_still_runs_both_tasks_together(
        self, mock_detect, tmp_path, mock_worktree_manager
    ):
        orch, task_ids, feature, worktree, output = self._drive(
            tmp_path, mock_worktree_manager, _INDEPENDENT
        )
        printed = _banner_numbers(output)
        assert printed == [2], printed
        allowance = _authoritative(orch, task_ids, feature, worktree)
        assert allowance == 4
        assert printed[0] == min(allowance, len(task_ids))
