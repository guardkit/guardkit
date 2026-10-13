"""Project commands run without the factory's credentials (13 October 2026).

Design: ``docs/designs/factory-project-commands-without-factory-credentials-
2026-10-13.md``, accepted in design review round 4.

GuardKit's own process holds the factory's credentials (Forge hands it
``OPENAI_API_KEY``, ``GUARDKIT_NATS_PASSWORD``, ``FLEET_MEMORY_PG_DSN`` and
others). Every place GuardKit runs a project's own command must give that
command an environment built from nothing
(``guardkit.orchestrator.project_command_env``), never a copy of its own.

The fixture plants a sentinel value in each factory setting, then drives each
project-command path. A stand-in project command writes its environment to a
file outside the project; no sentinel may appear in it. Positive controls
prove the declared settings, scratch folders, the run-owner marker and the
per-command additions still arrive. ``test_every_process_launch_is_accounted_for``
fails on any process launch in the package that neither uses the helper nor is
one of the factory's own programs (section 5 of the design).
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import socket
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import pytest

from guardkit.orchestrator import project_command_env as pce
from guardkit.orchestrator.launch_declaration import (
    LaunchDeclaration,
    LaunchEnvironmentError,
    snapshot_task_launch,
)
from guardkit.orchestrator.paths import BUILDER_SCRATCH_DIRNAME

# ---------------------------------------------------------------------------
# The fixture: a factory environment full of sentinels, and a real project
# ---------------------------------------------------------------------------

SENTINEL_NAMES = (
    "GUARDKIT_NATS_PASSWORD",
    "FLEET_MEMORY_PG_DSN",
    "FLEET_MEMORY_NATS_URL",
    "FORGE_NATS_URL",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "ANTHROPIC_API_KEY",
    "FORGE_DB_PATH",
    "SSH_AUTH_SOCK",
)
MARK = "SENTINEL-c4f1"
TASK = "TASK-CREDS-1"
_PROXIES = [
    name
    for base in ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY", "FTP_PROXY")
    for name in (base, base.lower())
]


def _sentinel(name: str) -> str:
    return f"{MARK}-{name}"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.invalid",
        },
    )


class Project(SimpleNamespace):
    """The stand-in project and the helpers that read what it saw."""

    repo: Path
    out: Path
    dump_sh: Path
    dump_py: Path

    def sh(self, label: str) -> str:
        """A shell command line that writes its environment to ``label``."""
        return f"sh {self.dump_sh} {label}"

    def read(self, label: str) -> Dict[str, str]:
        path = self.out / f"{label}.env"
        assert path.exists(), f"the stand-in command for {label!r} never ran"
        return _parse_env(path.read_text(encoding="utf-8"))


def _parse_env(text: str) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            name, value = line.split("=", 1)
            env[name] = value
    return env


def _assert_no_sentinel(env: Any, where: str) -> None:
    assert isinstance(env, dict), (
        f"{where}: the command was given no environment of its own "
        f"({env!r}), so it inherits the factory's, credentials included"
    )
    leaked = sorted(
        name for name, value in env.items() if MARK in str(value) or name in SENTINEL_NAMES
    )
    assert not leaked, f"{where}: the factory's settings reached the project: {leaked}"


@pytest.fixture()
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Project:
    for name in SENTINEL_NAMES:
        monkeypatch.setenv(name, _sentinel(name))
    for name in _PROXIES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("STANDIN_SETTING", "present")
    monkeypatch.setenv("GUARDKIT_RUN_OWNER", "build-x")
    monkeypatch.delenv("GUARDKIT_FACTORY_LAUNCH", raising=False)
    monkeypatch.delenv("PYTHONPATH", raising=False)

    repo = tmp_path / "repo"
    (repo / ".guardkit").mkdir(parents=True)
    (repo / ".guardkit" / "config.yaml").write_text(
        "launch:\n  settings: [STANDIN_SETTING]\n  scratch: [STANDIN_CACHE]\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("stand-in\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")

    out = tmp_path / "seen"
    out.mkdir()
    tools = tmp_path / "tools"
    tools.mkdir()
    dump_sh = tools / "dump.sh"
    dump_sh.write_text(f'#!/bin/sh\nenv > "{out}/$1.env"\n', encoding="utf-8")
    dump_sh.chmod(0o755)
    dump_py = tools / "dump.py"
    dump_py.write_text(
        textwrap.dedent(
            f"""\
            import os, sys
            label = sys.argv[1] if len(sys.argv) > 1 else "python"
            with open(os.path.join({str(out)!r}, label + ".env"), "w") as fh:
                for k, v in os.environ.items():
                    fh.write(k + "=" + v.replace("\\n", " ") + "\\n")
            """
        ),
        encoding="utf-8",
    )
    snapshot_task_launch(TASK, repo, repo)
    return Project(repo=repo, out=out, dump_sh=dump_sh, dump_py=dump_py)


class Recorder:
    """Stands in for ``subprocess.run``: records ``env=`` and either runs the
    real command (``run_real``) or answers a plain success."""

    def __init__(self, real: Callable[..., Any], run_real: Callable[[Any], bool] = lambda a: False):
        self.real = real
        self.run_real = run_real
        self.calls: List[Tuple[Any, Any]] = []

    def __call__(self, args: Any, *a: Any, **kw: Any) -> Any:
        self.calls.append((args, kw.get("env", "<no env= given>")))
        if self.run_real(args):
            return self.real(args, *a, **kw)
        text = kw.get("text") or kw.get("universal_newlines")
        out = "1 passed in 0.01s" if text else b"1 passed in 0.01s"
        err = "" if text else b""
        return subprocess.CompletedProcess(args, 0, stdout=out, stderr=err)


def _record_run(monkeypatch: pytest.MonkeyPatch, run_real=lambda a: False) -> Recorder:
    recorder = Recorder(subprocess.run, run_real)
    monkeypatch.setattr(subprocess, "run", recorder)
    return recorder


def _assert_recorded_clean(recorder: Recorder, where: str) -> None:
    assert recorder.calls, f"{where}: no command was started"
    for args, env in recorder.calls:
        _assert_no_sentinel(env, f"{where} ({args!r})")


# ---------------------------------------------------------------------------
# Test 1: the helper builds from nothing
# ---------------------------------------------------------------------------


def test_the_helper_builds_from_nothing(project: Project) -> None:
    declaration = LaunchDeclaration(settings=("STANDIN_SETTING",), scratch=("STANDIN_CACHE",))
    env = pce.project_command_environment(project.repo, declaration)
    expected = {"PATH", "HOME", "TMPDIR", "STANDIN_SETTING", "STANDIN_CACHE", "GUARDKIT_RUN_OWNER"}
    expected |= {n for n in os.environ if n in ("LANG", "LC_ALL") or n.startswith("LC_")}
    assert set(env) == expected
    _assert_no_sentinel(env, "the helper")
    scratch = project.repo / ".git" / BUILDER_SCRATCH_DIRNAME
    for name in ("HOME", "TMPDIR"):
        assert Path(env[name]).resolve().is_relative_to(scratch.resolve()), name


@pytest.mark.real_project_scratch
def test_a_work_folder_that_is_not_a_git_checkout_runs_nothing(tmp_path: Path) -> None:
    """No scratch folder, no private HOME: the command does not run, and
    nothing falls back to the factory's own environment."""
    from guardkit.orchestrator.completion_verification import run_completion_verification

    with pytest.raises(LaunchEnvironmentError) as caught:
        pce.project_command_environment(tmp_path, None)
    assert "no usable scratch folder" in str(caught.value)
    result = run_completion_verification(tmp_path, "true", "declared")
    assert result.status == "unverified"
    assert "could not start" in result.detail


# ---------------------------------------------------------------------------
# Test 2: every project-command path hides the factory's credentials
# ---------------------------------------------------------------------------


def _run_install(p: Project) -> Dict[str, str]:
    from guardkit.orchestrator.environment_bootstrap import (
        DetectedManifest,
        EnvironmentBootstrapper,
    )

    manifest = DetectedManifest(
        path=p.repo / ".guardkit" / "config.yaml",
        stack="generic",
        is_lock_file=False,
        install_command=["sh", str(p.dump_sh), "install"],
        declared=True,
        install_cwd=p.repo,
    )
    assert EnvironmentBootstrapper(p.repo)._run_install(manifest)
    return p.read("install")


def _run_install_retry(p: Project) -> Dict[str, str]:
    """Row 2: the PEP 668 retry, for real, into a venv made for it."""
    from guardkit.orchestrator.environment_bootstrap import (
        DetectedManifest,
        EnvironmentBootstrapper,
    )

    script = p.out.parent / "tools" / "pep668.py"
    script.write_text(
        textwrap.dedent(
            f"""\
            import os, sys
            if sys.prefix == sys.base_prefix:
                sys.stderr.write("error: externally-managed-environment\\n")
                sys.exit(1)
            exec(open({str(p.dump_py)!r}).read().replace("sys.argv[1] if len(sys.argv) > 1 else \\"python\\"", "'install-retry'"))
            """
        ),
        encoding="utf-8",
    )
    manifest = DetectedManifest(
        path=p.repo / ".guardkit" / "config.yaml",
        stack="python",
        is_lock_file=False,
        install_command=[sys.executable, str(script)],
        declared=True,
        install_cwd=p.repo,
    )
    assert EnvironmentBootstrapper(p.repo)._run_install(manifest)
    return p.read("install-retry")


