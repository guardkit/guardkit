"""
Docker test fixture definitions for infrastructure-dependent tasks.

Single source of truth for Docker container recipes used by both the Player
(via execution protocol instructions) and Coach (via CoachValidator).

Every fixture belongs to one owner (factory concurrent-builds design,
2026-10-03). Two builds, or two tasks of one build, may start the same service
at the same moment on one container engine, so nothing here is fixed:

- The container is named ``guardkit-test-<service>-<owner>``, where the owner is
  the sanitised ``GUARDKIT_RUN_OWNER`` (Forge sets it to the build ID) plus the
  task ID — or a per-process random ID when GuardKit runs outside the factory.
  Starting a fixture removes only a container of that same name.
- The engine chooses the host port (``-p 127.0.0.1::5432``) and it is read
  back with ``docker port``: by the Coach in Python, and by the Player's
  recipe in the shell. The exported URLs use the real port.
- Containers carry the labels ``guardkit.fixture.owner`` (the run owner) and
  ``guardkit.fixture.task`` (the task ID), which Forge uses to remove a
  cancelled build's fixtures.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import shlex
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Union


# Container name prefix for test isolation
CONTAINER_PREFIX = "guardkit-test"

#: Set by Forge per build (the build ID). Names and labels this build's fixtures.
RUN_OWNER_ENV = "GUARDKIT_RUN_OWNER"
#: Label carrying the run owner (the raw ``GUARDKIT_RUN_OWNER`` or process ID).
OWNER_LABEL = "guardkit.fixture.owner"
#: Label carrying the task ID.
TASK_LABEL = "guardkit.fixture.task"
#: Host address fixture ports are published on.
BIND_HOST = "127.0.0.1"

# Docker fixture definitions: service name -> configuration.
# ``{name}`` in a readiness command is the owner's container name; ``{host}``
# and ``{port}`` in an export are the published address.
DOCKER_FIXTURES: Dict[str, Dict[str, object]] = {
    "postgresql": {
        "label": "PostgreSQL",
        "container_name": f"{CONTAINER_PREFIX}-pg",  # prefix; the owner is appended
        "image": "postgres:16-alpine",
        "container_port": 5432,
        "env_vars": {"POSTGRES_PASSWORD": "test"},
        "readiness_cmd": "docker exec {name} pg_isready",
        "readiness_type": "command",  # "command" = until loop, "sleep" = fixed wait
        "env_export": {"DATABASE_URL": "postgresql://postgres:test@{host}:{port}/test"},
    },
    "redis": {
        "label": "Redis",
        "container_name": f"{CONTAINER_PREFIX}-redis",
        "image": "redis:7-alpine",
        "container_port": 6379,
        "env_vars": {},
        "readiness_cmd": None,
        "readiness_type": "sleep",
        "readiness_sleep": 1,
        "env_export": {"REDIS_URL": "redis://{host}:{port}"},
    },
    "mongodb": {
        "label": "MongoDB",
        "container_name": f"{CONTAINER_PREFIX}-mongo",
        "image": "mongo:7",
        "container_port": 27017,
        "env_vars": {},
        "readiness_cmd": None,
        "readiness_type": "sleep",
        "readiness_sleep": 2,
        "env_export": {"MONGODB_URL": "mongodb://{host}:{port}"},
    },
}

_PROCESS_OWNER_ID = f"local-{secrets.token_hex(4)}"
_MAX_SUFFIX = 60


def process_owner_id() -> str:
    """The random owner ID this process uses when ``GUARDKIT_RUN_OWNER`` is unset."""
    return _PROCESS_OWNER_ID


def _sanitise(value: str) -> str:
    """Lower-case a value into characters a container name accepts."""
    cleaned = re.sub(r"[^a-z0-9_.-]+", "-", value.lower()).strip("-_.")
    return cleaned or "x"


@dataclass(frozen=True)
class FixtureOwner:
    """Who a fixture belongs to: the run, the task and (for the Player) the role.

    ``owner`` and ``task_id`` are the label values; ``suffix`` is the sanitised
    form appended to container names. The Coach and the Player of one task use
    different roles so they never share a container.
    """

    owner: str
    task_id: str = ""
    role: str = ""

    @property
    def suffix(self) -> str:
        parts = [self.owner, self.task_id, self.role]
        suffix = _sanitise("-".join(p for p in parts if p))
        if len(suffix) > _MAX_SUFFIX:
            digest = hashlib.sha256(suffix.encode()).hexdigest()[:8]
            suffix = f"{suffix[: _MAX_SUFFIX - 9].rstrip('-_.')}-{digest}"
        return suffix


def fixture_owner(
    task_id: Optional[str] = None,
    *,
    role: str = "",
    environ: Optional[Mapping[str, str]] = None,
) -> FixtureOwner:
    """The owner for a task's fixtures: ``GUARDKIT_RUN_OWNER`` or this process."""
    env = os.environ if environ is None else environ
    run_owner = (env.get(RUN_OWNER_ENV) or "").strip() or _PROCESS_OWNER_ID
    return FixtureOwner(owner=run_owner, task_id=task_id or "", role=role)


