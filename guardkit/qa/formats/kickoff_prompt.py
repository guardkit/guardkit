"""F13 · kickoff-prompt schema (LPA-12) — session B10.

Instance: ``qa/kickoff-<session>.yaml`` — the structured form of a kickoff
prompt rendered per dispatched session. Writer: the forge Mode P dispatcher;
**render fails on any missing mandatory section** (enforcement map). Exemplars:
``lpa-platform-poc/docs/poc/lovable-integration-KICKOFF-prompt.md`` and
``voice-standup-KICKOFF-prompt.md`` (the human-rendered forms).

Every mandatory section is a required, non-empty field so a half-rendered
prompt fails loudly rather than dispatching a session missing its guardrails or
its gate ref.

Field list pinned by scope-design §2 (2026-07-07). Additions require a dated
note in that doc, never silent invention.
"""

from __future__ import annotations

from typing import ClassVar, List

from pydantic import BaseModel, ConfigDict, Field

from guardkit.qa.formats.base import QAFormatModel


class KickoffDeliverable(BaseModel):
    """What the dispatched session must produce, and the gate that judges it."""

    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1)
    gate_ref: str = Field(min_length=1, description="The pass-bar / gate the deliverable is judged by")


class KickoffPrompt(QAFormatModel):
    """F13 root model — a rendered dispatched-session kickoff prompt.

    Each list section requires at least one entry: an empty ``guardrails`` or
    ``evidence_expectations`` is a missing mandatory section, not an
    intentionally-blank one.
    """

    FORMAT_KIND: ClassVar[str] = "kickoff-prompt"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    task_ref: str = Field(min_length=1)
    decisions_already_made: List[str] = Field(min_length=1)
    context_you_can_rely_on: List[str] = Field(min_length=1)
    deliverable: KickoffDeliverable
    guardrails: List[str] = Field(min_length=1)
    evidence_expectations: List[str] = Field(min_length=1)
