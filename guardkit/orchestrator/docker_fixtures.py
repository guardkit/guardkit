"""
Docker test fixture definitions for infrastructure-dependent tasks.

Single source of truth for Docker container recipes used by both the Player
(via execution protocol instructions) and Coach (via CoachValidator).

Non-standard ports are used to avoid conflicts with local services:
- PostgreSQL: 5433 (standard: 5432)
- Redis: 6380 (standard: 6379)
- MongoDB: 27018 (standard: 27017)
"""

from __future__ import annotations

from typing import Dict, List


# Container name prefix for test isolation
CONTAINER_PREFIX = "guardkit-test"

# Docker fixture definitions: service name -> configuration
DOCKER_FIXTURES: Dict[str, Dict[str, object]] = {
    "postgresql": {
        "container_name": f"{CONTAINER_PREFIX}-pg",
        "image": "postgres:16-alpine",
        "port_mapping": "5433:5432",
        "env_vars": {"POSTGRES_PASSWORD": "test"},
        "readiness_cmd": "docker exec guardkit-test-pg pg_isready",
        "readiness_type": "command",  # "command" = until loop, "sleep" = fixed wait
        "env_export": {"DATABASE_URL": "postgresql+asyncpg://postgres:test@localhost:5433/test"},
    },
    "redis": {
        "container_name": f"{CONTAINER_PREFIX}-redis",
        "image": "redis:7-alpine",
        "port_mapping": "6380:6379",
        "env_vars": {},
        "readiness_cmd": None,
        "readiness_type": "sleep",
        "readiness_sleep": 1,
        "env_export": {"REDIS_URL": "redis://localhost:6380"},
    },
    "mongodb": {
        "container_name": f"{CONTAINER_PREFIX}-mongo",
        "image": "mongo:7",
        "port_mapping": "27018:27017",
        "env_vars": {},
        "readiness_cmd": None,
        "readiness_type": "sleep",
        "readiness_sleep": 2,
        "env_export": {"MONGODB_URL": "mongodb://localhost:27018"},
    },
}


def get_start_commands(service: str) -> List[str]:
    """Return the shell commands to start a Docker container for the given service.

    Args:
        service: Infrastructure service name (e.g., "postgresql", "redis", "mongodb")

    Returns:
        List of shell command strings to execute in order.

    Raises:
        KeyError: If service is not a known fixture.
    """
    fixture = DOCKER_FIXTURES[service.lower()]
    container = fixture["container_name"]
    image = fixture["image"]
    port = fixture["port_mapping"]

    commands: List[str] = []

    # Cleanup any existing container first
    commands.append(f"docker rm -f {container} 2>/dev/null || true")

    # Build docker run command
    env_flags = " ".join(f"-e {k}={v}" for k, v in fixture["env_vars"].items())
    run_cmd = f"docker run -d --name {container}"
    if env_flags:
        run_cmd += f" {env_flags}"
    run_cmd += f" -p {port} {image}"
    commands.append(run_cmd)

    # Readiness check
    if fixture["readiness_type"] == "command" and fixture.get("readiness_cmd"):
        commands.append(f'until {fixture["readiness_cmd"]}; do sleep 1; done')
    elif fixture["readiness_type"] == "sleep":
        commands.append(f'sleep {fixture.get("readiness_sleep", 2)}')

    return commands


def get_container_name(service: str) -> str:
    """Return the Docker container name for the given service.

    Args:
        service: Infrastructure service name (e.g., "postgresql")

    Returns:
        Container name string.

    Raises:
        KeyError: If service is not a known fixture.
    """
    return DOCKER_FIXTURES[service.lower()]["container_name"]


def get_env_exports(service: str) -> Dict[str, str]:
    """Return environment variables to export after starting the service.

    Args:
        service: Infrastructure service name (e.g., "postgresql")

    Returns:
        Dict mapping env var names to values.

    Raises:
        KeyError: If service is not a known fixture.
    """
    return dict(DOCKER_FIXTURES[service.lower()]["env_export"])


def is_known_service(service: str) -> bool:
    """Check if the service name is a known Docker fixture."""
    return service.lower() in DOCKER_FIXTURES
