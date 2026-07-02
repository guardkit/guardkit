# DECISION-DF-006 — Frontier is a revocable teacher, not a critical-path worker

**Status:** Accepted
**Date:** 2026-07-02
**Author:** Rich (pair-programmed with Claude in Claude Desktop)
**Scope:** All frontier-model use across the dark factory. Establishes that no unattended, autonomous, scheduled, or continuous workload may depend on a frontier model being *reachable*, and defines the two roles in which frontier is retained plus the per-stage degradation contract.
**Companions:** DECISION-DF-001 (no cloud on the unattended critical path — on *cost* grounds; this decision adds the *availability* dimension) · DECISION-DF-003 (attended-planning-frontier / unattended-build-local boundary — this decision is that boundary's resilience property) · DECISION-DF-004 (serving topology; §2.4's `fallbacks: []` guard is where this decision is *enforced* at the LiteLLM layer)
**Related:** `forge/docs/research/ideas/unattended-build-service-scope.md` (§3.5 "DF-001 holds… frontier never enters the unattended path" — this decision generalises that from cost to availability) · `forge/docs/research/ideas/conversation-capture-2026-06-14-forge-meta-harness.md` (§6 — the improve loop's proposer is local; frontier is the eval yardstick only)

---

## Summary

**Frontier availability is treated as revocable and volatile. No unattended, autonomous, scheduled, or continuous workload may depend on a frontier model being reachable. Frontier is retained in exactly two roles, both of which absorb its absence: (1) attended planning, where a human is present and can wait or fall back; and (2) an eval / calibration yardstick — gold traces and golden calibration sets captured once, while frontier is available, then used offline to train or grade local models. Every stage declares a substrate preference with a mandatory local fallback. An availability shock changes the *rate of model improvement*, never the *ability to ship*.**

DF-001 excluded cloud from the critical path because of what it *costs*. This decision excludes it because of whether it is *there at all* — a distinct failure mode (subscription-policy change, export controls, regional restriction, deprecation) that DF-001 does not cover. The answer is the same in shape (local by default) but now carries an explicit degradation contract for what happens the moment frontier disappears.

## 1. Context

### 1.1 The triggering events

Three frontier-availability shocks inside one month, all outside Rich's control and none pre-announced with useful notice:

- **Programmatic Max access was slated to be withdrawn on 15 June 2026** — the event that motivated building the LangChain Deep Agents AutoBuild path in the first place, so that the build loop would not depend on Max's API being available. That withdrawal was then **reversed on 15 June**.
- **Fable was released, then suspended, then restored.** The model became available in early June, was suspended shortly after to comply with U.S. Department of Commerce export controls, and was restored on 1 July 2026. Access came and went twice within weeks.

The pattern is the point, not any single event: the *availability and terms* of frontier access changed repeatedly, without warning, in ways Rich cannot influence or predict. A factory that depends on frontier being reachable is a factory whose uptime is set by other parties' policy decisions.

### 1.2 Why DF-001 did not already cover this

DF-001's exclusion is a *cost* argument — the £29.91 weekend Gemini spend, extrapolated to £1,200–£1,900/month at full fleet, which would make the factory self-throttle. That argument is about the meter.

But cost is not the only frontier risk. Even on the *attended* path, where DF-001 explicitly *permits* frontier because a human is driving and the per-session cost is justified, the **access itself can be revoked** for reasons that have nothing to do with the bill: a subscription policy change, an export-control ruling, a regional block, or a model deprecation. DF-001 protects the factory from the invoice. It does not protect the factory from the plug being pulled. That is the gap this decision closes.

### 1.3 The distinction that resolves it

Frontier has two roles that are *both* robust to availability shocks, and the resolution is simply to confine frontier to those two roles:

- **Attended planning quality.** A human is present. If frontier is unavailable, they fall back to the best local model or wait. The absence is absorbed by the human in the loop.
- **Eval / calibration yardstick.** The gold-standard artefacts — the weekend AutoBuild traces, the QA Verifier golden calibration set — are captured *once*, while frontier is available, and then used *offline* to train or grade local models. The frontier call is not on any continuous path; it is a one-time harvest whose product outlives it.

Neither role puts frontier on an unattended loop that must keep running. The 14 June meta-harness capture already embodies this for the improve loop: the proposer that rewrites the harness is **local**; frontier (Opus) is only the eval yardstick, and the weekend gold traces are already captured — "for free," and permanently.

## 2. Decision

### 2.1 The principle

**No unattended, autonomous, scheduled, or continuous workload may depend on a frontier model being reachable.** Frontier is retained only for the two roles in §1.3. Per-stage substrate policy:

| Stage | Substrate | On frontier-unavailable |
|---|---|---|
| **Attended planning** (ideation, `/feature-spec`, `/feature-plan`) | *Prefer* frontier; a human is present | Fall back to best local (workhorse / GPT-OSS-120B). Degraded, still functional. |
| **Unattended build** (UBS night shift, AutoBuild Player-Coach, QA Verifier runtime) | **Local only, always** (DF-001) | No effect — nothing to degrade. |
| **Improve loop** (meta-harness proposer) | **Local only** (proposer is local per the 14 June capture §6) | No effect. |
| **Eval / calibration** (gold traces, QA Verifier golden calibration set) | Frontier as yardstick, opportunistic, captured once | Pause the harvest. Already-captured artefacts and the local models trained from them are unaffected. |

### 2.2 The degradation contract

- **No code path hard-codes a frontier provider as a runtime dependency.** Every model call resolves through a substrate router — LiteLLM `:4000` / llama-swap `:9000` on the local side, and a coding harness's `--model provider:model` where one is involved.
- **Frontier entries in any router config are named, attended-only models with no automatic fallback *to* them.** Per DF-004 §2.4, set **both** `fallbacks: []` **and** `context_window_fallbacks: []` so the front door can never silently escalate an unattended request to cloud. Local→local fallback (e.g. proposer→workhorse) is permitted; local→cloud is not.
- **Preference is flipped by config/env, not by code.** An availability shock → the router serves local; the attended path's preference for frontier is a flag, not a hard dependency.

### 2.3 What this makes robust

The June access-withdrawal-then-reversal and the Fable suspension-then-restoration are **operationally invisible to the factory floor**. Through both, the build loop and (once running) the improve loop execute on local inference; only the calibration harvest would have paused, and its outputs were already captured. The shocks changed the *rate of model improvement*, never the *ability to ship*.

## 3. Consequences

**Positive:** availability shocks become non-events for the factory · the cost-inversion thesis reaches its strongest form — the market meters frontier for implementation *and* improvement, while the factory runs both local and borrows frontier once, as calibration · the LangChain Deep Agents AutoBuild investment is retrospectively justified as exactly the local build path this decision mandates · the factory is insulated from subscription-policy, export-control, regional, and deprecation risk in one stroke.

**Negative / accepted:** attended planning quality degrades during a frontier outage — accepted, because a human is present to wait or use local · the calibration harvest pauses during outages — accepted, because the artefacts are already captured and the local models trained from them keep running · keeping frontier off every unattended path requires ongoing discipline — mitigated by the router contract (§2.2) and DF-004's no-fallback guard, which make the safe path the default.

## 4. Relationship to existing decisions and current work

- **DF-001** — unchanged. DF-006 adds the *availability* dimension to DF-001's *cost* dimension. Same architectural answer (local by default), different failure mode.
- **DF-003** — unchanged. DF-006 is the resilience property of DF-003's attended/unattended boundary: the boundary is drawn exactly where a human can absorb frontier's absence.
- **DF-004** — DF-006's degradation contract is *enforced* at the LiteLLM layer DF-004 §2.4 already specifies. This decision is the *why* behind that guard.
- **Unattended Build Service (Phase UBS)** — the build-side embodiment. UBS §3.5 ("frontier never enters the unattended path") is DF-006 for the build loop; this record generalises the reason from cost to availability.
- **Meta-harness improve loop (14 June capture)** — the improve-side embodiment: proposer local, frontier as eval yardstick only.
- **QA Verifier** — its golden calibration set (Opus via Max) is the canonical DF-006 "frontier as opportunistic yardstick": captured once, trains the local Coach, unaffected by any subsequent outage.

## 5. Principle made explicit

> **Availability is an architectural property, not a given. Any workload that must run whether or not an external provider chooses to serve you cannot depend on that provider. Use frontier only where a human is present to absorb its absence, or as a yardstick captured once and used offline — never as a worker on a loop that must keep running. Build local by default; borrow frontier deliberately; never be held to a schedule you do not control.**

This applies beyond LLM APIs to any external dependency whose availability is set by another party's policy — hosted models, managed platforms, regionally-gated services. Confine each to a role that survives its disappearance, or keep it off the critical path.

## 6. Immediate actions

- **Audit every unattended path for a frontier resolution.** Confirm the UBS runner, the Mode C fix-agent, the QA Verifier runtime, and the meta-harness proposer all resolve to local providers. Any frontier entry on those paths is a DF-006 violation.
- **Confirm DF-004's guard is live** on the LiteLLM front door: `fallbacks: []` **and** `context_window_fallbacks: []`.
- **Resolve the one genuinely-open substrate question.** The 14 June capture §6 flags the *output-side* deploy/verify fix-agent substrate as still open (frontier Claude Code vs local). DF-006 resolves it in principle: it must be local if it runs unattended; frontier is permitted only if the loop is attended-by-exception with a human approving each irreversible step. Carry this into the output-side loop's `/system-arch`.
- **Seed this decision into fleet-memory** so agents retrieve it at context-load and never place frontier on an unattended path again.

## 7. References

- DECISION-DF-001, DECISION-DF-003, DECISION-DF-004 (`guardkit/docs/decisions/`).
- `forge/docs/research/ideas/unattended-build-service-scope.md` · `conversation-capture-2026-06-14-forge-meta-harness.md`.
- Anthropic statement on Fable/Mythos access (export-control suspension and 1 July restoration).

---

*Decision accepted: 2026-07-02*
*Scope: all frontier-model use across the dark factory — availability, not just cost.*
*"Availability is an architectural property. Build local by default; borrow frontier deliberately; never be held to a schedule you do not control."*
