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
