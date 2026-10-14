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
    """Record every project command, whether it is started with
    ``subprocess.run`` or with ``process_group.run_project_command``."""
    from guardkit.orchestrator import process_group

    recorder = Recorder(getattr(process_group, "run_project_command", subprocess.run), run_real)
    monkeypatch.setattr(subprocess, "run", recorder)
    monkeypatch.setattr(process_group, "run_project_command", recorder, raising=False)
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


def _live_gate_repo(p: Project, base_url_env: str = "STANDIN_BASE_URL") -> None:
    """A stand-in repository with one live gate that writes its environment."""
    import yaml

    (p.repo / "qa" / "gates").mkdir(parents=True, exist_ok=True)
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
                        "target": {"base_url_env": base_url_env, "environment_id": "local"},
                        "pass_bar_ref": "qa/pass-bar-T-1.yaml",
                        "evidence_dir_pattern": "qa/gates/evidence-{date}/shots-g1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _run_live_gate(p: Project) -> Dict[str, str]:
    import http.server
    import threading

    from guardkit.orchestrator.live_gate.runner import LiveGateRunner

    _live_gate_repo(p)
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
    assert entry.detail.count("could not run") == 1, entry.detail
    assert MARK not in entry.detail
    assert not (project.out / "never.env").exists()


def _nothing_under_qa_holds(project: Project, mark: str) -> None:
    for path in (project.repo / "qa").rglob("*"):
        if path.is_file():
            assert mark not in path.read_text(encoding="utf-8", errors="replace"), path


_LOGIN_ADDRESSES = {
    "well-formed": f"http://user:{MARK}@127.0.0.1:9/",
    "missing scheme": f"user:{MARK}@127.0.0.1:9/",
    "malformed scheme": f"http:/user:{MARK}@127.0.0.1:9/",
}


@pytest.mark.parametrize("handed_in", [False, True], ids=["inherited", "supplied"])
@pytest.mark.parametrize("form", sorted(_LOGIN_ADDRESSES))
def test_a_gate_address_with_a_login_is_refused_before_preflight(
    project: Project, monkeypatch: pytest.MonkeyPatch, handed_in: bool, form: str
) -> None:
    """The address is unreachable too, so pre-flight would fail and record it;
    the refusal comes first, by name, and nothing is written with the value,
    however the address parses (13 October 2026, review R20)."""
    from guardkit.orchestrator.live_gate.errors import LiveGateError
    from guardkit.orchestrator.live_gate.runner import LiveGateRunner

    _live_gate_repo(project)
    address = _LOGIN_ADDRESSES[form]
    if handed_in:
        runner = LiveGateRunner(project.repo, gate_env={"STANDIN_BASE_URL": address})
    else:
        monkeypatch.setenv("STANDIN_BASE_URL", address)
        runner = LiveGateRunner(project.repo)
    with pytest.raises(LiveGateError) as caught:
        runner.run("PILOT", "local")
    assert "STANDIN_BASE_URL" in str(caught.value)
    assert MARK not in str(caught.value)
    assert not (project.out / "live-gate.env").exists()
    _nothing_under_qa_holds(project, MARK)


@pytest.mark.parametrize("handed_in", [False, True], ids=["inherited", "supplied"])
@pytest.mark.parametrize("address", ["ftp://127.0.0.1:9/", "127.0.0.1:9", "http:///no-host"])
def test_a_gate_address_that_is_not_http_is_refused_by_name(
    project: Project, monkeypatch: pytest.MonkeyPatch, handed_in: bool, address: str
) -> None:
    from guardkit.orchestrator.live_gate.errors import LiveGateError
    from guardkit.orchestrator.live_gate.runner import LiveGateRunner

    _live_gate_repo(project)
    if handed_in:
        runner = LiveGateRunner(project.repo, gate_env={"STANDIN_BASE_URL": address})
    else:
        monkeypatch.setenv("STANDIN_BASE_URL", address)
        runner = LiveGateRunner(project.repo)
    with pytest.raises(LiveGateError) as caught:
        runner.run("PILOT", "local")
    assert "the gate address in STANDIN_BASE_URL is not an http(s) address" in str(caught.value)
    assert address not in str(caught.value)
    assert not (project.out / "live-gate.env").exists()


def test_the_reachability_check_never_echoes_a_refused_address() -> None:
    """The pre-flight provider applies the same rule on its own."""
    from guardkit.orchestrator.live_gate.preflight import DefaultF16ChecklistProvider
    from guardkit.qa.formats.gate_registry import GateEntry, GateTarget

    gate = GateEntry(
        id="g1", path="qa/gates/g1.py",
        target=GateTarget(base_url_env="STANDIN_BASE_URL", environment_id="local"),
        pass_bar_ref="qa/pass-bar-T-1.yaml",
        evidence_dir_pattern="qa/gates/evidence-{date}/shots",
    )
    for address in _LOGIN_ADDRESSES.values():
        result = DefaultF16ChecklistProvider([gate], env={"STANDIN_BASE_URL": address}).checklist()[0]
        assert result.ok is False and "STANDIN_BASE_URL" in result.detail
        assert MARK not in result.detail


def test_the_shadow_probe_note_never_records_a_login() -> None:
    from guardkit.qa.qav_shadow import _probe_unreachable_note

    for url in (f"http://user:{MARK}@probe:9/running", f"user:{MARK}@probe:9"):
        assert MARK not in _probe_unreachable_note(url)
    assert "http://probe:9/running" in _probe_unreachable_note("http://probe:9/running")


def test_a_gate_address_read_from_a_reserved_setting_is_refused_before_preflight(
    project: Project,
) -> None:
    from guardkit.orchestrator.live_gate.errors import LiveGateError
    from guardkit.orchestrator.live_gate.runner import LiveGateRunner

    _live_gate_repo(project, base_url_env="OPENAI_API_KEY")
    with pytest.raises(LiveGateError) as caught:
        LiveGateRunner(project.repo).run("PILOT", "local")
    assert "OPENAI_API_KEY" in str(caught.value)
    assert MARK not in str(caught.value)
    assert not (project.out / "live-gate.env").exists()
    _nothing_under_qa_holds(project, MARK)


def test_a_plain_gate_address_still_reaches_preflight_and_the_gate(project: Project) -> None:
    seen = _run_live_gate(project)
    assert seen["STANDIN_BASE_URL"].startswith("http://127.0.0.1:")


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


def _background_script(project: Project, label: str) -> Tuple[Path, Path]:
    """An executable that starts a long child, writes its pid and waits."""
    pid = project.out / f"{label}.pid"
    script = project.out.parent / "tools" / f"{label}.sh"
    script.write_text(f'#!/bin/sh\nsleep 300 &\necho $! > "{pid}"\nwait\n', encoding="utf-8")
    script.chmod(0o755)
    return script, pid


@pytest.mark.skipif(not Path("/proc/self/stat").exists(), reason="needs /proc")
def test_a_timed_out_install_leaves_nothing_running(project: Project) -> None:
    from guardkit.orchestrator.environment_bootstrap import (
        DetectedManifest,
        EnvironmentBootstrapper,
    )

    script, pid = _background_script(project, "install")
    manifest = DetectedManifest(
        path=project.repo / ".guardkit" / "config.yaml", stack="generic",
        is_lock_file=False, install_command=[str(script)], declared=True,
        install_cwd=project.repo, install_timeout=1,
    )
    assert EnvironmentBootstrapper(project.repo)._run_install(manifest) is False
    _nothing_left(pid)


@pytest.mark.skipif(not Path("/proc/self/stat").exists(), reason="needs /proc")
def test_a_timed_out_smoke_gate_leaves_nothing_running(project: Project) -> None:
    from guardkit.orchestrator.feature_loader import SmokeGates
    from guardkit.orchestrator.smoke_gates import run_smoke_gate

    script, pid = _background_script(project, "smoke")
    result = run_smoke_gate(SmokeGates(after_wave="all", command=str(script), timeout=1), project.repo, 1)
    assert result.timed_out is True
    _nothing_left(pid)


@pytest.mark.skipif(not Path("/proc/self/stat").exists(), reason="needs /proc")
def test_a_timed_out_checker_test_leaves_nothing_running(project: Project) -> None:
    script, pid = _background_script(project, "checker")
    _validator(project, test_command=str(script), test_timeout=1).run_independent_tests()
    _nothing_left(pid)


@pytest.mark.skipif(not Path("/proc/self/stat").exists(), reason="needs /proc")
def test_a_timed_out_bdd_run_leaves_nothing_running(project: Project) -> None:
    from guardkit.orchestrator.quality_gates import bdd_runner

    script, pid = _background_script(project, "bdd")
    bdd_runner._invoke_pytest_bdd(
        [project.repo / "x.feature"], "@task:X", project.repo,
        project.repo / "junit.xml", 1, str(script), TASK,
    )
    _nothing_left(pid)


