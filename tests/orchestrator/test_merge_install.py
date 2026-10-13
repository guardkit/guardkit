"""The merge installs before it checks, and its baseline is honest.

Design: ``docs/designs/factory-merge-install-and-honest-baseline-2026-10-13.md``
(ai-transition). Build E (FEAT-1F44) joined in a working folder that had no
installed dependencies: the merge never ran the project's declared install,
never applied its declared launch settings, and then recorded a failed run
that named no test as "0 failing, 0 passing".

Everything here runs on real code paths: real git repositories in
``tmp_path``, a working folder of their own (the shape Forge's join uses), and
a stand-in project whose install and check are small shell scripts. No
network, no mocks, and nothing here knows what stack a real project uses.

The stand-in project:

* ``deps.txt`` lists the dependencies, one per line;
* ``scripts/install.sh`` "installs" each one into ``installed/`` (git-ignored),
  refusing a dependency called ``forbidden`` the way a registry might;
* ``scripts/check.sh`` exits 1 unless every dependency is installed, then
  prints a pass line;
* the config declares ``toolchain.install``, ``toolchain.test`` and
  ``launch.scratch: [STANDIN_CACHE]`` (plus a ``launch.settings`` name).

Both scripts also leave marker files in a folder outside every repository, so
a test can prove that an install or a check did, or did not, run.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

import pytest

from guardkit.orchestrator.merge_executor import (
    OUTCOME_MERGED,
    OUTCOME_REFUSED,
    execute_merge,
    measure_pre_merge_baseline,
)

FEATURE = "FEAT-I"
TARGET = "factory-integration/FEAT-I"
CANNOT_FOLLOW = "uses shell syntax the factory cannot follow"
JUDGE_CHANGED = "the build changed the commands that judge it"

VALIDATE_OK = [
    sys.executable,
    "-c",
    "import json; print(json.dumps({'feature_id': 'FEAT-I', 'valid': True,"
    " 'errors': []}))",
]

SENTINELS = {
    "GUARDKIT_NATS_PASSWORD": "SENTINEL-nats-7f3a",
    "FLEET_MEMORY_PG_DSN": "SENTINEL-dsn-7f3a",
    "OPENAI_API_KEY": "SENTINEL-openai-7f3a",
    "FORGE_DB_PATH": "SENTINEL-forge-7f3a",
    "SSH_AUTH_SOCK": "SENTINEL-ssh-7f3a",
}

# ---------------------------------------------------------------------------
# The stand-in project
# ---------------------------------------------------------------------------

INSTALL_SH = """#!/bin/sh
set -e
echo install >> "@MARKERS@/install-ran"
env > "@MARKERS@/install.env"
echo "${STANDIN_CACHE:-}" >> "@MARKERS@/install-cache"
if [ -n "${STANDIN_CACHE:-}" ]; then echo filled > "$STANDIN_CACHE/filled"; fi
mkdir -p installed
while IFS= read -r dep; do
  [ -n "$dep" ] || continue
  if [ "$dep" = "forbidden" ]; then
    echo "the registry refused forbidden" >&2
    exit 4
  fi
  : > "installed/$dep"
done < deps.txt
"""

CHECK_SH = """#!/bin/sh
cd "$(dirname "$0")/.."
echo check >> "@MARKERS@/check-ran"
env > "@MARKERS@/check.env"
echo "${STANDIN_CACHE:-}" >> "@MARKERS@/check-cache"
while IFS= read -r dep; do
  [ -n "$dep" ] || continue
  if [ ! -f "installed/$dep" ]; then
    echo "not installed: $dep" >&2
    exit 1
  fi
