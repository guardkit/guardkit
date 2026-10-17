"""The security check on each change (piece 1 of the factory security design).

What is proven here, case by case from the design's "GuardKit piece" list:

* With a scratch git repository: a planted fake key fails; a JWT literal in a test
  fails; a clean change passes; an added package with a known critical advisory fails;
  a lower-severity one passes as advice; a brand-new package fails; a missing tool, a
  scanner that errors and an unreachable network each pass as "not checked".
* Through the real conformance executor (frozen before turn 1, run by
  ``evaluate_from_snapshot``, judged by the Coach guard):
  - a hanging scanner passes as "not checked" inside the outer limit (R2), and so does
    an unreachable network;
  - an ineffective upgrade blocks, an effective one passes, and an unrelated lockfile
    change with an old advisory passes (R7);
  - a Player-added ``osv-scanner.toml``, ``.gitleaks.toml``, ``.gitleaksignore`` and
    ``gitleaks:allow`` do not hide the planted findings (R9);
  - a Player-planted ``guardkit.py``, ``guardkit/__init__.py`` and ``sitecustomize.py``
    cannot bypass the security check or the architecture check (R1).

Scanners are stub scripts, so the results are fixed and nothing reaches the network.
The stubs honour repository settings the way the real tools do, so a test passes only
when the check really keeps those settings away from them. Tests with the real binaries
run when they are installed (or named by ``GUARDKIT_TEST_GITLEAKS`` /
``GUARDKIT_TEST_OSV_SCANNER``) and are skipped otherwise. No fake secret is written into
this file: each is built at run time.
"""

from __future__ import annotations

import base64
import http.server
import json
import os
import random
import re
import shlex
import shutil
import string
import subprocess
import sys
import textwrap
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import patch

import pytest

from guardkit.orchestrator import security_check
from guardkit.orchestrator.arch_conformance import (
    BLOCKING_ENV_VAR as ARCH_SWITCH,
    RULE_ID as ARCH_RULE_ID,
)
from guardkit.orchestrator.quality_gates.spec_conformance import (
    evaluate_from_snapshot,
    load_snapshot,
    snapshot_task_conformance,
)
from guardkit.orchestrator.security_check import (
    RULE_ID,
    RULE_TIMEOUT_SECONDS,
    build_security_rule,
    main,
    run_check,
)

# Every test here may let the check find scanners (its own stubs, or the real ones).
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

_OSV_STUB = r'''
import json, os, re, sys
DB = json.loads(__DB__)
LOG = __LOG__
args = sys.argv[1:]
folder = args[-1]
config = args[args.index("--config") + 1] if "--config" in args else None
if LOG:
    with open(LOG, "a") as f:
        f.write(json.dumps({"argv": args, "files": sorted(
            os.path.relpath(os.path.join(b, n), folder)
            for b, _d, fs in os.walk(folder) for n in fs)}) + "\n")
def ignored(path):
    if path and os.path.exists(path):
        return set(re.findall(r'id\s*=\s*"([^"]+)"', open(path).read()))
    return set()
hidden = set()
gitignore = os.path.join(folder, ".gitignore")
if "--no-ignore" not in args and os.path.exists(gitignore):
    hidden = {line.strip() for line in open(gitignore) if line.strip()}
results = []
for base, _dirs, files in os.walk(folder):
    for name in files:
        if name != "stub.lock" or os.path.relpath(os.path.join(base, name), folder) in hidden:
            continue
        path = os.path.join(base, name)
        skip = ignored(config) if config else ignored(os.path.join(base, "osv-scanner.toml"))
        packages = []
        lines = [line for line in open(path).read().splitlines() if line.strip()]
        if not lines or any(len(line.split()) != 3 for line in lines):
            # As the real tool does with an empty or broken lockfile.
            sys.stderr.write("Error during extraction: could not extract " + path + "\n")
            sys.exit(127)
        resolved = []
        for line in lines:
            resolved.append(line)
            # A manifest the real tool resolves over the network: extra packages
            # appear that are not written in the file.
            resolved.extend(DB.get("RESOLVES " + " ".join(line.split()), []))
        for line in resolved:
            eco, pkg, version = line.split()
            vulns, groups = [], []
            for v in DB.get(f"{eco} {pkg} {version}", []):
                if v["id"] in skip:
                    continue
                vulns.append({"id": v["id"], "aliases": v.get("aliases", []),
                              "database_specific": {"severity": v.get("label", "")},
                              "affected": [{"package": {"name": pkg, "ecosystem": eco},
                                            "ranges": [{"type": "SEMVER", "events": [
                                                {"introduced": "0"}, {"fixed": f}]}]}
                                           for f in v.get("fixed", [])]})
                groups.append({"ids": [v["id"]], "aliases": [v["id"], *v.get("aliases", [])],
                               "max_severity": v.get("score", "")})
            entry = {"package": {"name": pkg, "version": version, "ecosystem": eco}}
            if vulns:
                entry["vulnerabilities"] = vulns
                entry["groups"] = groups
            packages.append(entry)
        results.append({"source": {"path": path, "type": "lockfile"}, "packages": packages})
print(json.dumps({"results": results}))
sys.exit(1 if any(p.get("vulnerabilities") for r in results for p in r["packages"]) else 0)
'''


def _script(path: Path, body: str) -> Path:
    path.write_text(f"#!{sys.executable} -I\n" + textwrap.dedent(body), encoding="utf-8")
    path.chmod(0o755)
    return path


def make_gitleaks_stub(bindir: Path) -> Path:
    bindir.mkdir(parents=True, exist_ok=True)
    return _script(bindir / "gitleaks", _GITLEAKS_STUB)


def make_osv_stub(bindir: Path, db: Optional[dict] = None, log: Optional[Path] = None) -> Path:
    bindir.mkdir(parents=True, exist_ok=True)
    body = (_OSV_STUB.replace("__DB__", repr(json.dumps(db or {})))
            .replace("__LOG__", repr(str(log) if log else "")))
    return _script(bindir / "osv-scanner", body)


_OSV_REPLAY_STUB = r'''
import json, os, sys
recorded = json.loads(__RECORDED__)
folder = sys.argv[-1]
found = [os.path.join(b, n) for b, _d, fs in os.walk(folder) for n in fs if n == "requirements.txt"]
if not found:
    print(json.dumps({"results": []}))
    sys.exit(0)
for result in recorded["results"]:
    result["source"]["path"] = found[0]
print(json.dumps(recorded))
sys.exit(1)
'''

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "osv"


def make_osv_replay_stub(bindir: Path, recorded: Path) -> Path:
    """OSV-Scanner answering with output recorded from the real tool."""
    bindir.mkdir(parents=True, exist_ok=True)
    body = _OSV_REPLAY_STUB.replace("__RECORDED__", repr(recorded.read_text()))
    return _script(bindir / "osv-scanner", body)


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


def lockfile(*packages: str) -> str:
    """The stub's lockfile: one 'ecosystem name version' per line."""
    return "".join(f"{p}\n" for p in packages)


VITEST_DB = {
    "npm vitest 4.0.15": [{"id": "GHSA-5xrq-8626-4rwp", "score": "9.8", "label": "CRITICAL",
                           "fixed": ["4.1.0", "3.2.6"]}],
    "npm vitest 4.0.18": [{"id": "GHSA-5xrq-8626-4rwp", "score": "9.8", "label": "CRITICAL",
                           "fixed": ["4.1.0", "3.2.6"]}],
    "npm lodash 4.17.20": [{"id": "GHSA-lowx-0000-0000", "score": "5.3", "label": "MODERATE",
                            "fixed": ["4.17.21"]}],
    "npm evil-pkg 1.0.0": [{"id": "MAL-2026-1234", "score": "", "label": ""}],
    "npm critical-pkg 2.0.0": [{"id": "GHSA-crit-0000-0000", "score": "9.1",
                                "label": "CRITICAL", "fixed": ["2.0.1"]}],
}