def _run_single_dependency(p: Project) -> Dict[str, str]:
    from guardkit.orchestrator.environment_bootstrap import EnvironmentBootstrapper

    assert EnvironmentBootstrapper(p.repo)._run_single_command(
        ["sh", str(p.dump_sh), "dependency"], p.repo
    )
    return p.read("dependency")


def _validator(p: Project, **kw: Any):
    from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator

    return CoachValidator(str(p.repo), task_id=TASK, **kw)


def _run_checker_test(p: Project) -> Dict[str, str]:
    _validator(p, test_command=p.sh("checker-test")).run_independent_tests()
    return p.read("checker-test")


def _run_checker_isolated(p: Project) -> Dict[str, str]:
    _validator(p, test_command=p.sh("checker-isolated"))._run_isolated_tests(
        p.sh("checker-isolated")
    )
    return p.read("checker-isolated")


def _run_checker_coverage(p: Project) -> Dict[str, str]:
    validator = _validator(p)
    validator._declared_coverage_command = lambda: p.sh("checker-coverage")  # type: ignore[method-assign]
    validator.run_declared_coverage()
    return p.read("checker-coverage")


def _run_runtime_parity(p: Project) -> Dict[str, str]:
    _validator(p, smoke_command=p.sh("runtime-parity"))._gather_runtime_parity()
    return p.read("runtime-parity")


def _run_receipt_oracle(p: Project) -> Dict[str, str]:
    checker = p.repo / "checker.sh"
    checker.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (p.repo / "src.txt").write_text("x\n", encoding="utf-8")
    declaration = {
        "command": p.sh("oracle-receipt"),
        "expected_exit": 0,
        "expected_checks": 1,
        "checker_path": "checker.sh",
        "checker_sha256": hashlib.sha256(checker.read_bytes()).hexdigest(),
        "source_paths": ["src.txt"],
    }
    _validator(p)._run_required_shell_command(declaration, task_id=TASK, turn=1)
    return p.read("oracle-receipt")


def _run_yaml_oracle(p: Project) -> Dict[str, str]:
    _validator(p)._run_shell_command(p.sh("oracle-yaml"), None)
    return p.read("oracle-yaml")


def _feature_worktree(p: Project) -> Path:
    """A linked feature worktree, where the checker's criteria commands run."""
    worktree = p.repo / ".guardkit" / "worktrees" / "FEAT-CREDS"
    if not worktree.exists():
        _git(p.repo, "worktree", "add", "-q", "-b", "autobuild/FEAT-CREDS", str(worktree))
        snapshot_task_launch(TASK, worktree, p.repo)
    return worktree


def _run_criteria(p: Project) -> Dict[str, str]:
    from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator

    worktree = _feature_worktree(p)
    CoachValidator(str(worktree), task_id=TASK).verify_command_criteria(
        [f"`{p.sh('criteria')}` runs successfully"]
    )
    return p.read("criteria")


def _run_feature_check(p: Project) -> Dict[str, str]:
    from guardkit.orchestrator.feature_check import run_feature_check_command

    run_feature_check_command(
        p.sh("feature-check"), cwd=p.repo, timeout=60, launch_root=p.repo,
        env_extra={"GUARDKIT_FEATURE_ID": "FEAT-X"},
    )
    return p.read("feature-check")


def _run_smoke_gate(p: Project) -> Dict[str, str]:
    from guardkit.orchestrator.feature_loader import SmokeGates
    from guardkit.orchestrator.smoke_gates import run_smoke_gate

    run_smoke_gate(SmokeGates(after_wave="all", command=p.sh("smoke")), p.repo, 1)
    return p.read("smoke")


def _run_completion_verification(p: Project) -> Dict[str, str]:
    from guardkit.orchestrator.completion_verification import run_completion_verification

    run_completion_verification(p.repo, p.sh("verify"), "declared")
    return p.read("verify")


def _run_inventory(p: Project) -> Dict[str, str]:
    from guardkit.orchestrator.feature_check import run_feature_check_command
    from guardkit.orchestrator.run_evidence import EvidenceRequest

    run_feature_check_command(
        "true", cwd=p.repo, timeout=60, launch_root=p.repo,
        evidence=EvidenceRequest(kind="whole-feature check", environment_inventory=p.sh("inventory")),
    )
    return p.read("inventory")


def _run_machine_verify(p: Project, monkeypatch: pytest.MonkeyPatch) -> Dict[str, str]:
    from guardkit.orchestrator import baseline
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    monkeypatch.setattr(
        baseline, "read_baseline_from_worktree", lambda path: SimpleNamespace(command=p.sh("machine-verify"))
    )
    AutoBuildOrchestrator._observed_reds_in_worktree(None, SimpleNamespace(path=p.repo))  # type: ignore[arg-type]
    return p.read("machine-verify")


def _run_bin_entry_probe(p: Project) -> Dict[str, str]:
    from guardkit.orchestrator.autobuild import _check_direct_mode_bin_entries

    manifest = p.repo / "installer" / "core" / "commands" / "bin-entries.txt"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("probe.py\n", encoding="utf-8")
    (p.repo / "probe.py").write_text(
        p.dump_py.read_text(encoding="utf-8").replace(
            'sys.argv[1] if len(sys.argv) > 1 else "python"', '"bin-entry"'
        ),
        encoding="utf-8",
    )
    _check_direct_mode_bin_entries(p.repo, ["probe.py"], sys.executable)
    return p.read("bin-entry")


def _boot_config(entries: List[Dict[str, Any]]):
    import yaml

    from guardkit.orchestrator.seam_checks import _parse_config

    return _parse_config(yaml.safe_dump({"version": 1, "boot_smoke": entries}))


def _plant_module(p: Project, name: str, label: str) -> None:
    (p.repo / f"{name}.py").write_text(
        p.dump_py.read_text(encoding="utf-8").replace(
            'sys.argv[1] if len(sys.argv) > 1 else "python"', repr(label)
        )
        + "\ndef make():\n    return object()\n",
        encoding="utf-8",
    )


def _run_boot_import(p: Project) -> Dict[str, str]:
    from guardkit.orchestrator.boot_smoke import run_boot_smoke

    _plant_module(p, "standin_boot", "boot-import")
    run_boot_smoke(_boot_config([{"id": "i", "kind": "import", "target": "standin_boot"}]), p.repo)
    return p.read("boot-import")


def _run_boot_construct(p: Project) -> Dict[str, str]:
    from guardkit.orchestrator.boot_smoke import run_boot_smoke

    _plant_module(p, "standin_make", "boot-construct")
    run_boot_smoke(
        _boot_config([{"id": "c", "kind": "construct", "target": "standin_make:make"}]), p.repo
    )
    return p.read("boot-construct")


def _run_boot_serve(p: Project) -> Dict[str, str]:
    from guardkit.orchestrator.boot_smoke import run_boot_smoke

    _plant_module(p, "standin_serve", "boot-serve")
    run_boot_smoke(
        _boot_config([{"id": "s", "kind": "serve", "target": "standin_serve",
                       "readiness": {"kind": "exit_zero"}}]),
        p.repo,
    )
    return p.read("boot-serve")


def _run_boot_command(p: Project) -> Dict[str, str]:
    from guardkit.orchestrator.boot_smoke import run_boot_smoke

    run_boot_smoke(
        _boot_config([{"id": "k", "kind": "command", "target": f"sh {p.dump_sh} boot-command"}]),
        p.repo,
    )
    return p.read("boot-command")


def _run_boot_reachable(p: Project) -> Dict[str, str]:
    from guardkit.orchestrator.boot_smoke import run_boot_smoke

    run_boot_smoke(
        _boot_config([{"id": "r", "kind": "command", "target": "true",
                       "env_required": [{"reachable": p.sh("boot-reachable")}]}]),
        p.repo,
    )
    return p.read("boot-reachable")


def _run_assert_command(p: Project) -> Dict[str, str]:
    from guardkit.orchestrator.quality_gates.spec_conformance import (
        AssertCommandRule,
        _evaluate_assert_command,
    )

    _evaluate_assert_command(
        AssertCommandRule(id="a", type="assert_command", command=p.sh("assert-command")), p.repo
    )
    return p.read("assert-command")


def _run_evidence_repo(p: Project) -> Dict[str, str]:
    from guardkit.orchestrator.evidence_repos import EvidenceRepo, run_repo_tests

    run_repo_tests(EvidenceRepo(name="sibling", root=p.repo, test_command=p.sh("evidence-repo")))
    return p.read("evidence-repo")


