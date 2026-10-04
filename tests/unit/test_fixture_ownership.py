"""Test fixtures belong to one build's task, never to the whole machine.

Concurrent builds (factory design 2026-10-03, "Test fixtures"): two builds, or
two tasks of one build, may start the same test service at the same moment on
one container engine. Before this change every fixture had one fixed name and
one fixed port (``guardkit-test-redis`` on 6380), so the second start removed
the first task's container, and the Coach wrote the service URL into the
shared process environment, so one task's teardown removed another task's
``DATABASE_URL``.

What these checks prove:

* two owners start the same service at once through the real caller
  (``CoachValidator._start_infrastructure_containers``) on the local engine:
  distinct names and ports, both answer, and A's teardown leaves B running;
* the old fixed recipe, kept here as the negative control, collides;
* containers carry the owner and task labels Forge removes them by;
* two parallel task threads never see each other's service URLs, and the
  process environment is unchanged afterwards;
* the Coach's SDK test run hands PYTHONPATH/PATH to its harness explicitly
  instead of swapping them in the process environment;
* the Player's protocol names the task's own container and a concrete port;
* the separate-session serve probe carries the build's owner marker;
* the project's Coach model is still chosen with the new settings present.

Docker checks use disposable containers labelled ``forge.test=concurrent-builds``,
always remove them, and skip when no engine is reachable.
"""

from __future__ import annotations

import functools
import os
import re
import secrets
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock, patch

import pytest

from guardkit.orchestrator import docker_fixtures
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator

# Literal on purpose: these are the names Forge relies on, so a rename in the
# module must fail here rather than silently follow.
RUN_OWNER_ENV = "GUARDKIT_RUN_OWNER"
OWNER_LABEL = "guardkit.fixture.owner"
TASK_LABEL = "guardkit.fixture.task"


def fixture_owner(*args, **kwargs):
    return docker_fixtures.fixture_owner(*args, **kwargs)


def get_container_name(*args, **kwargs):
    return docker_fixtures.get_container_name(*args, **kwargs)


def get_start_commands(*args, **kwargs):
    return docker_fixtures.get_start_commands(*args, **kwargs)


def render_player_recipes(*args, **kwargs):
    return docker_fixtures.render_player_recipes(*args, **kwargs)

TEST_LABEL = "forge.test=concurrent-builds"
REDIS_IMAGE = "redis:7-alpine"


def _docker_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        info = subprocess.run(["docker", "info"], capture_output=True, timeout=10)
        if info.returncode != 0:
            return False
        image = subprocess.run(
            ["docker", "image", "inspect", REDIS_IMAGE],
            capture_output=True,
            timeout=10,
        )
        return image.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


needs_docker = pytest.mark.skipif(
    not _docker_ready(),
    reason=f"no reachable container engine with {REDIS_IMAGE} available",
)


def _redis_answers(port: int) -> bool:
    """True when a Redis server on 127.0.0.1:<port> answers PING."""
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2) as conn:
                conn.sendall(b"PING\r\n")
                if conn.recv(64).startswith(b"+PONG"):
                    return True
        except OSError:
            pass
        time.sleep(0.2)
    return False


def _container_ids(name: str) -> List[str]:
    out = subprocess.run(
        ["docker", "ps", "-aq", "--filter", f"name=^/{name}$"],
        capture_output=True,
        text=True,
    ).stdout
    return out.split()


def _remove_labelled(label: str) -> None:
    ids = subprocess.run(
        ["docker", "ps", "-aq", "--filter", f"label={label}"],
        capture_output=True,
        text=True,
    ).stdout.split()
    if ids:
        subprocess.run(["docker", "rm", "-f", "-v", *ids], capture_output=True)


@pytest.fixture
def run_owner(monkeypatch):
    """A unique build owner for this test; every container it labels is removed."""
    owner = f"cb-test-{secrets.token_hex(4)}"
    monkeypatch.setenv(RUN_OWNER_ENV, owner)
    yield owner
    if shutil.which("docker"):
        _remove_labelled(f"{OWNER_LABEL}={owner}")
        _remove_labelled(f"forge.test-run={owner}")