def _fixture(service: str) -> Dict[str, object]:
    return DOCKER_FIXTURES[service.lower()]


def get_start_commands(
    service: str,
    owner: Optional[FixtureOwner] = None,
    *,
    extra_labels: Optional[Mapping[str, str]] = None,
) -> List[str]:
    """Return the shell commands to start this owner's container for a service.

    Args:
        service: Infrastructure service name (e.g., "postgresql", "redis", "mongodb")
        owner: The fixture's owner; defaults to :func:`fixture_owner` with no task.
            The engine chooses the loopback host port; read it back with
            :func:`get_port_command`.
        extra_labels: Further labels to set (used by tests to mark disposables).

    Returns:
        List of shell command strings to execute in order.

    Raises:
        KeyError: If service is not a known fixture.
    """
    fixture = _fixture(service)
    owner = owner or fixture_owner()
    container = get_container_name(service, owner)
    publish = f"{BIND_HOST}::{fixture['container_port']}"

    commands: List[str] = []

    # Remove this owner's own disposable fixture and its anonymous volumes
    # before reuse. Docker preserves explicitly named volumes even with -v.
    commands.append(f"docker rm -f -v {container} 2>/dev/null || true")

    labels = {OWNER_LABEL: owner.owner, TASK_LABEL: owner.task_id}
    labels.update(extra_labels or {})
    label_flags = " ".join(
        f"--label {shlex.quote(f'{k}={v}')}" for k, v in labels.items()
    )
    env_flags = " ".join(f"-e {k}={v}" for k, v in fixture["env_vars"].items())
    run_cmd = f"docker run -d --name {container} {label_flags}"
    if env_flags:
        run_cmd += f" {env_flags}"
    run_cmd += f" -p {publish} {fixture['image']}"
    commands.append(run_cmd)

    # Readiness check
    if fixture["readiness_type"] == "command" and fixture.get("readiness_cmd"):
        ready = str(fixture["readiness_cmd"]).format(name=container)
        commands.append(f"until {ready}; do sleep 1; done")
    elif fixture["readiness_type"] == "sleep":
        commands.append(f'sleep {fixture.get("readiness_sleep", 2)}')

    return commands


def get_container_name(service: str, owner: Optional[FixtureOwner] = None) -> str:
    """Return this owner's Docker container name for the given service.

    Raises:
        KeyError: If service is not a known fixture.
    """
    owner = owner or fixture_owner()
    return f"{_fixture(service)['container_name']}-{owner.suffix}"


def get_port_command(service: str, owner: Optional[FixtureOwner] = None) -> List[str]:
    """Argv that prints the host address the engine published the service on."""
    fixture = _fixture(service)
    return [
        "docker",
        "port",
        get_container_name(service, owner),
        f"{fixture['container_port']}/tcp",
    ]


