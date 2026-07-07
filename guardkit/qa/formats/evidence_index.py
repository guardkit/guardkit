"""F5 · evidence-artifact index (LPA-07).

Instance: an ``EVIDENCE.yaml`` index living INSIDE the evidence dir it
describes (``evidence-<date>/``), whose artifact dirs follow the naming
convention ``shots-<topic>/NN-<name>.png`` (numbered, one per gate/walk
step). Artifact paths in entries are relative to the index file's directory.
Each RESULTS file names its evidence dir.

Writers: live-gate runner (automatic), walk driver, deploy stage, runbook
executors. Readers: the verdict step (the verifying agent must OPEN and read
key shots — an uninspected-evidence verdict is invalid), status audits, WS4
harvest.

Enforcement (the runner refuses a PASS verdict while any ``inspected_by`` on
a key artifact is empty) is B3's — the schema deliberately allows a null
``inspected_by``/``verdict`` because an index legitimately exists BEFORE
inspection; what it never allows is the fields being absent from the shape.

Committed exemplar lineage: the 64 shots under
``lpa-platform-poc/qa/gates/evidence-2026-07-05/shots-gate-phase{1..6}/``
(B0 rescue, commit 8980af1) and ``study-tutor/docs/runbooks/evidence/``
(8 campaign dirs).

Stack-blind by design. Field list pinned by scope-design §2 (2026-07-07):
entries are ``{artifact, checkpoint_or_assertion_id, description,
inspected_by, verdict}``. Additions require a dated note in that doc.
"""

from __future__ import annotations

from typing import ClassVar, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from guardkit.qa.formats.base import QAFormatModel


class EvidenceEntry(BaseModel):
    """One evidence artifact and its inspection state."""

    model_config = ConfigDict(extra="forbid")

    # Path relative to the index file's directory, e.g.
    # "shots-gate-phase1/anon-accounts-redirects-to-keycloak.png".
    artifact: str = Field(min_length=1)
    # The pass-bar criterion, gate assertion, or walk checkpoint this
    # artifact evidences.
    checkpoint_or_assertion_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    # Null until a verifier has actually OPENED the artifact. B3's verdict
    # step refuses PASS while a key artifact's inspected_by is empty.
    inspected_by: Optional[str] = None
    # The inspecting verifier's call on this artifact; null until inspected.
    verdict: Optional[str] = None


class EvidenceIndex(QAFormatModel):
    """F5 root model."""

    FORMAT_KIND: ClassVar[str] = "evidence-index"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    entries: List[EvidenceEntry] = Field(min_length=1)
