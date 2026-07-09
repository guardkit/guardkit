"""F6 · contract/seam manifest, incl. broker section (ST-02, ST-03, LPA-16) — session B10.

Instance: ``contracts/manifest.yaml`` per system (a cross-repo file).

The format answer to the FEAT-DD4F / MP-freeze class of wire-semantics defects:
every seam between two sides names its **arbiter** (the frozen contract doc —
never adapt the consuming side silently) and its attribution sides, so a live
failure can be binned this-side / other-side / contract-gap before verification
is called done. The broker section is the machine-readable expectation the
deploy + live-gate pre-flight diffs live JetStream state against (LPA-16).

Field list pinned by scope-design §2 (2026-07-07). Additions require a dated
note in that doc, never silent invention (the B1 rule).
"""

from __future__ import annotations

from typing import ClassVar, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from guardkit.qa.formats.base import QAFormatModel

#: How a seam is realized on the wire.
SeamKind = Literal["http", "broker", "lib_call", "process"]

#: How a broker publisher writes — core NATS or JetStream.
PublishPattern = Literal["core", "js"]


class ArbiterDoc(BaseModel):
    """The frozen contract doc that arbitrates a seam.

    ``sha`` is FROZEN: the consuming side is never adapted silently to a moved
    contract — a drifted arbiter is a contract-gap finding, not a quiet fix.
    """

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    sha: str = Field(min_length=1, description="Pinned arbiter sha (FROZEN)")


class ExpectationSeam(BaseModel):
    """One fake-vs-live expectation pair for a seam (the signature-binding check)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    fake_expectation: str = Field(min_length=1)
    live_expectation: str = Field(min_length=1)


class DurableConsumer(BaseModel):
    """A JetStream durable consumer and its subject filter."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    filter: str = Field(min_length=1, description="Subject filter, e.g. pipeline.build-queued.>")


class Seam(BaseModel):
    """One contract seam between two sides, attributed against its arbiter."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    kind: SeamKind
    sides: List[str] = Field(min_length=2, description="The two (or more) sides of the seam")
    arbiter_doc: ArbiterDoc
    attribution_sides: List[str] = Field(
        min_length=1,
        description="Which side(s) a failure at this seam can be attributed to",
    )
    expectation_seams: List[ExpectationSeam] = Field(default_factory=list)


class BrokerStream(BaseModel):
    """One JetStream stream's contract (the pre-flight diff target)."""

    model_config = ConfigDict(extra="forbid")

    stream: str = Field(min_length=1)
    subjects: List[str] = Field(min_length=1)
    retention: Optional[str] = None
    no_ack: Optional[bool] = None
    max_ack_pending: Optional[int] = None
    ack_wait: Optional[str] = Field(default=None, description="e.g. '1h', '30s'")
    durable_consumers: List[DurableConsumer] = Field(default_factory=list)
    publish_pattern: Optional[PublishPattern] = None


class SeamManifest(QAFormatModel):
    """F6 root model — the system's seams plus its broker contract."""

    FORMAT_KIND: ClassVar[str] = "seam-manifest"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    system: str = Field(min_length=1, description="The system this manifest covers")
    seams: List[Seam] = Field(default_factory=list)
    broker: List[BrokerStream] = Field(default_factory=list)
