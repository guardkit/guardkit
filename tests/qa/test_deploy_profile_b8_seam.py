"""WS2-B10 ↔ B8 cross-repo seam proof: a conforming ``deploy/profile.yaml``
validates against B10's canonical schema AND is accepted by B8's forge loader.

B10 owns the canonical deploy-profile schema (``guardkit/qa/formats/deploy_profile.py``);
WS2-B8 built the forge *loader* (``forge/src/forge/deploy/profile.py``) ahead of
B10 and filed a dated reconcile note. This test proves the two agree on a real
instance — the fixture-level proof the §B10 gate requires. It skips when the
forge sibling repo is absent (CI without the sibling checkout), the same
graceful-degrade posture as the harness cross-repo seam tests.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

from guardkit.qa.formats import validate_instance

FIXTURES = Path(__file__).parent.parent / "fixtures" / "qa_formats"
# guardkit and forge are sibling repos under the same parent.
_FORGE_LOADER = (
    Path(__file__).resolve().parents[3] / "forge" / "src" / "forge" / "deploy" / "profile.py"
)

_EXEMPLARS = [
    "lpa-platform-poc/deploy-profile.yaml",
    "study-tutor/deploy-profile.yaml",
    # Dated addition 2026-07-16 (C4-prep): exercises rollback_image_ref +
    # live_gate — the superset-invariant restore, proven on both sides.
    "study-tutor/deploy-profile-live-gate.yaml",
]


def _load_forge_loader():
    """Import forge's B8 deploy-profile loader by path (it is self-contained).

    Registers the module in ``sys.modules`` before exec so its ``slots=True``
    dataclasses resolve their own annotations.
    """
    if not _FORGE_LOADER.is_file():
        pytest.skip(f"forge sibling loader not present at {_FORGE_LOADER}")
    spec = importlib.util.spec_from_file_location("forge_deploy_profile_b8", _FORGE_LOADER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["forge_deploy_profile_b8"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("rel_path", _EXEMPLARS)
def test_exemplar_validates_on_both_sides(rel_path: str) -> None:
    path = FIXTURES / rel_path
    # B10 canonical schema accepts it...
    instance = validate_instance("deploy-profile", path)
    assert instance.FORMAT_KIND == "deploy-profile"

    # ...and B8's forge loader accepts the SAME bytes (format_version tolerated
    # as an extra key; env_id + compose.file are the shared required fields).
    forge = _load_forge_loader()
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    profile = forge.parse_deploy_profile(raw, source_ref=str(path))
    assert profile.env_id == instance.env_id
    assert profile.compose.file == instance.compose.file
    assert list(profile.secret_injection) == list(instance.secret_injection)
    # The 2026-07-16 additions agree wherever the instance carries them.
    assert getattr(profile, "rollback_image_ref", None) == instance.rollback_image_ref
    if instance.live_gate is not None:
        assert profile.live_gate is not None, "forge loader dropped live_gate"
        assert list(profile.live_gate.driver) == list(instance.live_gate.driver)
        assert list(profile.live_gate.gates) == list(instance.live_gate.gates)
        assert profile.live_gate.timeout_seconds == instance.live_gate.timeout_seconds
        assert dict(profile.live_gate.env) == dict(instance.live_gate.env)


def test_value_bearing_secret_refused_on_both_sides() -> None:
    """A smuggled secret VALUE is refused by both the B10 schema and the B8 loader."""
    bad = {
        "format_version": "1.0",
        "env_id": "x",
        "compose": {"file": "c.yml"},
        "secret_injection": ["FLEET_MEMORY_PG_DSN=postgres://u:p@nas:5432/db"],
    }
    # B8 loader refuses.
    forge = _load_forge_loader()
    with pytest.raises(forge.DeployProfileError):
        forge.parse_deploy_profile(bad)

    # B10 schema refuses.
    from guardkit.qa.formats import DeployProfile, QAFormatError

    with pytest.raises(Exception) as exc:
        DeployProfile.model_validate(bad)
    assert "REFS ONLY" in str(exc.value) or "register-key" in str(exc.value)
    # And through the public validator path (write to a temp file), loudly.
    _ = QAFormatError  # imported for symmetry with the loud-failure convention


def _base_profile_with_live_gate(live_gate: dict) -> dict:
    return {
        "format_version": "1.0",
        "env_id": "x",
        "compose": {"file": "c.yml"},
        "live_gate": live_gate,
    }


@pytest.mark.parametrize(
    "live_gate",
    [
        # empty driver argv
        {"driver": []},
        # empty-string argv part
        {"driver": ["python3", ""]},
        # bool timeout (a bool is not a timeout)
        {"driver": ["python3", "d.py"], "timeout_seconds": True},
        # zero timeout
        {"driver": ["python3", "d.py"], "timeout_seconds": 0},
        # lower-case env name (not an UPPER_SNAKE env-var NAME)
        {"driver": ["python3", "d.py"], "env": {"base_url": "http://x"}},
        # non-string env value
        {"driver": ["python3", "d.py"], "env": {"BASE_URL": 8100}},
        # parity-coach catches 2026-07-16: pydantic lax mode coerced these
        # where the forge loader's isinstance(int) check refuses — the fatal
        # direction of the superset invariant. Both sides must refuse.
        {"driver": ["python3", "d.py"], "timeout_seconds": "600"},
        {"driver": ["python3", "d.py"], "timeout_seconds": 600.0},
        {"driver": ["python3", "d.py"], "timeout_seconds": " 600 "},
    ],
)
def test_malformed_live_gate_refused_on_both_sides(live_gate: dict) -> None:
    """Every malformed live_gate shape is refused by BOTH validators (parity)."""
    bad = _base_profile_with_live_gate(live_gate)

    forge = _load_forge_loader()
    with pytest.raises(forge.DeployProfileError):
        forge.parse_deploy_profile(bad)

    from guardkit.qa.formats import DeployProfile

    with pytest.raises(Exception):
        DeployProfile.model_validate(bad)


def test_blank_rollback_ref_refused_on_both_sides() -> None:
    """A whitespace-only rollback_image_ref is refused by BOTH validators.

    Parity-coach catch 2026-07-16: min_length counted raw chars while the
    forge loader strips-and-refuses — a blank ref validating green would feed
    the O-32 revert garbage (the fatal direction of the superset invariant).
    """
    bad = {
        "format_version": "1.0",
        "env_id": "x",
        "compose": {"file": "c.yml"},
        "rollback_image_ref": "   ",
    }

    forge = _load_forge_loader()
    with pytest.raises(forge.DeployProfileError):
        forge.parse_deploy_profile(bad)

    from guardkit.qa.formats import DeployProfile

    with pytest.raises(Exception):
        DeployProfile.model_validate(bad)

    # And the padded-but-non-blank case NORMALIZES identically on both sides
    # (forge strips at profile.py:548; the canonical validator now strips too),
    # keeping the exemplar equality assertions meaningful.
    padded = dict(bad, rollback_image_ref="  tag:rollback-x  ")
    assert DeployProfile.model_validate(padded).rollback_image_ref == "tag:rollback-x"
    assert (
        forge.parse_deploy_profile(padded).rollback_image_ref == "tag:rollback-x"
    )
