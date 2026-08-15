"""Unit tests for the per-repo spec_track switch.

Covers the ``get_spec_track`` precedence contract:
env ``GUARDKIT_SPEC_TRACK`` > ``.guardkit/config.yaml`` ``qa.spec_track`` >
default ``"gherkin"``; and the loud ``ValueError`` on any unrecognised value (a
typo must never silently mean gherkin).

Since the DCL track's deletion (card Q11, ruled 08-15) ``gherkin`` is the only
legal value: the former dcl-accepting cases here now pin the loud rejection of
a leftover ``dcl`` opt-in.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guardkit.qa.spec_track import (
    ALLOWED_SPEC_TRACKS,
    DEFAULT_SPEC_TRACK,
    SPEC_TRACK_ENV,
    get_spec_track,
)


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    """Every test starts with the env override unset (config/default in play)."""
    monkeypatch.delenv(SPEC_TRACK_ENV, raising=False)


def _write_config(repo_root: Path, body: str) -> None:
    cfg = repo_root / ".guardkit"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "config.yaml").write_text(body, encoding="utf-8")


# --- default -----------------------------------------------------------------


def test_default_is_gherkin_no_config(tmp_path: Path):
    """No env, no config → the permanent fallback track."""
    assert get_spec_track(tmp_path) == "gherkin"
    assert DEFAULT_SPEC_TRACK == "gherkin"


def test_default_when_config_has_no_qa_section(tmp_path: Path):
    _write_config(tmp_path, "other: {}\n")
    assert get_spec_track(tmp_path) == "gherkin"


def test_default_when_qa_has_no_spec_track(tmp_path: Path):
    _write_config(tmp_path, "qa:\n  enforce_tier1: true\n")
    assert get_spec_track(tmp_path) == "gherkin"


# --- config precedence -------------------------------------------------------


def test_config_gherkin_explicit(tmp_path: Path):
    _write_config(tmp_path, "qa:\n  spec_track: gherkin\n")
    assert get_spec_track(tmp_path) == "gherkin"


def test_config_value_is_case_and_space_normalised(tmp_path: Path):
    _write_config(tmp_path, "qa:\n  spec_track: '  GHERKIN  '\n")
    assert get_spec_track(tmp_path) == "gherkin"


# --- env precedence (wins over config) --------------------------------------


def test_env_overrides_invalid_config(tmp_path: Path, monkeypatch):
    """A valid env value wins before the config value is even validated."""
    _write_config(tmp_path, "qa:\n  spec_track: bogus\n")
    monkeypatch.setenv(SPEC_TRACK_ENV, "GHERKIN")
    assert get_spec_track(tmp_path) == "gherkin"


def test_blank_env_falls_through_to_config(tmp_path: Path, monkeypatch):
    """An empty/whitespace env var is not a value — config still decides."""
    _write_config(tmp_path, "qa:\n  spec_track: gherkin\n")
    monkeypatch.setenv(SPEC_TRACK_ENV, "   ")
    assert get_spec_track(tmp_path) == "gherkin"


# --- invalid values raise LOUD (never silent gherkin) ------------------------


def test_invalid_env_raises(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(SPEC_TRACK_ENV, "gherkins")
    with pytest.raises(ValueError) as exc:
        get_spec_track(tmp_path)
    assert "gherkin" in str(exc.value)


def test_invalid_config_raises(tmp_path: Path):
    _write_config(tmp_path, "qa:\n  spec_track: bdd\n")
    with pytest.raises(ValueError) as exc:
        get_spec_track(tmp_path)
    # The allowed set is named in the message; gherkin is the ONLY legal track.
    assert set(ALLOWED_SPEC_TRACKS) == {"gherkin"}
    assert "allowed" in str(exc.value).lower()


def test_leftover_dcl_config_raises(tmp_path: Path):
    """A leftover dcl opt-in (the deleted track) is loud, never silent gherkin."""
    _write_config(tmp_path, "qa:\n  spec_track: dcl\n")
    with pytest.raises(ValueError):
        get_spec_track(tmp_path)


def test_leftover_dcl_env_raises(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(SPEC_TRACK_ENV, "dcl")
    with pytest.raises(ValueError):
        get_spec_track(tmp_path)


def test_env_invalid_raises_even_with_valid_config(tmp_path: Path, monkeypatch):
    _write_config(tmp_path, "qa:\n  spec_track: gherkin\n")
    monkeypatch.setenv(SPEC_TRACK_ENV, "typo")
    with pytest.raises(ValueError):
        get_spec_track(tmp_path)


def test_unreadable_config_falls_back_to_default(tmp_path: Path):
    """Malformed YAML is treated as absent (default), not a crash."""
    _write_config(tmp_path, "qa: [unterminated\n")
    assert get_spec_track(tmp_path) == "gherkin"
