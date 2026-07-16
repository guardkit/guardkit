"""Shared fixtures for the DCL derivation tests (D2)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "dcl"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def capability_dcl() -> Path:
    return FIXTURES / "capability.dcl"


@pytest.fixture
def broken_dcl() -> Path:
    return FIXTURES / "broken.dcl"


@pytest.fixture
def binding_file() -> Path:
    return FIXTURES / "binding.yaml"


requires_node = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node is required to run the vendored WASM DCL checker",
)
