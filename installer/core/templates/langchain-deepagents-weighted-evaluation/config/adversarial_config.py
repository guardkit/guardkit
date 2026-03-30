"""Adversarial cooperation configuration for weighted evaluation.

Defines intensity settings, acceptance thresholds, and evaluation
criteria configuration. Loaded from agent-config.yaml or defaults.

Implements TASK-TI-014: Configurable Adversarial Intensity (full/light/solo).
"""

from __future__ import annotations

import logging
import pathlib
import random
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AdversarialIntensity(str, Enum):
    """Intensity modes for adversarial cooperation."""

    FULL = "full"
    LIGHT = "light"
    SOLO = "solo"


# Default configuration values
DEFAULT_CONFIG: dict[str, Any] = {
    "intensity": AdversarialIntensity.FULL.value,
    "acceptance_threshold": 0.7,
    "max_retries": 3,
    "light_sample_rate": 0.33,
    "solo_bypass_validation": False,
    "evaluation_criteria": [
        {
            "name": "accuracy",
            "weight": 0.3,
            "description": "All claims supported by cited sources",
            "accept_example": "Every factual statement has a source reference",
            "reject_example": "Claims made without evidence or citation",
        },
        {
            "name": "completeness",
            "weight": 0.3,
            "description": "Content addresses the request fully",
            "accept_example": "All aspects of the query are covered",
            "reject_example": "Major aspects of the query are missing",
        },
        {
            "name": "structure",
            "weight": 0.2,
            "description": "Output follows required JSON schema",
            "accept_example": "Valid JSON with all required fields",
            "reject_example": "Missing fields or invalid JSON",
        },
        {
            "name": "quality",
            "weight": 0.2,
            "description": "Writing quality and clarity",
            "accept_example": "Clear, well-organized content",
            "reject_example": "Incoherent or poorly structured text",
        },
    ],
    "hitl": {
        "enabled": True,
        "borderline_range": 0.05,
        "trigger_on_exhaustion": True,
    },
    "sprint": {
        "max_sprints": 3,
        "improvement_threshold": 0.1,
    },
}

# Intensity-specific overrides
INTENSITY_OVERRIDES: dict[str, dict[str, Any]] = {
    "full": {
        # Full mode: all features enabled, standard thresholds
    },
    "light": {
        "max_retries": 1,
        "hitl": {"enabled": False},
        "sprint": {"max_sprints": 0},
    },
    "solo": {
        "max_retries": 0,
        "acceptance_threshold": 0.0,  # Auto-accept everything
        "hitl": {"enabled": False},
        "sprint": {"max_sprints": 0},
    },
}


def load_adversarial_config(
    config_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Load adversarial configuration from file or defaults.

    Configuration is merged in order:
    1. DEFAULT_CONFIG (base)
    2. agent-config.yaml adversarial section (if present)
    3. INTENSITY_OVERRIDES for the selected intensity

    Args:
        config_path: Path to agent-config.yaml. Defaults to ./agent-config.yaml.

    Returns:
        Merged configuration dict.
    """
    config = dict(DEFAULT_CONFIG)

    # Load from agent-config.yaml if available
    if config_path is None:
        config_path = pathlib.Path("agent-config.yaml")

    if config_path.exists():
        try:
            import yaml

            file_config = yaml.safe_load(config_path.read_text())
            adversarial_section = file_config.get("adversarial", {})
            _deep_merge(config, adversarial_section)
        except Exception as e:
            logger.warning("Failed to load adversarial config: %s", e)

    # Apply intensity overrides
    intensity = config.get("intensity", AdversarialIntensity.FULL.value)
    overrides = INTENSITY_OVERRIDES.get(intensity, {})
    _deep_merge(config, overrides)

    # Validate criteria weights sum to 1.0
    criteria = config.get("evaluation_criteria", [])
    if criteria:
        total_weight = sum(c.get("weight", 0.0) for c in criteria)
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(
                "Criteria weights sum to %.3f (expected 1.0). "
                "Scores may not be normalized.",
                total_weight,
            )

    return config


def _deep_merge(base: dict, override: dict) -> None:
    """Deep merge override into base dict (mutates base)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


class IntensityRouter:
    """Routes pipeline outputs through Coach evaluation based on intensity.

    Encapsulates the intensity-dependent routing logic:
    - full: Every output goes through Coach evaluation.
    - light: Random sampling at configurable rate; unevaluated outputs
      still pass through the validation pipeline.
    - solo: Skip Coach entirely; optionally bypass validation.

    Args:
        config: Merged adversarial configuration dict from load_adversarial_config().
        rng: Optional random.Random instance for deterministic testing.
    """

    def __init__(
        self,
        config: dict[str, Any],
        rng: random.Random | None = None,
    ) -> None:
        raw_intensity = config.get("intensity", AdversarialIntensity.FULL.value)
        self._intensity = AdversarialIntensity(raw_intensity)
        self._light_sample_rate = float(config.get("light_sample_rate", 0.33))
        self._solo_bypass_validation = bool(config.get("solo_bypass_validation", False))
        self._rng = rng or random.Random()

        logger.info(
            "IntensityRouter initialised: mode=%s, light_sample_rate=%.2f, "
            "solo_bypass_validation=%s",
            self._intensity.value,
            self._light_sample_rate,
            self._solo_bypass_validation,
        )

    @property
    def intensity(self) -> AdversarialIntensity:
        return self._intensity

    @property
    def light_sample_rate(self) -> float:
        return self._light_sample_rate

    @property
    def solo_bypass_validation(self) -> bool:
        return self._solo_bypass_validation

    def should_evaluate(self) -> bool:
        """Determine whether Coach should evaluate the current output.

        Returns:
            True if Coach evaluation should run for this output.
        """
        if self._intensity == AdversarialIntensity.FULL:
            return True

        if self._intensity == AdversarialIntensity.LIGHT:
            sampled = self._rng.random() < self._light_sample_rate
            logger.debug(
                "Light mode sampling: %s (rate=%.2f)",
                "EVALUATE" if sampled else "SKIP",
                self._light_sample_rate,
            )
            return sampled

        # SOLO mode: never evaluate via Coach
        return False

    def should_validate(self) -> bool:
        """Determine whether the validation pipeline should run.

        In full and light modes, validation always runs.
        In solo mode, validation is skipped if solo_bypass_validation is True.

        Returns:
            True if validation should run for this output.
        """
        if self._intensity == AdversarialIntensity.SOLO:
            if self._solo_bypass_validation:
                logger.debug("Solo mode: bypassing validation pipeline")
                return False
        return True