done < deps.txt
echo "STANDIN-PASS every dependency is installed"
"""

# A branch's edit of a judge script: it would green itself, and it still
# leaves the marker, so running it at all would show.
ALWAYS_GREEN_SH = """#!/bin/sh
echo edited >> "@MARKERS@/check-ran"
echo edited >> "@MARKERS@/install-ran"
echo "STANDIN-PASS (edited to always pass)"
exit 0
"""


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


def config_text(
    install: Optional[str] = "bash scripts/install.sh",
    test: Optional[str] = "bash scripts/check.sh",
    extra_toolchain: str = "",
    launch: Optional[str] = (
        "launch:\n  scratch: [STANDIN_CACHE]\n  settings: [STANDIN_SETTING]\n"
    ),
) -> str:
    lines = ["toolchain:\n"]
    if install is not None:
        lines.append(f"  install: {json.dumps(install)}\n")
    if test is not None:
        lines.append(f"  test: {json.dumps(test)}\n")
    lines.append(extra_toolchain)
    if launch:
        lines.append(launch)
    return "".join(lines)


class Standin:
    """A stand-in repository, its marker folder and its join folder."""

    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path
        self.repo = tmp_path / "repo"
        self.markers = tmp_path / "markers"
        self.markers.mkdir()
        self.folder: Optional[Path] = None

    def script(self, body: str) -> str:
        return body.replace("@MARKERS@", str(self.markers))

    def write(self, rel: str, content: Optional[str], root: Optional[Path] = None) -> None:
        path = (root or self.repo) / rel
        if content is None:
            path.unlink()
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if rel.endswith(".sh"):
            path.chmod(0o755)

    def init(
        self,
        config: Optional[str] = None,
        files: Optional[Dict[str, Optional[str]]] = None,
        with_config: bool = True,
    ) -> "Standin":
        self.repo.mkdir()
        _git(self.repo, "init", "-q", "-b", "main")
        _git(self.repo, "config", "user.email", "t@t.t")
        _git(self.repo, "config", "user.name", "t")
        self.write(".gitignore", "installed/\n")
        self.write("deps.txt", "alpha\nbeta\n")
        self.write("notes.txt", "a tracked file\n")
        self.write("scripts/install.sh", self.script(INSTALL_SH))
        self.write("scripts/check.sh", self.script(CHECK_SH))
        if with_config:
            self.write(
                ".guardkit/config.yaml",
                config if config is not None else config_text(),
            )
        for rel, content in (files or {}).items():
            self.write(rel, content)
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "the target as it stands")
        return self

    def branch(self, changes: Dict[str, Optional[str]]) -> "Standin":
        _git(self.repo, "checkout", "-q", "-b", f"autobuild/{FEATURE}")
        for rel, content in changes.items():
            self.write(rel, content)
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "the build's work")
        _git(self.repo, "checkout", "-q", "main")
        return self

    def join_folder(self) -> Path:
        """A working folder of its own, at main, on the join branch."""
        g = _git(self.repo, "rev-parse", "main")
        folder = self.tmp_path / "join"
        _git(self.repo, "worktree", "add", "-q", "-b", TARGET, str(folder), g)
        self.folder = folder
        return folder

    def merge(self, **kwargs):
        folder = self.folder or self.join_folder()
        kwargs.setdefault("validate_command", VALIDATE_OK)
        kwargs.setdefault("verify_timeout", 60)
        return execute_merge(
            repo_root=self.repo,
            feature_id=FEATURE,
            target_branch=TARGET,
            working_folder=folder,
            **kwargs,
        )

    def ran(self) -> set:
        return {
            name
            for name in ("install-ran", "check-ran")
            if (self.markers / name).exists()
        }

    def lines(self, name: str) -> list:
        path = self.markers / name
        if not path.exists():
            return []
        return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln]

    def env_file(self, name: str) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for line in self.lines(name):
            key, _, value = line.partition("=")
            result[key] = value
        return result

    def git_dir(self) -> Path:
        assert self.folder is not None
        return Path(
            os.path.realpath(_git(self.folder, "rev-parse", "--absolute-git-dir"))
        )


@pytest.fixture
def standin(tmp_path: Path) -> Standin:
    return Standin(tmp_path)


def _report_text(report) -> str:
    return json.dumps(report.to_dict()) + "\n" + "\n".join(report.receipt_lines())


# ---------------------------------------------------------------------------
# 1-7: the install runs, on both trees, with the declared launch environment
# ---------------------------------------------------------------------------


class TestTheMergeInstallsFirst:
    def test_the_target_is_installed_before_the_baseline(self, standin: Standin):
        standin.init().branch({"feature.txt": "built\n"})

        report = standin.merge()

        assert report.outcome == OUTCOME_MERGED
        assert report.verify_status == "passed", report.verify_detail
        assert report.verify_ok is True
        # The baseline is a real measurement now: a passing run on the
        # installed target, not a failed run that named nothing.
        assert report.baseline_measured is not None
        notes = " ".join(report.notes)
        assert "bash scripts/install.sh" in notes
        assert f"ran on {TARGET}" in notes
        assert "ran on the merged result" in notes

    def test_a_dependency_the_branch_adds_is_installed_for_the_check(
        self, standin: Standin
    ):
        standin.init().branch(
            {"deps.txt": "alpha\nbeta\ngamma\n", "feature.txt": "built\n"}
        )

        report = standin.merge()

        assert report.verify_status == "passed", report.verify_detail
        # Installed twice: once on the target, once on the merged result.
        assert len(standin.lines("install-ran")) == 2
        assert (standin.folder / "installed" / "gamma").exists()

    def test_a_branch_cannot_change_the_install_that_judges_it(
        self, standin: Standin
    ):
        standin.init().branch(
            {
                ".guardkit/config.yaml": config_text(install="true"),
                "deps.txt": "alpha\nbeta\ngamma\n",
            }
        )

        report = standin.merge()

        assert report.verify_status == "passed", report.verify_detail
        assert len(standin.lines("install-ran")) == 2
        assert (standin.folder / "installed" / "gamma").exists()

    def test_a_failed_install_is_could_not_run(self, standin: Standin):
        failing_install = (
            "#!/bin/sh\n"
            'echo install >> "@MARKERS@/install-ran"\n'
            'echo "registry unreachable" >&2\n'
            "exit 3\n"
        )
        standin.init(
            files={"scripts/install.sh": standin.script(failing_install)}
        ).branch({"feature.txt": "built\n"})

        report = standin.merge()

        assert report.outcome == OUTCOME_MERGED
        assert report.verify_status == "unverified"
        assert report.verify_ran is False
        assert report.baseline_measured is None
        assert "registry unreachable" in report.verify_detail
        assert "exit 3" in report.verify_detail
        assert "bash scripts/install.sh" in report.verify_detail
        assert "check-ran" not in standin.ran()

    def test_an_install_that_fails_only_after_the_join_is_could_not_run(
        self, standin: Standin
    ):
        standin.init().branch({"deps.txt": "alpha\nbeta\nforbidden\n"})

        report = standin.merge()

        assert report.outcome == OUTCOME_MERGED
        assert report.verify_status == "unverified", report.verify_detail
        assert report.verify_status != "failed"
        assert "the registry refused forbidden" in report.verify_detail
        assert "merged result" in report.verify_detail
        assert report.verify_ok is False

    def test_install_and_check_share_the_declared_launch_environment(
        self, standin: Standin, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("STANDIN_SETTING", "carried-through")
        standin.init().branch({"feature.txt": "built\n"})

        report = standin.merge()

        assert report.verify_status == "passed", report.verify_detail
        caches = set(standin.lines("install-cache") + standin.lines("check-cache"))
        assert len(caches) == 1, caches
        cache = Path(caches.pop())
        assert cache.is_dir()
        assert Path(os.path.realpath(cache)).is_relative_to(standin.git_dir())
        assert (cache / "filled").exists()
        assert standin.env_file("check.env").get("STANDIN_SETTING") == (
            "carried-through"
        )
        assert _git(standin.folder, "status", "--porcelain") == ""

    def test_an_install_that_changes_tracked_files_refuses_the_merge(
        self, standin: Standin
    ):
        dirtying_install = (
            "#!/bin/sh\n"
            'echo install >> "@MARKERS@/install-ran"\n'
            "echo changed >> notes.txt\n"
        )
        standin.init(
            files={"scripts/install.sh": standin.script(dirtying_install)}
        ).branch({"feature.txt": "built\n"})
        g = _git(standin.repo, "rev-parse", "main")

        report = standin.merge()

        assert report.outcome == OUTCOME_REFUSED
        assert "changed files" in (report.refusal_reason or "")
        assert "notes.txt" in (report.refusal_reason or "")
        # Nothing was joined.
        assert _git(standin.repo, "rev-parse", TARGET) == g
        assert "check-ran" not in standin.ran()


# ---------------------------------------------------------------------------
# 8, 9 and decision 3: an honest baseline
# ---------------------------------------------------------------------------


class TestAnHonestBaseline:
    def test_a_red_baseline_that_names_nothing_is_not_a_measurement(
        self, standin: Standin
    ):
        # The design's example command, ``sh -c 'exit 1'``, is itself refused
        # by item 2b (a word with a space in it), so the merge half of this
        # test uses ``false``: a plain word that also fails naming nothing.
        standin.init(config=config_text(install=None, test="false", launch=None))
        standin.branch({"feature.txt": "built\n"})
        folder = standin.join_folder()

        measured = measure_pre_merge_baseline(
            folder,
            TARGET,
            resolved_command=("sh -c 'exit 1'", "repository toolchain declaration", None),
        )
        assert measured.ran is False
        assert "measured nothing" in measured.detail
        assert "exit 1" in measured.detail

        report = standin.merge()

        assert report.verify_status == "unverified"
        assert report.verify_ran is False
        assert report.baseline_measured is None
        assert "measured nothing" in report.verify_detail
        notes = " ".join(report.notes)
        assert "0 failing, 0 passing" not in notes
        assert "measured nothing" in notes

    def test_no_install_and_no_launch_block_runs_exactly_as_before(
        self, tmp_path: Path
    ):
        """A pytest-shaped project without either block: the red baseline
        names its failure and the clean branch merges green, as before."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "config", "user.email", "t@t.t")
        _git(repo, "config", "user.name", "t")
        (repo / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
        (repo / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
        (repo / "tests").mkdir()
        (repo / "tests" / "test_a.py").write_text(
            "def test_green():\n    assert True\n\n\n"
            "def test_old_red():\n    assert False\n",
            encoding="utf-8",
        )
        (repo / ".guardkit").mkdir()
        command = f'"{sys.executable}" -m pytest -q -p no:cacheprovider tests/'
        (repo / ".guardkit" / "config.yaml").write_text(
            f"toolchain:\n  test: {json.dumps(command)}\n", encoding="utf-8"
        )
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "base")
        _git(repo, "checkout", "-q", "-b", f"autobuild/{FEATURE}")
        (repo / "tests" / "test_b.py").write_text(
            "def test_new():\n    assert True\n", encoding="utf-8"
        )
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "work")
        _git(repo, "checkout", "-q", "main")

        report = execute_merge(repo, FEATURE, validate_command=VALIDATE_OK)

        assert report.verify_status == "passed", report.verify_detail
        assert report.verify_suite_status == "failed"
        assert report.baseline_measured is not None
        assert report.baseline_measured.failing == (
            "tests/test_a.py::test_old_red",
        )
        assert report.verify_command == command

    @pytest.mark.parametrize("measure", [True, False])
    def test_a_declared_marker_a_passing_check_does_not_print_measured_nothing(
        self, standin: Standin, measure: bool
    ):
        standin.init(
            config=config_text(
                install=None,
                extra_toolchain='  ran_marker_regex: "NEVER-PRINTED"\n',
                launch=None,
            ),
            files={"deps.txt": ""},
        ).branch({"feature.txt": "built\n"})

        if measure:
            report = standin.merge()
        else:
            report = standin.merge(baseline_failing=[])

        assert report.verify_status == "unverified", report.verify_detail
        assert "measured nothing" in report.verify_detail
        assert report.verify_ok is False

    def test_a_declared_marker_that_matches_is_a_pass(self, standin: Standin):
        standin.init(
            config=config_text(
                install=None,
                extra_toolchain='  ran_marker_regex: "STANDIN-PASS"\n',
                launch=None,
            ),
            files={"deps.txt": ""},
        ).branch({"feature.txt": "built\n"})

        report = standin.merge()

        assert report.verify_status == "passed", report.verify_detail

    def test_without_a_declared_marker_a_pass_is_unchanged(self, standin: Standin):
        standin.init(
            config=config_text(install=None, launch=None), files={"deps.txt": ""}
        ).branch({"feature.txt": "built\n"})

        report = standin.merge()

        assert report.verify_status == "passed", report.verify_detail