# ============================================================================
# 1. Two owners, one service, one engine (real caller, real containers)
# ============================================================================


@needs_docker
def test_two_tasks_start_the_same_service_at_once_without_colliding(
    tmp_path: Path, run_owner: str
) -> None:
    labelled = functools.partial(
        get_start_commands,
        extra_labels={"forge.test": "concurrent-builds", "forge.test-run": run_owner},
    )
    a = CoachValidator(str(tmp_path / "a"), task_id="TASK-A")
    b = CoachValidator(str(tmp_path / "b"), task_id="TASK-B")
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    environ_before = dict(os.environ)

    envs: Dict[str, Dict[str, str]] = {}
    errors: List[BaseException] = []
    start = threading.Barrier(2)

    def _start(name: str, validator: CoachValidator) -> None:
        try:
            start.wait(timeout=10)
            envs[name] = validator._start_infrastructure_containers(["redis"])
        except BaseException as exc:  # surfaced below
            errors.append(exc)

    with patch(
        "guardkit.orchestrator.quality_gates.coach_validator.get_start_commands",
        labelled,
    ):
        threads = [
            threading.Thread(target=_start, args=("a", a)),
            threading.Thread(target=_start, args=("b", b)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)
    assert not errors, errors

    name_a = get_container_name("redis", fixture_owner("TASK-A"))
    name_b = get_container_name("redis", fixture_owner("TASK-B"))
    assert name_a != name_b
    assert _container_ids(name_a) and _container_ids(name_b)

    port_a = int(envs["a"]["REDIS_URL"].rsplit(":", 1)[1])
    port_b = int(envs["b"]["REDIS_URL"].rsplit(":", 1)[1])
    assert port_a != port_b
    assert _redis_answers(port_a)
    assert _redis_answers(port_b)

    # Owner-scoped labels Forge removes the build's fixtures by.
    labels = subprocess.run(
        ["docker", "inspect", "-f", "{{json .Config.Labels}}", name_b],
        capture_output=True,
        text=True,
    ).stdout
    assert f'"{OWNER_LABEL}":"{run_owner}"' in labels
    assert f'"{TASK_LABEL}":"TASK-B"' in labels
    assert '"forge.test":"concurrent-builds"' in labels

    # A's teardown removes A only.
    a._stop_infrastructure_containers(["redis"])
    assert _container_ids(name_a) == []
    assert _container_ids(name_b)
    assert _redis_answers(port_b)

    b._stop_infrastructure_containers(["redis"])
    assert _container_ids(name_b) == []
    assert dict(os.environ) == environ_before


@needs_docker
def test_old_fixed_recipe_collides_negative_control(run_owner: str) -> None:
    """The pre-change shape: one fixed name and one fixed port for everyone.

    A test-unique fixed name stands in for ``guardkit-test-redis`` so the
    control never touches a real fixture on this engine.
    """
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        fixed_port = s.getsockname()[1]
    fixed_name = f"guardkit-test-redis-negctl-{run_owner}"
    recipe = [
        f"docker rm -f -v {fixed_name} 2>/dev/null || true",
        (
            f"docker run -d --name {fixed_name} --label {TEST_LABEL} "
            f"--label forge.test-run={run_owner} -p {fixed_port}:6379 {REDIS_IMAGE}"
        ),
    ]

    def _start() -> str:
        for cmd in recipe:
            subprocess.run(cmd, shell=True, capture_output=True, text=True)
        ids = _container_ids(fixed_name)
        return ids[0] if ids else ""

    owner_a_container = _start()
    assert owner_a_container
    owner_b_container = _start()

    # B's start removed A's container: the two owners shared one fixture.
    assert owner_b_container and owner_b_container != owner_a_container
    remaining = subprocess.run(
        ["docker", "ps", "-aq", "--no-trunc", "--filter", f"label=forge.test-run={run_owner}"],
        capture_output=True,
        text=True,
    ).stdout.split()
    assert not any(cid.startswith(owner_a_container) for cid in remaining)
    assert len(remaining) == 1


# ============================================================================
# 2. Names, labels and ports in the recipe (no engine needed)
# ============================================================================


class TestOwnerScopedRecipe:
    def test_names_carry_run_owner_and_task(self, monkeypatch) -> None:
        monkeypatch.setenv(RUN_OWNER_ENV, "Build-FEAT-1/2026")
        name = get_container_name("postgresql", fixture_owner("TASK-DB-001"))
        assert name == "guardkit-test-pg-build-feat-1-2026-task-db-001"

    def test_without_run_owner_uses_a_per_process_id(self, monkeypatch) -> None:
        monkeypatch.delenv(RUN_OWNER_ENV, raising=False)
        owner = fixture_owner("TASK-1")
        assert owner.owner == docker_fixtures.process_owner_id()
        assert owner.owner.startswith("local-")
        assert get_container_name("redis", owner) != "guardkit-test-redis"

    def test_start_uses_engine_chosen_loopback_port_and_labels(self, monkeypatch) -> None:
        monkeypatch.setenv(RUN_OWNER_ENV, "build-7")
        owner = fixture_owner("TASK-9")
        name = get_container_name("postgresql", owner)
        cmds = get_start_commands("postgresql", owner)
        assert cmds[0] == f"docker rm -f -v {name} 2>/dev/null || true"
        assert f"--name {name} " in cmds[1]
        assert "-p 127.0.0.1::5432 " in cmds[1]
        assert f"--label {OWNER_LABEL}=build-7" in cmds[1]
        assert f"--label {TASK_LABEL}=TASK-9" in cmds[1]
        assert f"docker exec {name} pg_isready" in cmds[2]
        assert not re.search(r"guardkit-test-pg(?![-\w])", " ".join(cmds))

    def test_coach_and_player_never_share_a_container(self, monkeypatch) -> None:
        monkeypatch.setenv(RUN_OWNER_ENV, "build-7")
        coach = get_container_name("redis", fixture_owner("TASK-9"))
        player = get_container_name("redis", fixture_owner("TASK-9", role="player"))
        assert coach != player


# ============================================================================
# 3. Two parallel task threads in one Coach flow
# ============================================================================


def test_parallel_tasks_do_not_share_service_urls(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(RUN_OWNER_ENV, "build-env")
    monkeypatch.setenv("DATABASE_URL", "postgresql://operator-own")
    monkeypatch.setenv("REDIS_URL", "redis://operator-own")
    environ_before = dict(os.environ)

    ports: Dict[str, int] = {}
    seen: Dict[str, Dict[str, str]] = {}
    in_tests = threading.Barrier(2)

    def fake_run(cmd, *args, **kwargs):
        argv = cmd if isinstance(cmd, list) else None
        if argv and argv[:2] == ["docker", "port"]:
            port = ports.setdefault(argv[2], 40000 + len(ports))
            return Mock(returncode=0, stdout=f"127.0.0.1:{port}\n", stderr="")
        if kwargs.get("shell") and isinstance(cmd, str) and cmd.startswith("make test"):
            task = cmd.split()[-1]
            in_tests.wait(timeout=10)  # both tasks are inside their test run
            seen[task] = dict(kwargs["env"])
            return Mock(returncode=0, stdout="ok", stderr="")
        return Mock(returncode=0, stdout="", stderr="")

    def _run(task_id: str) -> None:
        wt = tmp_path / task_id
        wt.mkdir()
        v = CoachValidator(
            str(wt),
            task_id=task_id,
            test_command=f"make test {task_id}",
            coach_test_execution="subprocess",
        )
        with patch.object(v, "_is_docker_available", return_value=True):
            v.run_independent_tests(
                task_work_results={},
                task={"requires_infrastructure": ["postgresql", "redis"]},
            )

    with patch("subprocess.run", side_effect=fake_run):
        threads = [threading.Thread(target=_run, args=(t,)) for t in ("TASK-A", "TASK-B")]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

    assert set(seen) == {"TASK-A", "TASK-B"}
    for task, env in seen.items():
        own_pg = ports[get_container_name("postgresql", fixture_owner(task))]
        own_redis = ports[get_container_name("redis", fixture_owner(task))]
        assert env["DATABASE_URL"].endswith(f":{own_pg}/test"), (task, env["DATABASE_URL"])
        assert env["REDIS_URL"].endswith(f":{own_redis}"), (task, env["REDIS_URL"])
    assert seen["TASK-A"]["DATABASE_URL"] != seen["TASK-B"]["DATABASE_URL"]
    assert dict(os.environ) == environ_before


def test_sdk_test_run_passes_paths_explicitly(tmp_path: Path, monkeypatch) -> None:
    """The SDK test run must not swap PYTHONPATH/PATH in the shared environment."""
    import asyncio

    monkeypatch.setenv("PYTHONPATH", "/pre-existing")
    environ_before = dict(os.environ)
    during: List[Dict[str, str]] = []

    class _Harness:
        supports_resume = False
        session_id = None

        async def invoke(self, prompt, role, tools, cwd, *, timeout_seconds):
            during.append(dict(os.environ))
            if False:  # pragma: no cover - makes this an async generator
                yield None

    captured: Dict[str, object] = {}

    def fake_select_harness(**kwargs):
        captured.update(kwargs)
        return _Harness()

    v = CoachValidator(str(tmp_path))
    with patch(
        "guardkit.orchestrator.quality_gates.coach_validator.select_harness",
        side_effect=fake_select_harness,
    ):
        asyncio.run(v._run_tests_via_sdk("pytest tests/"))

    assert during == [environ_before]
    env = captured["env"]
    assert env["PYTHONPATH"] == f"{tmp_path}:/pre-existing"


# ============================================================================
# 4. The Player's protocol names the task's own fixture
# ============================================================================


@pytest.mark.parametrize("multiplier", [1.0, 2.0])
def test_player_protocol_names_the_tasks_own_fixture(
    tmp_path: Path, monkeypatch, multiplier: float
) -> None:
    from guardkit.orchestrator.agent_invoker import AgentInvoker

    monkeypatch.setenv(RUN_OWNER_ENV, "build-prompt")
    invoker = AgentInvoker(worktree_path=tmp_path)
    invoker.timeout_multiplier = multiplier
    prompt = invoker._build_autobuild_implementation_prompt("TASK-PG-1")

    name = get_container_name("postgresql", fixture_owner("TASK-PG-1", role="player"))
    assert f"--name {name} " in prompt
    # The engine chooses the port; the recipe reads it back. No port is fixed.
    assert re.search(rf"--name {re.escape(name)} .*?-p 127\.0\.0\.1::5432 ", prompt)
    assert not re.search(r"-p 127\.0\.0\.1:\d+:", prompt)
    readback = f"$(docker port {name} 5432/tcp | head -n 1 | sed 's/.*://')"
    assert f"DATABASE_URL=postgresql://postgres:test@127.0.0.1:{readback}/test" in prompt
    assert f"--label {OWNER_LABEL}=build-prompt" in prompt
    assert not re.search(r"guardkit-test-(pg|redis|mongo)(?![-\w])", prompt)
    assert "5433" not in prompt and "6380" not in prompt and "27018" not in prompt
    assert "{infrastructure" not in prompt


def test_slim_protocol_renders_too(monkeypatch) -> None:
    from guardkit.orchestrator.prompts import load_protocol

    monkeypatch.setenv(RUN_OWNER_ENV, "build-slim")
    rendered = render_player_recipes(
        load_protocol("autobuild_execution_protocol_slim"), "TASK-S"
    )
    name = get_container_name("redis", fixture_owner("TASK-S", role="player"))
    assert name in rendered
    assert "-p 127.0.0.1::6379 " in rendered
    assert f"$(docker port {name} 6379/tcp | head -n 1 | sed 's/.*://')" in rendered
    assert not re.search(r"guardkit-test-(pg|redis|mongo)(?![-\w])", rendered)
    assert "{infrastructure" not in rendered


@needs_docker
def test_rendered_player_recipe_runs_and_exports_a_working_url(run_owner: str) -> None:
    """Run the Player's rendered redis recipe in a shell on the local engine."""
    rendered = render_player_recipes("{infrastructure_recipes}", "TASK-SH")
    block = re.search(r"#### Redis\n\n```bash\n(.*?)\n```", rendered, re.S)
    assert block, rendered
    script = block.group(1).replace(
        "docker run -d ",
        "docker run -d --label forge.test=concurrent-builds "
        f"--label forge.test-run={run_owner} ",
        1,
    )
    name = get_container_name("redis", fixture_owner("TASK-SH", role="player"))
    try:
        out = subprocess.run(
            ["bash", "-c", f"set -e\n{script}\necho \"URL=$REDIS_URL\""],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert out.returncode == 0, out.stderr
        url = re.search(r"^URL=(\S+)$", out.stdout, re.M).group(1)
        match = re.fullmatch(r"redis://127\.0\.0\.1:(\d+)", url)
        assert match, url
        assert _redis_answers(int(match.group(1)))
    finally:
        subprocess.run(["docker", "rm", "-f", "-v", name], capture_output=True)
    assert _container_ids(name) == []


# ============================================================================
# 5. The separate-session serve probe carries the owner marker
# ============================================================================


class TestServeProbeOwnerMarker:
    def test_owner_marker_copied_from_parent(self, tmp_path, monkeypatch) -> None:
        from guardkit.orchestrator.boot_smoke import _hermetic_env

        monkeypatch.setenv(RUN_OWNER_ENV, "build-probe")
        env = _hermetic_env(tmp_path, {RUN_OWNER_ENV: "project-chosen"})
        assert env[RUN_OWNER_ENV] == "build-probe"

    def test_project_cannot_invent_an_owner(self, tmp_path, monkeypatch) -> None:
        from guardkit.orchestrator.boot_smoke import _hermetic_env

        monkeypatch.delenv(RUN_OWNER_ENV, raising=False)
        env = _hermetic_env(tmp_path, {RUN_OWNER_ENV: "project-chosen"})
        assert RUN_OWNER_ENV not in env


# ============================================================================
# 6. The project's Coach model still decides with the new settings present
# ============================================================================


@pytest.mark.parametrize(
    "cli_coach, config_model, expected",
    [
        ("cli-coach", "config-coach", "cli-coach"),
        (None, "config-coach", "config-coach"),
        (None, None, None),  # None: Coach falls back to the general model
    ],
)
def test_coach_model_precedence_with_concurrency_settings(
    tmp_path: Path, monkeypatch, cli_coach, config_model, expected
) -> None:
    import yaml

    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    monkeypatch.setenv("GUARDKIT_MAX_PARALLEL_TASKS", "4")
    monkeypatch.setenv("GUARDKIT_WAVE_SAME_AREA", "sequence-on-declared-overlap")
    monkeypatch.setenv(RUN_OWNER_ENV, "build-model")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    if config_model:
        (tmp_path / ".guardkit").mkdir()
        (tmp_path / ".guardkit" / "config.yaml").write_text(
            yaml.safe_dump({"autobuild": {"coach": {"model": config_model}}})
        )
    ab = AutoBuildOrchestrator(
        repo_root=tmp_path, model="general-model", coach_model=cli_coach
    )
    assert ab._coach_model_name == expected
    assert ab._model_name == "general-model"
