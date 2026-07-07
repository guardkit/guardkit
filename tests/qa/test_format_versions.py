"""format_version N/N-1 acceptance window (scope-design §2 evolution rules).

Simulated on a throwaway subclass at CURRENT=2.0 so the window has a real
N-1 to accept; the shipped formats are all at 1.0 where only major 1 exists.
"""

from __future__ import annotations

from typing import ClassVar

import pytest
from pydantic import ValidationError

from guardkit.qa.formats.base import QAFormatModel


class _FormatAtV2(QAFormatModel):
    FORMAT_KIND: ClassVar[str] = "test-format"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "2.0"


def test_current_major_accepted() -> None:
    assert _FormatAtV2(format_version="2.3").format_version == "2.3"


def test_previous_major_accepted() -> None:
    assert _FormatAtV2(format_version="1.0").format_version == "1.0"


def test_older_major_refused_with_migration_pointer() -> None:
    with pytest.raises(ValidationError, match="Migrate the instance forward"):
        _FormatAtV2(format_version="0.9")


def test_newer_major_refused_with_upgrade_pointer() -> None:
    with pytest.raises(ValidationError, match="Upgrade guardkit"):
        _FormatAtV2(format_version="3.0")


def test_garbage_version_refused() -> None:
    with pytest.raises(ValidationError, match="not a '<major>.<minor>'"):
        _FormatAtV2(format_version="latest")


def test_v1_formats_have_no_previous_major() -> None:
    """At 1.0 the window is {1} — a 0.x instance refuses (no major 0 ever shipped)."""

    class _FormatAtV1(QAFormatModel):
        FORMAT_KIND: ClassVar[str] = "test-format-v1"
        CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    assert _FormatAtV1(format_version="1.4").format_version == "1.4"
    with pytest.raises(ValidationError):
        _FormatAtV1(format_version="0.9")