# ---------------------------------------------------------------------------
# 12-15: the branch may not change the files that judge it
# ---------------------------------------------------------------------------


class TestTheJudgeFiles:
    def test_a_branch_that_edits_the_check_script_gets_no_automatic_verdict(
        self, standin: Standin
    ):
        standin.init()
        standin.branch({"scripts/check.sh": standin.script(ALWAYS_GREEN_SH)})

        report = standin.merge()

        assert report.outcome == OUTCOME_MERGED
        assert report.verify_status == "unverified"
        assert report.verify_ran is False
        assert JUDGE_CHANGED in report.verify_detail
        assert "scripts/check.sh" in report.verify_detail
        assert standin.ran() == set()

    def test_a_branch_that_edits_the_install_script_gets_no_automatic_verdict(
        self, standin: Standin
    ):
        standin.init()
        standin.branch({"scripts/install.sh": standin.script(ALWAYS_GREEN_SH)})

        report = standin.merge()

        assert report.verify_status == "unverified"
        assert JUDGE_CHANGED in report.verify_detail
        assert "scripts/install.sh" in report.verify_detail
        assert standin.ran() == set()

    def test_a_branch_that_adds_a_new_judge_script_counts(self, standin: Standin):
        standin.init(files={"scripts/check.sh": None})
        standin.branch({"scripts/check.sh": standin.script(ALWAYS_GREEN_SH)})

        report = standin.merge()

        assert report.verify_status == "unverified"
        assert JUDGE_CHANGED in report.verify_detail
        assert "scripts/check.sh" in report.verify_detail
        assert standin.ran() == set()

    @pytest.mark.parametrize(
        "check", ["bash scripts/check.sh&&echo DONE", "cd scripts && ./check.sh"]
    )
    def test_a_compound_command_still_finds_the_changed_script(
        self, standin: Standin, check: str
    ):
        standin.init(config=config_text(test=check))
        standin.branch({"scripts/check.sh": standin.script(ALWAYS_GREEN_SH)})

        report = standin.merge()

        assert report.verify_status == "unverified"
        assert "scripts/check.sh" in report.verify_detail
        assert standin.ran() == set()

    def test_a_named_test_folder_does_not_stop_the_verdict(self, standin: Standin):
        run_tests = (
            "#!/bin/sh\n"
            'for t in "$1"/*.sh; do bash "$t" || exit 1; done\n'
            'echo "STANDIN-PASS every test passed"\n'
        )
        standin.init(
            config=config_text(test="bash run-tests.sh tests"),
            files={
                "run-tests.sh": run_tests,
                "tests/test_old.sh": "#!/bin/sh\nexit 0\n",
            },
        )
        standin.branch({"tests/test_new.sh": "#!/bin/sh\nexit 0\n"})

        report = standin.merge()

        assert report.verify_status == "passed", report.verify_detail

    def test_quoting_and_escaping_do_not_hide_the_changed_script(
        self, standin: Standin
    ):
        standin.init(config=config_text(test='bash scripts/che"ck".sh'))
        standin.branch({"scripts/check.sh": standin.script(ALWAYS_GREEN_SH)})

        report = standin.merge()

        assert report.verify_status == "unverified"
        assert "scripts/check.sh" in report.verify_detail
        assert standin.ran() == set()

    CANNOT_FOLLOW_CASES = [
        ("bash $CHECK_SCRIPT", ("check", "install")),
        ("bash `echo scripts/check.sh`", ("check", "install")),
        ("bash scripts/*.sh", ("check", "install")),
        ("bash scripts/{check,lint}.sh", ("check", "install")),
        ("bash scripts/check#suite.sh", ("check", "install")),
        ("bash scripts/check\\ suite.sh", ("check", "install")),
        ("sh -c 'bash scripts/check.sh && echo DONE'", ("check", "install")),
        ("sh -c 'scripts/check.sh&&true'", ("check", "install")),
        ("bash scripts/check;suite.sh", ("install",)),
        ('bash "scripts/check.sh', ("check", "install")),
    ]

    @pytest.mark.parametrize(
        "command,role",
        [
            (command, role)
            for command, roles in CANNOT_FOLLOW_CASES
            for role in roles
        ],
    )
    def test_a_command_the_factory_cannot_follow_gets_no_automatic_verdict(
        self, standin: Standin, command: str, role: str
    ):
        if role == "check":
            config = config_text(test=command)
        else:
            config = config_text(install=command)
        standin.init(config=config)
        standin.branch({"deps.txt": "alpha\nbeta\n\n"})

        report = standin.merge()

        assert report.outcome == OUTCOME_MERGED
        assert report.verify_status == "unverified"
        assert report.verify_ran is False
        assert CANNOT_FOLLOW in report.verify_detail
        assert standin.ran() == set()

    @pytest.mark.parametrize("role", ["check", "install"])
    def test_a_script_whose_name_has_an_equals_sign_is_still_matched(
        self, standin: Standin, role: str
    ):
        if role == "check":
            config = config_text(test="bash check=suite.sh")
        else:
            config = config_text(install="bash check=suite.sh")
        standin.init(
            config=config, files={"check=suite.sh": "#!/bin/sh\nexit 0\n"}
        )
        standin.branch({"check=suite.sh": standin.script(ALWAYS_GREEN_SH)})

        report = standin.merge()

        assert report.verify_status == "unverified"
        assert JUDGE_CHANGED in report.verify_detail
        assert "check=suite.sh" in report.verify_detail
        assert standin.ran() == set()

    def test_the_commands_in_use_today_are_accepted(self):
        from guardkit.orchestrator.merge_environment import judge_words

        # Copied from the declarations on 13 October 2026: api_test's
        # .guardkit/config.yaml, and guardkit/react-go-notes-fixture's
        # (root install and test, and its two components' tests).
        test_commands = [
            "qa/run-suite.sh",
            "bash scripts/check.sh",
            "npm run test",
            "GOTOOLCHAIN=local GOWORK=off GOFLAGS=-mod=readonly go test -race "
            "-count=1 -v ./...",
        ]
        install_commands = ["bash scripts/install.sh"]
        for command in test_commands:
            words, refusal = judge_words(command, through_shell=True)
            assert refusal is None, (command, refusal)
            assert words
        for command in install_commands:
            words, refusal = judge_words(command, through_shell=False)
            assert refusal is None, (command, refusal)
            assert words == ("bash", "scripts/install.sh")

    def test_a_branch_that_only_adds_a_dependency_gets_a_normal_verdict(
        self, standin: Standin
    ):
        standin.init().branch({"deps.txt": "alpha\nbeta\ngamma\n"})

        report = standin.merge()

        assert report.verify_status == "passed", report.verify_detail


