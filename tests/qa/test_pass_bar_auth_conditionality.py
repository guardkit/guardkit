"""PB-14 (DECISION-DF-012 rider 1): auth-shaped negative paths are conditional
on ``auth_surface_bearing``; ``dependency_down_degradation`` stays universal.

The whole point is that an honest bar for an authless feature is EMITTABLE — an
emitter no longer has to fabricate four auth paths it has no surface for — while
an auth-surface-bearing feature keeps all five mandatory (no weakening there).
See ``guardkit/qa/formats/pass_bar.py`` module docstring.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner
from pydantic import ValidationError

from guardkit.cli.qa import qa
from guardkit.qa.formats.pass_bar import (
    AUTH_NEGATIVE_PATHS,
    REQUIRED_NEGATIVE_PATHS,
    UNIVERSAL_NEGATIVE_PATHS,
    PassBar,
)


def _bar(**overrides) -> dict:
    """A minimal valid 2.0 pass bar; override any field."""
    base = {
        "format_version": "2.0",
        "task_id": "TASK-PB14",
        "registered_at": {"sha": "abc1234", "date": "2026-07-08"},
        "auth_surface_bearing": True,
        "preconditions": ["suite_green_vs_ledger"],
        "criteria": [
            {
                "id": "AC-1",
                "text": "an observable behaviour",
                "class": "machine",
                "evidence_kind": "log",
            }
        ],
        "negative_paths": sorted(REQUIRED_NEGATIVE_PATHS),
    }
    base.update(overrides)
    return base


# --- the honest authless bar is emittable (the reason PB-14 exists) ----------


def test_authless_bar_with_only_dependency_path_validates() -> None:
    bar = PassBar.model_validate(
        _bar(
            auth_surface_bearing=False,
            negative_paths=["dependency_down_degradation"],
        )
    )
    assert bar.auth_surface_bearing is False
    assert bar.negative_paths == ["dependency_down_degradation"]


def test_authless_bar_may_still_declare_auth_paths_as_extras() -> None:
    # `false` relaxes the requirement; it does not forbid the paths.
    bar = PassBar.model_validate(
        _bar(
            auth_surface_bearing=False,
            negative_paths=[
                "dependency_down_degradation",
                "wrong_credential",
            ],
        )
    )
    assert "wrong_credential" in bar.negative_paths


def test_authless_bar_missing_dependency_path_still_fails() -> None:
    # dependency_down_degradation is the ONE universal path — dropping it is
    # invalid even for an authless bar.
    with pytest.raises(ValidationError, match="dependency_down_degradation"):
        PassBar.model_validate(
            _bar(
                auth_surface_bearing=False,
                negative_paths=["wrong_credential"],
            )
        )


# --- auth-surface-bearing bars keep all five, same message shape as today ----


def test_auth_bearing_bar_needs_all_five() -> None:
    bar = PassBar.model_validate(_bar(auth_surface_bearing=True))
    assert set(bar.negative_paths) == REQUIRED_NEGATIVE_PATHS


@pytest.mark.parametrize("dropped", sorted(AUTH_NEGATIVE_PATHS))
def test_auth_bearing_bar_missing_an_auth_path_fails_with_today_message(
    dropped: str,
) -> None:
    paths = sorted(REQUIRED_NEGATIVE_PATHS - {dropped})
    with pytest.raises(ValidationError) as excinfo:
        PassBar.model_validate(
            _bar(auth_surface_bearing=True, negative_paths=paths)
        )
    message = str(excinfo.value)
    # Same message shape as before PB-14 (the auth-bearing contract is unchanged).
    assert "the required minimum set entries" in message
    assert "Declare all five" in message
    assert dropped in message


# --- the flag is required with no default (guessing re-opens fabrication) -----


def test_auth_surface_bearing_is_required() -> None:
    payload = _bar()
    del payload["auth_surface_bearing"]
    with pytest.raises(ValidationError, match="auth_surface_bearing"):
        PassBar.model_validate(payload)


def test_absent_flag_does_not_relax_the_negative_path_gate() -> None:
    # Defensive: even with the flag absent (its own error), a bar that would be
    # authless-shaped must NOT be waved through — the validator falls back to
    # strict, so negative_paths is still reported.
    payload = _bar(negative_paths=["dependency_down_degradation"])
    del payload["auth_surface_bearing"]
    with pytest.raises(ValidationError) as excinfo:
        PassBar.model_validate(payload)
    message = str(excinfo.value)
    assert "auth_surface_bearing" in message
    assert "negative_paths" in message


# --- schema-version bump is visible ------------------------------------------


def test_schema_version_bumped_to_2() -> None:
    assert PassBar.CURRENT_FORMAT_VERSION == "2.0"


def test_prior_major_bar_without_flag_is_version_accepted_but_field_required() -> None:
    # A 1.0 bar is still inside the N/N-1 version window, but a real 1.0 bar
    # predates the flag and now fails on the missing required field — a loud,
    # actionable migration signal, not a confusing version error.
    payload = _bar(format_version="1.0")
    del payload["auth_surface_bearing"]
    with pytest.raises(ValidationError, match="auth_surface_bearing"):
        PassBar.model_validate(payload)


def test_qa_schema_pass_bar_exposes_the_new_field() -> None:
    result = CliRunner().invoke(qa, ["schema", "pass-bar"])
    assert result.exit_code == 0, result.output
    schema = json.loads(result.output)
    props = schema["properties"]
    assert "auth_surface_bearing" in props
    assert props["auth_surface_bearing"]["type"] == "boolean"
    # required-with-no-default => it appears in the schema's required list.
    assert "auth_surface_bearing" in schema["required"]


def test_constants_partition_the_required_set() -> None:
    # The five-path set is exactly the four auth paths plus the one universal.
    assert AUTH_NEGATIVE_PATHS | UNIVERSAL_NEGATIVE_PATHS == REQUIRED_NEGATIVE_PATHS
    assert AUTH_NEGATIVE_PATHS.isdisjoint(UNIVERSAL_NEGATIVE_PATHS)
    assert len(REQUIRED_NEGATIVE_PATHS) == 5