def real_tool(name: str, env_name: str) -> Optional[str]:
    found = os.environ.get(env_name) or shutil.which(name)
    return found if found and os.access(found, os.X_OK) else None


REAL_GITLEAKS = real_tool("gitleaks", "GUARDKIT_TEST_GITLEAKS")
REAL_OSV = real_tool("osv-scanner", "GUARDKIT_TEST_OSV_SCANNER")
needs_real_gitleaks = pytest.mark.skipif(REAL_GITLEAKS is None, reason="gitleaks is not installed")
needs_real_osv = pytest.mark.skipif(REAL_OSV is None, reason="osv-scanner is not installed")


def only_git_and(bindir: Path) -> str:
    """A PATH holding ``bindir`` and the folder git is in, so git still answers."""
    return f"{bindir}{os.pathsep}{os.path.dirname(shutil.which('git'))}"


@pytest.fixture(autouse=True)
def no_factory_settings(monkeypatch, tmp_path):
    """Point the factory settings at folders that do not exist, so a test machine's
    own ``/opt/factory-security`` never changes a result."""
    missing = tmp_path / "no-factory-settings"
    monkeypatch.setattr(security_check, "FACTORY_OSV_CONFIG", missing / "osv-scanner.toml")
    monkeypatch.setattr(security_check, "FACTORY_GITLEAKS_IGNORE_DIR", missing / "gitleaks-ignore")