def _run_live_gate(p: Project) -> Dict[str, str]:
    import http.server
    import threading

    import yaml

    from guardkit.orchestrator.live_gate.runner import LiveGateRunner

    (p.repo / "qa" / "gates").mkdir(parents=True)
    (p.repo / "qa" / "pass-bar-T-1.yaml").write_text(
        textwrap.dedent(
            """\
            format_version: "2.0"
            task_id: T-1
            registered_at: {sha: abcd, date: "2026-07-05"}
            auth_surface_bearing: true
            preconditions: [suite_green_vs_ledger]
            criteria:
              - {id: C1, text: "answers", class: machine, evidence_kind: json}
            negative_paths: [wrong_credential, anonymous_deep_link, post_logout_401, unauthorized_403_ui, dependency_down_degradation]
            """
        ),
        encoding="utf-8",
    )
    (p.repo / "qa" / "gates" / "g1.py").write_text(
        p.dump_py.read_text(encoding="utf-8").replace(
            'sys.argv[1] if len(sys.argv) > 1 else "python"', '"live-gate"'
        ),
        encoding="utf-8",
    )
    (p.repo / "qa" / "gates" / "registry.yaml").write_text(
        yaml.safe_dump(
            {
                "format_version": "1.0",
                "gates": [
                    {
                        "id": "g1",
                        "path": "qa/gates/g1.py",
                        "target": {"base_url_env": "STANDIN_BASE_URL", "environment_id": "local"},
                        "pass_bar_ref": "qa/pass-bar-T-1.yaml",
                        "evidence_dir_pattern": "qa/gates/evidence-{date}/shots-g1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        os.environ["STANDIN_BASE_URL"] = f"http://127.0.0.1:{server.server_address[1]}"
        LiveGateRunner(p.repo).run("PILOT", "local")
    finally:
        os.environ.pop("STANDIN_BASE_URL", None)
        server.shutdown()
        thread.join(timeout=5)
    seen = p.read("live-gate")
    assert seen.get("STANDIN_BASE_URL", "").startswith("http://127.0.0.1:")
    return seen


def _run_mutation(p: Project) -> Dict[str, str]:
    from guardkit.orchestrator.qa_stages.mutation import make_pytest_runner

    make_pytest_runner(["sh", str(p.dump_sh), "mutation"], work_folder=p.repo)(p.repo)
    return p.read("mutation")


def _run_qa_seed(p: Project) -> Dict[str, str]:
    from guardkit.templates.qa_seed import _default_suite_runner

    _default_suite_runner(["sh", str(p.dump_sh), "qa-seed"], p.repo)
    return p.read("qa-seed")


#: The generic sites, run for real: (row, label, driver).
GENERIC_SITES: List[Tuple[str, Callable[..., Dict[str, str]]]] = [
    ("1 builder's install", _run_install),
    ("2 install retry (PEP 668)", _run_install_retry),
    ("3 single dependency install", _run_single_dependency),
    ("4 checker's declared test", _run_checker_test),
    ("6 checker's run in an isolated copy", _run_checker_isolated),
    ("7 checker's declared coverage", _run_checker_coverage),
    ("8 runtime-parity smoke", _run_runtime_parity),
    ("10 oracle with a receipt", _run_receipt_oracle),
    ("11 oracle command from YAML", _run_yaml_oracle),
    ("12 acceptance-criteria command", _run_criteria),
    ("15 whole-feature check", _run_feature_check),
    ("16 smoke gate and baseline probe", _run_smoke_gate),
    ("17 check after a merge / autobuild --verify", _run_completion_verification),
    ("19 environment inventory", _run_inventory),
    ("20 machine verify re-run", _run_machine_verify),
    ("21 bin-entry probe", _run_bin_entry_probe),
    ("22 boot smoke: import", _run_boot_import),
    ("22 boot smoke: construct", _run_boot_construct),
    ("22 boot smoke: serve", _run_boot_serve),
    ("23 boot smoke: command", _run_boot_command),
    ("23 boot smoke: reachable probe", _run_boot_reachable),
    ("28 spec-conformance assert_command", _run_assert_command),
    ("29 sibling evidence repository", _run_evidence_repo),
    ("30 live-gate scripts", _run_live_gate),
    ("31 QA mutation stage", _run_mutation),
    ("32 QA seed suite", _run_qa_seed),
]


def _drive(driver: Callable[..., Dict[str, str]], p: Project, monkeypatch) -> Dict[str, str]:
    import inspect

    if "monkeypatch" in inspect.signature(driver).parameters:
        return driver(p, monkeypatch=monkeypatch)
    return driver(p)


@pytest.mark.parametrize("row,driver", GENERIC_SITES, ids=[r for r, _ in GENERIC_SITES])
def test_every_project_command_path_hides_factory_credentials(
    project: Project, monkeypatch: pytest.MonkeyPatch, row: str, driver
) -> None:
    seen = _drive(driver, project, monkeypatch)
    _assert_no_sentinel(seen, f"row {row}")


# ---- Python-only sites: the env= passed is captured ------------------------


def _capture_venv_creation(p: Project, monkeypatch) -> Recorder:
    from guardkit.orchestrator.environment_bootstrap import EnvironmentBootstrapper

    recorder = _record_run(monkeypatch)
    bs = EnvironmentBootstrapper(p.repo)
    bs._ensure_venv()
    bs._ensure_uv_venv(p.repo, None)
    bs._ensure_worktree_venv(p.repo / "elsewhere")
    return recorder


def _capture_pytest_path(p: Project, monkeypatch) -> Recorder:
    recorder = _record_run(monkeypatch)
    _validator(p, test_command="pytest tests").run_independent_tests()
    return recorder


def _capture_python_oracle(p: Project, monkeypatch) -> Recorder:
    oracle = p.repo / "tests" / "oracle_roundtrip.py"
    oracle.parent.mkdir()
    oracle.write_text("def test_x():\n    assert True\n", encoding="utf-8")
    recorder = _record_run(monkeypatch)
    _validator(p)._produce_python_oracle([oracle], [], None)
    return recorder


def _capture_timeout_probe(p: Project, monkeypatch) -> Recorder:
    other = p.out.parent / "tools" / "python"
    other.symlink_to(sys.executable)
    recorder = _record_run(monkeypatch)
    validator = _validator(p, venv_python=str(other))
    validator._probe_pytest_timeout()
    return recorder


def _capture_coverage_gate(p: Project, monkeypatch) -> Recorder:
    from guardkit.orchestrator.quality_gates.coverage_gate import _run_coverage

    (p.repo / "pkg").mkdir()
    (p.repo / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (p.repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    recorder = _record_run(monkeypatch)
    _run_coverage(p.repo, ["pkg/__init__.py"])
    return recorder


def _capture_honesty_verifier(p: Project, monkeypatch) -> Recorder:
    from guardkit.orchestrator.coach_verification import CoachVerifier

    recorder = _record_run(monkeypatch)
    CoachVerifier(p.repo, venv_python=sys.executable)._run_tests()
    return recorder


def _capture_env_parity(p: Project, monkeypatch) -> Recorder:
    from guardkit.orchestrator.env_parity import _run_resolution_probe

    recorder = _record_run(monkeypatch)
    _run_resolution_probe(["json"], sys.executable, p.repo)
    return recorder


def _capture_bdd_run(p: Project, monkeypatch) -> Recorder:
    from guardkit.orchestrator.quality_gates import bdd_runner

    recorder = _record_run(monkeypatch)
    junit = p.repo / "junit.xml"
    bdd_runner._invoke_pytest_bdd([p.repo / "a.feature"], "@task:X", p.repo, junit, 10, sys.executable, TASK)
    bdd_runner._invoke_pytest_sweep([p.repo / "glue.py"], p.repo, junit, 10, sys.executable, TASK)
    return recorder


def _capture_bdd_probe_for_task(p: Project, monkeypatch) -> Recorder:
    """Row 25a through ``run_bdd_for_task``: the probe runs before any BDD run."""
    from guardkit.orchestrator.quality_gates import bdd_runner

    (p.repo / "features").mkdir()
    (p.repo / "features" / "x.feature").write_text(
        f"@task:{TASK}\nFeature: x\n  Scenario: y\n    Given z\n", encoding="utf-8"
    )
    recorder = _record_run(monkeypatch)
    bdd_runner.run_bdd_for_task(TASK, p.repo, python_executable=sys.executable)
    assert recorder.calls and recorder.calls[0][0][-1] == "import pytest_bdd"
    return recorder


def _capture_bdd_probe_for_sweep(p: Project, monkeypatch) -> Recorder:
    from guardkit.orchestrator.quality_gates import bdd_runner

    glue = p.repo / "features" / "steps" / "test_glue.py"
    glue.parent.mkdir(parents=True)
    glue.write_text("", encoding="utf-8")
    recorder = _record_run(monkeypatch)
    bdd_runner.run_bdd_authoring_sweep(TASK, p.repo, [glue], python_executable=sys.executable)
    assert recorder.calls and recorder.calls[0][0][-1] == "import pytest_bdd"
    return recorder


#: The Python-only sites, checked by capturing env=: (row, driver).
CAPTURED_SITES: List[Tuple[str, Callable[..., Recorder]]] = [
    ("1a making the virtual environment", _capture_venv_creation),
    ("5 checker's pytest-path test", _capture_pytest_path),
    ("9 behavioural oracle (Python file)", _capture_python_oracle),
    ("13 pytest-timeout probe", _capture_timeout_probe),
    ("24 environment-parity probe", _capture_env_parity),
    ("25 BDD runs", _capture_bdd_run),
    ("25a pytest-bdd probe via run_bdd_for_task", _capture_bdd_probe_for_task),
    ("25a pytest-bdd probe via run_bdd_authoring_sweep", _capture_bdd_probe_for_sweep),
    ("26 coverage gate", _capture_coverage_gate),
    ("27 honesty verifier's pytest runs", _capture_honesty_verifier),
]


@pytest.mark.parametrize("row,driver", CAPTURED_SITES, ids=[r for r, _ in CAPTURED_SITES])
def test_every_python_only_path_is_given_a_clean_environment(
    project: Project, monkeypatch: pytest.MonkeyPatch, row: str, driver
) -> None:
    recorder = driver(project, monkeypatch)
    _assert_recorded_clean(recorder, f"row {row}")


# ---------------------------------------------------------------------------
# Test 3: positive control — declared settings, scratch and the owner arrive
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "row,driver",
    [s for s in GENERIC_SITES if not s[0].startswith(("29", "30"))],
    ids=[r for r, _ in GENERIC_SITES if not r.startswith(("29", "30"))],
)
def test_declared_settings_scratch_and_run_owner_still_arrive(
    project: Project, monkeypatch: pytest.MonkeyPatch, row: str, driver
) -> None:
    seen = _drive(driver, project, monkeypatch)
    assert seen.get("STANDIN_SETTING") == "present", row
    assert seen.get("GUARDKIT_RUN_OWNER") == "build-x", row
    cache = Path(seen["STANDIN_CACHE"]).resolve()
    assert cache.name == "STANDIN_CACHE" and cache.parent.name == "toolchain", row
    assert cache.parent.parent.name == BUILDER_SCRATCH_DIRNAME, row
    assert cache.is_relative_to((project.repo / ".git").resolve()), row
    assert Path(seen["HOME"]).resolve() == cache.parent / "HOME", row


def test_the_install_and_the_checker_share_one_scratch_folder(
    project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    install = _run_install(project)
    checker = _run_checker_test(project)
    assert install["STANDIN_CACHE"] == checker["STANDIN_CACHE"]


# ---------------------------------------------------------------------------
# Test 4: positive control — the per-command additions still arrive
# ---------------------------------------------------------------------------


def test_additions_still_arrive(project: Project, monkeypatch: pytest.MonkeyPatch) -> None:
    from guardkit.orchestrator.environment_bootstrap import EnvironmentBootstrapper
    from guardkit.orchestrator.feature_check import run_feature_check_command

    feature = {
        "GUARDKIT_FEATURE_ID": "FEAT-X",
        "GUARDKIT_FEATURE_RECORD": "/r",
        "GUARDKIT_WORKTREE": str(project.repo),
        "GUARDKIT_CANDIDATE_SHA": "abc",
    }
    run_feature_check_command(
        project.sh("feature-additions"), cwd=project.repo, timeout=60,
        env_extra=feature, launch_root=project.repo,
    )
    seen = project.read("feature-additions")
    for name, value in feature.items():
        assert seen.get(name) == value, name

    validator = _validator(project, test_command=project.sh("fixture-url"))
    validator._fixture_env["DATABASE_URL"] = "postgresql://127.0.0.1:5999/test"
    validator.run_independent_tests()
    assert project.read("fixture-url")["DATABASE_URL"] == "postgresql://127.0.0.1:5999/test"

    _run_receipt_oracle(project)
    receipt = project.read("oracle-receipt")
    assert receipt["GUARDKIT_BEHAVIOURAL_ORACLE_RECEIPT"].endswith("receipt.json")

    venv = project.repo / ".venv"
    env = EnvironmentBootstrapper(project.repo)._isolated_env(venv)
    assert env["VIRTUAL_ENV"] == str(venv)
    assert env["PATH"].split(os.pathsep)[0] == str(venv / "bin")
    _assert_no_sentinel(env, "the install retry")


# ---------------------------------------------------------------------------
# Test 5: no sentinel reaches a receipt
# ---------------------------------------------------------------------------


def test_no_sentinel_reaches_a_receipt(project: Project) -> None:
    from guardkit.orchestrator.feature_check import run_feature_check_command
    from guardkit.orchestrator.run_evidence import EvidenceRequest

    run = run_feature_check_command(
        "env; exit 3", cwd=project.repo, timeout=60, launch_root=project.repo,
        evidence=EvidenceRequest(kind="whole-feature check", environment_inventory="env"),
    )
    assert run["exit_code"] == 3
    assert run["run_evidence"]["environment_inventory"]["status"] == "recorded"
    validator = _validator(project, test_command="env; exit 4")
    result = validator.run_independent_tests()
    for blob in (json.dumps(run, default=str), json.dumps(vars(result), default=str)):
        assert MARK not in blob


# ---------------------------------------------------------------------------
# Tests 6 and 10: a proxy that carries credentials is refused by name
# ---------------------------------------------------------------------------


def test_a_proxy_with_credentials_is_refused_by_name(
    project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    from guardkit.orchestrator.feature_check import run_feature_check_command

    monkeypatch.setenv("HTTPS_PROXY", f"http://u:{MARK}@p:3128")
    run = run_feature_check_command(
        project.sh("proxy"), cwd=project.repo, timeout=60, launch_root=project.repo
    )
    assert run["exit_code"] is None
    assert "could not run" in run["stderr"] and "HTTPS_PROXY" in run["stderr"]
    assert not (project.out / "proxy.env").exists()
    assert MARK not in json.dumps(run, default=str)


@pytest.mark.parametrize("name", ["HTTPS_PROXY", "https_proxy"])
def test_a_declared_proxy_with_credentials_is_refused(
    project: Project, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    from guardkit.orchestrator.smoke_gates import run_smoke_gate
    from guardkit.orchestrator.feature_loader import SmokeGates

    for other in _PROXIES:
        monkeypatch.delenv(other, raising=False)
    (project.repo / ".guardkit" / "config.yaml").write_text(
        f"launch:\n  settings: [STANDIN_SETTING, {name}]\n  scratch: [STANDIN_CACHE]\n",
        encoding="utf-8",
    )
    declaration = LaunchDeclaration(settings=(name,))
    monkeypatch.setenv(name, f"http://u:{MARK}@p:3128")
    with pytest.raises(LaunchEnvironmentError) as caught:
        pce.project_command_environment(project.repo, declaration)
    assert name in str(caught.value) and MARK not in str(caught.value)

    result = run_smoke_gate(SmokeGates(after_wave="all", command=project.sh("dp")), project.repo, 1)
    assert result.could_not_start and name in result.stderr and MARK not in result.stderr
    assert not (project.out / "dp.env").exists()

    # A declared proxy without credentials still arrives.
    monkeypatch.setenv(name, "http://p:3128")
    env = pce.project_command_environment(project.repo, declaration)
    assert env[name] == "http://p:3128"


# ---------------------------------------------------------------------------
# Tests 7 and 8: what the project is told — names, never values
# ---------------------------------------------------------------------------


def test_a_failed_command_names_withheld_settings_never_values(
    project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    from guardkit.orchestrator.completion_verification import run_completion_verification

    monkeypatch.setenv("DOCKER_HOST", f"{MARK}-docker")
    result = run_completion_verification(project.repo, "exit 1", "declared")
    assert result.status == "failed"
    assert "DOCKER_HOST" in result.detail
    assert "launch.settings" in result.detail
    assert MARK not in result.detail
    # The factory's own names are counted, never offered.
    assert "OPENAI_API_KEY" not in result.detail

    validator = _validator(project, test_command="exit 1")
    summary = validator.run_independent_tests().test_output_summary
    assert "DOCKER_HOST" in summary and MARK not in summary


def test_a_declared_setting_that_is_not_set_is_said_plainly(
    project: Project, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from guardkit.orchestrator.feature_check import run_feature_check_command
    from guardkit.orchestrator.run_evidence import EvidenceRequest

    monkeypatch.delenv("STANDIN_SETTING")
    pce._ALREADY_SAID.discard("STANDIN_SETTING")
    with caplog.at_level("WARNING"):
        run = run_feature_check_command(
            "true", cwd=project.repo, timeout=60, launch_root=project.repo,
            evidence=EvidenceRequest(kind="whole-feature check"),
        )
    sentence = (
        "the project declares `STANDIN_SETTING` in `launch.settings`, but it is "
        "not set where the factory runs, so the command ran without it"
    )
    assert sentence in caplog.text
    assert run["run_evidence"]["environment"]["declared_but_not_set"] == ["STANDIN_SETTING"]
    assert sentence in run["run_evidence"]["environment"]["sentences"]


# ---------------------------------------------------------------------------
# Test 11: the run-owner marker
# ---------------------------------------------------------------------------


def _serve_module(p: Project) -> None:
    (p.repo / "standin_owner.py").write_text(
        textwrap.dedent(
            f"""\
            import os, socket, time
            with open("/proc/self/environ", "rb") as fh:
                raw = fh.read()
            with open(os.path.join({str(p.out)!r}, "serve-proc.env"), "w") as out:
                out.write("\\n".join(x.decode() for x in raw.split(b"\\0") if x))
            s = socket.socket()
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", int(os.environ["PORT"])))
            s.listen(5)
            time.sleep(30)
            """
        ),
        encoding="utf-8",
    )


@pytest.mark.skipif(not Path("/proc/self/environ").exists(), reason="needs /proc")
def test_boot_smoke_keeps_the_owner_marker(project: Project) -> None:
    from guardkit.orchestrator.boot_smoke import run_boot_smoke

    _serve_module(project)
    result = run_boot_smoke(
        _boot_config([{"id": "s", "kind": "serve", "target": "standin_owner",
                       "readiness": {"kind": "port", "timeout_s": 20},
                       "worktree_env": {"FOO": "1"}}]),
        project.repo,
    )
    assert result.entries[0].verdict == "pass", result.entries[0].detail
    seen = project.read("serve-proc")
    assert seen.get("GUARDKIT_RUN_OWNER") == "build-x"
    assert seen.get("FOO") == "1"
    _assert_no_sentinel(seen, "the serve probe")


def test_boot_smoke_refuses_an_overlay_owner_marker(project: Project) -> None:
    from guardkit.orchestrator.boot_smoke import run_boot_smoke

    _plant_module(project, "standin_conflict", "conflict")
    result = run_boot_smoke(
        _boot_config([{"id": "s", "kind": "serve", "target": "standin_conflict",
                       "readiness": {"kind": "exit_zero"},
                       "worktree_env": {"GUARDKIT_RUN_OWNER": "other"}}]),
        project.repo,
    )
    entry = result.entries[0]
    assert "could not run" in entry.detail and "GUARDKIT_RUN_OWNER" in entry.detail
    assert not (project.out / "conflict.env").exists()
    with pytest.raises(LaunchEnvironmentError):
        pce.finish_project_environment({}, overlay={"GUARDKIT_RUN_OWNER": "other"})


def test_boot_smoke_with_no_parent_marker_has_none(
    project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    from guardkit.orchestrator.boot_smoke import run_boot_smoke

    monkeypatch.delenv("GUARDKIT_RUN_OWNER")
    _plant_module(project, "standin_nomark", "no-marker")
    run_boot_smoke(
        _boot_config([{"id": "s", "kind": "serve", "target": "standin_nomark",
                       "readiness": {"kind": "exit_zero"}, "worktree_env": {"FOO": "1"}}]),
        project.repo,
    )
    seen = project.read("no-marker")
    assert "GUARDKIT_RUN_OWNER" not in seen
    assert seen.get("FOO") == "1"


def test_an_addition_cannot_set_the_owner_marker(project: Project) -> None:
    with pytest.raises(ValueError):
        pce.project_command_environment(
            project.repo, None, additions={"GUARDKIT_RUN_OWNER": "x"}
        )


# ---------------------------------------------------------------------------
# Test 12: the hosted SDK harness is refused on a factory launch
# ---------------------------------------------------------------------------


def test_the_sdk_harness_is_refused_on_a_factory_launch(monkeypatch: pytest.MonkeyPatch) -> None:
    from guardkit.orchestrator.exceptions import AgentInvocationError
    from guardkit.orchestrator.harness import selector

    monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")
    monkeypatch.setenv("GUARDKIT_FACTORY_LAUNCH", "1")
    monkeypatch.setattr(selector, "enforce_effective_seat", lambda *a, **k: None)
    with pytest.raises(AgentInvocationError) as caught:
        selector.select_harness(model="local-model")
    assert "passes the factory's whole environment to its shell" in str(caught.value)


# ---------------------------------------------------------------------------
# Coach review fixes (13 October 2026)
# ---------------------------------------------------------------------------


def test_a_credentialed_proxy_in_guardkits_own_environment_does_not_break_imports(
    project: Project,
) -> None:
    """GuardKit (and guardkitfactory, which registers its BDD plugins at
    import) still imports when its own HTTPS_PROXY carries a login, and a
    real project command is still refused by name."""
    script = textwrap.dedent(
        f"""\
        import guardkit.orchestrator.quality_gates.coach_validator
        import guardkit.orchestrator.feature_orchestrator
        from guardkit.orchestrator.completion_verification import run_completion_verification
        result = run_completion_verification(__import__("pathlib").Path({str(project.repo)!r}), "true", "declared")
        print(result.status, "|", result.detail)
        """
    )
    env = dict(os.environ)
    env["HTTPS_PROXY"] = f"http://user:{MARK}@proxy:3128"
    env["PYTHONPATH"] = os.pathsep.join(p for p in sys.path if p)
    run = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, env=env, timeout=300
    )
    assert run.returncode == 0, run.stderr[-3000:]
    assert run.stdout.startswith("unverified |"), run.stdout
    assert "HTTPS_PROXY" in run.stdout
    assert MARK not in run.stdout + run.stderr


def test_a_reachability_probe_that_cannot_be_given_its_environment_could_not_run(
    project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    from guardkit.orchestrator.boot_smoke import run_boot_smoke

    monkeypatch.setenv("HTTPS_PROXY", f"http://user:{MARK}@proxy:3128")
    result = run_boot_smoke(
        _boot_config([{"id": "r", "kind": "command", "target": "true",
                       "env_required": [{"reachable": project.sh("never")}]}]),
        project.repo,
    )
    entry = result.entries[0]
    assert entry.finding_kind == "BOOT_SMOKE_COULD_NOT_RUN", entry
    assert "could not run" in entry.detail and "HTTPS_PROXY" in entry.detail
    assert MARK not in entry.detail
    assert not (project.out / "never.env").exists()


def test_a_gate_address_with_a_login_is_refused_by_name(project: Project) -> None:
    from guardkit.orchestrator.live_gate.errors import LiveGateError
    from guardkit.orchestrator.live_gate.runner import LiveGateRunner
    from guardkit.qa.formats.gate_registry import GateEntry, GateTarget

    gate = GateEntry(
        id="g1", path="qa/gates/g1.py",
        target=GateTarget(base_url_env="STANDIN_BASE_URL", environment_id="local"),
        pass_bar_ref="qa/pass-bar-T-1.yaml",
        evidence_dir_pattern="qa/gates/evidence-{date}/shots",
    )
    runner = LiveGateRunner(
        project.repo, gate_env={"STANDIN_BASE_URL": f"http://user:{MARK}@app:8080"}
    )
    with pytest.raises(LiveGateError) as caught:
        runner._gate_script_env([gate])
    assert "STANDIN_BASE_URL" in str(caught.value)
    assert MARK not in str(caught.value)
    plain = LiveGateRunner(project.repo, gate_env={"STANDIN_BASE_URL": "http://app:8080"})
    assert plain._gate_script_env([gate])["STANDIN_BASE_URL"] == "http://app:8080"


# ---------------------------------------------------------------------------
# A timeout ends everything the command started (the merge build's
# process_group runner, used by the whole-feature check and the oracle's
# worktree commands)
# ---------------------------------------------------------------------------


def _still_running(pid: int) -> bool:
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as fh:
            state = fh.read().rsplit(")", 1)[1].split()[0]
    except OSError:
        return False
    return state != "Z"


def _nothing_left(pid_file: Path) -> None:
    import time as _time

    assert pid_file.exists(), "the command never started its child"
    pid = int(pid_file.read_text().strip())
    deadline = _time.monotonic() + 5
    while _time.monotonic() < deadline and _still_running(pid):
        _time.sleep(0.1)
    assert not _still_running(pid), f"the command's child {pid} is still running"


_BACKGROUND = 'sleep 300 & echo $! > "{pid}"; wait'


@pytest.mark.skipif(not Path("/proc/self/stat").exists(), reason="needs /proc")
def test_a_timed_out_feature_check_leaves_nothing_running(project: Project) -> None:
    from guardkit.orchestrator.feature_check import run_feature_check_command

    pid = project.out / "feature-check.pid"
    run = run_feature_check_command(
        _BACKGROUND.format(pid=pid), cwd=project.repo, timeout=1, launch_root=project.repo
    )
    assert run["timed_out"] is True and run["exit_code"] is None
    _nothing_left(pid)


@pytest.mark.skipif(not Path("/proc/self/stat").exists(), reason="needs /proc")
def test_a_timed_out_worktree_oracle_command_leaves_nothing_running(
    project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = project.out / "oracle.pid"
    monkeypatch.setenv("GUARDKIT_ORACLE_TIMEOUT", "1")
    result = _validator(project)._run_shell_command(_BACKGROUND.format(pid=pid), None)
    assert result is not None and result["timed_out"] is True
    _nothing_left(pid)


# ---------------------------------------------------------------------------
# Section 5: every process launch in the package is accounted for
# ---------------------------------------------------------------------------

PACKAGE = Path(__file__).resolve().parents[2] / "guardkit"

#: Launches that are allowed as they are, keyed by (file, function), each with
#: its one-line reason. A reviewer sees every line added here.
ALLOWED: Dict[Tuple[str, str], str] = {
    ("cli/doctor.py", "run"): "guardkit doctor's version checks of the factory's own tools",
    ("orchestrator/browser_verifier.py", "_verify_installation"): "agent-browser, the factory's own program",
    ("orchestrator/browser_verifier.py", "open"): "agent-browser, the factory's own program",
    ("orchestrator/browser_verifier.py", "screenshot"): "agent-browser, the factory's own program",
    ("orchestrator/browser_verifier.py", "get_accessibility_tree"): "agent-browser, the factory's own program",
    ("orchestrator/browser_verifier.py", "close"): "agent-browser, the factory's own program",
    ("orchestrator/review_runner.py", "attempt_fleet_memory_cli"): "guardkit memory search, the factory's own program",
    ("orchestrator/quality_gates/task_work_interface.py", "_execute_via_subprocess"): "guardkit task-work, the factory's own program",
    ("orchestrator/merge_executor.py", "run_feature_validate"): "guardkit feature validate, the factory's own program",
    ("orchestrator/feature_complete.py", "_candidate_sha"): "git through a variable (a list of git rev-parse argv lists)",
    ("orchestrator/quality_gates/coach_validator.py", "_start_infrastructure_containers"): "the container engine through a variable (the fixture recipes)",
    ("orchestrator/run_evidence.py", "docker_events_between"): "the container engine through a variable (docker events)",
    # Generic runners: each call to them is checked below.
    ("orchestrator/run_evidence.py", "_default_runner"): "generic runner; every call is checked",
    ("orchestrator/quality_gates/coach_validator.py", "_run_recorded"): "generic runner; every call is checked",
    ("orchestrator/worktree_checkpoints.py", "execute"): "worktree executor (git); every call is checked",
    ("worktrees/manager.py", "run"): "worktree executor (git); every call is checked",
    ("orchestrator/completion_verification.py", "run_completion_verification"): (
        "builds its environment with the helper unless the merge hands in the one "
        "it built with the same helper; every call is checked"
    ),
    ("orchestrator/process_group.py", "run_in_own_group"): (
        "generic runner (a process group of its own); every call is checked"
    ),
    ("orchestrator/live_gate/executor.py", "run"): (
        "runs a gate script with the caller's environment; the one production "
        "caller, LiveGateRunner, builds it with the helper"
    ),
    # Callers of generic runners that pass a value on.
    ("orchestrator/run_evidence.py", "run_environment_inventory"): (
        "the inventory runs with the environment of the command it records "
        "(always the helper's) and refuses to run with None"
    ),
    ("orchestrator/quality_gates/coach_validator.py", "_begin_run_evidence"): (
        "passes on the env of a _run_recorded call, each of which is checked"
    ),
    ("orchestrator/merge_executor.py", "measure_pre_merge_baseline"): (
        "the merge's environment from prepare_tree (project_command_environment), merge design item 2a"
    ),
    ("orchestrator/merge_executor.py", "verify_merged"): (
        "the merge's environment from prepare_tree (project_command_environment), merge design item 2a"
    ),
    ("orchestrator/work_runner.py", "_run"): "git through a local wrapper; its callers pass git argv lists",
    ("orchestrator/live_gate/executor.py", "execute_gate"): (
        "passes on its caller's environment, or an empty one; every call is checked"
    ),
    ("orchestrator/live_gate/executor.py", "execute_gates"): (
        "passes on its caller's environment, or an empty one; every call is checked"
    ),
    ("orchestrator/run_evidence.py", "_work"): (
        "the record's begin phase runs the inventory with the record's own env, "
        "which every start_command_evidence / CommandEvidence call is checked for"
    ),
    ("orchestrator/merge_executor.py", "execute_merge"): (
        "the merge's environment from prepare_tree (project_command_environment), merge design item 2a"
    ),
}

#: Generic runners: (file, function) -> how calls to it are found.
#: ``names`` match a call by its last name, however it is spelled (a module,
#: an object, a plain name); ``suffixes`` match a dotted callee for the
#: generic method names; ``scope`` limits the files searched;
#: ``default_is_safe`` says a call with no ``env=`` gets the helper's
#: environment (or an empty one); ``none_is_safe`` says ``env=None`` runs
#: nothing that inherits.
GENERIC_RUNNERS: Dict[Tuple[str, str], Dict[str, Any]] = {
    ("orchestrator/run_evidence.py", "_default_runner"): {
        "names": {"_default_runner", "runner"},
        "scope": {"orchestrator/run_evidence.py"},
    },
    ("orchestrator/run_evidence.py", "run_environment_inventory"): {
        "names": {"run_environment_inventory"},
        "none_is_safe": True,
    },
    ("orchestrator/quality_gates/coach_validator.py", "_run_recorded"): {
        "names": {"_run_recorded"},
    },
    ("orchestrator/quality_gates/coach_validator.py", "_begin_run_evidence"): {
        "names": {"_begin_run_evidence"},
        "env_position": 5,
        "none_is_safe": True,
    },
    ("orchestrator/run_evidence.py", "start_command_evidence"): {
        "names": {"start_command_evidence", "CommandEvidence"},
        "none_is_safe": True,
    },
    ("orchestrator/worktree_checkpoints.py", "execute"): {
        "suffixes": {"executor.execute"},
    },
    ("worktrees/manager.py", "run"): {
        "suffixes": {"executor.run"},
    },
    ("orchestrator/work_runner.py", "_run"): {
        "names": {"_run"},
        "scope": {"orchestrator/work_runner.py"},
    },
    ("orchestrator/completion_verification.py", "run_completion_verification"): {
        "names": {"run_completion_verification"},
        "default_is_safe": True,
    },
    ("orchestrator/process_group.py", "run_in_own_group"): {
        "names": {"run_in_own_group"},
    },
    ("orchestrator/merge_executor.py", "measure_pre_merge_baseline"): {
        "names": {"measure_pre_merge_baseline"},
        "default_is_safe": True,
    },
    ("orchestrator/merge_executor.py", "verify_merged"): {
        "names": {"verify_merged"},
        "default_is_safe": True,
    },
    ("orchestrator/live_gate/executor.py", "run"): {
        "suffixes": {"runner.run"},
        "scope": {"orchestrator/live_gate/executor.py"},
    },
    ("orchestrator/live_gate/executor.py", "execute_gate"): {
        "names": {"execute_gate"},
        "default_is_safe": True,
    },
    ("orchestrator/live_gate/executor.py", "execute_gates"): {
        "names": {"execute_gates"},
        "default_is_safe": True,
    },
}


#: The repository's helper, by the dotted name it is imported from. A
#: launch whose ``env=`` is a call to it (or to a function that only ever
#: returns its result, found by module and function, never by bare name) is
#: a project command done right.
HELPERS = {
    "guardkit.orchestrator.project_command_env.project_command_environment",
    "guardkit.orchestrator.project_command_env.finish_project_environment",
}

#: The factory's own programs, recognised from a literal first argument.
FACTORY_PROGRAMS = {"git", "docker", "pgrep", "ps"}

_LAUNCHES = {
    "subprocess": {"run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput"},
    "asyncio": {"create_subprocess_exec", "create_subprocess_shell"},
    "os": {
        "system", "popen", "execl", "execle", "execlp", "execlpe", "execv", "execve",
        "execvp", "execvpe", "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv",
        "spawnve", "spawnvp", "spawnvpe", "posix_spawn", "posix_spawnp", "fork", "forkpty",
    },
    "pty": {"spawn", "fork"},
}
#: Launch methods recognised on any object: ``asyncio.subprocess.create_*``
#: and an event loop's ``subprocess_exec`` / ``subprocess_shell``.
_ANY_RECEIVER_LAUNCHES = {
    "create_subprocess_exec", "create_subprocess_shell", "subprocess_exec", "subprocess_shell",
}
#: Methods that change a dictionary in place.
_MUTATORS = {"update", "setdefault", "__setitem__", "__ior__"}


class _Module(SimpleNamespace):
    rel: str
    dotted: str
    tree: ast.Module
    parents: Dict[int, ast.AST]
    imports: Dict[str, str]


def _load_modules(package: Path) -> List[_Module]:
    modules = []
    for path in sorted(package.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        parents: Dict[int, ast.AST] = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parents[id(child)] = node
        rel = str(path.relative_to(package))
        parts = [package.name, *Path(rel).with_suffix("").parts]
        is_package = parts[-1] == "__init__"
        if is_package:
            parts = parts[:-1]
        dotted = ".".join(parts)
        modules.append(
            _Module(
                rel=rel, dotted=dotted, tree=tree, parents=parents,
                imports=_imports(tree, dotted, is_package),
            )
        )
    return modules


def _imports(tree: ast.Module, dotted: str, is_package: bool) -> Dict[str, str]:
    """Every name an import binds anywhere in the module -> what it names."""
    out: Dict[str, str] = {}
    package = dotted if is_package else dotted.rsplit(".", 1)[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    out[alias.asname] = alias.name
                else:
                    out[alias.name.split(".")[0]] = alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                anchor = package.split(".")
                anchor = anchor[: len(anchor) - (node.level - 1)]
                base = ".".join([*anchor, base] if base else anchor)
            for alias in node.names:
                out[alias.asname or alias.name] = f"{base}.{alias.name}"
    return out


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_dotted(node.value)}.{node.attr}"
    return "?"


def _last_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _enclosing(mod: _Module, node: ast.AST, kinds) -> Optional[ast.AST]:
    current = mod.parents.get(id(node))
    while current is not None and not isinstance(current, kinds):
        current = mod.parents.get(id(current))
    return current


def _enclosing_function(mod: _Module, node: ast.AST) -> Optional[ast.AST]:
    return _enclosing(mod, node, (ast.FunctionDef, ast.AsyncFunctionDef))


def _qualname(mod: _Module, func: ast.AST) -> str:
    names = [func.name]
    current = mod.parents.get(id(func))
    while current is not None:
        if isinstance(current, ast.ClassDef):
            names.append(current.name)
        elif isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.append(f"{current.name}.<locals>")
        current = mod.parents.get(id(current))
    return ".".join(reversed(names))


def _resolve(mod: _Module, func_node: ast.AST, at: ast.AST) -> Optional[str]:
    """The dotted name a call target refers to, or ``None`` when unknown."""
    if isinstance(func_node, ast.Name):
        name = func_node.id
        scope = _enclosing_function(mod, at)
        while scope is not None:  # a function defined in an enclosing function
            for child in ast.iter_child_nodes(scope):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    return f"{mod.dotted}.{_qualname(mod, child)}"
            scope = _enclosing_function(mod, scope)
        for child in mod.tree.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and child.name == name:
                return f"{mod.dotted}.{name}"
        return mod.imports.get(name)
    if isinstance(func_node, ast.Attribute):
        value = func_node.value
        if isinstance(value, ast.Name) and value.id in ("self", "cls"):
            klass = _enclosing(mod, at, ast.ClassDef)
            if klass is not None:
                return f"{mod.dotted}.{klass.name}.{func_node.attr}"
            return None
        base = _resolve(mod, value, at)
        return f"{base}.{func_node.attr}" if base else None
    return None


def _module_constants(modules: Iterable[_Module]) -> Dict[str, ast.AST]:
    out: Dict[str, ast.AST] = {}
    for mod in modules:
        for node in mod.tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        out[target.id] = node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value:
                out[node.target.id] = node.value
    return out


def _assignments(func: ast.AST, name: str) -> List[ast.AST]:
    values: List[ast.AST] = []
    for node in ast.walk(func):
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
                values.append(node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            if node.value is not None:
                values.append(node.value)
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.With, ast.AsyncWith, ast.NamedExpr)):
            targets = (
                [node.target] if isinstance(node, (ast.For, ast.AsyncFor, ast.NamedExpr))
                else [i.optional_vars for i in node.items if i.optional_vars is not None]
            )
            for target in targets:
                if any(isinstance(n, ast.Name) and n.id == name for n in ast.walk(target)):
                    values.append(ast.Constant(value="<bound by a loop or with>"))
    return values


def _is_parameter(func: ast.AST, name: str) -> bool:
    args = func.args
    every = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    every += [a for a in (args.vararg, args.kwarg) if a is not None]
    return any(a.arg == name for a in every)


def _mutated(func: ast.AST, name: str) -> bool:
    """True when the dictionary ``name`` is changed in place in ``func``."""
    for node in ast.walk(func):
        targets: List[ast.AST] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            targets = [node.target]
            if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
                return True
        for target in targets:
            for sub in ast.walk(target):
                if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name) and sub.value.id == name:
                    return True
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _MUTATORS
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == name
        ):
            return True
    return False


def _helper_shaped(
    node: Optional[ast.AST], mod: _Module, func: Optional[ast.AST], wrappers: set,
    none_is_safe: bool = False,
) -> bool:
    """True when ``node`` (an ``env=`` value) can only be the helper's result."""
    if node is None:
        return False
    if isinstance(node, ast.Call):
        target = _resolve(mod, node.func, node)
        return target in HELPERS or target in wrappers
    if isinstance(node, ast.IfExp):
        return _helper_shaped(node.body, mod, func, wrappers, none_is_safe) and _helper_shaped(
            node.orelse, mod, func, wrappers, none_is_safe
        )
    if isinstance(node, ast.Constant) and node.value is None:
        return none_is_safe
    if isinstance(node, ast.Dict) and not node.keys:
        return True  # an empty environment holds nothing, unless it is filled later
    if isinstance(node, ast.Name) and func is not None:
        if _is_parameter(func, node.id) or _mutated(func, node.id):
            return False
        values = _assignments(func, node.id)
        return bool(values) and all(
            _helper_shaped(v, mod, func, wrappers, none_is_safe) for v in values
        )
    return False


def _wrappers(modules: List[_Module]) -> set:
    """Functions whose every return is the helper's result, by dotted name."""
    found: set = set()
    changed = True
    while changed:
        changed = False
        for mod in modules:
            for node in ast.walk(mod.tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                full = f"{mod.dotted}.{_qualname(mod, node)}"
                if full in found:
                    continue
                returns = [
                    r for r in ast.walk(node)
                    if isinstance(r, ast.Return) and _enclosing_function(mod, r) is node
                ]
                if returns and all(_helper_shaped(r.value, mod, node, found) for r in returns):
                    found.add(full)
                    changed = True
    return found


def _launch_kind(mod: _Module, node: ast.AST) -> Optional[str]:
    """What launch ``node`` (a call target or a value) names, if any."""
    if isinstance(node, ast.Attribute):
        if node.attr in _ANY_RECEIVER_LAUNCHES:
            return _dotted(node)
        if isinstance(node.value, ast.Name):
            module = mod.imports.get(node.value.id)
            if module in _LAUNCHES and node.attr in _LAUNCHES[module]:
                return f"{module}.{node.attr}"
    if isinstance(node, ast.Name):
        target = mod.imports.get(node.id, "")
        module, _, name = target.rpartition(".")
        if module in _LAUNCHES and name in _LAUNCHES[module]:
            return target
    return None


def _factory_literal(
    node: Optional[ast.AST], constants: Dict[str, ast.AST], func: Optional[ast.AST] = None
) -> bool:
    """A list whose first item is the literal git/docker/pgrep/ps."""
    if node is None:
        return False
    if isinstance(node, ast.Name) and func is not None and not _is_parameter(func, node.id):
        values = _assignments(func, node.id)
        if values and all(_factory_literal(v, constants) for v in values):
            return True
    if isinstance(node, (ast.List, ast.Tuple)):
        return bool(node.elts) and isinstance(node.elts[0], ast.Constant) and node.elts[0].value in FACTORY_PROGRAMS
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _factory_literal(node.left, constants)
    if isinstance(node, ast.Call) and _dotted(node.func) in ("list", "tuple") and node.args:
        return _factory_literal(node.args[0], constants)
    if isinstance(node, ast.Name) and node.id in constants:
        return _factory_literal(constants[node.id], constants)
    return False


def _env_keyword(call: ast.Call, position: Optional[int] = None) -> Optional[ast.AST]:
    for kw in call.keywords:
        if kw.arg == "env":
            return kw.value
    if position is not None and len(call.args) > position:
        return call.args[position]
    return None


def _annotation_nodes(tree: ast.AST) -> set:
    """Nodes inside type annotations: naming ``subprocess.Popen`` as a type
    launches nothing."""
    found: set = set()
    roots: List[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.arg) and node.annotation is not None:
            roots.append(node.annotation)
        elif isinstance(node, ast.AnnAssign):
            roots.append(node.annotation)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.returns is not None:
            roots.append(node.returns)
    for root in roots:
        found.update(id(n) for n in ast.walk(root))
    return found


def _first_argument(call: ast.Call) -> Optional[ast.AST]:
    if call.args:
        return call.args[0]
    for kw in call.keywords:
        if kw.arg in ("args", "argv", "command", "cmd"):
            return kw.value
    return None


def _runner_call_matches(call: ast.Call, spec: Dict[str, Any]) -> bool:
    """A call to a generic runner: by its last name (any object or module
    spelling), or by a dotted suffix for the generic method names."""
    if _last_name(call.func) in spec.get("names", ()):
        return True
    dotted = _callee_name(call)
    return any(dotted.endswith(suffix) for suffix in spec.get("suffixes", ()))


def _callee_name(call: ast.Call) -> str:
    return _dotted(call.func)


def unaccounted_launches(package: Path) -> List[str]:
    modules = _load_modules(package)
    constants = _module_constants(modules)
    wrappers = _wrappers(modules)
    problems: List[str] = []

    def place(mod: _Module, node: ast.AST) -> Tuple[Optional[ast.AST], str]:
        func = _enclosing_function(mod, node)
        return func, getattr(func, "name", "<module>")

    def judge(
        mod: _Module, call: ast.Call, what: str, *, default_is_safe=False,
        none_is_safe=False, env_position: Optional[int] = None,
    ) -> None:
        func, fname = place(mod, call)
        if (mod.rel, fname) in ALLOWED:
            return
        if _factory_literal(_first_argument(call), constants, func):
            return
        env = _env_keyword(call, env_position)
        if env is None and default_is_safe:
            return
        if _helper_shaped(env, mod, func, wrappers, none_is_safe):
            return
        reason = "no env= (it inherits everything)" if env is None else "env= is not the helper's"
        problems.append(f"{mod.rel}:{call.lineno} in {fname}: {what}: {reason}")

    for mod in modules:
        called = {id(n.func) for n in ast.walk(mod.tree) if isinstance(n, ast.Call)}
        called |= _annotation_nodes(mod.tree)
        for node in ast.walk(mod.tree):
            if isinstance(node, ast.Call):
                kind = _launch_kind(mod, node.func)
                if kind:
                    judge(mod, node, f"process launch {kind}")
                elif (
                    _dotted(node.func) == "getattr"
                    and len(node.args) >= 2
                    and _launch_kind(
                        mod,
                        ast.Attribute(value=node.args[0], attr=node.args[1].value, ctx=ast.Load())
                        if isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str)
                        else ast.Constant(value=None),
                    )
                ):
                    _, fname = place(mod, node)
                    if (mod.rel, fname) not in ALLOWED:
                        problems.append(
                            f"{mod.rel}:{node.lineno} in {fname}: a launch function "
                            f"looked up with getattr, so its env= cannot be checked"
                        )
            elif isinstance(node, (ast.Attribute, ast.Name)) and id(node) not in called:
                kind = _launch_kind(mod, node)
                if kind and isinstance(getattr(node, "ctx", None), ast.Load):
                    parent = mod.parents.get(id(node))
                    if isinstance(parent, (ast.Attribute,)):
                        continue  # part of a longer dotted name, judged there
                    _, fname = place(mod, node)
                    if (mod.rel, fname) not in ALLOWED:
                        problems.append(
                            f"{mod.rel}:{node.lineno} in {fname}: the launch function "
                            f"{kind} is used as a value (held in a variable, passed "
                            f"on or wrapped), so its env= cannot be checked"
                        )
    for (rel, fname), spec in GENERIC_RUNNERS.items():
        for mod in modules:
            if spec.get("scope") and mod.rel not in spec["scope"]:
                continue
            for node in ast.walk(mod.tree):
                if not isinstance(node, ast.Call) or not _runner_call_matches(node, spec):
                    continue
                func = _enclosing_function(mod, node)
                if mod.rel == rel and getattr(func, "name", None) == fname:
                    continue  # the runner's own body
                judge(
                    mod, node, f"call to the generic runner {fname}",
                    default_is_safe=spec.get("default_is_safe", False),
                    none_is_safe=spec.get("none_is_safe", False),
                    env_position=spec.get("env_position"),
                )
    return sorted(set(problems))


#: The coach's probes (13 October 2026): each ``vNN`` function must be named.
GUARD_PROBES = textwrap.dedent(
    '''\
    import asyncio
    import functools
    import os
    import subprocess
    from guardkit.orchestrator import process_group
    from guardkit.orchestrator.process_group import run_in_own_group
    from guardkit.orchestrator.project_command_env import project_command_environment


    def _project_env():  # the same name as a real wrapper elsewhere
        return dict(os.environ)


    def v01_name_collision(cmd):
        subprocess.run(cmd, shell=True, env=_project_env())


    def v02_mutated_after_helper(cmd, wf):
        env = project_command_environment(wf, None)
        env.update(os.environ)
        subprocess.run(cmd, shell=True, env=env)


    def v03_runner_by_reference(cmd):
        runner = subprocess.run
        runner(cmd, shell=True)


    def v04_partial(cmd):
        functools.partial(subprocess.run, shell=True)(cmd)


    async def v05_loop_method(cmd):
        loop = asyncio.get_running_loop()
        await loop.subprocess_shell(asyncio.SubprocessProtocol, cmd)


    async def v06_nested_attribute(cmd):
        await asyncio.subprocess.create_subprocess_shell(cmd)


    def v07_qualified_generic_runner(cmd):
        process_group.run_in_own_group(cmd, shell=True, cwd=".", env=dict(os.environ), timeout=5)


    def v08_plain_generic_runner(cmd):
        run_in_own_group(cmd, shell=True, cwd=".", env=dict(os.environ), timeout=5)


    def v09_other_object_run_recorded(validator, cmd):
        validator._run_recorded(cmd, evidence=("x", ".", None), shell=True, env=os.environ.copy())


    def v10_getattr(cmd):
        getattr(subprocess, "run")(cmd, shell=True)


    def v11_env_item_injected(cmd, wf):
        env = project_command_environment(wf, None)
        env["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]
        subprocess.run(cmd, shell=True, env=env)


    def v12_empty_dict_then_filled(cmd):
        env = {}
        env.update(os.environ)
        subprocess.run(cmd, shell=True, env=env)


    def _copy_everything():
        out = {}
        for k, v in os.environ.items():
            out[k] = v
        return out


    def v13_wrapper_built_from_empty(cmd):
        subprocess.run(cmd, shell=True, env=_copy_everything())


    def v14_existing_unrelated_wrapper_name(cmd, answer):
        subprocess.run(cmd, shell=True, env=parse_answer(answer))


    def v15_plain(cmd):
        subprocess.run(cmd, shell=True)


    def v16_empty_dict_item_filled(cmd):
        env = {}
        env["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]
        subprocess.run(cmd, shell=True, env=env)


    def v17_or_assigned(cmd, wf):
        env = project_command_environment(wf, None)
        env |= dict(os.environ)
        subprocess.run(cmd, shell=True, env=env)


    def ok_helper(cmd, wf):
        env = project_command_environment(wf, None)
        subprocess.run(cmd, shell=True, env=env)


    def ok_git(cmd):
        subprocess.run(["git", "status"])


    def ok_wrapper(cmd, wf):
        subprocess.run(cmd, shell=True, env=_real_wrapper(wf))


    def _real_wrapper(wf):
        return project_command_environment(wf, None, additions={"X": "1"})
    '''
)


def _probe_package(tmp_path: Path, name: str) -> Path:
    pkg = tmp_path / name
    (pkg / "orchestrator").mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "orchestrator" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "orchestrator" / "zz_probe.py").write_text(GUARD_PROBES, encoding="utf-8")
    return pkg


def test_the_guard_catches_every_probe(tmp_path: Path) -> None:
    """Synthetic source fed to the guard (never added to the package)."""
    problems = unaccounted_launches(_probe_package(tmp_path, PACKAGE.name))
    named = {p.split(" in ", 1)[1].split(":", 1)[0] for p in problems}
    expected = {
        n.name for n in ast.walk(ast.parse(GUARD_PROBES))
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("v")
    }
    assert expected - named == set(), f"slipped past the guard: {sorted(expected - named)}"
    assert not {"ok_helper", "ok_git", "ok_wrapper"} & named, problems


def test_every_process_launch_is_accounted_for() -> None:
    problems = unaccounted_launches(PACKAGE)
    assert not problems, (
        "These process launches neither build their environment with "
        "project_command_env, nor run the factory's own program by a literal "
        "first argument, nor are on the allowed list with a reason:\n  "
        + "\n  ".join(problems)
    )


def test_the_allowed_list_names_only_real_places() -> None:
    modules = {m.rel: m for m in _load_modules(PACKAGE)}
    missing = []
    for rel, fname in list(ALLOWED) + list(GENERIC_RUNNERS):
        mod = modules.get(rel)
        names = {
            n.name for n in ast.walk(mod.tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        } if mod else set()
        if fname not in names:
            missing.append(f"{rel}:{fname}")
    assert not missing, f"allowed-list entries that name nothing: {missing}"


def test_the_guard_catches_a_new_launch(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "new.py").write_text(
        textwrap.dedent(
            """\
            import os, subprocess
            from subprocess import Popen as P
            from guardkit.orchestrator.project_command_env import project_command_environment
            def a(cmd):
                subprocess.run(cmd, shell=True)
            def b(cmd):
                P(cmd, env=os.environ.copy())
            def c(cmd):
                subprocess.run(["git", "status"])
            def d(cmd, wf):
                env = project_command_environment(wf, None)
                subprocess.run(cmd, env=env)
            """
        ),
        encoding="utf-8",
    )
    problems = unaccounted_launches(pkg)
    assert any("new.py:5 in a" in p for p in problems)
    assert any("new.py:7 in b" in p for p in problems)
    assert not any(" in c:" in p or " in d:" in p for p in problems)
