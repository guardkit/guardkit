"""The deployment kit's scripts, driven the way the factory drives them.

Each test installs the kit into a temporary project with
``install_deploy_kit`` and runs ``deploy/deploy.sh``, ``deploy/healthcheck.sh``
or ``deploy/live-gate.sh`` with exactly the settings the factory (Forge) sends
that step, against a fake ``docker`` and a fake ``curl`` on ``PATH`` that
record every call and keep a small model of compose projects, containers,
labels and images.

What Forge sends each step (Forge src/forge/deploy/stage.py,
runbook_builder.py, executor/shell_steps.py, pipeline/merge_executor.py):
candidate ``CANDIDATE=1`` + candidate.env + ``DEPLOY_IDENTITY``; candidate down
``CANDIDATE_DOWN=1`` + candidate.env + ``DEPLOY_IDENTITY``; promote ``PROMOTE=1``
+ ``DEPLOY_IDENTITY`` + ``DEPLOY_ARTIFACT``; the read-only question
``RUNNING_IDENTITY=1``; health checks candidate.env (candidate) or nothing
(after a promote).

The last test runs the kit for real against Docker on this machine, and only
when ``GUARDKIT_DEPLOY_KIT_REAL=1`` is set.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from guardkit.templates.deploy_kit import install_deploy_kit

ENV_ID = "demo"
LIVE_PORT = 18961
CANDIDATE_PORT = 18962
IDENTITY = "j-abc123def456@0123456789abcdef"
OTHER_IDENTITY = "j-fedcba987654@fedcba9876543210"
CANDIDATE_ENV = {
    "CANDIDATE_PORT": str(CANDIDATE_PORT),
    "COMPOSE_PROJECT_NAME": f"{ENV_ID}-cand",
}

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")

# A fake docker: a JSON state file models containers (by compose project),
# their identity labels and images, and image tags. Every call is logged.
FAKE_DOCKER = r'''
import hashlib, json, os, re, sys

state_path = os.environ["FAKE_STATE"]
with open(os.environ["FAKE_LOG"], "a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\n")
try:
    with open(state_path) as fh:
        state = json.load(fh)
except FileNotFoundError:
    state = {"containers": [], "tags": {}, "images": []}

def save():
    with open(state_path, "w") as fh:
        json.dump(state, fh)

if os.environ.get("FAKE_DOCKER_DOWN") == "1":
    print("Cannot connect to the Docker daemon", file=sys.stderr)
    sys.exit(1)

args = sys.argv[1:]
LABEL = "guardkit.deploy.identity"

def resolve(ref):
    if ref.startswith("sha256:"):
        return ref if ref in state["images"] else None
    return state["tags"].get(ref)

if args[:1] == ["compose"]:
    rest = args[1:]
    if rest == ["version"]:
        print("Docker Compose version fake"); sys.exit(0)
    project, files = None, []
    while rest and rest[0].startswith("-"):
        opt, val = rest[0], rest[1]
        if opt == "--project-name": project = val
        if opt == "-f": files.append(val)
        rest = rest[2:]
    sub, opts = rest[0], rest[1:]
    services = os.environ.get("FAKE_SERVICES", "web").split()
    if sub == "config" and opts == ["--services"]:
        if not os.environ.get("APP_PORT"):
            print("required variable APP_PORT is missing a value", file=sys.stderr); sys.exit(1)
        print("\n".join(reversed(services))); sys.exit(0)
    if sub == "build":
        sys.exit(0)
    if sub == "up":
        if os.environ.get("FAKE_UP_FAIL") == "1":
            print("container failed to start", file=sys.stderr); sys.exit(1)
        labels, images, current = {}, {}, None
        for path in files[1:]:
            for line in open(path):
                m = re.match(r"^  ([A-Za-z0-9._-]+):$", line)
                if m: current = m.group(1)
                m = re.match(r'^      ' + re.escape(LABEL) + r': "(.*)"$', line)
                if m: labels[current] = m.group(1)
                m = re.match(r'^    image: "(.*)"$', line)
                if m: images[current] = m.group(1)
        state["containers"] = [c for c in state["containers"] if c["project"] != project]
        for svc in services:
            if svc in images:
                image = resolve(images[svc])
                if image is None:
                    print("no such image " + images[svc], file=sys.stderr); sys.exit(1)
            else:
                image = "sha256:" + hashlib.sha256((svc + labels.get(svc, "")).encode()).hexdigest()
                if image not in state["images"]:
                    state["images"].append(image)
            state["containers"].append({"id": f"{project}-{svc}-1", "project": project,
                                        "service": svc, "label": labels.get(svc, ""),
                                        "image": image})
        save(); sys.exit(0)
    if sub == "ps":
        svc = opts[-1]
        for c in state["containers"]:
            if c["project"] == project and c["service"] == svc:
                print(c["id"])
        sys.exit(0)
    if sub == "down":
        state["containers"] = [c for c in state["containers"] if c["project"] != project]
        save(); sys.exit(0)
    print("fake docker: unexpected compose call", args, file=sys.stderr); sys.exit(2)

if args[:1] == ["ps"]:
    prefix = "label=com.docker.compose.project="
    project = next(a[len(prefix):] for a in args if a.startswith(prefix))
    for c in state["containers"]:
        if c["project"] == project:
            print("c:" + c["label"])
    sys.exit(0)
if args[:1] == ["inspect"]:
    cid = args[-1]
    for c in state["containers"]:
        if c["id"] == cid:
            print(c["image"]); sys.exit(0)
    sys.exit(1)
if args[:2] == ["image", "inspect"]:
    sys.exit(0 if resolve(args[2]) else 1)
if args[:1] == ["tag"]:
    image = resolve(args[1])
    if image is None:
        sys.exit(1)
    state["tags"][args[2]] = image
    save(); sys.exit(0)
print("fake docker: unexpected call", args, file=sys.stderr)
sys.exit(2)
'''

FAKE_CURL = r'''
import os, sys
with open(os.environ["FAKE_CURL_LOG"], "a") as log:
    log.write(sys.argv[-1] + "\n")
sys.stdout.write(os.environ.get("FAKE_CURL_CODE", "200"))
'''


class Kit:
    """A temporary project with the kit installed and fake tools on PATH."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.project = root / "project"
        self.project.mkdir()
        (self.project / "compose.yaml").write_text("services: {}\n")
        install_deploy_kit(
            self.project,
            env_id=ENV_ID,
            live_port=LIVE_PORT,
            candidate_port=CANDIDATE_PORT,
            health_path="/health",
        )
        self.bin = root / "bin"
        self.bin.mkdir()
        for name, body in (("docker", FAKE_DOCKER), ("curl", FAKE_CURL)):
            tool = self.bin / name
            tool.write_text(f"#!{sys.executable}\n{body}")
            tool.chmod(0o755)
        self.state = root / "state.json"
        self.log = root / "docker.log"
        self.curl_log = root / "curl.log"
        self.tmp = root / "tmp"
        self.tmp.mkdir()

    def run(self, script: str, env: dict[str, str] | None = None, args: tuple[str, ...] = ()):
        # Built from nothing, as Forge builds a project program's environment.
        base = {
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "HOME": str(self.tmp),
            "TMPDIR": str(self.tmp),
            "FAKE_STATE": str(self.state),
            "FAKE_LOG": str(self.log),
            "FAKE_CURL_LOG": str(self.curl_log),
            "DEPLOY_HEALTH_WAIT_SECONDS": "0",
            "DEPLOY_GATE_WAIT_SECONDS": "0",
        }
        base.update(env or {})
        return subprocess.run(
            [str(self.project / "deploy" / script), *args],
            cwd=self.project,
            env=base,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def calls(self) -> list[list[str]]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def compose_calls(self, sub: str) -> list[list[str]]:
        out = []
        for call in self.calls():
            if call[:1] == ["compose"] and sub in call:
                out.append(call)
        return out

    def containers(self) -> list[dict]:
        if not self.state.exists():
            return []
        return json.loads(self.state.read_text())["containers"]

    def candidate(self, identity: str = IDENTITY):
        return self.run("deploy.sh", {"CANDIDATE": "1", **CANDIDATE_ENV, "DEPLOY_IDENTITY": identity})


def _line(stdout: str, marker: str) -> str | None:
    """The value of the last ``<marker>=`` line, as Forge reads it."""
    found = None
    for line in stdout.splitlines():
        if line.startswith(marker + "="):
            found = line[len(marker) + 1 :]
    return found


@pytest.fixture()
def kit(tmp_path: Path) -> Kit:
    return Kit(tmp_path)


# --- Mode selection ------------------------------------------------------------------


def test_no_signal_is_refused_without_touching_docker(kit: Kit) -> None:
    done = kit.run("deploy.sh")
    assert done.returncode != 0
    assert "no deploy mode is set" in done.stderr
    assert kit.calls() == []


@pytest.mark.parametrize(
    "signals",
    [
        {"CANDIDATE": "1", "PROMOTE": "1"},
        {"CANDIDATE_DOWN": "1", "RUNNING_IDENTITY": "1"},
        {"PROMOTE": "1", "REVERT": "1"},
    ],
)
def test_two_signals_are_refused(kit: Kit, signals: dict[str, str]) -> None:
    done = kit.run("deploy.sh", {**signals, "DEPLOY_IDENTITY": IDENTITY})
    assert done.returncode != 0
    assert "more than one deploy mode" in done.stderr
    assert kit.calls() == []


def test_revert_is_refused(kit: Kit) -> None:
    done = kit.run("deploy.sh", {"REVERT": "1", "ROLLBACK_IMAGE_REF": "x:rollback"})
    assert done.returncode != 0
    assert "keeps no rollback image" in done.stderr
    assert kit.calls() == []


def test_preview_is_refused(kit: Kit) -> None:
    done = kit.run("deploy.sh", {"PREVIEW": "1", "COMPOSE_PROJECT_NAME": "demo-pv0"})
    assert done.returncode != 0
    assert "no review preview" in done.stderr


# --- What is running -----------------------------------------------------------------


def test_running_identity_says_none_when_nothing_runs(kit: Kit) -> None:
    done = kit.run("deploy.sh", {"RUNNING_IDENTITY": "1"})
    assert done.returncode == 0, done.stderr
    assert _line(done.stdout, "RUNNING_IDENTITY") == "none"
    # Read-only: one container listing of the live project, nothing else.
    assert kit.calls() == [
        ["ps", "-a", "--filter", f"label=com.docker.compose.project={ENV_ID}-live",
         "--format", 'c:{{.Label "guardkit.deploy.identity"}}']
    ]


def test_running_identity_unknown_when_docker_cannot_be_asked(kit: Kit) -> None:
    done = kit.run("deploy.sh", {"RUNNING_IDENTITY": "1", "FAKE_DOCKER_DOWN": "1"})
    assert done.returncode == 0
    assert _line(done.stdout, "RUNNING_IDENTITY") is None
    assert _line(done.stdout, "RUNNING_IDENTITY_UNKNOWN")


def test_running_identity_unknown_when_labels_disagree(kit: Kit) -> None:
    kit.state.write_text(json.dumps({"tags": {}, "images": [], "containers": [
        {"id": "a", "project": f"{ENV_ID}-live", "service": "web", "label": IDENTITY, "image": "x"},
        {"id": "b", "project": f"{ENV_ID}-live", "service": "db", "label": OTHER_IDENTITY, "image": "y"},
    ]}))
    done = kit.run("deploy.sh", {"RUNNING_IDENTITY": "1"})
    assert done.returncode == 0
    assert "different identities" in _line(done.stdout, "RUNNING_IDENTITY_UNKNOWN")


# --- Candidate check ----------------------------------------------------------------


def test_candidate_builds_labels_and_reports(kit: Kit) -> None:
    done = kit.run(
        "deploy.sh",
        {"CANDIDATE": "1", **CANDIDATE_ENV, "DEPLOY_IDENTITY": IDENTITY, "FAKE_SERVICES": "web db"},
    )
    assert done.returncode == 0, done.stderr
    artifact = _line(done.stdout, "CHECKED_ARTIFACT")
    assert artifact is not None
    parts = artifact.split(",")
    assert [p.split("=")[0] for p in parts] == ["db", "web"]
    assert all(p.split("=", 1)[1].startswith("sha256:") for p in parts)
    assert _line(done.stdout, "DEPLOYED_IDENTITY") == IDENTITY
    # Only the candidate project was touched, and it carries the identity.
    for call in kit.compose_calls("up"):
        assert call[call.index("--project-name") + 1] == f"{ENV_ID}-cand"
        assert "--wait" in call
    assert {c["project"] for c in kit.containers()} == {f"{ENV_ID}-cand"}
    assert {c["label"] for c in kit.containers()} == {IDENTITY}
    # Each checked image is kept under a name made from the identity.
    tags = json.loads(kit.state.read_text())["tags"]
    assert set(tags) == {
        f"{ENV_ID}-deploy-web:j-abc123def456-0123456789abcdef",
        f"{ENV_ID}-deploy-db:j-abc123def456-0123456789abcdef",
    }
    assert not any(f"{ENV_ID}-live" in " ".join(call) for call in kit.calls())


@pytest.mark.parametrize(
    "env, words",
    [
        ({"CANDIDATE": "1", "COMPOSE_PROJECT_NAME": f"{ENV_ID}-cand", "DEPLOY_IDENTITY": IDENTITY},
         "needs CANDIDATE_PORT"),
        ({"CANDIDATE": "1", **CANDIDATE_ENV}, "needs DEPLOY_IDENTITY"),
        ({"CANDIDATE": "1", "CANDIDATE_PORT": "18962", "COMPOSE_PROJECT_NAME": f"{ENV_ID}-live",
          "DEPLOY_IDENTITY": IDENTITY}, "refuses to act on the live project"),
        ({"CANDIDATE": "1", **CANDIDATE_ENV, "DEPLOY_IDENTITY": "bad identity!"}, "DEPLOY_IDENTITY must be"),
    ],
)
def test_candidate_refusals(kit: Kit, env: dict[str, str], words: str) -> None:
    done = kit.run("deploy.sh", env)
    assert done.returncode != 0
    assert words in done.stderr
    assert kit.compose_calls("up") == []


def test_candidate_that_fails_to_start_reports_nothing(kit: Kit) -> None:
    done = kit.run("deploy.sh", {"CANDIDATE": "1", **CANDIDATE_ENV, "DEPLOY_IDENTITY": IDENTITY,
                                 "FAKE_UP_FAIL": "1"})
    assert done.returncode != 0
    assert _line(done.stdout, "CHECKED_ARTIFACT") is None
    assert _line(done.stdout, "DEPLOYED_IDENTITY") is None


# --- Promote ------------------------------------------------------------------------


def test_promote_runs_exactly_the_checked_images_as_live(kit: Kit) -> None:
    artifact = _line(kit.candidate().stdout, "CHECKED_ARTIFACT")
    done = kit.run("deploy.sh", {"PROMOTE": "1", "DEPLOY_IDENTITY": IDENTITY, "DEPLOY_ARTIFACT": artifact})
    assert done.returncode == 0, done.stderr
    assert _line(done.stdout, "DEPLOYED_IDENTITY") == IDENTITY
    assert _line(done.stdout, "CHECKED_ARTIFACT") is None
    live_up = [c for c in kit.compose_calls("up") if f"{ENV_ID}-live" in c]
    assert len(live_up) == 1
    assert "--no-build" in live_up[0] and ["--pull", "never"] == live_up[0][live_up[0].index("--pull"):][:2]
    assert not [c for c in kit.compose_calls("build") if f"{ENV_ID}-live" in c]
    live = [c for c in kit.containers() if c["project"] == f"{ENV_ID}-live"]
    assert [c["image"] for c in live] == [artifact.split("=", 1)[1]]
    # The read-only question now names it.
    asked = kit.run("deploy.sh", {"RUNNING_IDENTITY": "1"})
    assert _line(asked.stdout, "RUNNING_IDENTITY") == IDENTITY


@pytest.mark.parametrize(
    "artifact, words",
    [
        ("", "needs DEPLOY_ARTIFACT"),
        ("web=latest", "needs DEPLOY_ARTIFACT"),
        ("web=sha256:" + "0" * 64, "is not on this machine"),
        ("api=sha256:" + "0" * 64, "compose.yaml has"),
    ],
)
def test_promote_refusals(kit: Kit, artifact: str, words: str) -> None:
    done = kit.run("deploy.sh", {"PROMOTE": "1", "DEPLOY_IDENTITY": IDENTITY, "DEPLOY_ARTIFACT": artifact})
    assert done.returncode != 0
    assert words in done.stderr
    assert kit.compose_calls("up") == []


def test_promote_refuses_another_project(kit: Kit) -> None:
    done = kit.run("deploy.sh", {"PROMOTE": "1", "DEPLOY_IDENTITY": IDENTITY,
                                 "DEPLOY_ARTIFACT": "web=sha256:" + "0" * 64,
                                 "COMPOSE_PROJECT_NAME": f"{ENV_ID}-cand"})
    assert done.returncode != 0
    assert "deploys the live project" in done.stderr


# --- Candidate down -----------------------------------------------------------------


def test_candidate_down_removes_only_the_candidate(kit: Kit) -> None:
    artifact = _line(kit.candidate().stdout, "CHECKED_ARTIFACT")
    kit.run("deploy.sh", {"PROMOTE": "1", "DEPLOY_IDENTITY": IDENTITY, "DEPLOY_ARTIFACT": artifact})
    done = kit.run("deploy.sh", {"CANDIDATE_DOWN": "1", **CANDIDATE_ENV, "DEPLOY_IDENTITY": IDENTITY})
    assert done.returncode == 0, done.stderr
    downs = kit.compose_calls("down")
    assert len(downs) == 1
    assert downs[0][downs[0].index("--project-name") + 1] == f"{ENV_ID}-cand"
    assert "--volumes" in downs[0]
    assert {c["project"] for c in kit.containers()} == {f"{ENV_ID}-live"}


def test_candidate_down_leaves_another_builds_candidate(kit: Kit) -> None:
    kit.candidate(OTHER_IDENTITY)
    done = kit.run("deploy.sh", {"CANDIDATE_DOWN": "1", **CANDIDATE_ENV, "DEPLOY_IDENTITY": IDENTITY})
    assert done.returncode != 0
    assert "leaving it for its own build" in done.stderr
    assert kit.compose_calls("down") == []
    assert {c["label"] for c in kit.containers()} == {OTHER_IDENTITY}


def test_candidate_down_with_nothing_standing_succeeds(kit: Kit) -> None:
    done = kit.run("deploy.sh", {"CANDIDATE_DOWN": "1", **CANDIDATE_ENV, "DEPLOY_IDENTITY": IDENTITY})
    assert done.returncode == 0, done.stderr


def test_candidate_down_never_names_the_live_project(kit: Kit) -> None:
    done = kit.run("deploy.sh", {"CANDIDATE_DOWN": "1", "COMPOSE_PROJECT_NAME": f"{ENV_ID}-live",
                                 "DEPLOY_IDENTITY": IDENTITY})
    assert done.returncode != 0
    assert "refuses to act on the live project" in done.stderr
    assert kit.compose_calls("down") == []


# --- Health check and live gate -----------------------------------------------------


def test_healthcheck_targets_the_candidate_with_candidate_env(kit: Kit) -> None:
    kit.candidate()
    done = kit.run("healthcheck.sh", CANDIDATE_ENV)
    assert done.returncode == 0, done.stderr
    assert kit.curl_log.read_text().splitlines() == [f"http://127.0.0.1:{CANDIDATE_PORT}/health"]


def test_healthcheck_targets_live_after_promote(kit: Kit) -> None:
    artifact = _line(kit.candidate().stdout, "CHECKED_ARTIFACT")
    kit.run("deploy.sh", {"PROMOTE": "1", "DEPLOY_IDENTITY": IDENTITY, "DEPLOY_ARTIFACT": artifact})
    done = kit.run("healthcheck.sh")
    assert done.returncode == 0, done.stderr
    assert kit.curl_log.read_text().splitlines()[-1] == f"http://127.0.0.1:{LIVE_PORT}/health"
    assert IDENTITY in done.stdout


def test_healthcheck_fails_on_non_200(kit: Kit) -> None:
    kit.candidate()
    done = kit.run("healthcheck.sh", {**CANDIDATE_ENV, "FAKE_CURL_CODE": "503"})
    assert done.returncode != 0
    assert "HTTP 503" in done.stderr


def test_healthcheck_fails_when_nothing_is_deployed(kit: Kit) -> None:
    done = kit.run("healthcheck.sh")
    assert done.returncode != 0
    assert "no container" in done.stderr


def test_healthcheck_checks_expected_identity_when_given(kit: Kit) -> None:
    kit.candidate()
    done = kit.run("healthcheck.sh", {**CANDIDATE_ENV, "DEPLOY_IDENTITY": OTHER_IDENTITY})
    assert done.returncode != 0
    assert f"not {OTHER_IDENTITY}" in done.stderr


def test_live_gate_passes_with_an_envelope(kit: Kit) -> None:
    kit.candidate()
    done = kit.run("live-gate.sh", CANDIDATE_ENV, args=("--feature", "F1", "--target", ENV_ID))
    assert done.returncode == 0, done.stderr
    envelope = json.loads(done.stdout)  # Forge reads the whole stdout as JSON
    assert envelope["verdict"] == "pass"
    assert envelope["gates"][0]["gate_id"] == "deploy-kit-health"
    assert envelope["run_id"].startswith("F1-")


@pytest.mark.parametrize(
    "env, verdict, code",
    [
        ({"FAKE_CURL_CODE": "500"}, "fail", 1),
        ({"FAKE_DOCKER_DOWN": "1"}, "environment_fail", 4),
    ],
)
def test_live_gate_failures_map_to_forge_exit_codes(kit: Kit, env, verdict, code) -> None:
    kit.candidate()
    done = kit.run("live-gate.sh", {**CANDIDATE_ENV, **env}, args=("--feature", "F1", "--target", ENV_ID))
    assert done.returncode == code
    assert json.loads(done.stdout)["verdict"] == verdict


def test_live_gate_preview_is_an_instrument_failure(kit: Kit) -> None:
    done = kit.run("live-gate.sh", {"FACTORY_PREVIEW_PORT": "8950"}, args=("--feature", "F1", "--target", ENV_ID))
    assert done.returncode == 3
    assert json.loads(done.stdout)["verdict"] == "instrument_fail"


def test_installed_scripts_pass_shellcheck(kit: Kit) -> None:
    if shutil.which("shellcheck") is None:
        pytest.skip("shellcheck is not installed")
    done = subprocess.run(
        ["shellcheck", "-x", "deploy/deploy.sh", "deploy/healthcheck.sh", "deploy/live-gate.sh",
         "deploy/lib.sh", "deploy/settings.sh"],
        cwd=kit.project, capture_output=True, text=True,
    )
    assert done.returncode == 0, done.stdout + done.stderr


# --- The real thing -----------------------------------------------------------------

REAL_ENV_ID = "gkdk-e2e"
REAL_IMAGE = "busybox:1.36"


def _port_free(port: int) -> bool:
    with socket.socket() as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0


@pytest.mark.skipif(
    os.environ.get("GUARDKIT_DEPLOY_KIT_REAL") != "1",
    reason="real Docker run; set GUARDKIT_DEPLOY_KIT_REAL=1 to run it",
)
def test_real_candidate_promote_cycle(tmp_path: Path) -> None:
    """Candidate up, health, gate, promote, running identity, candidate down.

    Uses a base image already on the machine (never pulls), unused high ports
    and its own compose project names, and removes only what it created.
    """
    if shutil.which("docker") is None:
        pytest.skip("docker is not installed")
    if subprocess.run(["docker", "image", "inspect", REAL_IMAGE], capture_output=True).returncode != 0:
        pytest.skip(f"{REAL_IMAGE} is not on this machine (this test never pulls)")
    for port in (LIVE_PORT, CANDIDATE_PORT):
        if not _port_free(port):
            pytest.skip(f"port {port} is in use")

    project = tmp_path / "project"
    (project / "web").mkdir(parents=True)
    (project / "web" / "Dockerfile").write_text(
        f"FROM {REAL_IMAGE}\n"
        "RUN mkdir -p /www && echo ok > /www/health\n"
        'CMD ["httpd", "-f", "-p", "8080", "-h", "/www"]\n'
    )
    (project / "compose.yaml").write_text(
        "services:\n"
        "  web:\n"
        "    build: ./web\n"
        "    labels:\n"
        '      - "example.owner=deploy-kit-test"\n'
        "    ports:\n"
        '      - "127.0.0.1:${APP_PORT:?APP_PORT is required}:8080"\n'
    )
    install_deploy_kit(project, env_id=REAL_ENV_ID, live_port=LIVE_PORT,
                       candidate_port=CANDIDATE_PORT, health_path="/health")
    home = tmp_path / "home"
    home.mkdir()
    base = {"PATH": os.environ["PATH"], "HOME": str(home), "TMPDIR": str(home)}
    for name in ("DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_CONFIG"):
        if name in os.environ:
            base[name] = os.environ[name]
    cand_env = {"CANDIDATE_PORT": str(CANDIDATE_PORT), "COMPOSE_PROJECT_NAME": f"{REAL_ENV_ID}-cand"}

    def run(script: str, env: dict[str, str], *args: str) -> subprocess.CompletedProcess:
        done = subprocess.run([str(project / "deploy" / script), *args], cwd=project,
                              env={**base, **env}, capture_output=True, text=True, timeout=300)
        print(f"--- {script} {sorted(env)} -> {done.returncode}\n{done.stdout}{done.stderr[-1500:]}")
        return done

    try:
        asked = run("deploy.sh", {"RUNNING_IDENTITY": "1"})
        assert _line(asked.stdout, "RUNNING_IDENTITY") == "none"

        cand = run("deploy.sh", {"CANDIDATE": "1", **cand_env, "DEPLOY_IDENTITY": IDENTITY})
        assert cand.returncode == 0
        artifact = _line(cand.stdout, "CHECKED_ARTIFACT")
        assert artifact and artifact.startswith("web=sha256:")
        assert _line(cand.stdout, "DEPLOYED_IDENTITY") == IDENTITY
        assert run("healthcheck.sh", cand_env).returncode == 0
        gate = run("live-gate.sh", cand_env, "--feature", "F1", "--target", REAL_ENV_ID)
        assert gate.returncode == 0 and json.loads(gate.stdout)["verdict"] == "pass"

        promoted = run("deploy.sh", {"PROMOTE": "1", "DEPLOY_IDENTITY": IDENTITY, "DEPLOY_ARTIFACT": artifact})
        assert promoted.returncode == 0
        assert _line(promoted.stdout, "DEPLOYED_IDENTITY") == IDENTITY

        down = run("deploy.sh", {"CANDIDATE_DOWN": "1", **cand_env, "DEPLOY_IDENTITY": IDENTITY})
        assert down.returncode == 0
        left = subprocess.run(["docker", "ps", "-a", "-q", "--filter",
                               f"label=com.docker.compose.project={REAL_ENV_ID}-cand"],
                              capture_output=True, text=True)
        assert left.stdout.strip() == ""

        asked = run("deploy.sh", {"RUNNING_IDENTITY": "1"})
        assert _line(asked.stdout, "RUNNING_IDENTITY") == IDENTITY
        assert run("healthcheck.sh", {}).returncode == 0
        gate = run("live-gate.sh", {}, "--feature", "F1", "--target", REAL_ENV_ID)
        assert gate.returncode == 0 and json.loads(gate.stdout)["verdict"] == "pass"
    finally:
        for name, port in ((f"{REAL_ENV_ID}-cand", CANDIDATE_PORT), (f"{REAL_ENV_ID}-live", LIVE_PORT)):
            subprocess.run(["docker", "compose", "--project-name", name, "-f", str(project / "compose.yaml"),
                            "down", "--volumes", "--remove-orphans", "--timeout", "5"],
                           cwd=project, env={**os.environ, "APP_PORT": str(port)}, capture_output=True)
        tag = IDENTITY.replace("@", "-")
        subprocess.run(["docker", "image", "rm", f"{REAL_ENV_ID}-deploy-web:{tag}",
                        f"{REAL_ENV_ID}-cand-web"], capture_output=True)
