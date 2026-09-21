"""A ``memory:`` block that names only the project is not an invalid declaration.

Since 2026-09-21 every project declares ``memory: project: <name>``, usually
with nothing else in the block. The older reader of
``memory.fleet.context_sources`` treated that as a malformed declaration and
warned on every build. Nothing declared is nothing declared; only a level that
is present and malformed is worth a warning.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from guardkit.knowledge.autobuild_context_loader import (
    _load_relevant_pattern_document_tags,
)

LOGGER = "guardkit.knowledge.autobuild_context_loader"


def _project(tmp_path: Path, text: str) -> Path:
    folder = tmp_path / ".guardkit"
    folder.mkdir()
    (folder / "config.yaml").write_text(text, encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize(
    "text",
    [
        "memory:\n  project: widget_shop\n",
        "memory:\n  project: widget_shop\n  fleet: {}\n",
        "memory:\n  project: widget_shop\n  fleet:\n    something_else: 1\n",
    ],
)
def test_a_block_with_no_pattern_sources_is_quiet(tmp_path, caplog, text) -> None:
    root = _project(tmp_path, text)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert _load_relevant_pattern_document_tags(root) == ()
    assert "Invalid memory.fleet.context_sources" not in caplog.text


@pytest.mark.parametrize(
    "text",
    [
        "memory: just a sentence\n",
        "memory:\n  fleet: just a sentence\n",
        "memory:\n  fleet:\n    context_sources: just a sentence\n",
    ],
)
def test_a_level_that_is_present_and_malformed_still_warns(
    tmp_path, caplog, text
) -> None:
    root = _project(tmp_path, text)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert _load_relevant_pattern_document_tags(root) == ()
    assert "Invalid memory.fleet.context_sources" in caplog.text


def test_a_real_declaration_is_still_read(tmp_path) -> None:
    root = _project(
        tmp_path,
        "memory:\n  project: widget_shop\n  fleet:\n    context_sources:\n"
        "      relevant_patterns:\n        document_tags: [house_rules]\n",
    )
    assert _load_relevant_pattern_document_tags(root) == ("house_rules",)
