# ADR-FLEET-003 — Agent capability exposure: MCP for agent-hosts, HTTP/WS for app clients

**Status:** Accepted
**Date:** 2 July 2026
**Scope:** Fleet-wide — any agent exposed to more than one class of consumer (study-tutor, forge, specialist-agent, jarvis, …)
**Author:** Rich Woollcott (worked through with Claude)
**Relates to:** study-tutor mobile + voice client (see conversation-starter); ADR-POC-015 (GB10 voice endpoints)

---

## Context

Fleet agents encapsulate real capability — a fine-tuned model, session state, RAG, a review loop. A recurring question: when a capability must be reached by more than one kind of caller, what interface do you expose?

The confusion this ADR settles is treating **MCP as the universal interface**, including for app and device clients. Concretely — the study-tutor is exposed as an MCP server (`start` / `turn` / `status` / `end`) and was reached during the software-factory work via the Reachy → jarvis bridge (reused for convenience). When scoping a mobile app plus direct robot voice, the open question was whether the app should also speak MCP.

The underlying point: **MCP's value proposition is tool *discovery and invocation by a model*.** An app or device client is a deterministic caller making known calls to a known backend — it is not a model-driven host, and gains nothing from tool-discovery.

## Decision

1. **The agent core is the single source of truth.** Capability — logic, session state, model, RAG, review — lives once, transport-agnostic.

2. **Expose capability through thin adapters, chosen by consumer type:**
   - **MCP adapter** — for LLM / agent-host consumers: Claude Desktop (dev loop), Cowork, other fleet agents, an intent-router such as jarvis. Justified because a *model* discovers and calls the tools.
   - **HTTP / WebSocket adapter** — for deterministic app and device clients: mobile apps, web apps, robot bridges, UIs. REST for request/response; WebSocket for real-time and streaming (voice).

3. **One capability contract, two transports.** Where an MCP tool-set already defines the operations (study-tutor's four verbs), the HTTP/WS API **mirrors that exact shape** — create a session, post a turn, get status, end — so there is one semantic surface behind both transports. The MCP work is not wasted; it specified the contract.

4. **Rule of thumb:** put MCP in a path **only where the consumer is a model doing tool-discovery.** If the consumer is an app making known calls, use HTTP/WS. Never route an app through MCP for its own sake.

5. **Real-time media never traverses MCP.** Voice uses the WebSocket adapter directly: device → WS → STT → agent `turn` → TTS → stream back.

## Consequences

**Positive**
- No wasted MCP work — it defined the session contract the HTTP/WS API reuses.
- Apps get an idiomatic API; the voice hot path stays lean.
- The pattern **generalises**: any specialist agent reachable by both an agent-host and a UI uses the same two-adapter split. (The moment jarvis *and* a person's app both need forge, this is the answer.)
- Clean deployment story: the **product surface behind auth is the HTTP/WS API**; the MCP server is dev-time and fleet-integration tooling and need not deploy to the cloud. Two audiences, two interfaces.

**Costs / obligations**
- Two adapters to maintain — mitigated by keeping them thin and having both call the *same* core service methods, so behaviour can't drift.
- The contract must stay single-sourced. Prefer one schema / interface that both the MCP tools and the HTTP handlers are generated from or delegate to; do not let the two transports diverge into two definitions.

## Alternatives considered

- **MCP everywhere (apps included).** Rejected: indirection with no benefit for deterministic clients; forces apps to participate in tool-discovery they don't need; awkward for streaming voice.
- **HTTP/WS everywhere (drop MCP).** Rejected: loses the genuine value of MCP for agent-host consumers — the Claude Desktop dev loop, fleet agent-to-agent, intent routing — where a model discovering and calling tools is the whole point.

## Note on jarvis (recorded so it doesn't recur)

jarvis as a bridge to study-tutor was **transport reuse** — the Reachy → jarvis bridge already existed for the software factory, so routing study-tutor behind it was the path of least resistance. It is **not** the intended long-term interaction model. Going forward, clients interact with study-tutor **directly** via its HTTP/WS adapter. jarvis remains a legitimate agent-host consumer of MCP interfaces across the fleet (intent routing), but is not on study-tutor's primary path.

---

*Prepared: 2 July 2026 | fleet architecture — agent interface boundary*