@pytest.mark.skipif(not Path("/proc/self/stat").exists(), reason="needs /proc")
def test_a_serve_probe_that_never_gets_ready_leaves_no_stubborn_worker(project: Project) -> None:
    """The leader exits on SIGTERM; its worker ignores SIGTERM. The group,
    not the leader, decides when cleanup is finished."""
    from guardkit.orchestrator.boot_smoke import run_boot_smoke

    pid = project.out / "stubborn-serve.pid"
    (project.repo / "standin_stubborn.py").write_text(
        textwrap.dedent(
            f"""\
            import subprocess, time
            child = subprocess.Popen(["sh", "-c", 'trap "" TERM; exec sleep 300'])
            open({str(pid)!r}, "w").write(str(child.pid))
            time.sleep(300)
            """
        ),
        encoding="utf-8",
    )
    result = run_boot_smoke(
        _boot_config([{"id": "s", "kind": "serve", "target": "standin_stubborn",
                       "readiness": {"kind": "port", "timeout_s": 2}}]),
        project.repo,
    )
    assert result.entries[0].verdict == "ran_and_failed", result.entries[0]
    _nothing_left(pid)


@pytest.mark.skipif(not Path("/proc/self/stat").exists(), reason="needs /proc")
def test_a_timed_out_command_leaves_no_stubborn_worker(project: Project) -> None:
    """The same for the generic runner: the shell exits on SIGTERM, the
    worker it started ignores SIGTERM and is still ended."""
    from guardkit.orchestrator import process_group
    from guardkit.orchestrator.project_command_env import project_command_environment

    pid = project.out / "stubborn-command.pid"
    command = f'(trap "" TERM; exec sleep 300) & echo $! > "{pid}"; wait'
    with pytest.raises(subprocess.TimeoutExpired):
        process_group.run_project_command(
            command, shell=True, cwd=project.repo, timeout=1, capture_output=True,
            env=project_command_environment(project.repo, None),
        )
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
    ("orchestrator/run_evidence.py", "DockerProbe"): (
        "holds _default_runner as the probe's runner; every call through "
        "runner / probe.runner in this file is checked"
    ),
    ("orchestrator/run_evidence.py", "_source_manifest"): (
        "falls back to _default_runner in a local runner; every call through "
        "runner in this file is checked"
    ),
    ("orchestrator/run_evidence.py", "_originating_worktree_identity"): (
        "falls back to _default_runner in a local runner; every call through "
        "runner in this file is checked"
    ),
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
    ("orchestrator/process_group.py", "run_project_command"): (
        "generic runner (subprocess.run's shape, a process group of its own); "
        "every call is checked"
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
    ("orchestrator/merge_executor.py", "prepare_tree"): (
        "the merge build's code (merge design item 2a): the env it builds with "
        "project_command_environment runs the install and is returned for the "
        "merge's checks, so it is used besides as an env= keyword"
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
    ("orchestrator/process_group.py", "run_project_command"): {
        "names": {"run_project_command"},
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
#: ``finish_project_environment`` copies its input and adds to it; it is no
#: sanitiser. A call to it counts only when its input is itself the helper's.
_FINISH = "guardkit.orchestrator.project_command_env.finish_project_environment"

#: The factory's own programs, recognised from a literal first argument.
FACTORY_PROGRAMS = {"git", "docker", "pgrep", "ps"}

#: Every name a process launch goes by, in any launch module.
LAUNCH_NAMES = {
    "run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput",
    "create_subprocess_exec", "create_subprocess_shell", "subprocess_exec", "subprocess_shell",
    "system", "popen", "startfile",
    "execl", "execle", "execlp", "execlpe", "execv", "execve", "execvp", "execvpe",
    "spawn", "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe",
    "posix_spawn", "posix_spawnp", "fork", "forkpty",
}
#: Launch-shaped names that run no process: asyncio's event-loop runner.
NOT_LAUNCHES = {"asyncio.run", "asyncio.runners.run"}
#: The modules launches live in; their submodules count too (asyncio.subprocess).
LAUNCH_MODULES = {"subprocess", "os", "asyncio", "pty", "multiprocessing", "posix", "nt"}
#: Launch methods recognised on any object: an event loop's
#: ``subprocess_exec`` / ``subprocess_shell`` and ``create_subprocess_*``.
_ANY_RECEIVER_LAUNCHES = {
    "create_subprocess_exec", "create_subprocess_shell", "subprocess_exec", "subprocess_shell",
}


_REAL_SUBMODULES: Dict[str, bool] = {}


def _is_launch_module(dotted: str) -> bool:
    """A launch module, or a REAL submodule of one (asyncio.subprocess,
    os.path), never an attribute that only looks like one (os.getenv,
    asyncio.subprocess.create_subprocess_shell): below the top level the name
    must be importable as a module (``importlib.util.find_spec``)."""
    if dotted in LAUNCH_MODULES:
        return True
    if not any(dotted.startswith(m + ".") for m in LAUNCH_MODULES):
        return False
    if dotted not in _REAL_SUBMODULES:
        import importlib.util

        try:
            _REAL_SUBMODULES[dotted] = importlib.util.find_spec(dotted) is not None
        except (ImportError, AttributeError, ValueError):
            _REAL_SUBMODULES[dotted] = False
    return _REAL_SUBMODULES[dotted]


def _is_launch_target(dotted: str) -> bool:
    """THE ONE PREDICATE for a launch function: its resolved name ends in a
    launch name and its module is a launch module or a submodule of one. Used
    for direct, attribute and bare imported calls, guarded names and the
    alias rule alike, so no form can fall through a table gap."""
    module, _, last = dotted.rpartition(".")
    if dotted in NOT_LAUNCHES:
        return False
    return bool(module) and last in LAUNCH_NAMES and _is_launch_module(module)
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


def _import_bindings(node: ast.AST, dotted: str, is_package: bool) -> List[Tuple[str, str]]:
    """The (bound name, what it names) pairs one import statement makes."""
    package = dotted if is_package else dotted.rsplit(".", 1)[0]
    out: List[Tuple[str, str]] = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            if alias.asname:
                out.append((alias.asname, alias.name))
            else:
                out.append((alias.name.split(".")[0], alias.name.split(".")[0]))
    elif isinstance(node, ast.ImportFrom):
        base = node.module or ""
        if node.level:
            anchor = package.split(".")
            anchor = anchor[: len(anchor) - (node.level - 1)]
            base = ".".join([*anchor, base] if base else anchor)
        for alias in node.names:
            out.append((alias.asname or alias.name, f"{base}.{alias.name}"))
    return out


def _imports(tree: ast.Module, dotted: str, is_package: bool) -> Dict[str, set]:
    """Every name an import binds anywhere in the module, in any scope, ->
    the SET of everything it is imported as (never overwritten).

    A call through a name is a launch if ANY of its targets is a launch
    module or function (strict side); a helper or runner qualifies only when
    ALL of them are it (see :func:`_resolve`)."""
    out: Dict[str, set] = {}
    for node in ast.walk(tree):
        for name, target in _import_bindings(node, dotted, is_package):
            out.setdefault(name, set()).add(target)
    return out


def _names_bound_by(node: ast.AST, dotted: str, is_package: bool) -> List[Tuple[str, str, Optional[str]]]:
    """Every name ``node`` binds, as (name, kind, import target).

    THE ONE ENUMERATION of Python's binding forms, used by every "bound
    exactly once" and "not shadowed" decision in this guard: a name stored or
    deleted (plain, chained, unpacking, augmented, annotated and walrus
    assignment; for, with and comprehension targets; ``del``), a parameter
    (a lambda's included), an import or import-from alias, a def or class, an
    except target, a global or nonlocal declaration, and a match-case capture
    (``case x``, ``*rest``, ``**rest``). Kinds: name, param, import, def,
    except, declare, match."""
    if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
        return [(node.id, "name", None)]
    if isinstance(node, ast.arg):
        return [(node.arg, "param", None)]
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return [(bound, "import", target) for bound, target in _import_bindings(node, dotted, is_package)]
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [(node.name, "def", None)]
    if isinstance(node, ast.ExceptHandler) and node.name:
        return [(node.name, "except", None)]
    if isinstance(node, (ast.Global, ast.Nonlocal)):
        return [(name, "declare", None) for name in node.names]
    if isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
        return [(node.name, "match", None)]
    if isinstance(node, ast.MatchMapping) and node.rest:
        return [(node.rest, "match", None)]
    return []


def _binding_sites(
    nodes: Iterable[ast.AST], name: str, dotted: str, is_package: bool, own: Optional[ast.AST] = None
) -> List[Tuple[str, ast.AST, Optional[str]]]:
    """Where ``name`` is bound among ``nodes`` (``own``, the function being
    looked into, does not bind its own name inside itself)."""
    sites: List[Tuple[str, ast.AST, Optional[str]]] = []
    for node in nodes:
        if node is own:
            continue
        for bound, kind, target in _names_bound_by(node, dotted, is_package):
            if bound == name:
                sites.append((kind, node, target))
    return sites


def _bindings(nodes: Iterable[ast.AST], name: str, dotted: str, is_package: bool, own: Optional[ast.AST] = None) -> Tuple[set, bool, bool]:
    """How ``name`` is bound among ``nodes``: (import targets, defined by a
    def or class, bound any other way), from :func:`_binding_sites`."""
    imports: set = set()
    definitions = 0
    other = False
    for kind, _node, target in _binding_sites(nodes, name, dotted, is_package, own):
        if kind == "import":
            imports.add(target)
        elif kind == "def":
            definitions += 1
        else:
            other = True
    # Defined more than once (under if/else, or twice): which one runs is
    # not known, so it is not a definition the guard can rely on.
    if definitions > 1:
        other = True
    return imports, definitions == 1, other


def _module_scope_nodes(mod: "_Module") -> List[ast.AST]:
    """Nodes at module scope: not inside any function, lambda or class
    (the bodies are not entered; computed once per module)."""
    cached = getattr(mod, "_scope_nodes", None)
    if cached is not None:
        return cached
    out: List[ast.AST] = []
    pending = list(ast.iter_child_nodes(mod.tree))
    while pending:
        node = pending.pop()
        out.append(node)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # The def or class itself binds its name here; its decorators,
            # defaults and bases are evaluated here too, its body is not.
            pending.extend(node.decorator_list)
            if not isinstance(node, ast.ClassDef):
                pending.extend(d for d in node.args.defaults + node.args.kw_defaults if d)
            continue
        if isinstance(node, ast.Lambda):
            continue
        pending.extend(ast.iter_child_nodes(node))
    mod._scope_nodes = out
    return out


def _own_scope_nodes(mod: "_Module", holder: ast.AST) -> List[ast.AST]:
    """Nodes in ``holder``'s own scope (a module, class or function): its
    statements, not entering nested functions, lambdas or classes (whose
    def/class node, decorators and defaults are included), plus a function's
    own parameters. Cached per holder."""
    cache = mod.__dict__.setdefault("_own_scope_cache", {})
    if id(holder) in cache:
        return cache[id(holder)]
    out: List[ast.AST] = []
    pending: List[ast.AST] = list(getattr(holder, "body", []))
    if isinstance(holder, (ast.FunctionDef, ast.AsyncFunctionDef)):
        pending.extend(ast.walk(holder.args))
    while pending:
        node = pending.pop()
        out.append(node)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            pending.extend(node.decorator_list)
            if not isinstance(node, ast.ClassDef):
                pending.extend(d for d in node.args.defaults + node.args.kw_defaults if d)
            continue
        if isinstance(node, ast.Lambda):
            continue
        pending.extend(ast.iter_child_nodes(node))
    cache[id(holder)] = out
    return out


def _bound_once_as(mod: "_Module", node: ast.AST) -> bool:
    """True when the def ``node`` is the ONLY binding of its name in its own
    scope (no second def under if/else, no later assignment, no import...)."""
    holder = _enclosing(mod, node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) or mod.tree
    sites = _binding_sites(
        _own_scope_nodes(mod, holder), node.name, mod.dotted, mod.rel.endswith("__init__.py")
    )
    return len(sites) == 1 and sites[0][1] is node


def _scope_bindings(mod: "_Module", scope: ast.AST, name: str) -> Tuple[set, bool, bool]:
    """:func:`_bindings` for a function's whole subtree, cached."""
    cache = mod.__dict__.setdefault("_binding_cache", {})
    key = (id(scope), name)
    if key not in cache:
        cache[key] = _bindings(
            ast.walk(scope), name, mod.dotted, mod.rel.endswith("__init__.py"), own=scope
        )
    return cache[key]


def _module_bindings(mod: "_Module", name: str) -> Tuple[set, bool, bool]:
    cache = mod.__dict__.setdefault("_module_binding_cache", {})
    if name not in cache:
        cache[name] = _bindings(
            _module_scope_nodes(mod), name, mod.dotted, mod.rel.endswith("__init__.py")
        )
    return cache[name]


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


def _defining_scope(mod: _Module, node: ast.AST) -> Optional[ast.AST]:
    """The function whose BODY ``node`` is in, for name resolution.

    A parameter's default, an annotation and a decorator are evaluated where
    the function is defined, not inside it, so a function reached through its
    ``args``, ``decorator_list`` or ``returns`` is skipped."""
    child = node
    current = mod.parents.get(id(node))
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if child is current.args or child is current.returns or child in current.decorator_list:
                child, current = current, mod.parents.get(id(current))
                continue
            return current
        child, current = current, mod.parents.get(id(current))
    return None


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
    """The dotted name a call target refers to, or ``None`` when unknown.

    A plain name resolves through the scopes that enclose ``at``: a function
    that binds it any way other than an import (a parameter, a default, an
    assignment, a loop, ``with`` or ``except`` target, a nested def, a
    ``global`` or ``nonlocal``) makes it unknown, and so does a module that
    both imports it and binds it otherwise, or imports it twice."""
    if isinstance(func_node, ast.Name):
        name = func_node.id
        scope = _defining_scope(mod, at)
        while scope is not None:
            imports, defined, other = _scope_bindings(mod, scope, name)
            if other or defined or len(imports) > 1:
                return None
            if imports:
                target = next(iter(imports))
                # Imported as anything else anywhere in the module: unknown.
                return target if mod.imports.get(name, set()) == {target} else None
            scope = _defining_scope(mod, scope)
        imports, defined, other = _module_bindings(mod, name)
        if other or (imports and defined) or len(imports) > 1:
            return None
        if defined:
            return None if name in mod.imports else f"{mod.dotted}.{name}"
        if not imports:
            return None
        target = next(iter(imports))
        # Imported as anything else anywhere in the module: unknown.
        return target if mod.imports.get(name, set()) == {target} else None
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


def _name_is_shadowed(mod: _Module, at: ast.AST, name: str) -> bool:
    """True when a plain ``name`` is bound, other than by an import, in a
    function enclosing ``at`` or at module scope."""
    scope = _defining_scope(mod, at)
    while scope is not None:
        _, defined, other = _scope_bindings(mod, scope, name)
        if other or defined:
            return True
        scope = _defining_scope(mod, scope)
    return _module_bindings(mod, name)[2]


def _inline_helper(node: Optional[ast.AST], mod: _Module, wrappers: set, none_is_safe: bool = False) -> bool:
    """``node`` is a call to the helper (or to a function that only ever
    returns one) written right there, or ``None`` where that runs nothing."""
    if isinstance(node, ast.Constant) and node.value is None:
        return none_is_safe
    if isinstance(node, ast.Dict) and not node.keys:
        return True  # an empty environment, written inline, holds nothing
    if not isinstance(node, ast.Call):
        return False
    target = _resolve(mod, node.func, node)
    if isinstance(node.func, ast.Attribute) and target not in HELPERS and target != _FINISH:
        # Method dispatch (self.x(), obj.env()) is never trusted: only the
        # helper itself, or a module-level wrapper called by its plain name.
        return False
    if target == _FINISH:
        # It copies its input and adds to it: its input must be the helper's.
        given = node.args[0] if node.args else _env_keyword(node)
        return _inline_helper(given, mod, wrappers)
    return target in HELPERS or target in wrappers


def _single_use_helper_name(
    name: str, mod: _Module, func: ast.AST, wrappers: set, is_launch: Callable[[ast.Call], bool]
) -> bool:
    """``name`` is bound exactly once in ``func`` (by any binding form, see
    :func:`_names_bound_by`), by a single-target assignment of an inline helper
    call, is not declared global or nonlocal in an enclosing function, and
    every other use of it is as the ``env=`` keyword of a launch or
    generic-runner call in ``func`` itself."""
    sites = _binding_sites(ast.walk(func), name, mod.dotted, mod.rel.endswith("__init__.py"), own=func)
    if len(sites) != 1 or sites[0][0] != "name":
        return False
    stored = sites[0][1]
    statement = mod.parents.get(id(stored))
    if isinstance(statement, ast.Assign):
        if len(statement.targets) != 1 or statement.targets[0] is not stored:
            return False  # chained or unpacking assignment
    elif isinstance(statement, ast.AnnAssign):
        if statement.target is not stored or statement.value is None:
            return False
    else:
        return False  # augmented, walrus, loop, with, comprehension, del ...
    if not _inline_helper(statement.value, mod, wrappers):
        return False
    outer = _defining_scope(mod, func)
    while outer is not None:
        if any(
            kind == "declare"
            for kind, _n, _t in _binding_sites(
                ast.walk(outer), name, mod.dotted, mod.rel.endswith("__init__.py"), own=outer
            )
        ):
            return False
        outer = _defining_scope(mod, outer)
    for node in ast.walk(func):
        if not (isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, ast.Load)):
            continue
        parent = mod.parents.get(id(node))
        if not (isinstance(parent, ast.keyword) and parent.arg == "env"):
            return False  # attribute, subscript, argument, return, alias ...
        call = mod.parents.get(id(parent))
        if not isinstance(call, ast.Call) or not is_launch(call):
            return False
        scope = mod.parents.get(id(call))
        while scope is not None and scope is not func:
            if isinstance(scope, (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                return False  # captured by a closure
            scope = mod.parents.get(id(scope))
    return True


def _helper_shaped(
    node: Optional[ast.AST], mod: _Module, func: Optional[ast.AST], wrappers: set,
    none_is_safe: bool = False, is_launch: Optional[Callable[[ast.Call], bool]] = None,
) -> bool:
    """True when ``node`` (an ``env=`` value) is, provably, the helper's
    result: the helper called inline, or a name that holds nothing else and
    is used for nothing else (:func:`_single_use_helper_name`)."""
    if node is None:
        return False
    if _inline_helper(node, mod, wrappers, none_is_safe):
        return True
    if isinstance(node, ast.Name) and func is not None and is_launch is not None:
        return _single_use_helper_name(node.id, mod, func, wrappers, is_launch)
    return False


def _definition_counts(mod: _Module) -> Dict[str, int]:
    """How many definitions (def or class) each full qualified identity has
    across the whole module, nested paths included. Cached."""
    cached = getattr(mod, "_definition_counts", None)
    if cached is None:
        cached = {}
        for node in ast.walk(mod.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                qual = _qualname(mod, node)
                cached[qual] = cached.get(qual, 0) + 1
        mod._definition_counts = cached
    return cached


def _trusted_definition(mod: _Module, node: ast.AST) -> bool:
    """A def the guard may rely on as a wrapper: a MODULE-LEVEL function
    (never a method, never nested), whose full qualified identity has exactly
    one definition in the module and which is the only binding of its name
    in the module's scope."""
    if not isinstance(mod.parents.get(id(node)), ast.Module):
        return False
    if _definition_counts(mod).get(_qualname(mod, node), 0) != 1:
        return False
    return _bound_once_as(mod, node)


def _wrappers(modules: List[_Module]) -> set:
    """Functions whose whole body (after a docstring) is one ``return`` of an
    inline helper call, by dotted name."""
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
                body = list(node.body)
                if (
                    body
                    and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)
                ):
                    body = body[1:]  # a leading docstring
                # Exactly one statement, ``return <helper call>``: nothing can
                # fall through to an implicit None (which would inherit).
                if (
                    not node.decorator_list  # a decorator could turn a refusal into None
                    and _trusted_definition(mod, node)  # module level, defined once
                    and len(body) == 1
                    and isinstance(body[0], ast.Return)
                    and isinstance(body[0].value, ast.Call)
                    and _inline_helper(body[0].value, mod, found)
                ):
                    found.add(full)
                    changed = True
    return found


def _possible_targets(mod: _Module, node: ast.AST) -> set:
    """Every dotted name a plain or dotted name can stand for, through every
    import of its root anywhere in the module."""
    if isinstance(node, ast.Name):
        return set(mod.imports.get(node.id, ()))
    if isinstance(node, ast.Attribute):
        return {f"{base}.{node.attr}" for base in _possible_targets(mod, node.value)}
    return set()


def _launch_kind(mod: _Module, node: ast.AST) -> Optional[str]:
    """What launch ``node`` (a call target or a value) names, if any."""
    if isinstance(node, ast.Attribute) and node.attr in _ANY_RECEIVER_LAUNCHES:
        return _dotted(node)
    for target in sorted(_possible_targets(mod, node)):
        if _is_launch_target(target):
            return target
    return None


def _factory_literal(call: ast.Call) -> bool:
    """The launch runs one of the factory's own programs, provably.

    Only when (a) the command is a list or tuple literal written inline in
    this call, (b) its first item is the literal "git", "docker", "pgrep" or
    "ps", and (c) the call has no ``executable=``, no ``shell=`` other than a
    literal False, and no ``*`` or ``**`` unpacked arguments. A named
    command, a module-level constant or anything built elsewhere never
    qualifies: such a launch uses a helper-built environment, or is on the
    allowed list with a reason.
    """
    if len(call.args) > 1 or any(isinstance(a, ast.Starred) for a in call.args):
        return False  # a further positional argument can be the executable or shell
    for kw in call.keywords:
        if kw.arg is None or kw.arg == "executable":
            return False
        if kw.arg == "shell" and not (
            isinstance(kw.value, ast.Constant) and kw.value.value is False
        ):
            return False
    node = _first_argument(call)
    return (
        isinstance(node, (ast.List, ast.Tuple))
        and bool(node.elts)
        and isinstance(node.elts[0], ast.Constant)
        and isinstance(node.elts[0].value, str)
        and node.elts[0].value in FACTORY_PROGRAMS
    )


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


def _runner_identity(package_name: str, rel: str, fname: str) -> str:
    """The dotted name a generic runner is imported by."""
    if rel.startswith("guardkit:"):
        package_name, rel = "guardkit", rel[len("guardkit:"):]
    parts = [package_name, *Path(rel).with_suffix("").parts]
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join([*parts, fname])


def _runner_call_matches(
    call: ast.Call, spec: Dict[str, Any], mod: Optional[_Module] = None,
    identity: Optional[str] = None,
) -> bool:
    """A call to a generic runner: by what it resolves to (an imported alias
    included), by its last name (any object or module spelling), or by a
    dotted suffix for the generic method names."""
    if mod is not None and identity is not None and _resolve(mod, call.func, call) == identity:
        return True
    if _last_name(call.func) in spec.get("names", ()):
        # A plain name bound locally (a parameter, an assignment ...) is not
        # the runner, whatever it is called.
        if mod is not None and isinstance(call.func, ast.Name) and _name_is_shadowed(
            mod, call, call.func.id
        ):
            return False
        return True
    dotted = _callee_name(call)
    return any(dotted.endswith(suffix) for suffix in spec.get("suffixes", ()))


def _callee_name(call: ast.Call) -> str:
    return _dotted(call.func)


#: Generic method names a runner may have that are ordinary words elsewhere;
#: those runners are found by a dotted suffix, so the bare word is not reserved.
_ORDINARY_RUNNER_WORDS = {"run", "execute", "_run", "runner"}


def _reserved_names() -> set:
    """Names that may never be rebound: the helper's, and every generic
    runner's (outside the ordinary words above)."""
    reserved = {target.rsplit(".", 1)[1] for target in HELPERS}
    for (rel, fname), spec in GENERIC_RUNNERS.items():
        if fname not in _ORDINARY_RUNNER_WORDS:
            reserved.add(fname)
        if not spec.get("scope"):
            reserved.update(n for n in spec.get("names", ()) if n not in _ORDINARY_RUNNER_WORDS)
    return reserved


def _reserved_name_rebindings(modules: List[_Module]) -> List[str]:
    """Every rebinding of a reserved name: a parameter, a local binding, a
    nested def, a ``global``/``nonlocal``, or a module-level rebinding of the
    helper's, a generic runner's or a launch function's name (an imported
    alias of one included). Imports, and a module-level def or class that is
    not also imported, are not rebindings."""
    base = _reserved_names()
    problems: List[str] = []
    for mod in modules:
        reserved = set(base)
        for alias, targets in mod.imports.items():
            for target in targets:
                module, _, last = target.rpartition(".")
                if last in base or target in HELPERS or _is_launch_target(target):
                    reserved.add(alias)

        def flag(node: ast.AST, name: str, how: str) -> None:
            holder = _enclosing(mod, node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            where = getattr(holder, "name", "<module>")
            problems.append(
                f"{mod.rel}:{getattr(node, 'lineno', 0)} in {where}: the reserved name "
                f"{name!r} (the helper's, a generic runner's or a launch function's) is "
                f"rebound {how}"
            )

        is_package = mod.rel.endswith("__init__.py")
        how_by_kind = {
            "param": "as a parameter",
            "except": "by an except target",
            "declare": "by a global or nonlocal declaration",
            "match": "by a match-case capture",
        }
        for node in ast.walk(mod.tree):
            in_function = _enclosing(mod, node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) is not None
            for name, kind, _target in _names_bound_by(node, mod.dotted, is_package):
                if name not in reserved or kind == "import":
                    continue
                if kind == "def":
                    if in_function:
                        flag(node, name, "by a nested definition")
                    elif name in mod.imports and _enclosing(mod, node, ast.ClassDef) is None:
                        flag(node, name, "by a definition of an imported name")
                elif kind == "name":
                    flag(node, name, "by an assignment or target" if in_function else "at module level")
                else:
                    flag(node, name, how_by_kind[kind])
    return problems


def _guarded_names(mod: _Module, runner_ids: set) -> Dict[str, str]:
    """The names in ``mod`` that are guarded, by their own spelling: a launch
    module (kind ``module``), and a launch function, a generic runner or the
    helper (kind ``function``), whether imported (in any scope) or, for a
    runner, defined at module level here."""
    guarded: Dict[str, str] = {}
    for name, targets in mod.imports.items():
        for target in targets:
            module, _, last = target.rpartition(".")
            # Only the guarded name's own spelling: any other spelling is an
            # alias, which is a violation in itself (_aliased_guarded_imports).
            if name == last and (
                _is_launch_target(target) or target in runner_ids or target in HELPERS
            ):
                guarded[name] = "function"
            elif _is_launch_module(target) and (
                name == target.split(".")[0]  # import subprocess / os / asyncio ...
                or name == last  # a launch submodule: from asyncio import subprocess
            ):
                guarded.setdefault(name, "module")
    for node in mod.tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and f"{mod.dotted}.{node.name}" in runner_ids:
            guarded.setdefault(node.name, "function")
    return guarded


_LAUNCH_BEARING: Dict[str, bool] = {}


def _is_launch_bearing_module(dotted: str) -> bool:
    """A launch module, or a real submodule of one, that itself defines at
    least one launch name (found by importing it and looking; cached):
    subprocess, os, asyncio, asyncio.subprocess, multiprocessing.popen_fork;
    never os.path."""
    if not _is_launch_module(dotted):
        return False
    if dotted not in _LAUNCH_BEARING:
        import importlib

        try:
            module = importlib.import_module(dotted)
            _LAUNCH_BEARING[dotted] = any(
                hasattr(module, name) and not _is_not_launch(f"{dotted}.{name}")
                for name in LAUNCH_NAMES
            )
        except Exception:  # noqa: BLE001 - unknown means "treat as launch-bearing"
            _LAUNCH_BEARING[dotted] = True
    return _LAUNCH_BEARING[dotted]


def _is_not_launch(dotted: str) -> bool:
    return dotted in NOT_LAUNCHES


def _launch_attribute_names() -> set:
    return set(LAUNCH_NAMES)


def _indirect_use(mod: _Module, node: ast.Name, kind: str) -> Optional[str]:
    """Why a load of a guarded name is not a direct use, or ``None``.

    A function, runner or helper may only be called: the name is the
    ``func`` of a call. A module may only be the base of an attribute
    (``subprocess.run``, ``os.environ``); when that attribute chain names a
    launch function, the chain itself must be the ``func`` of a call."""
    parent = mod.parents.get(id(node))
    if kind == "function":
        if isinstance(parent, ast.Call) and parent.func is node:
            return None
        return (
            f"{node.id} is used other than by calling it (held, passed, returned, "
            f"stored or wrapped), so what it launches cannot be checked"
        )
    if not (isinstance(parent, ast.Attribute) and parent.value is node):
        return (
            f"the launch module {node.id} is used other than through its "
            f"attributes (held, passed, returned or stored), so what it launches "
            f"cannot be checked"
        )
    chain = parent
    launch_attr = any(_is_launch_target(t) for t in _possible_targets(mod, chain))
    while True:
        above = mod.parents.get(id(chain))
        if isinstance(above, ast.Attribute) and above.value is chain:
            chain = above
            launch_attr = launch_attr or any(
                _is_launch_target(t) for t in _possible_targets(mod, chain)
            )
            continue
        break
    if launch_attr and not (isinstance(above, ast.Call) and above.func is chain):
        if id(chain) in _annotation_nodes_cache(mod):
            return None
        return (
            f"the launch function {_dotted(chain)} is used other than by calling it, "
            f"so its env= cannot be checked"
        )
    # The whole chain names a launch-bearing submodule (it was not the base of
    # a further attribute): held, passed or stored, it could be called
    # through later (backend = multiprocessing.popen_fork; backend.Popen(...)).
    if any(_is_launch_bearing_module(t) for t in _possible_targets(mod, chain)):
        if id(chain) in _annotation_nodes_cache(mod):
            return None
        return (
            f"the launch-bearing module {_dotted(chain)} is used other than as the "
            f"base of an attribute, so what is launched through it cannot be checked"
        )
    return None


def _annotation_nodes_cache(mod: _Module) -> set:
    cached = getattr(mod, "_annotation_ids", None)
    if cached is None:
        cached = _annotation_nodes(mod.tree)
        mod._annotation_ids = cached
    return cached


#: Launch and runner names that are ordinary words elsewhere (``from x
#: import run as y`` is common and unrelated): the module-blind alias check
#: leaves them to the resolved-identity check.
_GENERIC_GUARDED_WORDS = {
    "run", "call", "system", "popen", "fork", "spawn", "execute", "_run", "runner",
}


def _distinctive_guarded_names(runner_ids: set) -> set:
    """The last components of guarded names that are not ordinary words."""
    names = {target.rsplit(".", 1)[1] for target in HELPERS}
    names.update(identity.rsplit(".", 1)[1] for identity in runner_ids)
    names.update(_launch_attribute_names())
    return names - _GENERIC_GUARDED_WORDS


def _aliased_guarded_imports(modules: List[_Module], runner_ids: set) -> List[str]:
    """A guarded name (a launch module or function, a generic runner, the
    helper) imported under another local name is a violation in itself:
    every guarded name is only ever used under its own spelling."""
    problems: List[str] = []
    distinctive = _distinctive_guarded_names(runner_ids)
    for mod in modules:
        for node in ast.walk(mod.tree):
            aliased: List[str] = []
            if isinstance(node, ast.Import):
                aliased = [
                    f"{a.name} as {a.asname}" for a in node.names
                    if a.asname and a.asname != a.name
                    and _is_launch_module(a.name)
                ]
            elif isinstance(node, ast.ImportFrom):
                # One resolver for every identity: relative levels included.
                bindings = _import_bindings(node, mod.dotted, mod.rel.endswith("__init__.py"))
                for alias, (_bound, target) in zip(node.names, bindings):
                    if not alias.asname or alias.asname == alias.name:
                        continue
                    module, _, last = target.rpartition(".")
                    if (
                        _is_launch_target(target)
                        or _is_launch_module(target)  # from asyncio import subprocess as x
                        or target in runner_ids
                        or target in HELPERS
                        # Belt and braces: a distinctive guarded name is never
                        # aliased, whatever module text it comes from.
                        or alias.name in distinctive
                    ):
                        aliased.append(f"{target} as {alias.asname}")
            for what in aliased:
                holder = _enclosing(mod, node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                problems.append(
                    f"{mod.rel}:{node.lineno} in {getattr(holder, 'name', '<module>')}: "
                    f"a guarded name (a launch module or function, a generic runner or "
                    f"the helper) is imported under another name ({what}); import it "
                    f"under its own name"
                )
    return problems


def unaccounted_launches(package: Path) -> List[str]:
    modules = _load_modules(package)
    wrappers = _wrappers(modules)
    problems: List[str] = []
    runner_ids = {
        _runner_identity(package.name, rel, fname) for rel, fname in GENERIC_RUNNERS
    }
    # Method-style runners (``x._run_recorded``) by name; plainly named ones
    # such as ``runner`` in one file are left to their scoped call check.
    runner_attrs = {
        name
        for spec in GENERIC_RUNNERS.values()
        if not spec.get("scope")
        for name in spec.get("names", ())
    }

    runner_specs = [
        (spec, _runner_identity(package.name, rel, fname))
        for (rel, fname), spec in GENERIC_RUNNERS.items()
    ]

    def launch_checker(mod: _Module) -> Callable[[ast.Call], bool]:
        def is_launch(call: ast.Call) -> bool:
            if _launch_kind(mod, call.func):
                return True
            return any(
                (not spec.get("scope") or mod.rel in spec["scope"])
                and _runner_call_matches(call, spec, mod, identity)
                for spec, identity in runner_specs
            )

        return is_launch

    def place(mod: _Module, node: ast.AST) -> Tuple[Optional[ast.AST], str]:
        func = _enclosing_function(mod, node)
        named = _enclosing(mod, node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        return func, getattr(named, "name", "<module>")

    def judge(
        mod: _Module, call: ast.Call, what: str, *, default_is_safe=False,
        none_is_safe=False, env_position: Optional[int] = None,
    ) -> None:
        func, fname = place(mod, call)
        if (mod.rel, fname) in ALLOWED:
            return
        if _factory_literal(call):
            return
        env = _env_keyword(call, env_position)
        if env is None and default_is_safe:
            return
        if _helper_shaped(env, mod, func, wrappers, none_is_safe, launch_checker(mod)):
            return
        reason = "no env= (it inherits everything)" if env is None else "env= is not the helper's"
        problems.append(f"{mod.rel}:{call.lineno} in {fname}: {what}: {reason}")

    for mod in modules:
        annotations = _annotation_nodes(mod.tree)
        guarded = _guarded_names(mod, runner_ids)
        for node in ast.walk(mod.tree):
            if isinstance(node, ast.Call):
                kind = _launch_kind(mod, node.func)
                if kind:
                    judge(mod, node, f"process launch {kind}")
                elif (
                    _dotted(node.func) in ("__import__", "importlib.import_module", "import_module")
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and _is_launch_module(str(node.args[0].value))
                ):
                    _, fname = place(mod, node)
                    if (mod.rel, fname) not in ALLOWED:
                        problems.append(
                            f"{mod.rel}:{node.lineno} in {fname}: the launch module "
                            f"{node.args[0].value} is imported by name, so its "
                            f"launches cannot be checked"
                        )
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in guarded:
                if id(node) in annotations:
                    continue  # a type annotation launches nothing
                problem = _indirect_use(mod, node, guarded[node.id])
                if problem:
                    _, fname = place(mod, node)
                    if (mod.rel, fname) not in ALLOWED:
                        problems.append(f"{mod.rel}:{node.lineno} in {fname}: {problem}")
            elif (
                isinstance(node, ast.Attribute)
                and isinstance(node.ctx, ast.Load)
                and node.attr in runner_attrs
                and id(node) not in annotations
            ):
                parent = mod.parents.get(id(node))
                if not (isinstance(parent, ast.Call) and parent.func is node):
                    _, fname = place(mod, node)
                    if (mod.rel, fname) not in ALLOWED:
                        problems.append(
                            f"{mod.rel}:{node.lineno} in {fname}: the generic runner "
                            f"{_dotted(node)} is used other than by calling it, so its "
                            f"env= cannot be checked"
                        )
    problems.extend(_reserved_name_rebindings(modules))
    problems.extend(_aliased_guarded_imports(modules, runner_ids))
    for mod in modules:
        for node in ast.walk(mod.tree):
            if isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names):
                problems.append(
                    f"{mod.rel}:{node.lineno} in <module>: a wildcard import "
                    f"(from {'.' * node.level}{node.module or ''} import *) binds names "
                    f"the guard cannot see; import names explicitly"
                )
    for (rel, fname), spec in GENERIC_RUNNERS.items():
        identity = _runner_identity(package.name, rel, fname)
        for mod in modules:
            if spec.get("scope") and mod.rel not in spec["scope"]:
                continue
            for node in ast.walk(mod.tree):
                if not isinstance(node, ast.Call) or not _runner_call_matches(
                    node, spec, mod, identity
                ):
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
    from guardkit.orchestrator.project_command_env import project_command_environment as pce_alias


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


    def _widen(env):
        env.update(os.environ)


    def v18_widened_through_an_alias(cmd, wf):
        env = project_command_environment(wf, None)
        other = env
        other.update(os.environ)
        subprocess.run(cmd, shell=True, env=env)


    def v19_handed_to_a_function_first(cmd, wf):
        env = project_command_environment(wf, None)
        _widen(env)
        subprocess.run(cmd, shell=True, env=env)


    def v20_dunder_import(cmd):
        __import__("subprocess").run(cmd, shell=True)


    class v21_PopenSubclass(subprocess.Popen):
        pass


    from guardkit.orchestrator.process_group import run_in_own_group as launch
    from guardkit.orchestrator.project_command_env import finish_project_environment


    def v22_generic_runner_under_an_alias(cmd):
        launch(cmd, cwd=".", env=dict(os.environ), timeout=5)


    def v23_finish_on_the_factory_environment(cmd):
        subprocess.run(cmd, shell=True, env=finish_project_environment(dict(os.environ)))


    def ok_finish(cmd, wf):
        env = finish_project_environment(project_command_environment(wf, None), additions={"X": "1"})
        subprocess.run(cmd, shell=True, env=env)


    from guardkit.orchestrator.process_group import run_project_command


    def v24_generic_runner_held_in_a_variable(cmd):
        invoke = run_project_command
        invoke(cmd, shell=True, env=dict(os.environ))


    def v25_generic_runner_partially_applied(cmd):
        functools.partial(run_project_command, shell=True)(cmd, env=dict(os.environ))


    def ok_runner(cmd, wf):
        run_project_command(cmd, shell=True, env=project_command_environment(wf, None))


    OK_ARGV = ("git", "status")
    MUTABLE_ARGV = ["git", "status"]


    def _swap(argv):
        argv[0] = "sh"


    def v26_command_list_item_replaced(cmd):
        argv = ["git", "-c", "x"]
        argv[0] = "sh"
        subprocess.run(argv)


    def v27_command_list_slice_replaced(cmd):
        argv = ["git", "x"]
        argv[:1] = ["sh"]
        subprocess.run(argv)


    def v28_command_list_changed_through_an_alias(cmd):
        argv = ["git", "x"]
        other = argv
        other[0] = "sh"
        subprocess.run(argv)


    def v29_command_list_handed_to_a_call_first(cmd):
        argv = ["git", "x"]
        _swap(argv)
        subprocess.run(argv)


    def v30_command_list_inserted_into(cmd):
        argv = ["git", "x"]
        argv.insert(0, "sh")
        subprocess.run(argv)


    def v31_module_level_list_command(cmd):
        subprocess.run(MUTABLE_ARGV)


    def v32_command_list_assigned_twice(cmd, other):
        argv = ["git", "x"]
        argv = other
        subprocess.run(argv)


    def v33_chained_assignment_alias(cmd):
        argv = other = ["git", "-c", "x"]
        other[0] = "sh"
        subprocess.run(argv)


    def v34_executable_override(cmd):
        subprocess.run(["git", "-c", "x"], executable="/bin/sh")


    def v35_shell_true(cmd):
        subprocess.run(["git", "status"], shell=True)


    def v36_keyword_unpacking(cmd, options):
        subprocess.run(["git", "status"], **options)


    def v37_positional_unpacking(cmd, rest):
        subprocess.run(["git", "status"], *rest)


    def v38_named_list(cmd):
        argv = ["git", "status"]
        subprocess.run(argv)


    def v39_module_tuple(cmd):
        subprocess.run(list(OK_ARGV))


    def v40_positional_executable(cmd):
        subprocess.Popen(["git", "-c", "x"], -1, "/bin/sh")


    def v41_positional_shell(cmd):
        subprocess.Popen(["git", "status"], -1, None, None, None, None, None, True, True)


    def v42_chained_env_alias(cmd, wf):
        env = other = project_command_environment(wf, None)
        other.update(os.environ)
        subprocess.run(cmd, env=env)


    def v43_tuple_unpacked_env(cmd, wf):
        env, other = project_command_environment(wf, None), None
        subprocess.run(cmd, env=env)


    def v44_env_handed_to_a_logger(cmd, wf, log):
        env = project_command_environment(wf, None)
        log.info("env %s", env)
        subprocess.run(cmd, env=env)


    def v45_env_returned(cmd, wf):
        env = project_command_environment(wf, None)
        subprocess.run(cmd, env=env)
        return env


    def _falls_through_on_error(wf):
        try:
            return project_command_environment(wf, None)
        except OSError:
            pass


    def _returns_only_sometimes(wf, ready):
        if ready:
            return project_command_environment(wf, None)


    def _does_something_first(wf):
        os.environ["OPENAI_API_KEY"] = "x"
        return project_command_environment(wf, None)


    def _single_return_wrapper(wf):
        """A docstring is fine."""
        return project_command_environment(wf, None, additions={"X": "1"})


    def v46_wrapper_falls_through_on_error(cmd, wf):
        subprocess.run(cmd, shell=True, env=_falls_through_on_error(wf))


    def v47_wrapper_returns_only_sometimes(cmd, wf):
        subprocess.run(cmd, shell=True, env=_returns_only_sometimes(wf, True))


    def v48_wrapper_does_something_first(cmd, wf):
        subprocess.run(cmd, shell=True, env=_does_something_first(wf))


    def _swallow(fn):
        def inner(*a, **k):
            try:
                return fn(*a, **k)
            except OSError:
                return None
        return inner


    @_swallow
    def _decorated_wrapper(wf):
        return project_command_environment(wf, None)


    def v49_decorated_wrapper(cmd, wf):
        subprocess.run(cmd, shell=True, env=_decorated_wrapper(wf))


    def v50_parameter_default_shadows_the_helper(
        cmd, wf, project_command_environment=lambda *a: dict(os.environ)
    ):
        subprocess.run(cmd, shell=True, env=project_command_environment(wf, None))


    def v51_local_reassignment_shadows_the_helper(cmd, wf):
        project_command_environment = lambda *a: dict(os.environ)  # noqa: E731
        subprocess.run(cmd, shell=True, env=project_command_environment(wf, None))


    def v52_for_target_shadows_the_helper(cmd, wf, makers):
        for project_command_environment in makers:
            subprocess.run(cmd, shell=True, env=project_command_environment(wf, None))


    def v54_same_named_default_capture(cmd, run_project_command=run_project_command):
        return run_project_command(cmd, shell=True, env=None, timeout=5)


    def v55_differently_named_default_capture(cmd, go=run_project_command):
        return go(cmd, shell=True, env=None, timeout=5)


    def v56_lambda_default_calling_a_runner(
        cmd, go=lambda c: run_project_command(c, shell=True, env=None, timeout=5)
    ):
        return go(cmd)


    def v57_local_named_like_the_helper(cmd, wf):
        finish_project_environment = lambda e: dict(os.environ)  # noqa: E731
        subprocess.run(cmd, shell=True, env=finish_project_environment(None))


    def v58_from_import_rebinds_env(cmd, wf):
        env = project_command_environment(wf, None)
        from os import environ as env
        subprocess.run(cmd, env=env)


    def v59_import_rebinds_env(cmd, wf):
        env = project_command_environment(wf, None)
        import os as env
        subprocess.run(cmd, env=env)


    def v60_class_rebinds_env(cmd, wf):
        env = project_command_environment(wf, None)

        class env(dict):
            pass

        subprocess.run(cmd, env=env)


    def v61_def_rebinds_env(cmd, wf):
        env = project_command_environment(wf, None)

        def env():
            return dict(os.environ)

        subprocess.run(cmd, env=env)


    def v62_match_capture_rebinds_env(cmd, wf):
        env = project_command_environment(wf, None)
        match dict(os.environ):
            case env:
                pass
        subprocess.run(cmd, env=env)


    def v63_del_then_reassign_env(cmd, wf):
        env = project_command_environment(wf, None)
        del env
        env = dict(os.environ)
        subprocess.run(cmd, env=env)


    def v64_module_alias_reused_elsewhere(cmd):
        import subprocess as tool
        tool.run(cmd, shell=True)


    def _other_tool_user(text):
        import json as tool
        return tool.loads(text)


    def v65_function_alias_reused_elsewhere(cmd):
        from subprocess import run as go
        go(cmd, shell=True)


    def _other_go_user(text):
        from json import loads as go
        return go(text)


    def ok_helper_env_beside_reused_names(cmd, wf):
        import json as tool
        subprocess.run(tool.loads(cmd), env=project_command_environment(wf, None))


    def v67_runner_alias_in_one_scope(cmd):
        from guardkit.orchestrator.process_group import run_project_command as invoke
        invoke(cmd, shell=True, env=None)


    def _other_invoke(text):
        from json import loads as invoke
        return invoke(text)


    def v68_module_assigned_to_a_variable(cmd):
        process_tool = subprocess
        process_tool.run(cmd, shell=True)


    def v69_module_passed_as_an_argument(cmd, use):
        use(subprocess, cmd)


    def v70_module_as_a_default(cmd, sp_module=subprocess):
        sp_module.run(cmd, shell=True)


    def v71_launch_function_stored_in_a_dict(cmd):
        table = {"go": subprocess.run}
        table["go"](cmd, shell=True)


    def v72_launch_function_stored_in_a_list(cmd):
        table = [subprocess.Popen]
        table[0](cmd, shell=True)


    def v73_runner_returned_from_a_function():
        return run_project_command


    def v74_relative_runner_alias_assigned(cmd):
        from .process_group import run_project_command as invoke
        dispatch = invoke
        dispatch(cmd, shell=True, env=None)


    def v75_relative_plugin_runner_alias_assigned(cmd):
        from ..bdd.plugin import run_project_command as invoke_plugin
        dispatch = invoke_plugin
        dispatch(cmd, shell=True, env=None)


    def v76_relative_alias_reused_in_unrelated_scopes(cmd):
        from .process_group import run_in_own_group as starter
        starter(cmd, cwd=".", env=dict(os.environ), timeout=5)


    def _unrelated_starter(text):
        from json import loads as starter
        return starter(text)


    def v77_parent_relative_alias(cmd):
        from ..orchestrator.process_group import run_project_command as go_relative
        go_relative(cmd, shell=True, env=None)


    def ok_unaliased_relative_import_with_helper_env(cmd, wf):
        from .process_group import run_project_command
        run_project_command(cmd, shell=True, env=project_command_environment(wf, None))


    if os.environ.get("PROBE_CHOICE"):
        def _maybe_wrapper(wf):
            return project_command_environment(wf, None)
    else:
        def _maybe_wrapper(wf):
            return dict(os.environ)


    def v78_conditional_safe_and_unsafe_definitions(cmd, wf):
        subprocess.run(cmd, shell=True, env=_maybe_wrapper(wf))


    def _twice_wrapper(wf):
        return project_command_environment(wf, None)


    def _twice_wrapper(wf):  # noqa: F811
        return dict(os.environ)


    def v79_duplicate_plain_definitions(cmd, wf):
        subprocess.run(cmd, shell=True, env=_twice_wrapper(wf))


    def _rebound_wrapper(wf):
        return project_command_environment(wf, None)


    _rebound_wrapper = lambda wf: dict(os.environ)  # noqa: E731


    def v80_definition_rebound_by_assignment(cmd, wf):
        subprocess.run(cmd, shell=True, env=_rebound_wrapper(wf))


    class _TwiceMethods:
        def _env(self, wf):
            return project_command_environment(wf, None)

        def _env(self, wf):  # noqa: F811
            return dict(os.environ)

        def v81_duplicate_method_definitions(self, cmd, wf):
            subprocess.run(cmd, shell=True, env=self._env(wf))


    if os.environ.get("PROBE_CLASS"):
        class _Commands:
            def command_env(self, wf):
                return project_command_environment(wf, None)

            def v82_conditional_duplicate_classes(self, cmd, wf):
                subprocess.run(cmd, shell=True, env=self.command_env(wf))
    else:
        class _Commands:
            def command_env(self, wf):
                return dict(os.environ)

            def v82_conditional_duplicate_classes(self, cmd, wf):
                subprocess.run(cmd, shell=True, env=self.command_env(wf))


    class _PlainTwice:
        def command_env(self, wf):
            return project_command_environment(wf, None)

        def v83_duplicate_plain_classes(self, cmd, wf):
            subprocess.run(cmd, shell=True, env=self.command_env(wf))


    class _PlainTwice:  # noqa: F811
        def command_env(self, wf):
            return dict(os.environ)

        def v83_duplicate_plain_classes(self, cmd, wf):
            subprocess.run(cmd, shell=True, env=self.command_env(wf))


    class _ReboundClass:
        def command_env(self, wf):
            return project_command_environment(wf, None)

        def v84_class_rebound_by_assignment(self, cmd, wf):
            subprocess.run(cmd, shell=True, env=self.command_env(wf))


    _ReboundClass = dict  # noqa: F811


    def _outer_twice():
        def _inner_env(wf):
            return project_command_environment(wf, None)

        def v85_nested_under_a_duplicated_outer(cmd, wf):
            subprocess.run(cmd, shell=True, env=_inner_env(wf))

        return v85_nested_under_a_duplicated_outer


    def _outer_twice():  # noqa: F811
        def _inner_env(wf):
            return dict(os.environ)

        def v85_nested_under_a_duplicated_outer(cmd, wf):
            subprocess.run(cmd, shell=True, env=_inner_env(wf))

        return v85_nested_under_a_duplicated_outer


    class _BaseCommands:
        def command_env(self, wf):
            return project_command_environment(wf, None)

        def v86_subclass_overrides_the_wrapper(self, cmd, wf):
            subprocess.run(cmd, shell=True, env=self.command_env(wf))


    class _UnsafeCommands(_BaseCommands):
        def command_env(self, wf):
            return dict(os.environ)


    class _SingleCommands:
        def command_env(self, wf):
            return project_command_environment(wf, None)

        def v91_plain_method_wrapper_via_self(self, cmd, wf):
            subprocess.run(cmd, shell=True, env=self.command_env(wf))


    class _CondBase:
        def command_env(self, wf):
            return project_command_environment(wf, None)

        def v90_conditional_subclass_override(self, cmd, wf):
            subprocess.run(cmd, shell=True, env=self.command_env(wf))


    class _CondChild(_CondBase):
        if os.environ.get("PROBE_OVERRIDE"):
            def command_env(self, wf):
                return dict(os.environ)


    async def v92_bare_create_subprocess_shell(cmd):
        from asyncio.subprocess import create_subprocess_shell
        await create_subprocess_shell(cmd)


    async def v93_bare_create_subprocess_exec(cmd):
        from asyncio.subprocess import create_subprocess_exec
        await create_subprocess_exec(cmd)


    def v94_bare_os_system(cmd):
        from os import system
        system(cmd)


    def v95_bare_pty_spawn(cmd):
        from pty import spawn
        spawn(cmd)


    async def v96_bare_asyncio_create_subprocess_exec(cmd):
        from asyncio import create_subprocess_exec
        await create_subprocess_exec(cmd)


    async def ok_bare_create_subprocess_shell_with_helper_env(cmd, wf):
        from asyncio.subprocess import create_subprocess_shell
        await create_subprocess_shell(cmd, env=project_command_environment(wf, None))


    async def ok_bare_create_subprocess_exec_with_helper_env(cmd, wf):
        from asyncio import create_subprocess_exec
        await create_subprocess_exec(cmd, env=project_command_environment(wf, None))


    def v97_deep_launch_held_in_a_variable(process_object):
        import multiprocessing.popen_fork
        launch = multiprocessing.popen_fork.Popen
        launch(process_object)


    def v98_deep_asyncio_launch_held_in_a_variable(cmd):
        f = asyncio.subprocess.create_subprocess_exec
        return f(cmd)


    def ok_module_attribute_that_is_not_a_launch(cmd):
        x = os.path
        return x.join(cmd, "a")


    async def ok_direct_deep_call_with_helper_env(cmd, wf):
        await asyncio.subprocess.create_subprocess_exec(
            cmd, env=project_command_environment(wf, None)
        )


    def v99_launch_bearing_submodule_stored(process_object):
        import multiprocessing.popen_fork
        backend = multiprocessing.popen_fork
        backend.Popen(process_object)


    async def v100_asyncio_subprocess_stored(cmd):
        m = asyncio.subprocess
        await m.create_subprocess_exec(cmd)


    def v101_subprocess_module_stored(cmd):
        s = subprocess
        s.run(cmd, shell=True)


    async def ok_direct_dotted_call_through_a_submodule(cmd, wf):
        await asyncio.subprocess.create_subprocess_shell(
            cmd, env=project_command_environment(wf, None)
        )


    def ok_asyncio_run_is_not_a_launch(coroutine):
        return asyncio.run(coroutine)


    def ok_bare_os_getenv_is_not_a_module(cmd, wf):
        from os import getenv
        if getenv("PROBE_FLAG"):
            subprocess.run(cmd, shell=True, env=project_command_environment(wf, None))


    def ok_direct_subprocess_run_with_helper_env(cmd, wf):
        subprocess.run(cmd, shell=True, env=project_command_environment(wf, None))


    def ok_direct_runner_with_helper_env(cmd, wf):
        run_project_command(cmd, shell=True, env=project_command_environment(wf, None))


    def ok_os_path_and_environ(cmd):
        return os.path.join(cmd, os.environ.get("HOME", ""))


    def ok_unshadowed_alias(cmd, wf):
        subprocess.run(cmd, shell=True, env=pce_alias(wf, None))


    def ok_single_return_wrapper(cmd, wf):
        subprocess.run(cmd, shell=True, env=_single_return_wrapper(wf))


    def ok_single_use_named_env(cmd, wf):
        env = project_command_environment(wf, None)
        subprocess.run(cmd, shell=True, env=env)


    def ok_inline_env(cmd, wf):
        subprocess.run(cmd, shell=True, env=project_command_environment(wf, None))


    def ok_git_inline_no_env(cmd):
        subprocess.run(["git", "status"], shell=False)


    def ok_git_inline_with_helper(cmd, wf):
        subprocess.run(("git", "status"), env=project_command_environment(wf, None))


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


#: Wildcard imports, one module each: the import itself is the violation.
GUARD_PROBES_WILDCARD = {
    "zz_wild_subprocess.py": "from subprocess import *  # noqa: F403\n\n\ndef w_run(cmd):\n    run(cmd, shell=True)  # noqa: F405\n",
    "zz_wild_os.py": "from os import *  # noqa: F403\n\n\ndef w_system(cmd):\n    system(cmd)  # noqa: F405\n",
    "zz_wild_json.py": "from json import *  # noqa: F403\n\n\ndef w_loads(text):\n    return loads(text)  # noqa: F405\n",
}


#: A module that imports the helper and then rebinds its name.
GUARD_PROBES_REBOUND = textwrap.dedent(
    '''\
    import os
    import subprocess
    from guardkit.orchestrator.project_command_env import project_command_environment

    import subprocess as launcher

    project_command_environment = lambda *a: dict(os.environ)  # noqa: E731


    def _reuses_the_alias(text):
        import json as launcher
        return launcher.loads(text)


    def v66_module_alias_reused_in_a_function(cmd):
        launcher.run(cmd, shell=True)


    def v53_module_level_rebinding(cmd, wf):
        subprocess.run(cmd, shell=True, env=project_command_environment(wf, None))
    '''
)


def _probe_package(tmp_path: Path, name: str) -> Path:
    pkg = tmp_path / name
    (pkg / "orchestrator").mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "orchestrator" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "orchestrator" / "zz_probe.py").write_text(GUARD_PROBES, encoding="utf-8")
    (pkg / "orchestrator" / "zz_rebound.py").write_text(GUARD_PROBES_REBOUND, encoding="utf-8")
    for filename, text in GUARD_PROBES_WILDCARD.items():
        (pkg / "orchestrator" / filename).write_text(text, encoding="utf-8")
    return pkg


def test_the_guard_catches_every_probe(tmp_path: Path) -> None:
    """Synthetic source fed to the guard (never added to the package)."""
    problems = unaccounted_launches(_probe_package(tmp_path, PACKAGE.name))
    named = {p.split(" in ", 1)[1].split(":", 1)[0] for p in problems}
    expected = {
        n.name for n in ast.walk(ast.parse(GUARD_PROBES + "\n" + GUARD_PROBES_REBOUND))
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name.startswith("v")
    }
    assert expected - named == set(), f"slipped past the guard: {sorted(expected - named)}"
    for filename in GUARD_PROBES_WILDCARD:
        assert any(
            f"orchestrator/{filename}:1 in <module>: a wildcard import" in p for p in problems
        ), filename
    # The reserved-name rule itself, not only the checks it backs up.
    reserved_hits = {
        p.split(" in ", 1)[1].split(":", 1)[0] for p in problems if "the reserved name" in p
    }
    assert {
        "v51_local_reassignment_shadows_the_helper",
        "v54_same_named_default_capture",
        "v57_local_named_like_the_helper",
    } <= reserved_hits, reserved_hits
    assert any(
        "zz_rebound.py" in p and "the reserved name" in p and "at module level" in p
        for p in problems
    ), problems
    assert not {
        "ok_helper", "ok_git", "ok_wrapper", "ok_finish", "ok_runner",
        "ok_git_inline_no_env", "ok_git_inline_with_helper",
        "ok_single_use_named_env", "ok_inline_env", "ok_single_return_wrapper",
        "ok_unshadowed_alias", "ok_helper_env_beside_reused_names",
        "ok_direct_subprocess_run_with_helper_env", "ok_direct_runner_with_helper_env",
        "ok_os_path_and_environ", "ok_unaliased_relative_import_with_helper_env",
        "ok_bare_create_subprocess_shell_with_helper_env",
        "ok_bare_create_subprocess_exec_with_helper_env",
        "ok_asyncio_run_is_not_a_launch", "ok_bare_os_getenv_is_not_a_module",
        "ok_module_attribute_that_is_not_a_launch", "ok_direct_deep_call_with_helper_env",
        "ok_direct_dotted_call_through_a_submodule",
    } & named, problems


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
            n.name for n in ast.walk(mod.tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
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