@pytest.fixture
def no_network(monkeypatch):
    """Every HTTP request goes to a closed local port."""
    for name in ("NO_PROXY", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
    for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY"):
        monkeypatch.setenv(name, "http://127.0.0.1:9")


class _DepsDev(http.server.BaseHTTPRequestHandler):
    published: Dict[str, str] = {}
    seen: List[str] = []

    def do_GET(self):  # noqa: N802 - the handler's own name
        self.seen.append(self.path)
        name = self.path.rsplit("/", 1)[-1]
        from urllib.parse import unquote

        when = self.published.get(unquote(name))
        if when is None:
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps({"versions": [{"versionKey": {"version": "1.0.0"},
                                         "publishedAt": when}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # quiet
        pass


@pytest.fixture
def deps_dev():
    _DepsDev.published = {}
    _DepsDev.seen = []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _DepsDev)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", _DepsDev
    finally:
        server.shutdown()


@pytest.fixture
def on_path(monkeypatch, checkout_python):
    """Put stub scanners on PATH for the rule builder. ``checkout_python`` (in
    tests/conftest.py) has already made both rule builders name an interpreter whose
    -I import of guardkit is this checkout, not whichever one is installed."""

    def _put(bindir: Path) -> None:
        monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}")

    return _put


def _snapshot(root: Path, frontmatter: Optional[dict] = None):
    with patch("guardkit.tasks.task_loader.TaskLoader.load_task",
               return_value={"frontmatter": frontmatter or {}}):
        return snapshot_task_conformance(task_id=TASK_ID, worktree_path=root, repo_root=root)


def _guard(decision: dict, leg, tmp_path: Path) -> dict:
    from guardkit.orchestrator.agent_invoker import AgentInvoker
    from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle

    inv = AgentInvoker.__new__(AgentInvoker)
    coach_path = tmp_path / "coach_turn_1.json"
    coach_path.write_text(json.dumps(decision))
    inv._apply_spec_conformance_guard(
        decision=decision,
        evidence_bundle=CoachEvidenceBundle(honesty=None, spec_conformance=leg),
        task_id=TASK_ID, turn=1, coach_output_path=coach_path, acceptance_criteria=None)
    return decision


def _security_failure(leg: dict) -> Optional[dict]:
    for failure in leg.get("failures") or []:
        if failure["rule_id"] == RULE_ID:
            return failure
    return None


def _scale_frozen_rule(snapshot_dir: Path, *, budget: float, tool_deadline: float,
                       timeout: int) -> None:
    """Keep the frozen rule's proportions (budget inside the outer limit) while
    waiting seconds instead of minutes. Only the numbers change; the command is the
    one the builder wrote."""
    block_path = snapshot_dir / "conformance.json"
    block = json.loads(block_path.read_text())
    for rule in block["rules"]:
        if rule["id"] == RULE_ID:
            rule["command"] += f" --budget {budget} --tool-deadline {tool_deadline}"
            rule["timeout"] = timeout
    block_path.write_text(json.dumps(block))


# ---------------------------------------------------------------------------
# 1. The rule
# ---------------------------------------------------------------------------


def test_no_scanner_installed_means_no_rule_and_nothing_frozen(repo, monkeypatch, tmp_path):
    monkeypatch.delenv(ARCH_SWITCH, raising=False)
    root, _sha = repo({})
    monkeypatch.setenv("PATH", only_git_and(tmp_path / "empty-bin"))
    assert build_security_rule(root, TASK_ID) is None
    assert _snapshot(root) is None


def test_the_switch_is_off_by_default_so_nothing_is_frozen_even_with_the_tools(
    repo, monkeypatch, tmp_path
):
    """Rich, 17 October 2026: off until the projects' existing problems are fixed."""
    bindir = tmp_path / "bin"
    make_gitleaks_stub(bindir)
    make_osv_stub(bindir)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.delenv(ARCH_SWITCH, raising=False)
    monkeypatch.delenv("GUARDKIT_SECURITY_CHECK_BLOCKING", raising=False)
    root, _sha = repo({})

    assert build_security_rule(root, TASK_ID) is None
    assert _snapshot(root) is None


@pytest.mark.parametrize("value", ["", "0", "false", "off", "no", "maybe"])
def test_anything_but_an_on_word_leaves_the_switch_off(repo, monkeypatch, tmp_path, value):
    bindir = tmp_path / "bin"
    make_gitleaks_stub(bindir)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    root, _sha = repo({})
    assert build_security_rule(
        root, TASK_ID, env={"GUARDKIT_SECURITY_CHECK_BLOCKING": value}) is None


@pytest.mark.parametrize("value", ["1", "true", "YES", " on "])
def test_an_on_word_switches_it_on(repo, monkeypatch, tmp_path, value):
    bindir = tmp_path / "bin"
    make_gitleaks_stub(bindir)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    root, _sha = repo({})
    rule = build_security_rule(root, TASK_ID, env={"GUARDKIT_SECURITY_CHECK_BLOCKING": value})
    assert rule is not None and rule["id"] == RULE_ID


def test_the_rule_runs_isolated_with_absolute_scanner_paths(repo, monkeypatch, tmp_path):
    bindir = tmp_path / "bin"
    gitleaks = make_gitleaks_stub(bindir)
    osv = make_osv_stub(bindir)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    root, sha = repo({})

    rule = build_security_rule(root, TASK_ID)

    assert rule["id"] == RULE_ID and rule["type"] == "assert_command"
    assert rule["timeout"] == RULE_TIMEOUT_SECONDS == 300
    argv = shlex.split(rule["command"])
    assert argv[:4] == [sys.executable, "-I", "-m", "guardkit.orchestrator.security_check"]
    assert argv[argv.index("--since") + 1] == sha
    assert argv[argv.index("--gitleaks") + 1] == str(gitleaks)
    assert argv[argv.index("--osv-scanner") + 1] == str(osv)
    assert all(os.path.isabs(argv[argv.index(f) + 1]) for f in ("--gitleaks", "--osv-scanner"))


def test_only_the_installed_scanner_is_named(repo, monkeypatch, tmp_path):
    bindir = tmp_path / "bin"
    make_gitleaks_stub(bindir)
    root, _sha = repo({})
    monkeypatch.setenv("PATH", only_git_and(bindir))
    argv = shlex.split(build_security_rule(root, TASK_ID)["command"])
    assert "--gitleaks" in argv and "--osv-scanner" not in argv


def test_no_starting_commit_means_no_rule(monkeypatch, tmp_path):
    bindir = tmp_path / "bin"
    make_gitleaks_stub(bindir)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    not_a_repo = tmp_path / "plain"
    not_a_repo.mkdir()
    assert build_security_rule(not_a_repo, TASK_ID) is None


# ---------------------------------------------------------------------------
# 2. Secrets (scratch repository, the command called directly)
# ---------------------------------------------------------------------------


def test_a_planted_fake_key_fails_and_its_value_is_never_printed(repo, tmp_path):
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    root, sha = repo({})
    planted = fake_marker()
    write(root, "src/settings.py", f'API_KEY = "{planted}"\n')

    code, text = run_check(root, sha, gitleaks=str(gitleaks), osv_scanner=None)

    assert code == 1
    assert "secret -- src/settings.py:1" in text
    assert planted not in text
    assert "read them from the environment or a secret file" in text


def test_no_scanner_setting_from_the_environment_reaches_a_scanner(repo, tmp_path,
                                                                  monkeypatch):
    monkeypatch.setenv("GITLEAKS_CONFIG_TOML", "[allowlist]\nregexes = ['.*']\n")
    monkeypatch.setenv("GITLEAKS_CONFIG", str(tmp_path / "allow-all.toml"))
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    root, sha = repo({})
    write(root, "src/settings.py", f'KEY = "{fake_marker()}"\n')
    code, text = run_check(root, sha, gitleaks=str(gitleaks), osv_scanner=None)
    assert code == 1, text


def test_a_clean_change_passes(repo, tmp_path):
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    osv = make_osv_stub(tmp_path / "bin", VITEST_DB)
    root, sha = repo({})
    write(root, "src/app.py", "def add(a, b):\n    return a + b\n")

    code, text = run_check(root, sha, gitleaks=str(gitleaks), osv_scanner=str(osv))

    assert code == 0, text
    assert "nothing here blocks" in text


def test_guardkit_records_are_not_this_tasks_change(repo, tmp_path):
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    root, sha = repo({})
    write(root, ".guardkit/autobuild/TASK-1/player_turn_1.json", f'"{fake_marker()}"\n')
    code, text = run_check(root, sha, gitleaks=str(gitleaks), osv_scanner=None)
    assert code == 0
    assert "changed no files yet" in text


def test_a_symbolic_link_is_recorded_and_not_followed(repo, tmp_path):
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    outside = write(tmp_path / "outside", "secret.txt", f"{fake_marker()}\n")
    root, sha = repo({})
    (root / "linked.txt").symlink_to(outside)
    code, text = run_check(root, sha, gitleaks=str(gitleaks), osv_scanner=None)
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

    code, text = run_check(root, sha, gitleaks=REAL_GITLEAKS, osv_scanner=None)

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

    code, text = run_check(root, sha, gitleaks=REAL_GITLEAKS, osv_scanner=None)

    assert code == 1, text
    assert "secret -- src/config.py:1" in text


# ---------------------------------------------------------------------------
# 3. Dependencies (scratch repository, the command called directly)
# ---------------------------------------------------------------------------


def test_an_added_package_with_a_critical_advisory_fails_with_every_fix(repo, tmp_path):
    osv = make_osv_stub(tmp_path / "bin", VITEST_DB)
    root, sha = repo({"web/stub.lock": lockfile("npm left-pad 1.3.0")})
    write(root, "web/stub.lock", lockfile("npm left-pad 1.3.0", "npm vitest 4.0.15"))

    code, text = run_check(root, sha, gitleaks=None, osv_scanner=str(osv),
                           deps_dev_url="http://127.0.0.1:9")

    assert code == 1
    assert ("dependency -- vitest 4.0.15 (npm) in web/stub.lock has advisory "
            "GHSA-5xrq-8626-4rwp (critical, 9.8); OSV lists it fixed in 3.2.6 and 4.1.0."
            ) in text


def test_a_lower_severity_advisory_passes_as_advice(repo, tmp_path):
    osv = make_osv_stub(tmp_path / "bin", VITEST_DB)
    root, sha = repo({"stub.lock": lockfile("npm left-pad 1.3.0")})
    write(root, "stub.lock", lockfile("npm left-pad 1.3.0", "npm lodash 4.17.20"))

    code, text = run_check(root, sha, gitleaks=None, osv_scanner=str(osv),
                           deps_dev_url="http://127.0.0.1:9")

    assert code == 0, text
    assert "advice -- lodash 4.17.20 (npm) in stub.lock has advisory GHSA-lowx-0000-0000" in text
    assert "This does not block." in text


def test_a_malicious_package_always_blocks(repo, tmp_path):
    osv = make_osv_stub(tmp_path / "bin", VITEST_DB)
    root, sha = repo({"stub.lock": lockfile("npm left-pad 1.3.0")})
    write(root, "stub.lock", lockfile("npm left-pad 1.3.0", "npm evil-pkg 1.0.0"))

    code, text = run_check(root, sha, gitleaks=None, osv_scanner=str(osv),
                           deps_dev_url="http://127.0.0.1:9")

    assert code == 1
    assert "evil-pkg 1.0.0 (npm) in stub.lock is listed as a known malicious package" in text


def test_a_brand_new_package_fails_and_an_established_one_passes(repo, tmp_path, deps_dev):
    url, server = deps_dev
    now = datetime.now(timezone.utc)
    server.published = {
        "fresh-pkg": (now - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "@scope/old-pkg": (now - timedelta(days=900)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    osv = make_osv_stub(tmp_path / "bin", VITEST_DB)
    root, sha = repo({"stub.lock": lockfile("npm left-pad 1.3.0")})
    write(root, "stub.lock", lockfile(
        "npm left-pad 1.3.0", "npm fresh-pkg 0.0.1", "npm @scope/old-pkg 2.0.0",
        "npm unknown-pkg 1.0.0"))

    code, text = run_check(root, sha, gitleaks=None, osv_scanner=str(osv), deps_dev_url=url)

    assert code == 1
    assert "new package -- fresh-pkg (npm) is new in this change" in text
    assert "Choose an established package instead." in text
    assert "old-pkg (npm) is new" not in text
    assert "unknown-pkg (deps.dev does not know it)" in text
    assert "/v3/systems/NPM/packages/%40scope%2Fold-pkg" in server.seen
    assert not any("left-pad" in p for p in server.seen), "an old package is not looked up"


def test_at_most_twenty_new_packages_are_looked_up(repo, tmp_path, deps_dev):
    url, server = deps_dev
    osv = make_osv_stub(tmp_path / "bin", VITEST_DB)
    root, sha = repo({"stub.lock": lockfile("npm left-pad 1.3.0")})
    write(root, "stub.lock", lockfile("npm left-pad 1.3.0",
                                      *[f"npm pkg-{n:02d} 1.0.0" for n in range(25)]))

    code, text = run_check(root, sha, gitleaks=None, osv_scanner=str(osv), deps_dev_url=url)

    assert code == 0
    assert len(server.seen) == 20
    assert ("The age of 5 more new package(s) was not checked: only the first 20 new "
            "packages are looked up. " + NOT_CLEAN) in text


# ---------------------------------------------------------------------------
# 4. Never a wall (the command called directly)
# ---------------------------------------------------------------------------


def test_missing_tools_pass_as_not_checked(repo, tmp_path):
    root, sha = repo({})
    write(root, "src/settings.py", f'KEY = "{fake_marker()}"\n')
    code, text = run_check(root, sha, gitleaks=str(tmp_path / "nope" / "gitleaks"),
                           osv_scanner=None)
    assert code == 0
    assert "Secret detection was not checked: gitleaks is not there or cannot be run" in text
    assert "Dependency safety was not checked: osv-scanner is not installed." in text
    assert NOT_CLEAN in text


def test_a_scanner_that_cannot_reach_the_network_passes_as_not_checked(repo, tmp_path):
    osv = make_failing_tool(tmp_path / "bin", "osv-scanner", 127)
    root, sha = repo({})
    write(root, "stub.lock", lockfile("npm vitest 4.0.15"))
    code, text = run_check(root, sha, gitleaks=None, osv_scanner=str(osv))
    assert code == 0
    assert "osv-scanner stopped with exit code 127" in text and NOT_CLEAN in text


def test_deps_dev_unreachable_passes_as_not_checked(repo, tmp_path, no_network):
    osv = make_osv_stub(tmp_path / "bin", VITEST_DB)
    root, sha = repo({"stub.lock": lockfile("npm left-pad 1.3.0")})
    write(root, "stub.lock", lockfile("npm left-pad 1.3.0", "npm fresh-pkg 0.0.1"))
    code, text = run_check(root, sha, gitleaks=None, osv_scanner=str(osv))
    assert code == 0, text
    assert "fresh-pkg (deps.dev could not be reached" in text and NOT_CLEAN in text


def test_unreadable_scanner_output_passes_as_not_checked(repo, tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    osv = bindir / "osv-scanner"
    osv.write_text("#!/bin/sh\necho 'not json'\nexit 1\n")
    osv.chmod(0o755)
    root, sha = repo({})
    write(root, "stub.lock", lockfile("npm vitest 4.0.15"))
    code, text = run_check(root, sha, gitleaks=None, osv_scanner=str(osv))
    assert code == 0
    assert "could not be read" in text and NOT_CLEAN in text


def test_findings_from_a_finished_part_still_block_when_another_cannot_run(repo, tmp_path):
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    osv = make_failing_tool(tmp_path / "bin", "osv-scanner", 127)
    root, sha = repo({})
    write(root, "src/settings.py", f'KEY = "{fake_marker()}"\n')
    write(root, "stub.lock", lockfile("npm vitest 4.0.15"))
    code, text = run_check(root, sha, gitleaks=str(gitleaks), osv_scanner=str(osv))
    assert code == 1
    assert "secret -- src/settings.py:1" in text
    assert "Dependency safety was not checked" in text


def test_a_spent_budget_passes_as_not_checked(repo, tmp_path):
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    root, sha = repo({})
    write(root, "src/settings.py", f'KEY = "{fake_marker()}"\n')
    code, text = run_check(root, sha, gitleaks=str(gitleaks), osv_scanner=None,
                           budget_seconds=0)
    assert code == 0
    assert "time budget was spent" in text


def test_a_bad_command_line_or_a_git_failure_passes(tmp_path, capsys):
    assert main(["--no-such-flag"]) == 0
    assert NOT_CLEAN in capsys.readouterr().out
    (tmp_path / "plain").mkdir()
    assert main(["--repo", str(tmp_path / "plain"), "--since", "HEAD"]) == 0
    assert NOT_CLEAN in capsys.readouterr().out


@needs_real_osv
def test_real_osv_scanner_with_no_network_passes_as_not_checked(repo, no_network):
    root, sha = repo({})
    write(root, "web/package-lock.json", json.dumps({
        "name": "probe", "version": "1.0.0", "lockfileVersion": 3, "requires": True,
        "packages": {
            "": {"name": "probe", "version": "1.0.0", "devDependencies": {"vitest": "4.0.15"}},
            "node_modules/vitest": {"version": "4.0.15", "dev": True,
                                    "resolved": "https://registry.npmjs.org/vitest/-/vitest-4.0.15.tgz"},
        }}))
    code, text = run_check(root, sha, gitleaks=None, osv_scanner=REAL_OSV)
    assert code == 0, text
    assert "Dependency safety was not checked" in text and NOT_CLEAN in text


# ---------------------------------------------------------------------------
# 5. Through the real conformance executor
# ---------------------------------------------------------------------------


def test_through_the_executor_a_planted_key_is_one_must_fix_issue(repo, on_path, tmp_path,
                                                                    monkeypatch):
    monkeypatch.delenv(ARCH_SWITCH, raising=False)
    bindir = tmp_path / "bin"
    make_gitleaks_stub(bindir)
    on_path(bindir)
    root, _sha = repo({})

    snapshot_dir = _snapshot(root)
    block, _authority = load_snapshot(snapshot_dir)
    assert [r.id for r in block.rules] == [RULE_ID]

    planted = fake_marker()
    write(root, "src/settings.py", f'KEY = "{planted}"\n')  # written after the freeze
    leg = evaluate_from_snapshot(snapshot_dir, root, task_id=TASK_ID)
    failure = _security_failure(leg)
    assert leg["status"] == "failed" and failure is not None
    assert "secret -- src/settings.py:1" in failure["detail"]
    assert planted not in failure["detail"]

    decision = _guard({"decision": "approve", "issues": []}, leg, tmp_path)
    assert decision["decision"] == "feedback"
    must_fix = [i for i in decision["issues"] if i["severity"] == "must_fix"]
    assert len(must_fix) == 1 and RULE_ID in must_fix[0]["description"]


def test_through_the_executor_a_hanging_scanner_passes_inside_the_outer_limit(
        repo, on_path, tmp_path):
    bindir = tmp_path / "bin"
    make_failing_tool(bindir, "gitleaks", hang=True)
    make_failing_tool(bindir, "osv-scanner", hang=True)
    on_path(bindir)
    root, _sha = repo({})
    snapshot_dir = _snapshot(root)
    # 200 s budget and 60 s deadlines inside a 300 s limit, scaled down tenfold.
    _scale_frozen_rule(snapshot_dir, budget=20, tool_deadline=6, timeout=30)
    write(root, "src/settings.py", f'KEY = "{fake_marker()}"\n')
    write(root, "stub.lock", lockfile("npm vitest 4.0.15"))

    started = time.monotonic()
    leg = evaluate_from_snapshot(snapshot_dir, root, task_id=TASK_ID)
    elapsed = time.monotonic() - started

    assert _security_failure(leg) is None, leg
    assert elapsed < 30


def test_through_the_executor_an_unreachable_network_passes(repo, on_path, tmp_path,
                                                            no_network):
    bindir = tmp_path / "bin"
    make_osv_stub(bindir, VITEST_DB)
    on_path(bindir)
    root, _sha = repo({"stub.lock": lockfile("npm left-pad 1.3.0")})
    snapshot_dir = _snapshot(root)
    write(root, "stub.lock", lockfile("npm left-pad 1.3.0", "npm fresh-pkg 0.0.1"))

    leg = evaluate_from_snapshot(snapshot_dir, root, task_id=TASK_ID)

    assert _security_failure(leg) is None, leg


@pytest.mark.parametrize(
    "start_lock, head_lock, blocks, words",
    [
        pytest.param(
            lockfile("npm vitest 4.0.15"), lockfile("npm vitest 4.0.18"), True,
            "this change moved vitest to 4.0.18 in web/stub.lock, which is still affected "
            "by GHSA-5xrq-8626-4rwp (critical, 9.8); OSV lists fixes in 3.2.6 and 4.1.0.",
            id="ineffective-upgrade-blocks"),
        pytest.param(
            lockfile("npm vitest 4.0.15"), lockfile("npm vitest 4.1.0"), False, None,
            id="effective-upgrade-passes"),
        pytest.param(
            lockfile("npm vitest 4.0.15", "npm left-pad 1.3.0"),
            lockfile("npm vitest 4.0.15", "npm left-pad 1.3.1"), False, None,
            id="unrelated-change-with-an-old-advisory-passes"),
    ],
)
def test_through_the_executor_upgrades_are_judged_on_what_changed(
        repo, on_path, tmp_path, start_lock, head_lock, blocks, words):
    bindir = tmp_path / "bin"
    log = tmp_path / "osv-calls.jsonl"
    make_osv_stub(bindir, VITEST_DB, log)
    on_path(bindir)
    root, _sha = repo({"web/stub.lock": start_lock})
    snapshot_dir = _snapshot(root)
    write(root, "web/stub.lock", head_lock)

    leg = evaluate_from_snapshot(snapshot_dir, root, task_id=TASK_ID)
    failure = _security_failure(leg)

    if blocks:
        assert failure is not None, leg
        assert words in failure["detail"]
    else:
        assert failure is None, leg
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert len(calls) == 2, "the head and the starting versions are both read"
    assert all(c["files"] == ["web/stub.lock"] for c in calls)


def test_through_the_executor_player_settings_do_not_hide_findings(repo, on_path, tmp_path):
    bindir = tmp_path / "bin"
    log = tmp_path / "osv-calls.jsonl"
    make_gitleaks_stub(bindir)
    make_osv_stub(bindir, VITEST_DB, log)
    on_path(bindir)
    root, _sha = repo({"stub.lock": lockfile("npm critical-pkg 1.0.0")})
    snapshot_dir = _snapshot(root)

    planted = fake_marker()
    write(root, "src/settings.py", f'KEY = "{planted}"  # gitleaks:allow\n')
    write(root, "stub.lock", lockfile("npm critical-pkg 2.0.0"))
    write(root, "osv-scanner.toml", '[[IgnoredVulns]]\nid = "GHSA-crit-0000-0000"\n'
                                    'reason = "the Player says so"\n')
    write(root, ".gitleaks.toml", "# allow-everything\n[allowlist]\nregexes = ['.*']\n")
    write(root, ".gitleaksignore", "src/settings.py:stub-fake-secret:1\n")

    leg = evaluate_from_snapshot(snapshot_dir, root, task_id=TASK_ID)
    failure = _security_failure(leg)

    assert failure is not None, leg
    assert "secret -- src/settings.py:1" in failure["detail"]
    assert "critical-pkg 2.0.0 (npm) in stub.lock has advisory GHSA-crit-0000-0000" in failure["detail"]
    assert planted not in failure["detail"]
    for call in (json.loads(line) for line in log.read_text().splitlines()):
        assert "osv-scanner.toml" not in call["files"]
        config = Path(call["argv"][call["argv"].index("--config") + 1])
        assert config.parent.name == "settings" and "guardkit-security-" in str(config)
        assert config.read_text() == "" if config.exists() else True


def _plant_import_bypass(root: Path) -> None:
    for rel in ("guardkit.py", "guardkit/__init__.py", "sitecustomize.py"):
        write(root, rel, "import sys\nsys.exit(0)\n")


def test_through_the_executor_planted_modules_cannot_bypass_the_security_check(
        repo, on_path, tmp_path):
    bindir = tmp_path / "bin"
    make_gitleaks_stub(bindir)
    on_path(bindir)
    root, _sha = repo({})
    snapshot_dir = _snapshot(root)
    _plant_import_bypass(root)
    write(root, "src/settings.py", f'KEY = "{fake_marker()}"\n')

    leg = evaluate_from_snapshot(snapshot_dir, root, task_id=TASK_ID)
    failure = _security_failure(leg)
    assert failure is not None, leg
    assert "secret -- src/settings.py:1" in failure["detail"]

    # The same command without -I is fooled: the planted package answers instead.
    block, _authority = load_snapshot(snapshot_dir)
    command = next(r.command for r in block.rules if r.id == RULE_ID)
    assert " -I " in command
    fooled = subprocess.run(command.replace(" -I ", " ", 1), shell=True, cwd=root,
                            capture_output=True, text=True, timeout=120,
                            env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    assert fooled.returncode == 0 and fooled.stdout == ""


ARCH_RULES = """
format_version: "1.0"
layout:
  source_root: src
rules:
  - id: R-NO-URLLIB
    rule: A feature module does not reach the network directly; it uses the shared client.
    source_document: docs/architecture/adr-009.md
    source_section: "HTTP"
    source_sentence: "Outbound HTTP goes through the shared client, never urllib."
    signals:
      kind: forbidden-imports
      scope: feature_modules
      modules: [urllib.request]
"""


def test_through_the_executor_planted_modules_cannot_bypass_the_architecture_check(
        repo, on_path, tmp_path, monkeypatch):
    monkeypatch.setenv(ARCH_SWITCH, "1")
    on_path(tmp_path / "empty-bin")
    # No scanner on PATH here, so only the architecture rule is frozen.
    monkeypatch.setenv("PATH", only_git_and(tmp_path / "empty-bin"))
    root, _sha = repo({
        "docs/architecture-rules.yaml": ARCH_RULES,
        "src/search/router.py": "from shared.client import get\n",
    })
    snapshot_dir = _snapshot(root)
    block, _authority = load_snapshot(snapshot_dir)
    assert [r.id for r in block.rules] == [ARCH_RULE_ID]
    assert " -I -m guardkit.orchestrator.arch_conformance " in block.rules[0].command

    _plant_import_bypass(root)
    write(root, "src/search/router.py", "import urllib.request\n")

    leg = evaluate_from_snapshot(snapshot_dir, root, task_id=TASK_ID)
    assert leg["status"] == "failed", leg
    assert [f["rule_id"] for f in leg["failures"]] == [ARCH_RULE_ID]
    assert "R-NO-URLLIB" in leg["failures"][0]["detail"]

    # The same command without -I is fooled: the planted package answers instead.
    fooled = subprocess.run(block.rules[0].command.replace(" -I ", " ", 1), shell=True,
                            cwd=root, capture_output=True, text=True, timeout=120,
                            env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    assert fooled.returncode == 0 and fooled.stdout == ""


def test_the_security_rule_is_added_beside_declared_and_architecture_rules(
        repo, on_path, tmp_path, monkeypatch):
    monkeypatch.setenv(ARCH_SWITCH, "1")
    bindir = tmp_path / "bin"
    make_gitleaks_stub(bindir)
    on_path(bindir)
    root, _sha = repo({"docs/architecture-rules.yaml": ARCH_RULES})
    frontmatter = {"conformance": {"rules": [
        {"id": "the-task-said-so", "type": "assert_command", "command": "true"}]}}
    block, _authority = load_snapshot(_snapshot(root, frontmatter))
    assert [r.id for r in block.rules] == ["the-task-said-so", ARCH_RULE_ID, RULE_ID]


# ---------------------------------------------------------------------------
# 6. Fix pass after the independent coach's review (17 October 2026)
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

    code, text = run_check(root, sha, gitleaks=str(gitleaks), osv_scanner=None)

    assert code == 1, text
    for rel in ODD_NAMES:
        assert f"secret -- {rel}:1" in text, (rel, text)


@needs_real_gitleaks
def test_real_gitleaks_reads_files_with_unusual_names(repo):
    root, sha = repo({})
    for rel in ODD_NAMES[:2]:
        write(root, rel, f'AWS_ACCESS_KEY_ID = "{fake_aws_key()}"\n')
    code, text = run_check(root, sha, gitleaks=REAL_GITLEAKS, osv_scanner=None)
    assert code == 1, text
    for rel in ODD_NAMES[:2]:
        assert f"secret -- {rel}:1" in text, (rel, text)


def test_the_architecture_check_lists_unusual_names_exactly(repo):
    from guardkit.orchestrator.arch_conformance import files_changed_since

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
        code, text = run_check(root, sha, gitleaks=str(gitleaks), osv_scanner=None)
    finally:
        locked.chmod(0o644)
    assert code == 0
    assert ("The changed file src/locked.py was not checked: it could not be opened "
            "(PermissionError). " + NOT_CLEAN) in text


def test_a_changed_file_over_the_size_limit_is_read_up_to_it(repo, tmp_path, monkeypatch):
    monkeypatch.setattr(security_check, "MAX_FILE_BYTES", 1000)
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    osv = make_osv_stub(tmp_path / "bin", VITEST_DB)
    root, sha = repo({})
    write(root, "big.txt", f'KEY = "{fake_marker()}"\n' + "a" * 2000
          + f'\nKEY = "{fake_marker()}"\n')
    write(root, "stub.lock", lockfile("npm vitest 4.0.15") + "#" * 2000 + "\n")
    code, text = run_check(root, sha, gitleaks=str(gitleaks), osv_scanner=str(osv))
    assert code == 1
    assert "secret -- big.txt:1" in text and "secret -- big.txt:3" not in text
    assert ("The rest of the changed file big.txt was not checked: it is over 0 MB, so "
            "only its first 0 MB were read for secrets and it was not read for "
            "dependencies.") in text
    assert "The rest of the changed file stub.lock was not checked" in text
    assert "vitest 4.0.15" not in text, "a cut lockfile is not given to OSV-Scanner"


def test_a_gitignore_does_not_hide_a_lockfile(repo, tmp_path):
    osv = make_osv_stub(tmp_path / "bin", VITEST_DB)
    root, sha = repo({"stub.lock": lockfile("npm vitest 4.1.0")})
    write(root, "stub.lock", lockfile("npm vitest 4.0.15"))
    write(root, ".gitignore", "stub.lock\n")

    code, text = run_check(root, sha, gitleaks=None, osv_scanner=str(osv),
                           deps_dev_url="http://127.0.0.1:9")

    assert code == 1, text
    assert "vitest 4.0.15 (npm) in stub.lock has advisory GHSA-5xrq-8626-4rwp" in text


@pytest.mark.parametrize("start_text", ["", "this is not json {\n"], ids=["empty", "not-json"])
def test_an_unreadable_start_version_reports_head_advisories_as_not_checked(
        repo, tmp_path, start_text):
    """The design's rule (decided 17 October 2026): only a known malicious package
    blocks when the start cannot be read; other serious advisories are not checked."""
    osv = make_osv_stub(tmp_path / "bin", VITEST_DB)
    root, sha = repo({"stub.lock": start_text})
    write(root, "stub.lock", lockfile("npm vitest 4.0.15"))

    code, text = run_check(root, sha, gitleaks=None, osv_scanner=str(osv),
                           deps_dev_url="http://127.0.0.1:9")

    assert code == 0, text
    assert ("Advisory GHSA-5xrq-8626-4rwp (critical, 9.8) on vitest 4.0.15 (npm) in "
            "stub.lock was not checked: the starting versions could not be read, so "
            "whether this change brought it in is unknown. " + NOT_CLEAN) in text
    assert "the starting versions could not be read" in text
    # The age check still ran (deps.dev is a closed port here, so it says so).
    assert "vitest (deps.dev could not be reached" in text


def test_each_advisory_is_listed_once_without_commit_hashes(repo, tmp_path):
    """Recorded from the real OSV-Scanner 2.7.0 for requests==2.19.0 (17 October 2026):
    five advisories, each listed under a PYSEC and a GHSA id, two with GIT ranges."""
    osv = make_osv_replay_stub(tmp_path / "bin", FIXTURES / "requests-2.19.0.json")
    root, sha = repo({})
    write(root, "requirements.txt", "requests==2.19.0\n")

    code, text = run_check(root, sha, gitleaks=None, osv_scanner=str(osv),
                           deps_dev_url="http://127.0.0.1:9")

    assert code == 1  # GHSA-x84v-xcm2-53pg scores 7.5
    for ghsa, pysec in (("GHSA-x84v-xcm2-53pg", "PYSEC-2018-28"),
                        ("GHSA-j8r2-6x86-q33q", "PYSEC-2023-74"),
                        ("GHSA-9hjg-9r4m-mvj7", "PYSEC-2026-1872"),
                        ("GHSA-9wx4-h78v-vm56", "PYSEC-2026-1873"),
                        ("GHSA-gc5v-m9x4-r6x2", "PYSEC-2026-2275")):
        assert text.count(ghsa) == 1, (ghsa, text)
        assert text.count(pysec) == 1, (pysec, text)
        assert f"{ghsa} (also {pysec})" in text
    assert "OSV lists it fixed in 2.20.0." in text
    assert not re.search(r"\b[0-9a-f]{40}\b", text), "a commit hash is not a version"


@pytest.mark.parametrize(
    "head_lock, blocks, words",
    [
        pytest.param(lockfile("npm vitest 4.0.15", "npm vitest 4.1.0"), False, None,
                     id="a-second-fixed-copy-is-not-a-move"),
        pytest.param(lockfile("npm vitest 4.0.15", "npm vitest 4.0.18"), True,
                     "this change added vitest 4.0.18 beside 4.0.15 in stub.lock, which is "
                     "still affected by GHSA-5xrq-8626-4rwp",
                     id="a-second-affected-copy-is-named"),
    ],
)
def test_a_second_copy_of_a_package_is_described_as_it_is(repo, tmp_path, head_lock,
                                                          blocks, words):
    osv = make_osv_stub(tmp_path / "bin", VITEST_DB)
    root, sha = repo({"stub.lock": lockfile("npm vitest 4.0.15")})
    write(root, "stub.lock", head_lock)

    code, text = run_check(root, sha, gitleaks=None, osv_scanner=str(osv),
                           deps_dev_url="http://127.0.0.1:9")

    assert "moved vitest to 4.0.15" not in text
    assert code == (1 if blocks else 0), text
    if words:
        assert words in text


def _self_test(python: str, *extra: str, path: Optional[str] = None):
    return subprocess.run(
        [python, "-I", "-m", "guardkit.orchestrator.security_check", "--self-test", *extra],
        capture_output=True, text=True, timeout=120, cwd="/",
        env={"PATH": path or os.environ["PATH"], "HOME": os.environ.get("HOME", "/")})


def test_the_self_test_passes_with_both_scanners(checkout_isolated_python, tmp_path):
    bindir = tmp_path / "bin"
    make_version_stub(bindir, "gitleaks", "8.30.1")
    make_version_stub(bindir, "osv-scanner", "osv-scanner version: 2.7.0")

    done = _self_test(checkout_isolated_python, path=only_git_and(bindir))

    assert done.returncode == 0, done.stdout + done.stderr
    lines = done.stdout.strip().splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("Security check self-test passed: guardkit ")
    assert "isolated" in lines[0] and "gitleaks 8.30.1" in lines[0]
    assert "osv-scanner 2.7.0" in lines[0]


def test_the_self_test_fails_plainly_when_a_scanner_is_missing(checkout_isolated_python,
                                                              tmp_path):
    bindir = tmp_path / "bin"
    make_version_stub(bindir, "gitleaks", "8.30.1")
    done = _self_test(checkout_isolated_python, path=only_git_and(bindir))
    assert done.returncode == 1
    assert done.stdout.startswith("Security check self-test failed: osv-scanner is not installed")


@needs_real_gitleaks
@needs_real_osv
def test_the_self_test_with_the_real_scanners(checkout_isolated_python):
    done = _self_test(checkout_isolated_python, "--gitleaks", REAL_GITLEAKS,
                      "--osv-scanner", REAL_OSV)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "Security check self-test passed" in done.stdout


# ---------------------------------------------------------------------------
# 7. Second fix pass after the coach's re-check (17 October 2026)
# ---------------------------------------------------------------------------


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


def _run_rule_like_the_executor(rule_command: str, root: Path, home: Path):
    env = {"PATH": os.environ["PATH"], "HOME": str(home), "LANG": _utf8_locale()}
    return subprocess.run(["sh", "-c", rule_command], cwd=root, capture_output=True,
                          timeout=300, env=env)


def test_names_that_are_not_utf8_or_hold_a_newline_never_crash_the_command(
        repo, on_path, tmp_path):
    """p9_badname_note.py: a symbolic link named b'bad\\xfflink', plus a file whose
    name holds a newline, under a full UTF-8 locale."""
    bindir = tmp_path / "bin"
    make_gitleaks_stub(bindir)
    on_path(bindir)
    root, _sha = repo({})
    os.symlink(b"README.md", os.path.join(os.fsencode(root), b"bad\xfflink"))
    write(root, "new\nline.py", f'KEY = "{fake_marker()}"\n')
    rule = build_security_rule(root, TASK_ID)

    done = _run_rule_like_the_executor(rule["command"], root, tmp_path)
    out = done.stdout.decode("utf-8")

    assert b"Traceback" not in done.stderr, done.stderr.decode("utf-8", "replace")
    assert done.returncode == 1, out
    assert "bad\\xfflink is a symbolic link; it was recorded and not followed." in out
    assert "secret -- new\\nline.py:1:" in out
    assert not any(line.startswith("line.py") for line in out.splitlines())


def test_the_architecture_check_prints_a_name_that_is_not_utf8(repo, on_path, tmp_path,
                                                              monkeypatch):
    monkeypatch.setenv(ARCH_SWITCH, "1")
    root, _sha = repo({
        "docs/architecture-rules.yaml": ARCH_RULES,
        "src/search/router.py": "from shared.client import get\n",
    })
    bad = os.path.join(os.fsencode(root), b"src", b"search", b"r\xffouter.py")
    with open(bad, "wb") as handle:
        handle.write(b"import urllib.request\n")
    from guardkit.orchestrator.arch_conformance import build_arch_conformance_rule

    rule = build_arch_conformance_rule(root, TASK_ID)
    done = _run_rule_like_the_executor(rule["command"], root, tmp_path)

    assert b"Traceback" not in done.stderr, done.stderr.decode("utf-8", "replace")
    assert done.returncode in (0, 1)
    if done.returncode == 1:
        assert "r\\xffouter.py" in done.stdout.decode("utf-8")


def test_a_nul_byte_early_in_a_file_does_not_hide_a_key(repo, tmp_path):
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    root, sha = repo({})
    (root / "data.bin").write_bytes(b"\x00\x01header\n" + f'KEY = "{fake_marker()}"\n'.encode())
    code, text = run_check(root, sha, gitleaks=str(gitleaks), osv_scanner=None)
    assert code == 1, text
    assert "secret -- data.bin:2" in text


@needs_real_gitleaks
def test_real_gitleaks_decides_about_a_file_with_an_early_nul(repo):
    root, sha = repo({})
    (root / "data.bin").write_bytes(
        b"\x00\x01header\n" + f'AWS_ACCESS_KEY_ID = "{fake_aws_key()}"\n'.encode())
    code, text = run_check(root, sha, gitleaks=REAL_GITLEAKS, osv_scanner=None)
    assert "Secrets: 1 changed file(s) read" in text
    # Whatever Gitleaks decides about this file, it was given it.
    assert code in (0, 1)


def test_a_malicious_package_blocks_even_when_the_start_cannot_be_read(repo, tmp_path):
    osv = make_osv_stub(tmp_path / "bin", VITEST_DB)
    root, sha = repo({"stub.lock": "this is not json {\n"})
    write(root, "stub.lock", lockfile("npm evil-pkg 1.0.0"))
    code, text = run_check(root, sha, gitleaks=None, osv_scanner=str(osv),
                           deps_dev_url="http://127.0.0.1:9")
    assert code == 1, text
    assert "evil-pkg 1.0.0 (npm) in stub.lock is listed as a known malicious package" in text


def test_age_is_not_checked_for_a_package_the_unreadable_start_may_have_held(repo, tmp_path,
                                                                            deps_dev):
    url, server = deps_dev
    osv = make_osv_stub(tmp_path / "bin", VITEST_DB)
    root, sha = repo({"stub.lock": "npm left-pad\n"})  # names left-pad, but is broken
    write(root, "stub.lock", lockfile("npm left-pad 1.3.0", "npm fresh-pkg 0.0.1"))
    code, text = run_check(root, sha, gitleaks=None, osv_scanner=str(osv), deps_dev_url=url)
    assert code == 0, text
    assert ("The age of 1 package(s) was not checked: the starting versions could not be "
            "read, so whether this change added them is unknown.") in text
    assert [p.rsplit("/", 1)[-1] for p in server.seen] == ["fresh-pkg"]


def test_an_indirect_dependency_is_named_as_one(repo, tmp_path):
    db = dict(VITEST_DB)
    db["RESOLVES npm parent 1.0.0"] = ["npm critical-pkg 2.0.0"]
    osv = make_osv_stub(tmp_path / "bin", db)
    root, sha = repo({"stub.lock": lockfile("npm left-pad 1.3.0")})
    write(root, "stub.lock", lockfile("npm left-pad 1.3.0", "npm parent 1.0.0"))
    code, text = run_check(root, sha, gitleaks=None, osv_scanner=str(osv),
                           deps_dev_url="http://127.0.0.1:9")
    assert code == 1, text
    assert ("critical-pkg 2.0.0 (npm) in stub.lock (an indirect dependency resolved by "
            "OSV-Scanner) has advisory GHSA-crit-0000-0000") in text


def test_an_indirect_upgrade_that_does_not_fix_it_is_named_as_indirect(repo, tmp_path):
    db = dict(VITEST_DB)
    db["RESOLVES npm parent 1.0.0"] = ["npm vitest 4.0.15"]
    db["RESOLVES npm parent 1.0.1"] = ["npm vitest 4.0.18"]
    osv = make_osv_stub(tmp_path / "bin", db)
    root, sha = repo({"stub.lock": lockfile("npm parent 1.0.0")})
    write(root, "stub.lock", lockfile("npm parent 1.0.1"))
    code, text = run_check(root, sha, gitleaks=None, osv_scanner=str(osv),
                           deps_dev_url="http://127.0.0.1:9")
    assert code == 1, text
    assert ("this change moved vitest to 4.0.18 in stub.lock (an indirect dependency "
            "resolved by OSV-Scanner), which is still affected by GHSA-5xrq-8626-4rwp") in text


def test_a_passing_security_check_is_written_to_the_build_log(repo, on_path, tmp_path,
                                                              caplog, monkeypatch):
    from guardkit.orchestrator.quality_gates import spec_conformance

    assert spec_conformance._SECURITY_RULE_ID == RULE_ID
    bindir = tmp_path / "bin"
    make_gitleaks_stub(bindir)  # no OSV-Scanner: that part says it was not checked
    monkeypatch.setenv("PATH", only_git_and(bindir))  # a real osv-scanner stays out
    root, _sha = repo({})
    snapshot_dir = _snapshot(root)
    write(root, "src/app.py", "x = 1\n")

    with caplog.at_level("INFO", logger=spec_conformance.__name__):
        leg = evaluate_from_snapshot(snapshot_dir, root, task_id=TASK_ID)

    assert _security_failure(leg) is None, leg
    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert f"Conformance rule '{RULE_ID}' passed; what it printed:" in logged
    assert "Dependency safety was not checked: osv-scanner is not installed." in logged


# ---------------------------------------------------------------------------
# 8. Codex implementation review round 1 (17 October 2026)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "start_files, head_files",
    [
        pytest.param(
            {"a/stub.lock": "this is not json {\n"},
            {"a/stub.lock": lockfile("npm left-pad 1.3.0"),
             "b/stub.lock": lockfile("npm vitest 4.0.15")},
            id="a-new-file-beside-an-unreadable-start"),
        pytest.param(
            {"a/stub.lock": "this is not json {\n", "b/stub.lock": lockfile("npm vitest 4.1.0")},
            {"a/stub.lock": lockfile("npm left-pad 1.3.0"),
             "b/stub.lock": lockfile("npm vitest 4.0.15")},
            id="a-readable-start-beside-an-unreadable-one"),
    ],
)
def test_through_the_executor_one_unreadable_start_does_not_hide_another_file(
        repo, on_path, tmp_path, no_network, start_files, head_files):
    """SC-001: a failed baseline is judged per file. vitest 4.0.15 in b/stub.lock
    blocks whatever happened to a/stub.lock's starting version."""
    bindir = tmp_path / "bin"
    make_osv_stub(bindir, VITEST_DB)
    on_path(bindir)
    root, _sha = repo(start_files)
    snapshot_dir = _snapshot(root)
    for rel, text in head_files.items():
        write(root, rel, text)

    leg = evaluate_from_snapshot(snapshot_dir, root, task_id=TASK_ID)
    failure = _security_failure(leg)

    assert failure is not None, leg
    assert ("vitest 4.0.15 (npm) in b/stub.lock has advisory GHSA-5xrq-8626-4rwp "
            "(critical, 9.8)") in failure["detail"]


def test_an_unreadable_start_still_reports_its_own_advisories_as_not_checked(repo, tmp_path):
    osv = make_osv_stub(tmp_path / "bin", VITEST_DB)
    root, sha = repo({"a/stub.lock": "this is not json {\n",
                      "b/stub.lock": lockfile("npm left-pad 1.3.0")})
    write(root, "a/stub.lock", lockfile("npm vitest 4.0.15"))
    write(root, "b/stub.lock", lockfile("npm left-pad 1.3.0", "npm lodash 4.17.20"))

    code, text = run_check(root, sha, gitleaks=None, osv_scanner=str(osv),
                           deps_dev_url="http://127.0.0.1:9")

    assert code == 0, text
    assert "on vitest 4.0.15 (npm) in a/stub.lock was not checked" in text
    assert "the starting version of a/stub.lock could not be read" in text
    assert "advice -- lodash 4.17.20 (npm) in b/stub.lock has advisory" in text


class _Trickle(http.server.BaseHTTPRequestHandler):
    """Answers at once, then sends its body one byte a second."""

    def do_GET(self):  # noqa: N802 - the handler's own name
        body = b'{"versions": [{"publishedAt": "2015-01-01T00:00:00Z"}]}' + b" " * 40
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        for byte in body:
            try:
                self.wfile.write(bytes([byte]))
                self.wfile.flush()
            except OSError:
                return
            time.sleep(1)

    def log_message(self, *args):
        pass


def _serve(handler) -> tuple:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def test_a_deps_dev_answer_trickling_in_is_given_up_on_at_its_deadline(repo, tmp_path):
    """SC-002: a socket timeout alone would wait for the whole trickle (about 95 s)."""
    server, url = _serve(_Trickle)
    try:
        osv = make_osv_stub(tmp_path / "bin", VITEST_DB)
        root, sha = repo({"stub.lock": lockfile("npm left-pad 1.3.0")})
        write(root, "stub.lock", lockfile("npm left-pad 1.3.0", "npm fresh-pkg 0.0.1"))
        started = time.monotonic()
        code, text = run_check(root, sha, gitleaks=None, osv_scanner=str(osv),
                               deps_dev_url=url)
        elapsed = time.monotonic() - started
    finally:
        server.shutdown()
    assert code == 0, text
    assert "fresh-pkg (deps.dev gave no complete answer within 5 seconds)" in text
    assert NOT_CLEAN in text
    assert elapsed < 20


class _TrickleProxy(http.server.BaseHTTPRequestHandler):
    """A proxy that accepts a CONNECT and sends its reply one byte a second."""

    def do_CONNECT(self):  # noqa: N802 - the handler's own name
        reply = b"HTTP/1.1 200 Connection established\r\nX-Slow: " + b"y" * 60 + b"\r\n\r\n"
        for byte in reply:
            try:
                self.wfile.write(bytes([byte]))
                self.wfile.flush()
            except OSError:
                return
            time.sleep(1)

    def log_message(self, *args):
        pass


def test_through_the_executor_a_trickling_network_finishes_as_not_checked(
        repo, on_path, tmp_path, monkeypatch):
    """SC-002 through the real executor: deps.dev is reached through a proxy that
    sends its answer a byte a second. Every lookup is given up on at 5 seconds and the
    check passes as not checked, far inside the 300-second limit."""
    server, url = _serve(_TrickleProxy)
    for name in ("NO_PROXY", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
    for name in ("HTTPS_PROXY", "https_proxy"):
        monkeypatch.setenv(name, url)
    try:
        bindir = tmp_path / "bin"
        make_osv_stub(bindir, VITEST_DB)
        on_path(bindir)
        root, _sha = repo({"stub.lock": lockfile("npm left-pad 1.3.0")})
        snapshot_dir = _snapshot(root)
        write(root, "stub.lock", lockfile("npm left-pad 1.3.0", "npm fresh-a 0.0.1",
                                          "npm fresh-b 0.0.1"))
        started = time.monotonic()
        leg = evaluate_from_snapshot(snapshot_dir, root, task_id=TASK_ID)
        elapsed = time.monotonic() - started
    finally:
        server.shutdown()
    assert _security_failure(leg) is None, leg
    assert elapsed < 60


def test_staging_stops_when_the_budget_is_spent(repo, tmp_path, monkeypatch):
    gitleaks = make_gitleaks_stub(tmp_path / "bin")
    root, sha = repo({})
    for n in range(3):
        write(root, f"f{n}.py", f'KEY = "{fake_marker()}"\n')
    clock = iter([100.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    monkeypatch.setattr(security_check.Budget, "left", lambda self: next(clock, 0.0))
    code, text = run_check(root, sha, gitleaks=str(gitleaks), osv_scanner=None)
    assert code == 0, text
    assert "3 changed file(s) was not checked: the check's time budget was spent" in text
