"""The secrets check on each change (a safety fence the cull of 27 October 2026 keeps).

What is proven here:

* The command (``security_check_command``): built only when the operator's switch is
  on and Gitleaks is installed, isolated (``-I``) with absolute paths, from the commit
  the task starts from.
* With a scratch git repository and the command called directly: a planted fake key
  fails and its value is never printed; a JWT literal in a test fails; a clean change
  passes; a missing tool, a scanner that errors and a spent budget each pass as "not
  checked"; repository settings, ``gitleaks:allow`` and planted modules do not hide a
  key.
* Through the Coach's evidence run and its guard (``CoachValidator._gather_security_check``
  and ``AgentInvoker._apply_security_check_guard``): a planted key sends the turn back
  with the lines that hold it, a clean change leaves the decision alone, and a hanging
  scanner passes inside the outer limit.

The dependency (OSV-Scanner) part of the check was removed in the cull, with its tests.

Scanners are stub scripts, so the results are fixed and nothing reaches the network.
The stub honours repository settings the way the real tool does, so a test passes only
when the check really keeps those settings away from it. Tests with the real binary
run when it is installed (or named by ``GUARDKIT_TEST_GITLEAKS``) and are skipped
otherwise. No fake secret is written into this file: each is built at run time.
"""

from __future__ import annotations

import base64
import json
import os
import random
import shlex
import shutil
import string
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import Dict, Optional

import pytest

from guardkit.orchestrator import security_check
from guardkit.orchestrator.security_check import (
    BLOCKING_ENV_VAR,
    main,
    run_check,
    security_check_command,
)

# Every test here may let the check find scanners (its own stubs, or the real one).
pytestmark = pytest.mark.security_scanners

TASK_ID = "TASK-SEC-CHECK"
NOT_CLEAN = "Nothing was checked, which is not the same as clean."


# ---------------------------------------------------------------------------
# Fixture material
# ---------------------------------------------------------------------------


def git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, text=True, check=True, timeout=60)
    return done.stdout


def write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def repo(tmp_path: Path):
    """A small git repository; returns its path and the commit the task starts from."""

    def _make(files: Dict[str, str]) -> tuple[Path, str]:
        root = tmp_path / "worktree"
        root.mkdir(parents=True, exist_ok=True)
        write(root, "README.md", "# the starting point\n")
        for rel, text in files.items():
            write(root, rel, text)
        git(root, "init", "-q")
        git(root, "add", ".")
        git(root, "-c", "user.email=t@example.com", "-c", "user.name=T",
            "commit", "-q", "-m", "the starting point")
        return root, git(root, "rev-parse", "HEAD").strip()

    return _make


def fake_marker() -> str:
    """A secret only the stub Gitleaks recognises."""
    rnd = random.Random()
    return "FAKESECRET" + "".join(rnd.choice(string.ascii_uppercase) for _ in range(8))


def fake_aws_key() -> str:
    """A real-looking AWS access key id, made now so none is ever written in a file."""
    rnd = random.Random(20261017)
    return "AKIA" + "".join(rnd.choice(string.ascii_uppercase + "234567") for _ in range(16))


