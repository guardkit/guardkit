# AutoBuild harness cutover — LangGraph is now the default (AC-005 announce draft)

> **Status:** DRAFT, ready to send. AC-005 of [TASK-HMIG-011](./TASK-HMIG-011-cutover-ceremony-flip-default-harness.md).
> Operator picks the channel(s) + audience and sends; check AC-005 once sent.
> Two versions below — a short one for a chat channel, a full one for docs/email.

---

## Short version (chat / Slack)

> 📣 **AutoBuild now runs on the LangGraph harness by default.** The flip landed
> 2026-06-16 — with `GUARDKIT_HARNESS` unset, `guardkit autobuild …` routes
> through LangGraph (local models via `OPENAI_BASE_URL`), not the Claude Agent
> SDK. The SDK path stays available as an emergency fallback:
> `GUARDKIT_HARNESS=sdk guardkit autobuild …` (per-invocation) or export it.
> Nothing to do if you weren't pinning a harness. Rollback is a one-line revert
> (`DEFAULT_HARNESS` in `selector.py`). Validated on FEAT-9DDE + FEAT-FAUD.
> Details: TASK-HMIG-011.

---

## Full version (README note / email / downstream consumers)

**What changed.** As of **2026-06-16**, GuardKit AutoBuild defaults to the
**LangGraph** harness. Previously the default was the Claude Agent SDK harness;
LangGraph was opt-in. That is now inverted: with `GUARDKIT_HARNESS` unset,
`guardkit autobuild task|feature …` runs on LangGraph.

**Why.** The LangGraph migration (FEAT-HMIG) is complete and validated — the
5-layer fix chain proven by TASK-HMIG-009A, and recent full-feature runs
(FEAT-9DDE, FEAT-FAUD) are green. LangGraph drives local models via
`OPENAI_BASE_URL`, so it is unaffected by Anthropic API-key validation
(the SDK path's `ANTHROPIC_BASE_URL` redirect to a local endpoint can break
under that enforcement).

**What you need to do.**
- **Most users / downstream consumers (jarvis, forge, dataset-factory):**
  nothing — the new default just works.
- **If you were relying on the SDK path** with local models via an
  `ANTHROPIC_BASE_URL` redirect: prefer the new default (LangGraph), or pin the
  SDK explicitly while you migrate (see below). The SDK path remains fully
  functional as a fallback.

**Opt back to the SDK (emergency fallback — fully supported).**
```bash
# Per-invocation:
GUARDKIT_HARNESS=sdk guardkit autobuild task TASK-XXX
# Or for a shell/session:
export GUARDKIT_HARNESS=sdk
```

**Rollback (permanent revert of the default).** One line —
[`guardkit/orchestrator/harness/selector.py:49`](../../../guardkit/orchestrator/harness/selector.py#L49):
```python
DEFAULT_HARNESS = "langgraph"   # change back to "sdk" to revert the default
```
Commit + redeploy. (The SDK adapter stays in-repo; no SDK code was removed.)

**Support window.** The SDK harness remains available as a fallback indefinitely
for now — the Anthropic key-validation cutoff that originally scheduled SDK
removal was cancelled, so Phase-3 dependency removal (`ClaudeSDKHarness` +
`claude-agent-sdk`) is **optional**, not deadline-driven.

**Where the default lives (one place):** `selector.py`'s `DEFAULT_HARNESS`
constant, resolved in `select_harness()` (`os.environ.get("GUARDKIT_HARNESS",
DEFAULT_HARNESS)`). `cli/autobuild.py` neither reads nor sets the env var.

**Traceability:** TASK-HMIG-011 (cutover ceremony), parent review TASK-REV-HMIG §7.4.
