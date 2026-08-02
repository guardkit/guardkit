"""Machine-derived F1 pass bars for producer-minted fix tasks (Rich's ruling, 2026-08-02).

The review leg's producer mints a minimal pass bar per fix task, so the bar
exists BEFORE any work leg can run — the bar-before-implementation law held
mechanically instead of by convention.

Nothing here re-implements the gate. The suite drives:

* the **real producer** (``implement_orchestrator.handle_implement_option_sync``)
  through ``review_runner.produce_fix_tasks``, in a **real git repo**;
* the **real schema** (``guardkit.qa.formats.validate_instance`` → ``PassBar``);
* the **real checker** — ``guardkit.qa.enforcement.check_pass_bar_precondition``,
  the exact function whose refusal text ("no pinned F1 pass bar for <task>…")
  this lane exists to satisfy;
* the **real flag reader** — ``is_tier1_enforced`` (config file AND env override).

Two controls keep the suite honest: the checker still REFUSES a task with no
minted bar (so a passing assertion is not a vacuous one), and a derivation that
cannot satisfy the schema leaves NO file on disk.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from guardkit.cli.main import cli
from guardkit.orchestrator import pass_bar_mint, review_runner
from guardkit.qa.enforcement import (
    ENFORCE_ENV,
    check_pass_bar_precondition,
    is_tier1_enforced,
    pass_bar_path_for,
)
from guardkit.qa.formats import PassBar, QAFormatError, validate_instance

REVIEW_TASK_ID = "TASK-REV-A1B2C3"

REPORT = (
    f"# Review Report — {REVIEW_TASK_ID}\n\n"
    "## Summary\n\nTwo defects.\n\n"
    "## Recommendations\n\n"
    "1. Add a null guard to parse_header() in src/parser.py.\n"
    "2. Cover the truncated-header path in tests/test_parser.py.\n"
)

AUTH_REPORT = (
    f"# Review Report — {REVIEW_TASK_ID}\n\n"
    "## Summary\n\nOne defect.\n\n"
    "## Recommendations\n\n"
    "1. Reject an expired login session in check_credential() in src/auth.py.\n"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q", "-b", "main")
    (path / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "seed")
    return path


def _head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def _arm_enforcement(repo: Path, on: bool = True) -> None:
    """Arm ``qa.enforce_tier1`` the way a real repo does — the config file."""
    config = repo / ".guardkit" / "config.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(f"qa:\n  enforce_tier1: {'true' if on else 'false'}\n", encoding="utf-8")


def _write_report(repo: Path, body: str = REPORT) -> Path:
    report = repo / ".claude" / "reviews" / f"{REVIEW_TASK_ID}-review-report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(body, encoding="utf-8")
    return report


def _run_producer(repo: Path, body: str = REPORT):
    """Drive the REAL fix-task producer with ``cwd`` set to ``repo``."""
    report = _write_report(repo, body)
    cwd = Path.cwd()
    os.chdir(repo)
    try:
        return review_runner.produce_fix_tasks(
            task_id=REVIEW_TASK_ID,
            task={"frontmatter": {"title": "Review header parser subsystem"}},
            report_path=report,
            repo_root=repo,
        )
    finally:
        os.chdir(cwd)


@pytest.fixture(autouse=True)
def _no_env_leak(monkeypatch):
    """The operator's own enforcement flag must never decide a test's outcome."""
    monkeypatch.delenv(ENFORCE_ENV, raising=False)


@pytest.fixture
def repo(tmp_path):
    return _init_repo(tmp_path / "repo")


# ===========================================================================
# 1. Enforcement ARMED — a schema-valid bar per fix task
# ===========================================================================


class TestMintWhenArmed:
    def test_one_schema_valid_bar_per_fix_task(self, repo):
        _arm_enforcement(repo)
        written, info = _run_producer(repo)
        assert len(written) == 2, info

        for fix_task in written:
            bar_path = pass_bar_path_for(repo, fix_task.stem)
            assert bar_path.is_file(), f"no bar minted beside {fix_task.name}"
            # The REAL validator, the REAL model.
            bar = validate_instance("pass-bar", bar_path)
            assert isinstance(bar, PassBar)
            # The id the work leg will be dispatched with IS the file stem, and
            # the checker refuses a bar whose task_id disagrees.
            assert bar.task_id == fix_task.stem
            assert bar.criteria, "a bar with no criteria is not a bar"

    def test_criteria_are_derived_from_the_fix_tasks_acceptance_criteria(self, repo):
        _arm_enforcement(repo)
        written, _info = _run_producer(repo)
        fix_task = written[0]
        source = pass_bar_mint.read_acceptance_criteria(
            fix_task.read_text(encoding="utf-8")
        )
        assert source, "the producer wrote no acceptance criteria to derive from"

        bar = validate_instance("pass-bar", pass_bar_path_for(repo, fix_task.stem))
        assert len(bar.criteria) == len(source)
        # Every criterion's text traces back to a line of the fix task.
        for criterion, raw in zip(bar.criteria, source):
            assert criterion.text in raw
        # The producer's own anti-stub ids survive the derivation by name.
        ids = {c.id for c in bar.criteria}
        assert {"AC-ANTISTUB-1", "AC-ANTISTUB-2"} <= ids, ids

    def test_bar_pins_head_before_the_work_and_the_env_flag_arms_it_too(
        self, repo, monkeypatch
    ):
        """No config file at all — the env override is the other real reader."""
        monkeypatch.setenv(ENFORCE_ENV, "1")
        assert is_tier1_enforced(repo) is True
        head_before = _head(repo)

        written, _info = _run_producer(repo)
        bar = validate_instance("pass-bar", pass_bar_path_for(repo, written[0].stem))
        assert bar.registered_at.sha == head_before

    def test_an_authless_fix_declares_only_the_universal_negative_path(self, repo):
        _arm_enforcement(repo)
        written, _info = _run_producer(repo)
        bar = validate_instance("pass-bar", pass_bar_path_for(repo, written[0].stem))
        assert bar.auth_surface_bearing is False
        assert bar.negative_paths == ["dependency_down_degradation"]

    def test_an_auth_bearing_fix_declares_all_five(self, repo):
        """PB-14: the flag is DECLARED from the fix task's own words, not guessed."""
        _arm_enforcement(repo)
        written, info = _run_producer(repo, AUTH_REPORT)
        assert written, info
        bar = validate_instance("pass-bar", pass_bar_path_for(repo, written[0].stem))
        assert bar.auth_surface_bearing is True
        assert set(bar.negative_paths) == {
            "wrong_credential",
            "anonymous_deep_link",
            "post_logout_401",
            "unauthorized_403_ui",
            "dependency_down_degradation",
        }

    def test_auth_lookalike_words_do_not_fabricate_the_four_auth_paths(self):
        """The PB coach's driven false positives, pinned as regressions.

        Bare-substring matching flagged 5 of 6 innocuous titles as
        auth-bearing — ``author`` fired "auth", ``SQLAlchemy session`` fired
        "session", ``permission bits`` fired "permission", and a line number
        4013 fired "401" — each fabricating four auth negative paths the fix
        has no surface for (the QAV-corpus poison PB-14 names), and each
        arming the runtime-surface gate through
        ``enforcement._pass_bar_is_runtime_surface``. Word-bounded matching
        with the generic words dropped must stay quiet on all of them.
        """
        from guardkit.orchestrator.pass_bar_mint import _auth_surface_basis

        for innocuous in (
            "Name the authoritative source for the config default",
            "Close the SQLAlchemy session leak in the request handler",
            "Correct the file permission bits on the export",
            "Refactor the loop at line 4013 to avoid quadratic rescans",
            "Rename the variable `author` for clarity",
        ):
            bearing, basis = _auth_surface_basis(innocuous)
            assert bearing is False, (innocuous, basis)

    def test_real_auth_words_still_fire_with_word_boundaries(self):
        from guardkit.orchestrator.pass_bar_mint import _auth_surface_basis

        for auth_bearing in (
            "Reject an expired login token in check_credential()",
            "Return 401-shaped errors from the auth middleware",
            "Harden the OAuth callback against replay",
            "The unauthorized branch in src/auth.py never logs",
        ):
            bearing, basis = _auth_surface_basis(auth_bearing)
            assert bearing is True, (auth_bearing, basis)


