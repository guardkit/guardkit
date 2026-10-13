"""The merge installs before it checks, and its baseline is honest.

The merge design of 13 October 2026. A factory build was joined in a working
folder that had no installed dependencies: the merge never ran the project's declared install,
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
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

import pytest

from tests.self_contained_python import self_contained_python
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
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """A pytest-shaped project without either block: the red baseline
        names its failure and the clean branch merges green, as before.

        The design's premise, corrected: an interpreter on PATH that carries
        its own packages is found, because the merge keeps GuardKit's PATH.
        One that finds its packages only through the real HOME is not (see
        the next test); this one is this session's interpreter made
        independent of HOME (``tests.self_contained_python``).
        """
        python = Path(self_contained_python())
        monkeypatch.setenv(
            "PATH", f"{python.parent}{os.pathsep}{os.environ.get('PATH', '')}"
        )
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
        command = f"{python.name} -m pytest -q -p no:cacheprovider tests/"
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

    def test_a_package_only_in_the_real_homes_user_site_is_not_visible(
        self, standin: Standin, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """The private HOME is deliberate: the check cannot read the user's
        own folders (~/.docker/config.json, ~/.git-credentials, ~/.netrc),
        and so it cannot use a package found only in the user's site folder
        either. The result is a plain "could not run" that names nothing
        from that folder."""
        home = tmp_path / "real-home"
        candidates = [sys.executable, getattr(sys, "_base_executable", "")]
        candidates += [shutil.which("python3") or ""]
        python = None
        for candidate in [c for c in candidates if c]:
            version = subprocess.run(
                [candidate, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
                capture_output=True, text=True,
            ).stdout.strip()
            user_site = home / ".local" / "lib" / f"python{version}" / "site-packages"
            user_site.mkdir(parents=True, exist_ok=True)
            (user_site / "standin_only_in_home.py").write_text(
                "VALUE = 1\n", encoding="utf-8"
            )
            control = subprocess.run(
                [candidate, "-c", "import standin_only_in_home"],
                env={"PATH": os.environ.get("PATH", ""), "HOME": str(home)},
                capture_output=True,
            )
            if control.returncode == 0:
                python = candidate
                break
        if python is None:
            pytest.skip("no interpreter here reads a user site folder")
        # The control above: with the real HOME the package IS importable.
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("GUARDKIT_NATS_PASSWORD", SENTINELS["GUARDKIT_NATS_PASSWORD"])
        check = (
            "#!/bin/sh\n"
            f'"{python}" -c "import standin_only_in_home" || exit 1\n'
            'echo "STANDIN-PASS"\n'
        )
        standin.init(
            config=config_text(install=None, launch=None),
            files={"scripts/check.sh": check, "deps.txt": ""},
        ).branch({"feature.txt": "built\n"})

        report = standin.merge()

        assert report.outcome == OUTCOME_MERGED
        assert report.verify_status == "unverified", report.verify_detail
        assert report.verify_ran is False
        assert "measured nothing" in report.verify_detail
        text = _report_text(report)
        assert str(home) not in text
        assert "standin_only_in_home" not in text
        assert SENTINELS["GUARDKIT_NATS_PASSWORD"] not in text

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

        # Copied on 13 October 2026 from the declarations of the two projects
        # the factory builds today: a Python service's test script, and a
        # web-and-Go project's root install and test and its two components'
        # tests.
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
            folder, None, additions={"GUARDKIT_FEATURE_ID": "FEAT-I"}
        )
        assert env["GUARDKIT_FEATURE_ID"] == "FEAT-I"
        for value in SENTINELS.values():
            assert value not in env.values()

        for bad in ("SERVICE_TOKEN", "DB_PASSWORD", "OPENAI_API_KEY", "x y"):
            with pytest.raises(ValueError):
                project_command_environment(folder, None, additions={bad: "v"})

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
                project_command_environment(folder, None, additions={name: "build-forged"})
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
            folder, None, additions={"GUARDKIT_FEATURE_ID": "FEAT-I"}
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



PROXY_SENTINEL = "SENTINEL-proxy-9c1e"
CREDENTIAL_PROXY = f"http://u:{PROXY_SENTINEL}@proxy.invalid:3128"


class TestTheProxyCheckCoversTheWholeEnvironment:
    """The credential-bearing-proxy check runs on the composed environment."""

    @pytest.mark.parametrize(
        "name", ["HTTPS_PROXY", "https_proxy", "FTP_PROXY", "ftp_proxy"]
    )
    def test_a_declared_proxy_with_credentials_is_refused_by_name_only(
        self, standin: Standin, monkeypatch: pytest.MonkeyPatch, name: str
    ):
        monkeypatch.setenv(name, CREDENTIAL_PROXY)
        standin.init(
            config=config_text(
                launch=(
                    "launch:\n  scratch: [STANDIN_CACHE]\n"
                    f"  settings: [STANDIN_SETTING, {name}]\n"
                )
            )
        ).branch({"feature.txt": "built\n"})

        report = standin.merge()

        assert report.verify_status == "unverified", report.verify_detail
        assert report.verify_ran is False
        assert name in report.verify_detail
        text = _report_text(report)
        assert PROXY_SENTINEL not in text
        assert "u:" not in report.verify_detail
        assert standin.ran() == set()

    def test_a_declared_proxy_without_credentials_passes(
        self, standin: Standin, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("FTP_PROXY", "http://proxy.invalid:3128")
        standin.init(
            config=config_text(
                launch=(
                    "launch:\n  scratch: [STANDIN_CACHE]\n"
                    "  settings: [STANDIN_SETTING, FTP_PROXY]\n"
                )
            )
        ).branch({"feature.txt": "built\n"})

        report = standin.merge()

        assert report.verify_status == "passed", report.verify_detail
        assert standin.env_file("check.env").get("FTP_PROXY") == (
            "http://proxy.invalid:3128"
        )

    @pytest.mark.parametrize("where", ["additions", "overlay"])
    @pytest.mark.parametrize("name", ["HTTPS_PROXY", "https_proxy", "all_proxy"])
    def test_an_added_proxy_with_credentials_is_refused_by_name_only(
        self, standin: Standin, where: str, name: str
    ):
        from guardkit.orchestrator.launch_declaration import LaunchEnvironmentError
        from guardkit.orchestrator.project_command_env import (
            project_command_environment,
        )

        standin.init()
        folder = standin.join_folder()

        with pytest.raises(LaunchEnvironmentError) as caught:
            project_command_environment(folder, None, **{where: {name: CREDENTIAL_PROXY}})
        assert name in str(caught.value)
        assert PROXY_SENTINEL not in str(caught.value)

    def test_an_added_proxy_without_credentials_passes(self, standin: Standin):
        from guardkit.orchestrator.project_command_env import (
            project_command_environment,
        )

        standin.init()
        folder = standin.join_folder()

        env = project_command_environment(
            folder, None, additions={"HTTPS_PROXY": "http://proxy.invalid:3128"}
        )
        assert env["HTTPS_PROXY"] == "http://proxy.invalid:3128"


class TestTheBuildOrder:
    """Base, additions, overlay, proxy check, run-owner marker last."""

    def test_an_overlay_value_arrives(self, standin: Standin):
        from guardkit.orchestrator.project_command_env import (
            project_command_environment,
        )

        standin.init()
        folder = standin.join_folder()

        env = project_command_environment(
            folder, None, overlay={"APP_MODE": "test"}
        )
        assert env["APP_MODE"] == "test"

    @pytest.mark.parametrize(
        "name",
        ["GUARDKIT_RUN_OWNER", "SERVICE_TOKEN", "DB_PASSWORD", "OPENAI_API_KEY", "PATH"],
    )
    def test_an_overlay_may_not_set_a_reserved_or_credential_name(
        self, standin: Standin, monkeypatch: pytest.MonkeyPatch, name: str
    ):
        from guardkit.orchestrator.launch_declaration import LaunchEnvironmentError
        from guardkit.orchestrator.project_command_env import (
            project_command_environment,
        )

        monkeypatch.setenv("GUARDKIT_RUN_OWNER", "build-x")
        standin.init()
        folder = standin.join_folder()

        with pytest.raises(LaunchEnvironmentError) as caught:
            project_command_environment(folder, None, overlay={name: "v-overlay"})
        assert name in str(caught.value)

    def test_an_overlay_may_not_replace_an_addition_or_a_scratch_folder(
        self, standin: Standin
    ):
        from guardkit.orchestrator.launch_declaration import (
            LaunchDeclaration,
            LaunchEnvironmentError,
        )
        from guardkit.orchestrator.project_command_env import (
            project_command_environment,
        )

        standin.init()
        folder = standin.join_folder()
        declaration = LaunchDeclaration(scratch=("STANDIN_CACHE",))

        with pytest.raises(LaunchEnvironmentError):
            project_command_environment(
                folder,
                declaration,
                additions={"GIT_CEILING_DIRECTORIES": "/a"},
                overlay={"GIT_CEILING_DIRECTORIES": "/b"},
            )
        with pytest.raises(LaunchEnvironmentError):
            project_command_environment(
                folder, declaration, overlay={"STANDIN_CACHE": "/elsewhere"}
            )

    def test_an_addition_may_not_be_credential_shaped(self, standin: Standin):
        from guardkit.orchestrator.project_command_env import (
            project_command_environment,
        )

        standin.init()
        folder = standin.join_folder()

        for bad in ("GUARDKIT_RUN_OWNER", "SERVICE_TOKEN", "API_SECRET"):
            with pytest.raises(ValueError):
                project_command_environment(folder, None, additions={bad: "v"})

    def test_the_run_owner_is_applied_last_from_the_parent(
        self, standin: Standin, monkeypatch: pytest.MonkeyPatch
    ):
        from guardkit.orchestrator.project_command_env import (
            finish_project_environment,
        )

        monkeypatch.setenv("GUARDKIT_RUN_OWNER", "build-x")
        finished = finish_project_environment(
            {"PATH": "/bin", "GUARDKIT_RUN_OWNER": "left-behind"},
            additions={"GIT_CEILING_DIRECTORIES": "/a"},
            overlay={"APP_MODE": "test"},
        )
        assert finished["GUARDKIT_RUN_OWNER"] == "build-x"
        assert finished["APP_MODE"] == "test"

        monkeypatch.delenv("GUARDKIT_RUN_OWNER")
        finished = finish_project_environment(
            {"PATH": "/bin", "GUARDKIT_RUN_OWNER": "left-behind"}
        )
        assert "GUARDKIT_RUN_OWNER" not in finished

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
    # Present but empty is not the same as absent (implementation review R1).
    "toolchain is null": "toolchain: null\n",
    "toolchain is bare": "toolchain:\n",
    "launch is null": _VALID_TOOLCHAIN + "launch: null\n",
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


# ---------------------------------------------------------------------------
# Follow-up pass (coach findings, 13 October 2026)
# ---------------------------------------------------------------------------


def _still_running(pid: int, wait: float = 3.0) -> bool:
    """True while ``pid`` is a live process (a zombie counts as gone)."""
    import time

    deadline = time.monotonic() + wait
    while True:
        try:
            with open(f"/proc/{pid}/stat", encoding="utf-8") as handle:
                state = handle.read().rsplit(")", 1)[1].split()[0]
        except (FileNotFoundError, ProcessLookupError, IndexError):
            return False
        if state == "Z":
            return False
        if time.monotonic() >= deadline:
            return True
        time.sleep(0.1)


def _kill_quietly(pid: int) -> None:
    import signal

    try:
        os.kill(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


class TestNothingOutlivesATimeout:
    def test_a_timed_out_install_leaves_nothing_running(self, standin: Standin):
        hanging_install = (
            "#!/bin/sh\n"
            'sleep 37 &\n'
            'echo $! > "@MARKERS@/background.pid"\n'
            "sleep 37\n"
        )
        standin.init(
            files={"scripts/install.sh": standin.script(hanging_install)}
        ).branch({"feature.txt": "built\n"})

        report = standin.merge(verify_timeout=2)

        pid = int(standin.lines("background.pid")[0])
        try:
            assert report.verify_status == "unverified"
            assert "ran out of its 2 seconds" in report.verify_detail
            assert not _still_running(pid), "the install's child outlived the merge"
        finally:
            _kill_quietly(pid)

    def test_a_timed_out_check_leaves_nothing_running(self, standin: Standin):
        hanging_check = (
            "#!/bin/sh\n"
            'sleep 37 &\n'
            'echo $! > "@MARKERS@/background.pid"\n'
            "sleep 37\n"
        )
        standin.init(
            config=config_text(install=None, launch=None),
            files={"scripts/check.sh": standin.script(hanging_check)},
        ).branch({"feature.txt": "built\n"})

        report = standin.merge(verify_timeout=2)

        pid = int(standin.lines("background.pid")[0])
        try:
            assert report.verify_status == "unverified"
            assert not _still_running(pid), "the check's child outlived the merge"
        finally:
            _kill_quietly(pid)


class TestInstallPathsTheCoachProvedByHand:
    def test_an_install_that_times_out_before_the_merge_is_could_not_run(
        self, standin: Standin
    ):
        slow_install = "#!/bin/sh\nexec sleep 30\n"
        standin.init(files={"scripts/install.sh": slow_install}).branch(
            {"feature.txt": "built\n"}
        )

        report = standin.merge(verify_timeout=2)

        assert report.outcome == OUTCOME_MERGED
        assert report.verify_status == "unverified"
        assert report.verify_ran is False
        assert report.baseline_measured is None
        assert "ran out of its 2 seconds" in report.verify_detail
        assert TARGET in report.verify_detail
        assert "check-ran" not in standin.ran()

    @pytest.mark.parametrize("how", ["baseline off", "baseline handed in"])
    def test_a_single_install_when_no_baseline_is_measured(
        self, standin: Standin, how: str
    ):
        standin.init().branch({"deps.txt": "alpha\nbeta\ngamma\n"})

        if how == "baseline off":
            report = standin.merge(measure_baseline=False)
        else:
            report = standin.merge(baseline_failing=[])

        assert report.verify_status == "passed", report.verify_detail
        assert len(standin.lines("install-ran")) == 1
        assert len(standin.lines("check-ran")) == 1
        notes = " ".join(report.notes)
        assert "ran on the merged result" in notes
        assert f"ran on {TARGET}" not in notes

    def test_an_install_that_dirties_the_merged_tree_is_could_not_run(
        self, standin: Standin
    ):
        dirtying_on_merged = (
            "#!/bin/sh\n"
            'echo install >> "@MARKERS@/install-ran"\n'
            "if grep -qx dirty deps.txt; then echo changed >> notes.txt; fi\n"
            "mkdir -p installed\n"
        )
        standin.init(
            config=config_text(launch=None),
            files={
                "scripts/install.sh": standin.script(dirtying_on_merged),
                "deps.txt": "",
            },
        ).branch({"deps.txt": "dirty\n"})

        report = standin.merge()

        # Not a refusal: the join has already happened by then.
        assert report.outcome == OUTCOME_MERGED
        assert report.verify_status == "unverified"
        assert report.verify_ran is False
        assert "changed files" in report.verify_detail
        assert "notes.txt" in report.verify_detail
        assert "merged result" in report.verify_detail
        assert len(standin.lines("install-ran")) == 2
        assert "check-ran" in standin.ran()  # the baseline ran; nothing after

    def test_an_install_command_that_cannot_start_is_could_not_run(
        self, standin: Standin
    ):
        standin.init(
            config=config_text(install="no-such-installer-7f3a scripts/install.sh")
        ).branch({"feature.txt": "built\n"})

        report = standin.merge()

        assert report.outcome == OUTCOME_MERGED
        assert report.verify_status == "unverified"
        assert report.verify_ran is False
        assert "could not start" in report.verify_detail
        assert "no-such-installer-7f3a" in report.verify_detail
        assert standin.ran() == set()


class TestJudgeFilesInsideOptionLists:
    @pytest.mark.parametrize("separator", [",", ":"])
    def test_a_changed_script_named_inside_an_option_list_is_found(
        self, standin: Standin, separator: str
    ):
        run_all = '#!/bin/sh\necho "STANDIN-PASS"\n'
        standin.init(
            config=config_text(
                install=None, test=f"bash run-all.sh --with=a{separator}check.sh"
            ),
            files={"run-all.sh": run_all},
        )
        standin.branch({"scripts/check.sh": standin.script(ALWAYS_GREEN_SH)})

        report = standin.merge()

        assert report.verify_status == "unverified", report.verify_detail
        assert JUDGE_CHANGED in report.verify_detail
        assert "scripts/check.sh" in report.verify_detail

    def test_the_rule_matches_the_pieces_of_a_word(self):
        from guardkit.orchestrator.merge_environment import judge_files

        for word in ("--opt=a,check.sh", "--opt=a:check.sh", "x,./scripts/check.sh"):
            assert judge_files(["scripts/check.sh"], [word]) == ["scripts/check.sh"]
        assert judge_files(["src/other.sh"], ["--opt=a,check.sh"]) == []


class TestTheChangedFilesComeFromTheMergedCommit:
    def test_a_submodule_pointer_change_is_listed_whatever_the_config(
        self, tmp_path: Path
    ):
        from guardkit.orchestrator.merge_executor import files_the_branch_changed

        repo = tmp_path / "repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "config", "user.email", "t@t.t")
        _git(repo, "config", "user.name", "t")
        (repo / "a.txt").write_text("a\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "a")
        first = _git(repo, "rev-parse", "HEAD")
        _git(repo, "update-index", "--add", "--cacheinfo", f"160000,{first},vendor/sub")
        _git(repo, "commit", "-q", "-m", "a submodule pointer")
        _git(repo, "checkout", "-q", "-b", "autobuild/FEAT-S")
        (repo / "b.txt").write_text("b\n", encoding="utf-8")
        _git(repo, "add", "b.txt")
        _git(repo, "commit", "-q", "-m", "b")
        second = _git(repo, "rev-parse", "HEAD")
        _git(repo, "update-index", "--cacheinfo", f"160000,{second},vendor/sub")
        _git(repo, "commit", "-q", "-m", "move the submodule pointer")
        _git(repo, "checkout", "-q", "main")
        # A repository may tell git to hide submodule changes from diffs.
        _git(repo, "config", "diff.ignoreSubmodules", "all")
        tip = _git(repo, "rev-parse", "autobuild/FEAT-S")

        changed, problem = files_the_branch_changed(repo, "main", tip)

        assert problem is None
        assert "vendor/sub" in (changed or [])
        assert "b.txt" in (changed or [])

    def test_the_merge_joins_the_commit_that_was_compared(self, tmp_path: Path):
        from guardkit.orchestrator.merge_executor import perform_merge

        repo = tmp_path / "repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "config", "user.email", "t@t.t")
        _git(repo, "config", "user.name", "t")
        (repo / "a.txt").write_text("a\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "a")
        _git(repo, "checkout", "-q", "-b", f"autobuild/{FEATURE}")
        (repo / "compared.txt").write_text("c\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "compared")
        compared = _git(repo, "rev-parse", "HEAD")
        # The branch moves on after the comparison.
        (repo / "later.txt").write_text("l\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "later")
        _git(repo, "checkout", "-q", "main")

        report = perform_merge(repo, FEATURE, "main", merge_commit=compared)

        assert report.outcome == OUTCOME_MERGED
        assert (repo / "compared.txt").exists()
        assert not (repo / "later.txt").exists()
        assert report.branch == f"autobuild/{FEATURE}"


class TestAnUnverifiedRunChargesNothing:
    """Implementation review R2: a run that measured nothing charges nothing."""

    FAILED_WITHOUT_MARKER = (
        "#!/bin/sh\n"
        'echo "FAILED tests/test_new.py::test_new - looks like a failure"\n'
        "exit 0\n"
    )

    @pytest.mark.parametrize("how", ["baseline handed in", "baseline off"])
    def test_a_check_without_the_declared_marker_charges_nothing(
        self, standin: Standin, how: str
    ):
        standin.init(
            config=config_text(
                install=None,
                extra_toolchain='  ran_marker_regex: "NEVER-PRINTED"\n',
                launch=None,
            ),
            files={"scripts/check.sh": self.FAILED_WITHOUT_MARKER},
        ).branch({"feature.txt": "built\n"})

        if how == "baseline handed in":
            report = standin.merge(baseline_failing=[])
        else:
            report = standin.merge(measure_baseline=False)

        assert report.verify_status == "unverified", report.verify_detail
        assert "measured nothing" in report.verify_detail
        assert report.charged_failures == ()
        data = report.to_dict()
        assert data["charged_failures"] == []
        receipt = "\n".join(report.receipt_lines())
        assert "tests/test_new.py::test_new" not in receipt
        assert "charged to this merge" not in receipt
        assert "diff unavailable" not in receipt
        assert not any("failure" in note for note in report.notes), report.notes

    def test_the_baseline_reads_no_names_from_a_run_that_measured_nothing(
        self, standin: Standin
    ):
        standin.init(
            config=config_text(
                install=None,
                extra_toolchain='  ran_marker_regex: "NEVER-PRINTED"\n',
                launch=None,
            ),
            files={"scripts/check.sh": self.FAILED_WITHOUT_MARKER},
        ).branch({"feature.txt": "built\n"})

        report = standin.merge()

        assert report.verify_status == "unverified"
        assert report.baseline_measured is None
        assert report.charged_failures == ()
        assert "tests/test_new.py::test_new" not in _report_text(report)