def fake_jwt() -> str:
    def b64(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    rnd = random.Random(7)
    signature = "".join(rnd.choice(string.ascii_letters + string.digits) for _ in range(43))
    return (b64({"alg": "HS256", "typ": "JWT"}) + "."
            + b64({"sub": "1234567890", "name": "probe user", "iat": 1516239022})
            + "." + signature)


# ---------------------------------------------------------------------------
# Stub scanners
# ---------------------------------------------------------------------------

_GITLEAKS_STUB = r'''
import json, os, re, sys
args = sys.argv[1:]
def opt(name, default=None):
    return args[args.index(name) + 1] if name in args else default
target = args[args.index("dir") + 1]
report = opt("--report-path")
ignore_dir = opt("--gitleaks-ignore-path", ".")
honour_allow = "--ignore-gitleaks-allow" not in args
exit_code = int(opt("--exit-code", "1"))
log = os.environ.get("STUB_LOG_NEVER_SET")  # the scanner environment is built from nothing
hidden = bool(os.environ.get("GITLEAKS_CONFIG") or os.environ.get("GITLEAKS_CONFIG_TOML"))
cfg = os.path.join(target, ".gitleaks.toml")
if os.path.exists(cfg) and "allow-everything" in open(cfg).read():
    hidden = True
ign = ignore_dir if os.path.isfile(ignore_dir) else os.path.join(ignore_dir, ".gitleaksignore")
if os.path.exists(ign) and open(ign).read().strip():
    hidden = True
findings = []
for base, _dirs, files in os.walk(target):
    for name in files:
        path = os.path.join(base, name)
        for n, line in enumerate(open(path, errors="replace").read().splitlines(), 1):
            if re.search(r"FAKESECRET[A-Z]{8}", line):
                if honour_allow and "gitleaks:allow" in line:
                    continue
                findings.append({"RuleID": "stub-fake-secret", "File": path, "StartLine": n,
                                 "Secret": "REDACTED", "Match": "REDACTED"})
if hidden:
    findings = []
open(report, "w").write(json.dumps(findings))
sys.exit(exit_code if findings else 0)
'''


def _script(path: Path, body: str) -> Path:
    path.write_text(f"#!{sys.executable} -I\n" + textwrap.dedent(body), encoding="utf-8")
    path.chmod(0o755)
    return path


def make_gitleaks_stub(bindir: Path) -> Path:
    bindir.mkdir(parents=True, exist_ok=True)
    return _script(bindir / "gitleaks", _GITLEAKS_STUB)



def make_version_stub(bindir: Path, name: str, says: str) -> Path:
    bindir.mkdir(parents=True, exist_ok=True)
    path = bindir / name
    path.write_text(f"#!/bin/sh\necho '{says}'\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def make_failing_tool(bindir: Path, name: str, code: int = 127, *, hang: bool = False) -> Path:
    bindir.mkdir(parents=True, exist_ok=True)
    path = bindir / name
    if hang:
        # A child that keeps the output open, as a real hung scanner's worker would.
        path.write_text("#!/bin/sh\nsleep 600 &\nsleep 600\n", encoding="utf-8")
    else:
        path.write_text(f"#!/bin/sh\necho 'request failed: network is unreachable' >&2\n"
                        f"exit {code}\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def real_tool(name: str, env_name: str) -> Optional[str]:
    found = os.environ.get(env_name) or shutil.which(name)
    return found if found and os.access(found, os.X_OK) else None


REAL_GITLEAKS = real_tool("gitleaks", "GUARDKIT_TEST_GITLEAKS")
needs_real_gitleaks = pytest.mark.skipif(REAL_GITLEAKS is None, reason="gitleaks is not installed")


def only_git_and(bindir: Path) -> str:
    """A PATH holding ``bindir`` and the folder git is in, so git still answers."""
    return f"{bindir}{os.pathsep}{os.path.dirname(shutil.which('git'))}"


@pytest.fixture(autouse=True)
def no_factory_settings(monkeypatch, tmp_path):
    """Point the factory settings at a folder that does not exist, so a test machine's
    own ``/opt/factory-security`` never changes a result."""
    missing = tmp_path / "no-factory-settings"
    monkeypatch.setattr(security_check, "FACTORY_GITLEAKS_IGNORE_DIR", missing / "gitleaks-ignore")


@pytest.fixture
def on_path(monkeypatch, checkout_python):
    """Put stub scanners on PATH for the command builder. ``checkout_python`` (in
    tests/conftest.py) has already made the builder name an interpreter whose -I
    import of guardkit is this checkout, not whichever one is installed."""

    def _put(bindir: Path) -> None:
        monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}")

    return _put


def _gather(root: Path, command: str) -> Dict:
    """The Coach's evidence run of the secrets check, as gather_evidence makes it."""
    from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator

    validator = CoachValidator(str(root), task_id=TASK_ID, security_command=command)
    return validator._gather_security_check()


def _guard(decision: dict, result: Optional[Dict], tmp_path: Path) -> dict:
    from guardkit.orchestrator.agent_invoker import AgentInvoker
    from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle

    inv = AgentInvoker.__new__(AgentInvoker)
    coach_path = tmp_path / "coach_turn_1.json"
    coach_path.write_text(json.dumps(decision))
    inv._apply_security_check_guard(
        decision=decision,
        evidence_bundle=CoachEvidenceBundle(security_check=result),
        task_id=TASK_ID, turn=1, coach_output_path=coach_path)
    assert json.loads(coach_path.read_text())["decision"] == decision["decision"]
    return decision


# ---------------------------------------------------------------------------
# 1. The command
# ---------------------------------------------------------------------------


def test_no_scanner_installed_means_no_command(repo, monkeypatch, tmp_path):
    root, _sha = repo({})
    monkeypatch.setenv("PATH", only_git_and(tmp_path / "empty-bin"))
    assert security_check_command(root, TASK_ID) is None


def test_the_switch_is_off_by_default_even_with_the_tool(repo, monkeypatch, tmp_path):
    """Rich, 17 October 2026: off until the projects' existing problems are fixed."""
    bindir = tmp_path / "bin"
    make_gitleaks_stub(bindir)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.delenv(BLOCKING_ENV_VAR, raising=False)
    root, _sha = repo({})

    assert security_check_command(root, TASK_ID) is None


@pytest.mark.parametrize("value", ["", "0", "false", "off", "no", "maybe"])
def test_anything_but_an_on_word_leaves_the_switch_off(repo, monkeypatch, tmp_path, value):
    bindir = tmp_path / "bin"
    make_gitleaks_stub(bindir)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    root, _sha = repo({})
    assert security_check_command(root, TASK_ID, env={BLOCKING_ENV_VAR: value}) is None


@pytest.mark.parametrize("value", ["1", "true", "YES", " on "])
def test_an_on_word_switches_it_on(repo, monkeypatch, tmp_path, value):
    bindir = tmp_path / "bin"
    make_gitleaks_stub(bindir)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    root, _sha = repo({})
    assert security_check_command(root, TASK_ID, env={BLOCKING_ENV_VAR: value}) is not None


def test_the_command_runs_isolated_with_an_absolute_scanner_path(repo, monkeypatch, tmp_path):
    bindir = tmp_path / "bin"
    gitleaks = make_gitleaks_stub(bindir)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    root, sha = repo({})

    argv = shlex.split(security_check_command(root, TASK_ID))

    assert argv[:4] == [sys.executable, "-I", "-m", "guardkit.orchestrator.security_check"]
    assert argv[argv.index("--since") + 1] == sha
    assert argv[argv.index("--gitleaks") + 1] == str(gitleaks)
    assert os.path.isabs(argv[argv.index("--gitleaks") + 1])


def test_a_known_starting_commit_is_used(repo, monkeypatch, tmp_path):
    bindir = tmp_path / "bin"
    make_gitleaks_stub(bindir)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    root, _sha = repo({})
    argv = shlex.split(security_check_command(root, TASK_ID, start_commit="abc123"))
    assert argv[argv.index("--since") + 1] == "abc123"


def test_no_starting_commit_means_no_command(monkeypatch, tmp_path):
    bindir = tmp_path / "bin"
    make_gitleaks_stub(bindir)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    not_a_repo = tmp_path / "plain"
    not_a_repo.mkdir()
    assert security_check_command(not_a_repo, TASK_ID) is None


# ---------------------------------------------------------------------------
# 2. Secrets (scratch repository, the command called directly)
# ---------------------------------------------------------------------------


def test_a_planted_fake_key_fails_and_its_value_is_never_printed(repo, tmp_path):
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    root, sha = repo({})
    planted = fake_marker()
    write(root, "src/settings.py", f'API_KEY = "{planted}"\n')

    code, text = run_check(root, sha, gitleaks=str(gitleaks))

    assert code == 1
    assert "secret -- src/settings.py:1" in text
    assert planted not in text
    assert "from the environment or a secret file" in text


def test_no_scanner_setting_from_the_environment_reaches_a_scanner(repo, tmp_path,
                                                                  monkeypatch):
    monkeypatch.setenv("GITLEAKS_CONFIG_TOML", "[allowlist]\nregexes = ['.*']\n")
    monkeypatch.setenv("GITLEAKS_CONFIG", str(tmp_path / "allow-all.toml"))
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    root, sha = repo({})
    write(root, "src/settings.py", f'KEY = "{fake_marker()}"\n')
    code, text = run_check(root, sha, gitleaks=str(gitleaks))
    assert code == 1, text


def test_repository_settings_and_allow_comments_do_not_hide_a_key(repo, tmp_path):
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    root, sha = repo({})
    planted = fake_marker()
    write(root, "src/settings.py", f'KEY = "{planted}"  # gitleaks:allow\n')
    write(root, ".gitleaks.toml", "# allow-everything\n[allowlist]\nregexes = ['.*']\n")
    write(root, ".gitleaksignore", "src/settings.py:stub-fake-secret:1\n")

    code, text = run_check(root, sha, gitleaks=str(gitleaks))

    assert code == 1, text
    assert "secret -- src/settings.py:1" in text
    assert planted not in text


def test_a_clean_change_passes(repo, tmp_path):
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    root, sha = repo({})
    write(root, "src/app.py", "def add(a, b):\n    return a + b\n")

    code, text = run_check(root, sha, gitleaks=str(gitleaks))

    assert code == 0, text
    assert "nothing here blocks" in text


def test_guardkit_records_are_not_this_tasks_change(repo, tmp_path):
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    root, sha = repo({})
    write(root, ".guardkit/autobuild/TASK-1/player_turn_1.json", f'"{fake_marker()}"\n')
    code, text = run_check(root, sha, gitleaks=str(gitleaks))
    assert code == 0
    assert "changed no files yet" in text


def test_a_symbolic_link_is_recorded_and_not_followed(repo, tmp_path):
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    outside = write(tmp_path / "outside", "secret.txt", f"{fake_marker()}\n")
    root, sha = repo({})
    (root / "linked.txt").symlink_to(outside)
    code, text = run_check(root, sha, gitleaks=str(gitleaks))
    assert code == 0, text
    assert "linked.txt is a symbolic link" in text


@needs_real_gitleaks
def test_real_gitleaks_a_planted_key_fails_and_the_value_never_appears(repo, capsys):
    root, sha = repo({})
    planted = fake_aws_key()
    write(root, "src/config.py", f'AWS_ACCESS_KEY_ID = "{planted}"\n')

    code = main(["--repo", str(root), "--since", sha, "--gitleaks", REAL_GITLEAKS])
    out = capsys.readouterr().out

    assert code == 1
    assert "secret -- src/config.py:1" in out and "aws-access-token" in out
    assert planted not in out


@needs_real_gitleaks
def test_real_gitleaks_a_jwt_literal_in_a_test_fails(repo):
    root, sha = repo({})
    planted = fake_jwt()
    write(root, "apps/api/internal/auth/auth_test.go",
          f'package auth\n\nconst token = "{planted}"\n')

    code, text = run_check(root, sha, gitleaks=REAL_GITLEAKS)

    assert code == 1
    assert "apps/api/internal/auth/auth_test.go:3" in text and "jwt" in text
    assert planted not in text


@needs_real_gitleaks
def test_real_gitleaks_player_settings_and_allow_comments_do_not_hide_a_key(repo):
    root, sha = repo({})
    planted = fake_aws_key()
    write(root, "src/config.py", f'AWS_ACCESS_KEY_ID = "{planted}"  # gitleaks:allow\n')
    write(root, ".gitleaks.toml",
          '[extend]\nuseDefault = true\n[allowlist]\npaths = [".*"]\nregexes = [".*"]\n')
    write(root, ".gitleaksignore", "src/config.py:aws-access-token:1\n")

    code, text = run_check(root, sha, gitleaks=REAL_GITLEAKS)

    assert code == 1, text
    assert "secret -- src/config.py:1" in text


# ---------------------------------------------------------------------------
# 3. A check that cannot run never stops a build
# ---------------------------------------------------------------------------


def test_a_missing_tool_passes_as_not_checked(repo, tmp_path):
    root, sha = repo({})
    write(root, "src/settings.py", f'KEY = "{fake_marker()}"\n')
    code, text = run_check(root, sha, gitleaks=str(tmp_path / "nope" / "gitleaks"))
    assert code == 0
    assert "Secret detection was not checked: gitleaks is not there or cannot be run" in text
    assert NOT_CLEAN in text


def test_a_scanner_that_errors_passes_as_not_checked(repo, tmp_path):
    gitleaks = make_failing_tool(tmp_path / "bin", "gitleaks", 2)
    root, sha = repo({})
    write(root, "src/settings.py", f'KEY = "{fake_marker()}"\n')
    code, text = run_check(root, sha, gitleaks=str(gitleaks))
    assert code == 0
    assert "gitleaks stopped with exit code 2" in text and NOT_CLEAN in text


def test_a_spent_budget_passes_as_not_checked(repo, tmp_path):
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    root, sha = repo({})
    write(root, "src/settings.py", f'KEY = "{fake_marker()}"\n')
    code, text = run_check(root, sha, gitleaks=str(gitleaks), budget_seconds=0)
    assert code == 0
    assert "time budget was spent" in text


def test_a_bad_command_line_or_a_git_failure_passes(tmp_path, capsys):
    assert main(["--no-such-flag"]) == 0
    assert NOT_CLEAN in capsys.readouterr().out
    (tmp_path / "plain").mkdir()
    assert main(["--repo", str(tmp_path / "plain"), "--since", "HEAD"]) == 0
    assert NOT_CLEAN in capsys.readouterr().out


def test_staging_stops_when_the_budget_is_spent(repo, tmp_path, monkeypatch):
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    root, sha = repo({})
    for n in range(3):
        write(root, f"f{n}.py", f'KEY = "{fake_marker()}"\n')
    clock = iter([100.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    monkeypatch.setattr(security_check.Budget, "left", lambda self: next(clock, 0.0))
    code, text = run_check(root, sha, gitleaks=str(gitleaks))
    assert code == 0, text
    assert "3 changed file(s) was not checked: the check's time budget was spent" in text


# ---------------------------------------------------------------------------
# 4. Files that are hard to read
# ---------------------------------------------------------------------------

ODD_NAMES = ["配置/密钥.py", 'q"uote.py', " leading space.py"]


@pytest.mark.parametrize("committed", [False, True], ids=["uncommitted", "committed"])
def test_files_with_unusual_names_are_read(repo, tmp_path, committed):
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    root, sha = repo({})
    for rel in ODD_NAMES:
        write(root, rel, f'KEY = "{fake_marker()}"\n')
    if committed:
        git(root, "add", ".")
        git(root, "-c", "user.email=t@example.com", "-c", "user.name=T",
            "commit", "-q", "-m", "the task's work")

    code, text = run_check(root, sha, gitleaks=str(gitleaks))

    assert code == 1, text
    for rel in ODD_NAMES:
        assert f"secret -- {rel}:1" in text, (rel, text)


@needs_real_gitleaks
def test_real_gitleaks_reads_files_with_unusual_names(repo):
    root, sha = repo({})
    for rel in ODD_NAMES[:2]:
        write(root, rel, f'AWS_ACCESS_KEY_ID = "{fake_aws_key()}"\n')
    code, text = run_check(root, sha, gitleaks=REAL_GITLEAKS)
    assert code == 1, text
    for rel in ODD_NAMES[:2]:
        assert f"secret -- {rel}:1" in text, (rel, text)


def test_changed_files_with_unusual_names_are_listed_exactly(repo):
    from guardkit.orchestrator.security_check import files_changed_since

    root, sha = repo({})
    for rel in ODD_NAMES:
        write(root, rel, "x = 1\n")
    assert files_changed_since(root, sha) == sorted(ODD_NAMES)


def test_a_changed_file_that_cannot_be_read_is_reported(repo, tmp_path):
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    root, sha = repo({})
    locked = write(root, "src/locked.py", f'KEY = "{fake_marker()}"\n')
    locked.chmod(0)
    try:
        if os.access(locked, os.R_OK):
            pytest.skip("this user can read a file with no permissions (root)")
        code, text = run_check(root, sha, gitleaks=str(gitleaks))
    finally:
        locked.chmod(0o644)
    assert code == 0
    assert ("The changed file src/locked.py was not checked: it could not be opened "
            "(PermissionError). " + NOT_CLEAN) in text


def test_a_changed_file_over_the_size_limit_is_read_up_to_it(repo, tmp_path, monkeypatch):
    monkeypatch.setattr(security_check, "MAX_FILE_BYTES", 1000)
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    root, sha = repo({})
    write(root, "big.txt", f'KEY = "{fake_marker()}"\n' + "a" * 2000
          + f'\nKEY = "{fake_marker()}"\n')
    code, text = run_check(root, sha, gitleaks=str(gitleaks))
    assert code == 1
    assert "secret -- big.txt:1" in text and "secret -- big.txt:3" not in text
    assert ("The rest of the changed file big.txt was not checked: it is over 0 MB, so "
            "only its first 0 MB were read for secrets.") in text


def test_a_nul_byte_early_in_a_file_does_not_hide_a_key(repo, tmp_path):
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    root, sha = repo({})
    (root / "data.bin").write_bytes(b"\x00\x01header\n" + f'KEY = "{fake_marker()}"\n'.encode())
    code, text = run_check(root, sha, gitleaks=str(gitleaks))
    assert code == 1, text
    assert "secret -- data.bin:2" in text


@needs_real_gitleaks
def test_real_gitleaks_decides_about_a_file_with_an_early_nul(repo):
    root, sha = repo({})
    (root / "data.bin").write_bytes(
        b"\x00\x01header\n" + f'AWS_ACCESS_KEY_ID = "{fake_aws_key()}"\n'.encode())
    code, text = run_check(root, sha, gitleaks=REAL_GITLEAKS)
    assert "Secrets: 1 changed file(s) read" in text
    # Whatever Gitleaks decides about this file, it was given it.
    assert code in (0, 1)


def _utf8_locale() -> str:
    """A full UTF-8 locale (not C), under which Python's stdout refuses a lone surrogate."""
    found = subprocess.run(["locale", "-a"], capture_output=True, text=True).stdout.split()
    for wanted in ("en_GB.utf8", "en_US.utf8"):
        if wanted in found:
            return wanted
    others = [n for n in found if n.lower().endswith(("utf8", "utf-8")) and not n.startswith("C")]
    if not others:
        pytest.skip("no full UTF-8 locale is installed")
    return others[0]


def test_names_that_are_not_utf8_or_hold_a_newline_never_crash_the_command(
        repo, on_path, tmp_path):
    """A symbolic link named b'bad\\xfflink', plus a file whose name holds a
    newline, under a full UTF-8 locale."""
    bindir = tmp_path / "bin"
    make_gitleaks_stub(bindir)
    on_path(bindir)
    root, _sha = repo({})
    os.symlink(b"README.md", os.path.join(os.fsencode(root), b"bad\xfflink"))
    write(root, "new\nline.py", f'KEY = "{fake_marker()}"\n')
    command = security_check_command(root, TASK_ID)

    env = {"PATH": os.environ["PATH"], "HOME": str(tmp_path), "LANG": _utf8_locale()}
    done = subprocess.run(["sh", "-c", command], cwd=root, capture_output=True,
                          timeout=300, env=env)
    out = done.stdout.decode("utf-8")

    assert b"Traceback" not in done.stderr, done.stderr.decode("utf-8", "replace")
    assert done.returncode == 1, out
    assert "bad\\xfflink is a symbolic link; it was recorded and not followed." in out
    assert "secret -- new\\nline.py:1:" in out
    assert not any(line.startswith("line.py") for line in out.splitlines())


# ---------------------------------------------------------------------------
# 5. Through the Coach's evidence run and its guard
# ---------------------------------------------------------------------------


def test_through_the_coach_a_planted_key_sends_the_turn_back(repo, on_path, tmp_path):
    bindir = tmp_path / "bin"
    make_gitleaks_stub(bindir)
    on_path(bindir)
    root, _sha = repo({})
    command = security_check_command(root, TASK_ID)  # before the first turn
    assert command is not None

    planted = fake_marker()
    write(root, "src/settings.py", f'KEY = "{planted}"\n')  # written by the turn
    result = _gather(root, command)

    assert result["ran"] is True and result["passed"] is False, result
    assert "secret -- src/settings.py:1" in result["output_tail"]
    assert planted not in result["output_tail"]

    decision = _guard({"decision": "approve", "issues": []}, result, tmp_path)
    assert decision["decision"] == "feedback"
    must_fix = [i for i in decision["issues"] if i["severity"] == "must_fix"]
    assert [i["category"] for i in must_fix] == ["secret_in_change"]
    assert "secret -- src/settings.py:1" in must_fix[0]["test_output"]


def test_through_the_coach_a_clean_change_leaves_the_decision_alone(repo, on_path, tmp_path):
    bindir = tmp_path / "bin"
    make_gitleaks_stub(bindir)
    on_path(bindir)
    root, _sha = repo({})
    command = security_check_command(root, TASK_ID)
    write(root, "src/app.py", "x = 1\n")

    result = _gather(root, command)

    assert result["ran"] is True and result["passed"] is True, result
    assert _guard({"decision": "approve", "issues": []}, result, tmp_path) == {
        "decision": "approve", "issues": []}


def test_with_the_check_off_there_is_nothing_to_run(repo, tmp_path):
    root, _sha = repo({})
    assert _gather(root, None) is None
    assert _guard({"decision": "approve", "issues": []}, None, tmp_path)["decision"] == "approve"


def test_through_the_coach_a_hanging_scanner_passes_inside_the_outer_limit(
        repo, on_path, tmp_path):
    bindir = tmp_path / "bin"
    make_failing_tool(bindir, "gitleaks", hang=True)
    on_path(bindir)
    root, _sha = repo({})
    # 200 s budget and 60 s deadlines inside a 300 s limit, scaled down tenfold.
    command = security_check_command(root, TASK_ID) + " --budget 20 --tool-deadline 6"
    write(root, "src/settings.py", f'KEY = "{fake_marker()}"\n')

    started = time.monotonic()
    result = _gather(root, command)
    elapsed = time.monotonic() - started

    assert result["passed"] is True, result
    assert "Secret detection was not checked" in result["output_tail"]
    assert elapsed < 30


def _plant_import_bypass(root: Path) -> None:
    for rel in ("guardkit.py", "guardkit/__init__.py", "sitecustomize.py"):
        write(root, rel, "import sys\nsys.exit(0)\n")


def test_through_the_coach_planted_modules_cannot_bypass_the_check(
        repo, on_path, tmp_path):
    bindir = tmp_path / "bin"
    make_gitleaks_stub(bindir)
    on_path(bindir)
    root, _sha = repo({})
    command = security_check_command(root, TASK_ID)
    _plant_import_bypass(root)
    write(root, "src/settings.py", f'KEY = "{fake_marker()}"\n')

    result = _gather(root, command)
    assert result["passed"] is False, result
    assert "secret -- src/settings.py:1" in result["output_tail"]

    # The same command without -I is fooled: the planted package answers instead.
    assert " -I " in command
    fooled = subprocess.run(command.replace(" -I ", " ", 1), shell=True, cwd=root,
                            capture_output=True, text=True, timeout=120,
                            env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    assert fooled.returncode == 0 and fooled.stdout == ""


# ---------------------------------------------------------------------------
# 6. The self-test for the release's live check
# ---------------------------------------------------------------------------


def _self_test(python: str, *extra: str, path: Optional[str] = None):
    return subprocess.run(
        [python, "-I", "-m", "guardkit.orchestrator.security_check", "--self-test", *extra],
        capture_output=True, text=True, timeout=120, cwd="/",
        env={"PATH": path or os.environ["PATH"], "HOME": os.environ.get("HOME", "/")})


def test_the_self_test_passes_with_gitleaks(checkout_isolated_python, tmp_path):
    bindir = tmp_path / "bin"
    make_version_stub(bindir, "gitleaks", "8.30.1")

    done = _self_test(checkout_isolated_python, path=only_git_and(bindir))

    assert done.returncode == 0, done.stdout + done.stderr
    lines = done.stdout.strip().splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("Security check self-test passed: guardkit ")
    assert "isolated" in lines[0] and "gitleaks 8.30.1" in lines[0]


def test_the_self_test_fails_plainly_when_gitleaks_is_missing(checkout_isolated_python,
                                                             tmp_path):
    done = _self_test(checkout_isolated_python, path=only_git_and(tmp_path / "empty-bin"))
    assert done.returncode == 1
    assert done.stdout.startswith("Security check self-test failed: gitleaks is not installed")


@needs_real_gitleaks
def test_the_self_test_with_the_real_scanner(checkout_isolated_python):
    done = _self_test(checkout_isolated_python, "--gitleaks", REAL_GITLEAKS)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "Security check self-test passed" in done.stdout