# ---------------------------------------------------------------------------
# 16-18: a minimal environment, with no factory credentials
# ---------------------------------------------------------------------------


class TestNoFactoryCredentials:
    def test_install_and_check_never_see_factory_credentials(
        self, standin: Standin, monkeypatch: pytest.MonkeyPatch
    ):
        for name, value in SENTINELS.items():
            monkeypatch.setenv(name, value)
        monkeypatch.setenv("STANDIN_SETTING", "declared-and-set")
        standin.init().branch({"feature.txt": "built\n"})

        report = standin.merge()

        assert report.verify_status == "passed", report.verify_detail
        scratch = standin.git_dir() / "guardkit-scratch"
        for name in ("install.env", "check.env"):
            text = (standin.markers / name).read_text(encoding="utf-8")
            for value in SENTINELS.values():
                assert value not in text, (name, value)
            env = standin.env_file(name)
            for reserved in ("HOME", "TMPDIR"):
                assert Path(os.path.realpath(env[reserved])).is_relative_to(
                    scratch
                ), (name, reserved, env[reserved])
            assert env.get("STANDIN_SETTING") == "declared-and-set"

    def test_a_failing_install_receipt_carries_no_credential(
        self, standin: Standin, monkeypatch: pytest.MonkeyPatch
    ):
        for name, value in SENTINELS.items():
            monkeypatch.setenv(name, value)
        noisy_install = "#!/bin/sh\nenv >&2\nexit 1\n"
        standin.init(files={"scripts/install.sh": noisy_install}).branch(
            {"feature.txt": "built\n"}
        )

        report = standin.merge()

        assert report.verify_status == "unverified"
        assert "exit 1" in report.verify_detail
        text = _report_text(report)
        for value in SENTINELS.values():
            assert value not in text

    def test_the_run_owner_marker_reaches_install_and_check(
        self, standin: Standin, monkeypatch: pytest.MonkeyPatch
    ):
        """Forge's stop sweep finds leftover processes by this build id."""
        monkeypatch.setenv("GUARDKIT_RUN_OWNER", "build-x")
        standin.init().branch({"feature.txt": "built\n"})

        report = standin.merge()

        assert report.verify_status == "passed", report.verify_detail
        assert standin.env_file("install.env").get("GUARDKIT_RUN_OWNER") == "build-x"
        assert standin.env_file("check.env").get("GUARDKIT_RUN_OWNER") == "build-x"

    def test_a_factory_set_value_arrives_and_a_credential_shaped_one_is_refused(
        self, standin: Standin, monkeypatch: pytest.MonkeyPatch
    ):
        from guardkit.orchestrator.project_command_env import (
            project_command_environment,
        )

        for name, value in SENTINELS.items():
            monkeypatch.setenv(name, value)
        standin.init()
        folder = standin.join_folder()

        env = project_command_environment(
            folder, None, named={"GUARDKIT_FEATURE_ID": "FEAT-I"}
        )
        assert env["GUARDKIT_FEATURE_ID"] == "FEAT-I"
        for value in SENTINELS.values():
            assert value not in env.values()

        for bad in ("SERVICE_TOKEN", "DB_PASSWORD", "OPENAI_API_KEY", "x y"):
            with pytest.raises(ValueError):
                project_command_environment(folder, None, named={bad: "v"})

    def test_an_addition_may_not_set_the_run_owner(
        self, standin: Standin, monkeypatch: pytest.MonkeyPatch
    ):
        from guardkit.orchestrator.project_command_env import (
            project_command_environment,
        )

        monkeypatch.setenv("GUARDKIT_RUN_OWNER", "build-x")
        standin.init()
        folder = standin.join_folder()

        for name in ("GUARDKIT_RUN_OWNER", "guardkit_run_owner"):
            with pytest.raises(ValueError):
                project_command_environment(folder, None, named={name: "build-forged"})
        env = project_command_environment(folder, None)
        assert env["GUARDKIT_RUN_OWNER"] == "build-x"

    def test_without_a_parent_marker_there_is_no_run_owner(
        self, standin: Standin, monkeypatch: pytest.MonkeyPatch
    ):
        from guardkit.orchestrator.project_command_env import (
            project_command_environment,
        )

        monkeypatch.delenv("GUARDKIT_RUN_OWNER", raising=False)
        standin.init()
        folder = standin.join_folder()

        env = project_command_environment(
            folder, None, named={"GUARDKIT_FEATURE_ID": "FEAT-I"}
        )
        assert "GUARDKIT_RUN_OWNER" not in env
        assert not any(key.upper() == "GUARDKIT_RUN_OWNER" for key in env)

    def test_a_proxy_with_credentials_is_not_passed(
        self, standin: Standin, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("HTTPS_PROXY", "http://u:SENTINEL-proxy-7f3a@proxy:3128")
        standin.init().branch({"feature.txt": "built\n"})

        report = standin.merge()

        assert report.verify_status == "unverified"
        assert report.verify_ran is False
        assert "HTTPS_PROXY" in report.verify_detail
        assert "SENTINEL-proxy-7f3a" not in _report_text(report)
        assert standin.ran() == set()


# ---------------------------------------------------------------------------
# 19-20: the merge reads declarations fail-closed
# ---------------------------------------------------------------------------

_VALID_TOOLCHAIN = config_text(launch=None)

INVALID_DECLARATIONS = {
    "install_timeout zero": config_text(extra_toolchain="  install_timeout: 0\n"),
    "install_timeout text": config_text(
        extra_toolchain='  install_timeout: "abc"\n'
    ),
    "regex that does not compile": config_text(
        extra_toolchain='  ran_marker_regex: "("\n'
    ),
    "test is a number": config_text(test=None, extra_toolchain="  test: 5\n"),
    "install is a list": config_text(
        install=None, extra_toolchain="  install: [a, b]\n"
    ),
    "toolchain is text": 'toolchain: "text"\n',
    "launch settings is text": _VALID_TOOLCHAIN
    + 'launch:\n  settings: "PATH_X"\n',
    "top level is a list": "- toolchain\n- launch\n",
    "broken yaml": "toolchain:\n  test: [unclosed\n",
}


class TestDeclarationsAreReadFailClosed:
    @pytest.mark.parametrize(
        "config", list(INVALID_DECLARATIONS.values()), ids=list(INVALID_DECLARATIONS)
    )
    def test_an_invalid_declaration_is_could_not_run(
        self, standin: Standin, config: str
    ):
        # pyproject.toml and tests/ tempt the Python stack default.
        standin.init(
            config=config,
            files={
                "pyproject.toml": "[project]\nname = 'standin'\n",
                "tests/test_x.py": "def test_x():\n    assert True\n",
            },
        ).branch({"feature.txt": "built\n"})

        report = standin.merge()

        assert report.outcome == OUTCOME_MERGED
        assert report.verify_status == "unverified"
        assert report.verify_ran is False
        assert "config.yaml" in report.verify_detail
        assert standin.ran() == set()
        assert report.verify_command is None
        assert "stack default" not in (report.verify_source or "")

    @pytest.mark.parametrize("shape", ["no file", "empty file", "no keys"])
    def test_a_missing_or_empty_declaration_is_today_behaviour(
        self, standin: Standin, shape: str
    ):
        if shape == "no file":
            standin.init(with_config=False)
        elif shape == "empty file":
            standin.init(config="")
        else:
            standin.init(config="qa:\n  enforce_tier1: false\n")
        standin.branch({"feature.txt": "built\n"})

        report = standin.merge()

        # No declared command and no stack markers: exactly today's answer.
        assert report.outcome == OUTCOME_MERGED
        assert report.verify_command is None
        assert report.verify_source == "no test runner detected"
        assert report.verify_status == "unverified"
        assert report.verify_ran is False
        assert standin.ran() == set()