# ===========================================================================
# 2. The REAL checker — driven, not re-implemented
# ===========================================================================


class TestTheRealCheckerAcceptsAMintedBar:
    def test_precondition_passes_against_a_minted_bar(self, repo):
        """``check_pass_bar_precondition`` — the very function whose refusal
        text this lane exists to satisfy — passes for every minted bar, after
        implementation commits have moved HEAD on."""
        _arm_enforcement(repo)
        written, _info = _run_producer(repo)

        # The journey continues: the fix tasks (and bars) are committed, then
        # implementation lands on top. The bar must still read as predating it.
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "review leg: fix tasks + minted pass bars")
        (repo / "impl.py").write_text("x = 1\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "impl")

        for fix_task in written:
            result = check_pass_bar_precondition(repo, fix_task.stem)
            assert result.passed is True, result.detail
            assert result.pass_bar_path == str(pass_bar_path_for(repo, fix_task.stem))

    def test_precondition_passes_before_anything_is_even_committed(self, repo):
        """The bar is on disk the moment the fix task is — no commit required.

        The checker tests the *file* and the *sha it pins*; the sha is HEAD at
        production time, so the ordering holds from the first instant.
        """
        _arm_enforcement(repo)
        written, _info = _run_producer(repo)
        result = check_pass_bar_precondition(repo, written[0].stem)
        assert result.passed is True, result.detail

    def test_control_the_checker_still_refuses_an_unminted_task(self, repo):
        """The load-bearing control: the assertions above are not vacuous."""
        _arm_enforcement(repo)
        _run_producer(repo)
        result = check_pass_bar_precondition(repo, "TASK-NOPE-999-never-minted")
        assert result.passed is False
        assert "no pinned F1 pass bar" in result.detail


# ===========================================================================
# 3. Enforcement NOT armed — mint NOTHING
# ===========================================================================


class TestMintNothingWhenNotArmed:
    def test_default_off_repo_grows_no_qa_tree(self, repo):
        assert is_tier1_enforced(repo) is False
        written, info = _run_producer(repo)
        assert len(written) == 2
        assert not (repo / "qa").exists(), "a bar was minted with enforcement OFF"
        assert info["pass_bars"]["enforcement"] == "off"
        assert info["pass_bars"]["bars"] == []

    def test_config_off_is_off(self, repo):
        _arm_enforcement(repo, on=False)
        _run_producer(repo)
        assert not (repo / "qa").exists()

    def test_env_off_beats_config_on(self, repo, monkeypatch):
        """One reader, honoured verbatim — precedence included."""
        _arm_enforcement(repo, on=True)
        monkeypatch.setenv(ENFORCE_ENV, "0")
        assert is_tier1_enforced(repo) is False
        _run_producer(repo)
        assert not (repo / "qa").exists()

    def test_mint_pass_bars_writes_nothing_when_told_enforcement_is_off(self, repo):
        (repo / "tasks").mkdir(exist_ok=True)
        fake = repo / "tasks" / "TASK-ABC-001-x.md"
        fake.write_text("## Acceptance Criteria\n\n- [ ] done\n", encoding="utf-8")
        report = pass_bar_mint.mint_pass_bars(
            [fake], repo_root=repo, parent_review_id=REVIEW_TASK_ID, enforced=False
        )
        assert report.enforcement == "off"
        assert report.bars == []
        assert not (repo / "qa").exists()


# ===========================================================================
# 4. Provenance — a minted bar is NAMED machine-derived
# ===========================================================================


class TestProvenance:
    def test_the_file_names_itself_machine_derived_and_its_parent_review(self, repo):
        _arm_enforcement(repo)
        written, _info = _run_producer(repo)
        text = pass_bar_path_for(repo, written[0].stem).read_text(encoding="utf-8")

        assert pass_bar_mint.PASS_BAR_PROVENANCE_MARKER in text
        assert "not human-authored" in text
        assert "guardkit task-review" in text
        assert REVIEW_TASK_ID in text  # the parent review id, from frontmatter
        assert written[0].name in text
        # The provenance rides ABOVE the document, so a reader meets it first.
        assert text.splitlines()[0].startswith("#")
        assert text.index(pass_bar_mint.PASS_BAR_PROVENANCE_MARKER) < text.index(
            "format_version"
        )

    def test_the_provenance_block_states_every_judgement_it_had_to_make(self, repo):
        _arm_enforcement(repo)
        written, _info = _run_producer(repo)
        text = pass_bar_path_for(repo, written[0].stem).read_text(encoding="utf-8")
        assert "auth_surface_bearing: false —" in text
        assert "classed `machine`" in text
        assert "evidence_kind `log`" in text
        assert "suite_green_vs_ledger" in text

    def test_the_provenance_comment_does_not_break_the_schema(self, repo):
        """The comment is the form ``extra='forbid'`` admits — YAML ignores it."""
        _arm_enforcement(repo)
        written, _info = _run_producer(repo)
        path = pass_bar_path_for(repo, written[0].stem)
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert set(loaded) == {
            "format_version",
            "task_id",
            "registered_at",
            "auth_surface_bearing",
            "preconditions",
            "criteria",
            "negative_paths",
        }
        PassBar.model_validate(loaded)

    def test_the_receipt_block_lists_the_bars_with_the_provenance_note(self, repo):
        _arm_enforcement(repo)
        written, info = _run_producer(repo)
        block = info["pass_bars"]
        assert block["enforcement"] == "armed"
        assert pass_bar_mint.PASS_BAR_PROVENANCE_NOTE == block["provenance"]
        assert "machine-derived" in block["provenance"]
        assert len(block["bars"]) == len(written)
        for entry in block["bars"]:
            assert entry["status"] == "written"
            assert entry["provenance"] == "machine-derived"
            assert Path(entry["pass_bar_path"]).is_file()


# ===========================================================================
# 5. A derivation that cannot satisfy the schema — loud, and NO file
# ===========================================================================


class TestLoudRefusalNeverAMalformedFile:
    def test_a_fix_task_with_no_acceptance_criteria_mints_nothing(self, repo, capsys):
        _arm_enforcement(repo)
        backlog = repo / "tasks" / "backlog" / "header-parser"
        backlog.mkdir(parents=True)
        fix_task = backlog / "TASK-HPR-001-no-criteria.md"
        fix_task.write_text(
            "---\nid: TASK-HPR-001\nparent_review: " + REVIEW_TASK_ID + "\n---\n\n"
            "# No criteria here\n\n## Description\n\nNothing to derive from.\n",
            encoding="utf-8",
        )
        capsys.readouterr()

        report = pass_bar_mint.mint_pass_bars(
            [fix_task], repo_root=repo, parent_review_id=REVIEW_TASK_ID
        )

        assert not pass_bar_path_for(repo, fix_task.stem).exists()
        assert not (repo / "qa").exists(), "an empty qa/ tree is still a side effect"
        assert [b.status for b in report.bars] == ["error"]
        assert "Acceptance Criteria" in (report.bars[0].detail or "")
        # LOUD: stderr, never stdout (stdout is the pipeline's control surface).
        captured = capsys.readouterr()
        assert "pass-bar mint" in captured.err
        assert captured.out == ""

    def test_derive_raises_rather_than_inventing_a_criterion(self, tmp_path):
        empty = tmp_path / "TASK-ABC-001-empty.md"
        empty.write_text("# nothing\n", encoding="utf-8")
        with pytest.raises(pass_bar_mint.PassBarDerivationError) as exc:
            pass_bar_mint.derive_pass_bar(
                fix_task_path=empty, task_id="TASK-ABC-001-empty", registered_sha="a" * 40
            )
        assert "Acceptance Criteria" in str(exc.value)

    def test_a_mapping_the_model_rejects_never_reaches_disk(self, repo, capsys):
        """The validate-BEFORE-write branch, driven: an unusable sha.

        ``RegisteredAt.sha`` has ``min_length=4``; a 3-char sha builds a mapping
        fine and dies at ``PassBar.model_validate`` — which is the point. The
        file must not exist, in any state.
        """
        _arm_enforcement(repo)
        backlog = repo / "tasks" / "backlog" / "hp"
        backlog.mkdir(parents=True)
        fix_task = backlog / "TASK-HPR-002-short-sha.md"
        fix_task.write_text(
            "## Acceptance Criteria\n\n- [ ] Implementation complete\n", encoding="utf-8"
        )
        capsys.readouterr()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(pass_bar_mint, "head_sha", lambda _root: "abc")
            report = pass_bar_mint.mint_pass_bars(
                [fix_task], repo_root=repo, parent_review_id=REVIEW_TASK_ID
            )

        assert not pass_bar_path_for(repo, fix_task.stem).exists()
        assert report.bars[0].status == "error"
        assert "NOT a valid" in (report.bars[0].detail or "")
        assert "pass-bar mint" in capsys.readouterr().err

    def test_the_serialised_text_is_round_tripped_before_it_is_written(self, tmp_path):
        """Belt to the mapping's brace: the BYTES are validated too."""
        with pytest.raises(pass_bar_mint.PassBarDerivationError) as exc:
            pass_bar_mint._round_trip_check(
                "format_version: '2.0'\ntask_id: T\n", tmp_path / "TASK-X-1.md"
            )
        assert "round-trip" in str(exc.value)

    def test_no_head_sha_mints_nothing_and_says_so(self, tmp_path, capsys):
        """A non-git tree with enforcement armed: no bar can honestly pin an
        ancestor sha, so none is written and the work leg's refusal stands."""
        plain = tmp_path / "notarepo"
        (plain / "tasks").mkdir(parents=True)
        _arm_enforcement(plain)
        fix_task = plain / "tasks" / "TASK-ABC-001-x.md"
        fix_task.write_text(
            "## Acceptance Criteria\n\n- [ ] Implementation complete\n", encoding="utf-8"
        )
        capsys.readouterr()

        report = pass_bar_mint.mint_pass_bars(
            [fix_task], repo_root=plain, parent_review_id=REVIEW_TASK_ID
        )
        assert not (plain / "qa").exists()
        assert report.error and "HEAD" in report.error
        assert [b.status for b in report.bars] == ["error"]
        assert "pass-bar mint" in capsys.readouterr().err


# ===========================================================================
# 6. An existing bar outranks a derived one
# ===========================================================================


class TestExistingBarIsNeverClobbered:
    def test_a_human_bar_survives_a_second_review(self, repo):
        _arm_enforcement(repo)
        written, _info = _run_producer(repo)
        target = pass_bar_path_for(repo, written[0].stem)
        widened = target.read_text(encoding="utf-8").replace(
            "auth_surface_bearing: false", "auth_surface_bearing: false  # widened by hand"
        )
        target.write_text(widened, encoding="utf-8")

        report = pass_bar_mint.mint_pass_bars(
            [written[0]], repo_root=repo, parent_review_id=REVIEW_TASK_ID
        )
        assert report.bars[0].status == "exists"
        assert "widened by hand" in target.read_text(encoding="utf-8")


# ===========================================================================
# 7. End to end through the CLI — the leg receipt carries the block
# ===========================================================================


class TestLegReceipt:
    def _fake_specialist(self, monkeypatch, repo: Path, body: str):
        class _Result:
            status = "passed"
            error = None
            duration_seconds = 1.0

        async def _run(*args, **kwargs):
            task_id = args[2]
            report = repo / ".claude" / "reviews" / f"{task_id}-review-report.md"
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(body, encoding="utf-8")
            findings = (
                repo / ".guardkit" / "autobuild" / task_id / "review_findings.json"
            )
            findings.parent.mkdir(parents=True, exist_ok=True)
            findings.write_text(
                json.dumps(
                    [
                        {
                            "id": "F1",
                            "severity": "high",
                            "title": "Unguarded attribute access",
                            "file": "src/parser.py",
                            "line": 88,
                        }
                    ]
                ),
                encoding="utf-8",
            )
            return _Result()

        monkeypatch.setattr(review_runner, "run_specialist", _run)
        monkeypatch.setattr(
            review_runner, "_build_agent_invoker", lambda **kwargs: object()
        )

    def test_receipt_pass_bars_key_on_a_real_leg(self, repo, monkeypatch):
        _arm_enforcement(repo)
        monkeypatch.setenv("GUARDKIT_REVIEW_MEMORY_CLI", "0")
        task_dir = repo / "tasks" / "in_progress"
        task_dir.mkdir(parents=True)
        (task_dir / f"{REVIEW_TASK_ID}.md").write_text(
            "---\n"
            f"id: {REVIEW_TASK_ID}\n"
            "title: Review the header parser\n"
            "status: in_progress\n"
            "task_type: review\n"
            "---\n\n# Review the header parser\n\n"
            "## Requirements\n\nAssess src/parser.py.\n",
            encoding="utf-8",
        )
        self._fake_specialist(monkeypatch, repo, REPORT)
        monkeypatch.chdir(repo)

        result = CliRunner().invoke(cli, ["task-review", "--task-id", REVIEW_TASK_ID])
        assert result.exit_code == 0, result.output

        receipt = json.loads(
            review_runner.receipt_path_for(repo, REVIEW_TASK_ID).read_text(
                encoding="utf-8"
            )
        )
        block = receipt["pass_bars"]
        assert block["enforcement"] == "armed"
        assert block["bars"], "the leg minted no bars for its own fix tasks"
        for entry in block["bars"]:
            assert entry["status"] == "written"
            bar = validate_instance("pass-bar", Path(entry["pass_bar_path"]))
            assert bar.task_id == entry["fix_task_id"]
            # And the real checker accepts it, from the leg's own receipt path.
            assert check_pass_bar_precondition(repo, entry["fix_task_id"]).passed

    def test_receipt_records_off_honestly(self, repo, monkeypatch):
        monkeypatch.setenv("GUARDKIT_REVIEW_MEMORY_CLI", "0")
        task_dir = repo / "tasks" / "in_progress"
        task_dir.mkdir(parents=True)
        (task_dir / f"{REVIEW_TASK_ID}.md").write_text(
            f"---\nid: {REVIEW_TASK_ID}\ntitle: Review the header parser\n"
            "status: in_progress\ntask_type: review\n---\n\n"
            "# Review the header parser\n\n## Requirements\n\nAssess src/parser.py.\n",
            encoding="utf-8",
        )
        self._fake_specialist(monkeypatch, repo, REPORT)
        monkeypatch.chdir(repo)

        result = CliRunner().invoke(cli, ["task-review", "--task-id", REVIEW_TASK_ID])
        assert result.exit_code == 0, result.output
        receipt = json.loads(
            review_runner.receipt_path_for(repo, REVIEW_TASK_ID).read_text(
                encoding="utf-8"
            )
        )
        assert receipt["pass_bars"]["enforcement"] == "off"
        assert receipt["pass_bars"]["bars"] == []


# ===========================================================================
# 8. Unit-level derivation details
# ===========================================================================


class TestDerivationUnits:
    def test_acceptance_criteria_reader_stops_at_the_next_heading(self):
        text = (
            "# T\n\n## Acceptance Criteria\n\n"
            "- [ ] one\n- [x] two\n\n"
            "## Files to Modify\n\n- [ ] not a criterion\n"
        )
        assert pass_bar_mint.read_acceptance_criteria(text) == ["one", "two"]

    def test_criterion_ids_are_unique_even_when_the_text_repeats(self, tmp_path):
        fix_task = tmp_path / "TASK-ABC-001-dupes.md"
        fix_task.write_text(
            "## Acceptance Criteria\n\n"
            "- [ ] AC-1: alpha\n- [ ] AC-1: beta\n- [ ] gamma\n",
            encoding="utf-8",
        )
        mapping, _facts = pass_bar_mint.derive_pass_bar(
            fix_task_path=fix_task, task_id="TASK-ABC-001-dupes", registered_sha="a" * 40
        )
        ids = [c["id"] for c in mapping["criteria"]]
        assert len(set(ids)) == len(ids), ids
        # PassBar's own duplicate-id validator is the real bar; prove it passes.
        PassBar.model_validate(mapping)

    def test_the_bar_path_comes_from_the_enforcers_own_function(self, tmp_path):
        assert pass_bar_mint.pass_bar_path_for_fix_task(
            tmp_path, "TASK-ABC-001-x"
        ) == pass_bar_path_for(tmp_path, "TASK-ABC-001-x")

    def test_format_version_tracks_the_model(self, tmp_path):
        fix_task = tmp_path / "TASK-ABC-001-v.md"
        fix_task.write_text("## Acceptance Criteria\n\n- [ ] one\n", encoding="utf-8")
        mapping, _facts = pass_bar_mint.derive_pass_bar(
            fix_task_path=fix_task, task_id="TASK-ABC-001-v", registered_sha="a" * 40
        )
        assert mapping["format_version"] == PassBar.CURRENT_FORMAT_VERSION

    def test_an_unparseable_frontmatter_never_takes_the_mint_down(self, repo):
        _arm_enforcement(repo)
        backlog = repo / "tasks" / "backlog" / "hp"
        backlog.mkdir(parents=True)
        fix_task = backlog / "TASK-HPR-003-bad-frontmatter.md"
        fix_task.write_text(
            "---\nid: TASK-HPR-003\ntitle: broken: unquoted: colons\n---\n\n"
            "## Acceptance Criteria\n\n- [ ] Implementation complete\n",
            encoding="utf-8",
        )
        report = pass_bar_mint.mint_pass_bars(
            [fix_task], repo_root=repo, parent_review_id=REVIEW_TASK_ID
        )
        assert report.bars[0].status == "written"
        text = pass_bar_path_for(repo, fix_task.stem).read_text(encoding="utf-8")
        # Falls back to the caller-supplied parent review id, never a traceback.
        assert REVIEW_TASK_ID in text
        assert not isinstance(
            validate_instance("pass-bar", pass_bar_path_for(repo, fix_task.stem)),
            QAFormatError,
        )