def parse_port_output(output: str) -> Optional[int]:
    """Read the host port from ``docker port`` output (``127.0.0.1:49153``)."""
    if not isinstance(output, str):
        return None
    for line in output.splitlines():
        match = re.search(r":(\d+)\s*$", line.strip())
        if match:
            return int(match.group(1))
    return None


def get_env_exports(
    service: str,
    consumer_context: Optional[Dict] = None,
    *,
    host_port: Union[int, str],
) -> Dict[str, str]:
    """Return environment variables to export after starting the service.

    When ``consumer_context`` is provided, each key that has a matching entry
    in the returned dict is passed through the adapter's ``adapt_url()`` method.
    This allows consumers to upgrade a base URL (e.g. ``postgresql://``) to a
    driver-specific scheme (e.g. ``postgresql+asyncpg://``) without baking
    driver knowledge into the fixture definitions.

    Args:
        service: Infrastructure service name (e.g., "postgresql")
        consumer_context: Optional mapping of env-var names to adapter objects.
            Each adapter must expose an ``adapt_url(base_url: str) -> str``
            method.  Keys not present in the returned exports are silently
            ignored.
        host_port: The port the container is really published on, or a shell
            expression that prints it (the Player's recipe).

    Returns:
        Dict mapping env var names to values.

    Raises:
        KeyError: If service is not a known fixture.
    """
    templates = _fixture(service)["env_export"]
    exports = {
        key: str(value).format(host=BIND_HOST, port=host_port)
        for key, value in templates.items()
    }
    if consumer_context:
        for key, adapter in consumer_context.items():
            if key in exports:
                exports[key] = adapter.adapt_url(exports[key])
    return exports


def is_known_service(service: str) -> bool:
    """Check if the service name is a known Docker fixture."""
    return service.lower() in DOCKER_FIXTURES


# Placeholders in autobuild_execution_protocol*.md, filled per task.
RECIPES_PLACEHOLDER = "{infrastructure_recipes}"
BRIEF_RECIPES_PLACEHOLDER = "{infrastructure_recipes_brief}"
CLEANUP_PLACEHOLDER = "{infrastructure_cleanup}"


def render_player_recipes(
    protocol_content: str,
    task_id: str,
    *,
    environ: Optional[Mapping[str, str]] = None,
) -> str:
    """Fill the protocol's fixture placeholders with this task's own recipes.

    The Player's containers are named for the run, the task and the ``player``
    role. As for the Coach, the engine chooses the host port; the recipe reads
    it back with ``docker port`` when the URL is exported, so the commands can
    be run as written and no port is guessed in advance. Content without the
    placeholders is returned unchanged.
    """
    placeholders = (RECIPES_PLACEHOLDER, BRIEF_RECIPES_PLACEHOLDER, CLEANUP_PLACEHOLDER)
    if not any(p in protocol_content for p in placeholders):
        return protocol_content

    owner = fixture_owner(task_id, role="player", environ=environ)
    sections: List[str] = []
    bullets: List[str] = []
    names: List[str] = []
    for service, fixture in DOCKER_FIXTURES.items():
        commands = get_start_commands(service, owner)
        port = f"$({' '.join(get_port_command(service, owner))} | head -n 1 | sed 's/.*://')"
        exports = get_env_exports(service, host_port=port)
        export_lines = [f"export {k}={v}" for k, v in exports.items()]
        names.append(get_container_name(service, owner))
        body = "\n".join(commands + export_lines)
        sections.append(f"#### {fixture['label']}\n\n```bash\n{body}\n```")
        bullets.append(
            f"- {fixture['label']}: `{commands[1]}` then "
            + ", ".join(f"`{line}`" for line in export_lines)
        )
    cleanup = f"docker rm -f -v {' '.join(names)} 2>/dev/null || true"

    return (
        protocol_content.replace(RECIPES_PLACEHOLDER, "\n\n".join(sections))
        .replace(BRIEF_RECIPES_PLACEHOLDER, "\n".join(bullets))
        .replace(CLEANUP_PLACEHOLDER, cleanup)
    )
