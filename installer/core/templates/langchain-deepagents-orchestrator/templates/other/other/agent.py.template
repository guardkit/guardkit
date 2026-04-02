"""Entrypoint for the DeepAgents orchestrator exemplar.

Reads ``orchestrator-config.yaml`` for model selection, loads domain context
from ``domains/{domain}/DOMAIN.md``, creates the orchestrator agent graph, and
exports a module-level ``agent`` variable required by ``langgraph.json``.

Usage via LangGraph::

    langgraph.json  →  ``{"graphs": {"orchestrator": "./agent.py:agent"}}``
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from agents import create_orchestrator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Project root directory (where this file lives).
_PROJECT_ROOT = Path(__file__).resolve().parent

#: Default domain name used when no override is provided.
DEFAULT_DOMAIN = "example-domain"

#: Fallback model identifiers used when the config file is missing or invalid.
_DEFAULT_CONFIG: dict[str, Any] = {
    "orchestrator": {
        "reasoning_model": "anthropic:claude-sonnet-4-6",
        "implementation_model": "anthropic:claude-haiku-4-5",
    },
}

#: Fallback domain prompt returned when the DOMAIN.md file cannot be read.
_DEFAULT_DOMAIN_PROMPT = "No domain-specific guidelines loaded. Follow general software engineering best practices."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_config(config_path: Path) -> dict[str, Any]:
    """Read and parse ``orchestrator-config.yaml``.

    Uses :func:`yaml.safe_load` for safe YAML parsing.  If the file is
    missing or contains invalid YAML, sensible defaults are returned so the
    orchestrator can still start.

    Args:
        config_path: Absolute or relative path to the YAML config file.

    Returns:
        Parsed configuration dictionary with at least ``orchestrator.reasoning_model``
        and ``orchestrator.implementation_model`` keys.
    """
    try:
        with open(config_path) as fh:
            raw = yaml.safe_load(fh)
    except FileNotFoundError:
        logger.warning("Config file not found at %s — using defaults.", config_path)
        return dict(_DEFAULT_CONFIG)
    except (yaml.YAMLError, OSError) as exc:
        logger.warning("Failed to parse config at %s (%s) — using defaults.", config_path, exc)
        return dict(_DEFAULT_CONFIG)

    if not isinstance(raw, dict) or "orchestrator" not in raw:
        logger.warning("Config file %s has unexpected structure — using defaults.", config_path)
        return dict(_DEFAULT_CONFIG)

    orch = raw.get("orchestrator", {})
    if not isinstance(orch, dict):
        logger.warning("orchestrator key is not a mapping — using defaults.")
        return dict(_DEFAULT_CONFIG)

    if "reasoning_model" not in orch or "implementation_model" not in orch:
        logger.warning("Config missing required model keys — merging with defaults.")
        merged_orch = {**_DEFAULT_CONFIG["orchestrator"], **orch}
        raw["orchestrator"] = merged_orch

    return raw


def _load_domain_prompt(project_root: Path, domain: str) -> str:
    """Read domain-specific guidelines from ``domains/{domain}/DOMAIN.md``.

    If the file is missing or cannot be decoded, a default prompt is returned
    so the orchestrator can operate without domain customisation.

    Args:
        project_root: Root directory of the project.
        domain: Name of the domain sub-directory under ``domains/``.

    Returns:
        The domain prompt text, or a default placeholder string.
    """
    domain_path = project_root / "domains" / domain / "DOMAIN.md"
    try:
        return domain_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("Domain file not found at %s — using default prompt.", domain_path)
        return _DEFAULT_DOMAIN_PROMPT
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("Failed to read domain file %s (%s) — using default prompt.", domain_path, exc)
        return _DEFAULT_DOMAIN_PROMPT


def _build_agent(
    config: dict[str, Any],
    domain_prompt: str,
) -> Any:
    """Wire configuration and domain prompt into :func:`create_orchestrator`.

    This helper exists so that the wiring logic can be tested independently
    of module-level side effects.

    Args:
        config: Parsed configuration dictionary (from ``_load_config``).
        domain_prompt: Domain-specific prompt text (from ``_load_domain_prompt``).

    Returns:
        A compiled state graph produced by ``create_orchestrator()``.
    """
    orch_config = config.get("orchestrator", _DEFAULT_CONFIG["orchestrator"])
    reasoning_model = orch_config.get("reasoning_model", _DEFAULT_CONFIG["orchestrator"]["reasoning_model"])
    implementation_model = orch_config.get(
        "implementation_model", _DEFAULT_CONFIG["orchestrator"]["implementation_model"]
    )

    return create_orchestrator(
        reasoning_model=reasoning_model,
        implementation_model=implementation_model,
        domain_prompt=domain_prompt,
    )


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

# Use parse_known_args() so that unexpected sys.argv values injected by the
# LangGraph server (or other import-time callers) do not raise SystemExit.
_arg_parser = argparse.ArgumentParser(
    description="DeepAgents orchestrator exemplar",
    add_help=True,
)
_arg_parser.add_argument(
    "--domain",
    default=DEFAULT_DOMAIN,
    help="Domain name to load from domains/{domain}/DOMAIN.md (default: %(default)s)",
)
_parsed_args, _unknown_args = _arg_parser.parse_known_args()

# ---------------------------------------------------------------------------
# Module-level initialisation
# ---------------------------------------------------------------------------

# Load environment variables from .env (no error if absent).
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env", override=False)

# Read config and domain, then build the orchestrator agent.
_config = _load_config(_PROJECT_ROOT / "orchestrator-config.yaml")
_domain_prompt = _load_domain_prompt(_PROJECT_ROOT, _parsed_args.domain)

#: Module-level agent variable required by langgraph.json.
#: ``langgraph.json`` references ``./agent.py:agent``.
agent = _build_agent(_config, _domain_prompt)
