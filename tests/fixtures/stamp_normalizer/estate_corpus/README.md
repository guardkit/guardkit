# The estate corpus — the stamp normalizer's NEGATIVE regression fixture

READ-ONLY copies of every primary-tree `.feature` across the estate repos
(tracked `features/**/*.feature`; lpa-platform-poc: `docs/poc/features/`),
at the SHAs listed in `MANIFEST.tsv` (115 files, 3,077 scenarios; worktrees,
archives and test fixtures excluded), plus each repo's SURFACE evidence
(`qa/gates/registry.yaml`, `.guardkit/config.yaml`, `pyproject.toml`,
`package.json`) so the HTTP surface is detected structurally from the fixture.

`EXPECTED.json` is the committed per-repo histogram of homes + REFUSED (the
honest number). `tests/orchestrator/test_stamp_normalizer_estate_corpus.py`
asserts (a) operator == the three enumerated explicit-human scenarios,
(b) hurl == 0 wherever there is no hurl gate / declared surface, (c) the
histogram equals this file. Re-baseline ONLY after a deliberate rule change:
`STAMP_CORPUS_REBASELINE=1 pytest tests/orchestrator/test_stamp_normalizer_estate_corpus.py`.

Do not edit the copies. Refresh = re-copy from the repos + update MANIFEST.tsv
+ re-baseline, in one commit that says so.

| repo | http | total | refused | bus | process | exam | flutter | playwright | hurl | operator |
|---|---|---|---|---|---|---|---|---|---|---|
| forge | no | 535 | 412 | 96 | 27 | 0 | 0 | 0 | 0 | 0 |
| jarvis | no | 279 | 229 | 44 | 6 | 0 | 0 | 0 | 0 | 0 |
| fleet-memory | no | 233 | 210 | 19 | 4 | 0 | 0 | 0 | 0 | 0 |
| fleet-gateway | no | 33 | 24 | 9 | 0 | 0 | 0 | 0 | 0 | 0 |
| specialist-agent | no | 796 | 731 | 28 | 2 | 35 | 0 | 0 | 0 | 0 |
| study-tutor | YES (starlette) | 501 | 444 | 14 | 10 | 3 | 28 | 1 | 0 | 1 |
| guardkit | no | 168 | 161 | 7 | 0 | 0 | 0 | 0 | 0 | 0 |
| lpa-platform-poc | no | 205 | 195 | 0 | 0 | 4 | 0 | 4 | 0 | 2 |
| agentic-dataset-factory | no | 253 | 251 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| api_test | YES (hurl-twins gate) | 74 | 41 | 0 | 17 | 0 | 0 | 0 | 16 | 0 |
| **TOTAL** | | **3077** | **2698** | 217 | 68 | 42 | 28 | 5 | 16 | 3 |

## Changes vs 8dd28830 (the second tightening, 2026-08-16)

The re-verifier of 8dd28830 found ~40 of 496 minted stamps still silently
mis-homed (8%). Six findings, six fixes — R4 = bus PROTOCOL ACTS only
(quotes blanked, `nats-core`-style identifiers excluded, negated acts
skipped) · R9 = STRONG wire markers only (the loose family is gone) · R2
negation within three words · R3 `smoke` requirement for the two generic
idioms · R7 judged-OUTPUT + score-as-input exclusion, and R7 now runs BEFORE
R4 · R10 "on the real NAS" refuses when an automation subject does the work.
This baseline was re-drawn DELIBERATELY (`STAMP_CORPUS_REBASELINE=1`).

**203 stamps moved.** Headline: hurl 133 → 16 (study-tutor 76 → 0, api_test
57 → 16 — every loose-idiom hand-hurl scenario now REFUSES rather than
minting by a bare noun; api_test reproduction is 32/60 same · 28 refused ·
0 silent divergences, was 57/60 · 3 divergent) · probe:bus 209 → 217 (32
name/quote/negation mis-homes out, 42 protocol acts in) · exam 44 → 42 (+2
domain-fidelity exams in from bus, −4 score-as-input out) · process 73 → 68 ·
operator 4 → 3 · refused 2,581 → 2,698. Every row below: title · old home →
new home · why.

### hurl → REFUSED (finding 2, R9 strong-only) — 117

| repo | scenario | old → new | why |
|---|---|---|---|
| study-tutor | A revision attempt that scores below an earlier accepted attempt is not emitted in place of it | hurl → REFUSED | finding 2 — R9 loose marker `response` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | Requesting session status returns its lifecycle state and turn count | hurl → REFUSED | finding 2 — R9 loose marker `requesting` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | Listing respects the requested limit and returns the most recent | hurl → REFUSED | finding 2 — R9 loose marker `requested` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | Session status is available even after a session has ended | hurl → REFUSED | finding 2 — R9 loose marker `requested` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | Acting on an unknown session reports the session as not found | hurl → REFUSED | finding 2 — R9 loose marker `not found` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | The tutor tool surface is unchanged after moving sessions onto the durable store | hurl → REFUSED | finding 2 — R9 loose marker `not-found` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A code path that would invoke the cross-encoder reranker is treated as a critical error | hurl → REFUSED | finding 2 — R9 loose marker `endpoint` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | The wired client construction never reads the OpenAI API key from the environment | hurl → REFUSED | finding 2 — R9 loose marker `endpoint` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | Two simultaneous Graphiti client constructions share the loaded configuration rather than racing on parse | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A learner is associated with the subjects they study and the texts they are working on | hurl → REFUSED | finding 2 — R9 loose marker `conflict` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | Recommending topics returns the requested number when enough are available | hurl → REFUSED | finding 2 — R9 loose marker `requested` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A malformed extraction response from the entity-extraction service fails the write without partial persistence | hurl → REFUSED | finding 2 — R9 loose marker `response` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | The service reports ready only once it is answering requests | hurl → REFUSED | finding 2 — R9 loose marker `requests` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | Every served endpoint matches the published binding table | hurl → REFUSED | finding 2 — R9 loose marker `endpoint` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A request without a token is rejected as unauthenticated | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | An unknown token is rejected as unauthenticated | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A client-asserted student identity is ignored in favour of the token's | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A session identifier that does not exist is reported as not found | hurl → REFUSED | finding 2 — R9 loose marker `not found` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A token mapping to an unseeded student is refused cleanly | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A malformed request is rejected without touching any session state | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | The dev reset does not exist under the prod configuration | hurl → REFUSED | finding 2 — R9 loose marker `route` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | The prod configuration accepts only the single configured student | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A token is honoured only from the credential header | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A tutor-loop failure mid-turn leaves the session consistent and resumable | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | The realm discovery document is served over the tailnet https issuer | hurl → REFUSED | finding 2 — R9 loose marker `requests` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | The identity service is not reachable from the public internet | hurl → REFUSED | finding 2 — R9 loose marker `route` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A plain-http issuer is not accepted as the realm issuer | hurl → REFUSED | finding 2 — R9 loose marker `rejected as` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | In table mode a configured token identifies its student | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | In keycloak mode a valid identity token identifies the student from its verified claim | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A streaming connection authenticates through the same resolver as the plain routes | hurl → REFUSED | finding 2 — R9 loose marker `routes` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | The Bearer extraction contract is identical in both modes | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A token whose expiry has not yet passed is accepted | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A token whose expiry has passed is rejected | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | Keycloak mode refuses to start when a required OIDC setting is missing | hurl → REFUSED | finding 2 — R9 loose marker `requests` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A token with an unrecognised signature is rejected | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A token from an unexpected issuer is rejected | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A token whose audience does not include this server is rejected | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A valid token missing the student claim is rejected as unauthenticated | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A valid token for an unseeded student is refused | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A non-Bearer Authorization header is rejected in both modes | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A token signed with a newly-rotated signing key still validates | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | Signing keys are fetched by tailnet address while the issuer stays pinned to the realm name | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | The developer reset route and keycloak mode never coexist | hurl → REFUSED | finding 2 — R9 loose marker `route` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A token using an unexpected signing algorithm is rejected | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A token referencing an unknown signing key is rejected | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | When the realm's signing keys are unreachable tokens are refused cleanly | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A garbage Bearer value is refused as unauthenticated in keycloak mode | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A token that is not yet valid is rejected | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | SIGTERM during an in-flight tutor turn drains the request before deregistration | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A command arriving before the adapter is ready is rejected with a clear error | hurl → REFUSED | finding 2 — R9 loose marker `rejected with` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A command with an unknown name is rejected with a list of supported commands | hurl → REFUSED | finding 2 — R9 loose marker `rejected with` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | SIGTERM during an in-flight tutor turn drains the request before deregistration | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A retrieval request for a text absent from the corpus returns an empty result with an explicit reason | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | The student-model lookup reads from the durable student store | hurl → REFUSED | finding 2 — R9 loose marker `looks up` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | Tutoring-turn responsiveness depends on the tutor model's residency | hurl → REFUSED | finding 2 — R9 loose marker `response` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A typed question's answer streams while it is still being composed | hurl → REFUSED | finding 2 — R9 loose marker `requesting` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | Asking without streaming still returns the whole answer in one response | hurl → REFUSED | finding 2 — R9 loose marker `requesting` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | Streaming never waits for the tutor's quality review | hurl → REFUSED | finding 2 — R9 loose marker `requesting` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | Streaming a turn on an ended session is refused | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | The live channel for an unknown session is refused as not found | hurl → REFUSED | finding 2 — R9 loose marker `not found` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | Answer generation fails partway through streaming | hurl → REFUSED | finding 2 — R9 loose marker `requesting` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | An announced chunk reference is valid only within its own session | hurl → REFUSED | finding 2 — R9 loose marker `not found` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A tutor model that stalls without producing anything ends in a visible failure | hurl → REFUSED | finding 2 — R9 loose marker `requesting` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A confidence update outside the valid percentage range is rejected | hurl → REFUSED | finding 2 — R9 loose marker `rejected as` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A recording just over the size cap is rejected as too large | hurl → REFUSED | finding 2 — R9 loose marker `rejected as` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A recording just over the duration cap is rejected as too long | hurl → REFUSED | finding 2 — R9 loose marker `rejected as` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A recording in an unsupported format is rejected naming the received type | hurl → REFUSED | finding 2 — R9 loose marker `rejected as` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | An empty recording is rejected | hurl → REFUSED | finding 2 — R9 loose marker `rejected as` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A recording the tutor cannot make out is rejected as not understood | hurl → REFUSED | finding 2 — R9 loose marker `rejected as` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A voice turn on another student's session is refused | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A voice turn without valid credentials is refused | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A voice turn on an ended session is refused | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | Another student cannot fetch my reply audio | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | When speech services are unavailable, voice degrades and text tutoring continues | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A speech service that stops responding fails the voice turn cleanly | hurl → REFUSED | finding 2 — R9 loose marker `requests` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| study-tutor | A recording whose true size exceeds the cap is rejected even if it claims to be smaller | hurl → REFUSED | finding 2 — R9 loose marker `rejected as` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | The ready endpoint returns success when the service is ready | hurl → REFUSED | finding 2 — R9 loose marker `endpoint` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | The ready endpoint returns failure when the service is not ready | hurl → REFUSED | finding 2 — R9 loose marker `endpoint` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | The ready endpoint responds within an acceptable time | hurl → REFUSED | finding 2 — R9 loose marker `endpoint` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | The ready endpoint is accessible at the standard path | hurl → REFUSED | finding 2 — R9 loose marker `endpoint` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | The endpoint reflects readiness state changes | hurl → REFUSED | finding 2 — R9 loose marker `endpoint` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | A user created through the service reads back with identical details | hurl → REFUSED | finding 2 — R9 loose marker `through the service` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Looking up a user that was never created is reported as not found | hurl → REFUSED | finding 2 — R9 loose marker `not found` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Creating a user with an email already in use is rejected as a conflict | hurl → REFUSED | finding 2 — R9 loose marker `conflict` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | A malformed user submission is rejected as invalid | hurl → REFUSED | finding 2 — R9 loose marker `rejected as` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Requesting statistics returns the service identity and request activity | hurl → REFUSED | finding 2 — R9 loose marker `requesting` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | The served-request count increases as requests are handled | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | The first-request time is stable once set | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | The served-request count never decreases while the service is running | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Modifying the statistics is not allowed | hurl → REFUSED | finding 2 — R9 loose marker `not allowed` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Requesting uptime returns the service identity and running time | hurl → REFUSED | finding 2 — R9 loose marker `requesting` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Uptime increases between consecutive requests | hurl → REFUSED | finding 2 — R9 loose marker `requests` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Attempting to modify the uptime resource is rejected | hurl → REFUSED | finding 2 — R9 loose marker `endpoint` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Searching for a partial name returns matching users | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Searching with lowercase matches uppercase names | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Searching with an empty name returns all users | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Searching with a single character returns all users containing that character | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Searching for a name with no matches returns an empty list | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Searching with special characters returns exact literal matches | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Searching with only whitespace returns all users | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Requesting search without a name parameter returns an error | hurl → REFUSED | finding 2 — R9 loose marker `requesting` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | An existing user is found by their email | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | The lookup returns exactly the matching user among several | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | An unknown email returns not-found | hurl → REFUSED | finding 2 — R9 loose marker `not-found response` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | A malformed email is rejected as invalid input | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Requesting a user by id still works alongside the by-email route | hurl → REFUSED | finding 2 — R9 loose marker `requesting` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | The count reflects the number of stored users | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | The count of an empty store is zero | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Creating a user increments the count | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Requesting a user by id still works alongside the count route | hurl → REFUSED | finding 2 — R9 loose marker `requesting` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Attempting to modify the users count is rejected | hurl → REFUSED | finding 2 — R9 loose marker `endpoint` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | An existing user is deleted by their email | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Deleting by email removes exactly the matching user | hurl → REFUSED | finding 2 — R9 loose marker `looking up` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Deleting an unknown email reports not found | hurl → REFUSED | finding 2 — R9 loose marker `not-found response` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Deleting the same email twice reports not found the second time | hurl → REFUSED | finding 2 — R9 loose marker `not-found response` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | A malformed email address is rejected as invalid | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |
| api_test | Deleting by id still works alongside the by-email route | hurl → REFUSED | finding 2 — R9 loose marker `request` is gone; no strong wire marker (verb+path/endpoint, status code, method not allowed, content type) in the scenario → REFUSED (loud) |

### probe:bus → REFUSED (finding 1, R4 names / quotes / identifiers / negation) — 32

| repo | scenario | old → new | why |
|---|---|---|---|
| forge | A transient sidecar disconnection mid-build does not produce a spurious build-failed envelope | probe:bus → REFUSED | finding 1 — R4 `envelope` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| forge | An in-sidecar emit carrying a correlation identifier that does not match the registered build is rejected | probe:bus → REFUSED | finding 1 — R4 `envelope` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| forge | The production image builds from a fresh clone using the canonical invocation | probe:bus → REFUSED | finding 1 — R4 `nats` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| forge | The build fails with a clear diagnostic when the nats-core build context is missing | probe:bus → REFUSED | finding 1 — R4 `nats` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| forge | A stale image whose fleet manifest has drifted is detected before a build is dispatched | probe:bus → REFUSED | finding 1 — R4 `fleet manifest` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| forge | A failed lifecycle publish does not regress the build's recorded transition | probe:bus → REFUSED | finding 1 — R4 `envelope` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| forge | Queueing a build from the assistant notifies my phone that it is queued | probe:bus → REFUSED | finding 1 — R4 `published to` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| forge | A greenfield build with no available specialists is flagged for review at every specialist stage | probe:bus → REFUSED | finding 1 — R4 `on the fleet` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| forge | A Mode B build does not record a degraded-specialist rationale because no specialist dispatch is attempted | probe:bus → REFUSED | finding 1 — R4 `on the fleet` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| forge | When two agents at the same trust tier advertise the same tool, the one with the shallower queue is preferred | probe:bus → REFUSED | finding 1 — R4 `heartbeat` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| forge | Queueing a build against a repository path outside the allowlist is refused | probe:bus → REFUSED | finding 1 — R4 `published to` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| forge | Queueing with a feature identifier that contains path-traversal characters is refused | probe:bus → REFUSED | finding 1 — R4 `published to` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| forge | A build row is written but the pipeline publish then fails | probe:bus → REFUSED | finding 1 — R4 `publishing to` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| forge | A specialist reporting degraded status is excluded from resolution | probe:bus → REFUSED | finding 1 — R4 `heartbeat` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| jarvis | Stubbed dispatches construct real nats-core payloads before logging | probe:bus → REFUSED | finding 1 — R4 `nats` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| jarvis | Queueing a build when the dispatch concurrency cap is saturated returns a degraded response | probe:bus → REFUSED | finding 1 — R4 `published to` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| jarvis | Queueing a build with invalid arguments returns a structured validation error | probe:bus → REFUSED | finding 1 — R4 `published to` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| fleet-memory | The project resource lists the projects that have memories | probe:bus → REFUSED | finding 1 — R4 `nats` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| fleet-memory | A reviewed backfill payload is published on the next run | probe:bus → REFUSED | finding 1 — R4 `published on` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| fleet-gateway | Building a command envelope from a user message | probe:bus → REFUSED | finding 1 — R4 `envelope` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| fleet-gateway | Correlation identifier is honoured or generated | probe:bus → REFUSED | finding 1 — R4 `envelope` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| fleet-gateway | OpenWebUI pipe rejects a request body with no messages | probe:bus → REFUSED | finding 1 — R4 `envelope` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| fleet-gateway | The deployable OpenWebUI pipe is self-contained | probe:bus → REFUSED | finding 1 — R4 `nats` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| fleet-gateway | Two interleaved tool calls produce distinct correlation identifiers | probe:bus → REFUSED | finding 1 — R4 `envelopes` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| fleet-gateway | OpenWebUI pipe extracts response text when payload nesting differs | probe:bus → REFUSED | finding 1 — R4 `envelope` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| specialist-agent | Mode inference works via NATS CommandPayload | probe:bus → REFUSED | finding 1 — R4 `nats` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| specialist-agent | Confirmation prompt is natural language suitable for voice | probe:bus → REFUSED | finding 1 — R4 `nats` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| specialist-agent | Processing an answer generates follow-up questions | probe:bus → REFUSED | finding 1 — R4 `nats` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| specialist-agent | Query results are scoped and ordered by project then role then fleet | probe:bus → REFUSED | finding 1 — R4 `jetstream` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| specialist-agent | Agent processes two concurrent commands within capacity | probe:bus → REFUSED | finding 1 — R4 `heartbeat` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| specialist-agent | An attended session without fleet dispatch records its lineage as absent by design | probe:bus → REFUSED | finding 1 — R4 `fleet dispatch` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |
| guardkit | An eval with a weighted score exactly at the escalate threshold fails but is not escalated | probe:bus → REFUSED | finding 1 — R4 `published to` was a bare name / package identifier / quoted data literal / negated act, not a protocol act → REFUSED |

### REFUSED → probe:bus (finding 1, the protocol-act family reads acts the noun family did not) — 42

| repo | scenario | old → new | why |
|---|---|---|---|
| forge | A stage with ambiguous evidence pauses and requests human review | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `published for human attention on the build-specific approval channel` is a protocol act the old noun family did not read → probe:bus |
| forge | The database password never appears in the runbook record or events | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `published lifecycle events` is a protocol act the old noun family did not read → probe:bus |
| forge | The run produces an ordered event stream and a queryable per-step record | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `lifecycle events should be published` is a protocol act the old noun family did not read → probe:bus |
| forge | A duplicated approval reply resumes the build only once | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `approval reply is delivered` is a protocol act the old noun family did not read → probe:bus |
| forge | An approval reply carrying the wrong correlation is refused | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `approval reply arrives` is a protocol act the old noun family did not read → probe:bus |
| forge | An approval response is routed to the build whose identifier matches the response channel | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `approval response is received` is a protocol act the old noun family did not read → probe:bus |
| forge | Two simultaneous approval responses for the same paused build resolve as first-wins | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `approval responses arrive` is a protocol act the old noun family did not read → probe:bus |
| forge | Every published lifecycle event for a build threads the same correlation identifier from queue to terminal | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `lifecycle event published` is a protocol act the old noun family did not read → probe:bus |
| forge | An approval response is routed to the Mode B or Mode C build whose identifier matches the response channel | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `approval response is received` is a protocol act the old noun family did not read → probe:bus |
| forge | Every published lifecycle event for a Mode B or Mode C build threads the same correlation identifier from queue to terminal | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `lifecycle event published` is a protocol act the old noun family did not read → probe:bus |
| forge | Two simultaneous approval responses for the same paused build resolve as first-wins | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `approval responses arrive` is a protocol act the old noun family did not read → probe:bus |
| forge | Completed product docs pause the run at the product docs checkpoint | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `approval request should be sent` is a protocol act the old noun family did not read → probe:bus |
| forge | A redelivered planning request does not create a second run | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `planning request is delivered` is a protocol act the old noun family did not read → probe:bus |
| forge | Forge maintains a live cache of fleet agents | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `registered with the fleet` is a protocol act the old noun family did not read → probe:bus |
| forge | A newly-registered specialist becomes available for resolution | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `publishes its registration` is a protocol act the old noun family did not read → probe:bus |
| forge | Simultaneous fleet-change events update the cache without loss | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `publish registration` is a protocol act the old noun family did not read → probe:bus |
| forge | A reply from a source other than the resolved specialist is not trusted | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `reply arrives on the correlation-keyed channel` is a protocol act the old noun family did not read → probe:bus |
| forge | A duplicate reply on the same correlation-keyed channel is ignored | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `reply on the same correlation-keyed channel` is a protocol act the old noun family did not read → probe:bus |
| jarvis | Queueing a build publishes the request to Forge and returns a queued acknowledgement | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `receive the build-queued request` is a protocol act the old noun family did not read → probe:bus |
| jarvis | A reasoning-model attempt to override the originating adapter is silently overridden by the session adapter | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `published build-queued request` is a protocol act the old noun family did not read → probe:bus |
| jarvis | Queueing a build without an active session uses the originating-adapter argument as a fallback | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `published build-queued request` is a protocol act the old noun family did not read → probe:bus |
| jarvis | A follow-up chat request on the same conversation sees the earlier turn | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `sent one chat request to jarvis through the fleet` is a protocol act the old noun family did not read → probe:bus |
| jarvis | The queued planning request is valid against the installed event contract | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `published message should round-trip through the installed planning-queue` is a protocol act the old noun family did not read → probe:bus |
| jarvis | A message in a channel other than the planning channel is ignored | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `planning channel is` is a protocol act the old noun family did not read → probe:bus |
| jarvis | A redelivered message event is queued exactly once | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `redelivered message` is a protocol act the old noun family did not read → probe:bus |
| fleet-memory | A structured JSON episode is dispatched through the registry to the deterministic writer | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `episode should be acknowledged` is a protocol act the old noun family did not read → probe:bus |
| fleet-memory | A markdown episode is chunked, embedded, and stored as chunks under the project chunk namespace | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `episode should be acknowledged` is a protocol act the old noun family did not read → probe:bus |
| fleet-memory | A plain text episode is chunked and embedded on the same path as markdown | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `episode should be acknowledged` is a protocol act the old noun family did not read → probe:bus |
| fleet-memory | A mixed batch of structured and prose episodes yields typed records and chunks | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `episodes should be acknowledged` is a protocol act the old noun family did not read → probe:bus |
| fleet-memory | An episode is acknowledged only after it is durably stored | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `episode is acknowledged` is a protocol act the old noun family did not read → probe:bus |
| fleet-memory | A prose episode with an empty body produces no chunks and is acknowledged | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `episode should be acknowledged` is a protocol act the old noun family did not read → probe:bus |
| fleet-memory | Redelivery of an already-chunked prose episode creates no duplicate chunks | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `redelivery of an already-chunked prose episode` is a protocol act the old noun family did not read → probe:bus |
| fleet-memory | A prose episode interrupted partway through chunking leaves no partial chunk set | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `episode is redeliver` is a protocol act the old noun family did not read → probe:bus |
| specialist-agent | Agent receives and executes an alignment command | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `registered with the fleet` is a protocol act the old noun family did not read → probe:bus |
| specialist-agent | Agent receives and executes an explore command | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `registered with the fleet` is a protocol act the old noun family did not read → probe:bus |
| specialist-agent | Manifest with metadata at the 64KB limit is accepted | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `the manifest should be published` is a protocol act the old noun family did not read → probe:bus |
| specialist-agent | Agent rejects an unrecognised command | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `registered with the fleet` is a protocol act the old noun family did not read → probe:bus |
| specialist-agent | Agent rejects a command with missing required arguments | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `registered with the fleet` is a protocol act the old noun family did not read → probe:bus |
| specialist-agent | Agent rejects command args containing path traversal | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `registered with the fleet` is a protocol act the old noun family did not read → probe:bus |
| specialist-agent | Simultaneous registration with the same agent_id resolves cleanly | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `publish manifests` is a protocol act the old noun family did not read → probe:bus |
| specialist-agent | Agent handles a MessageEnvelope with an unknown schema version | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `registered with the fleet` is a protocol act the old noun family did not read → probe:bus |
| specialist-agent | A fleet-dispatched session records its correlation lineage | REFUSED → probe:bus | finding 1 (act family) — the bus VERB+NOUN pair `dispatched over the fleet` is a protocol act the old noun family did not read → probe:bus |

### probe:bus → exam (finding 1, R7 before R4) — 2

| repo | scenario | old → new | why |
|---|---|---|---|
| specialist-agent | Coach detects DOMAIN_DILUTION when only some domain terms are genericised | probe:bus → exam | finding 1 — R7 now runs before R4: the Then judges the Coach's output (`coach should report`); the bus word was a quoted scope input → exam |
| specialist-agent | Coach penalises when Player omits explicitly scoped technology | probe:bus → exam | finding 1 — R7 now runs before R4: the Then judges the Coach's output (`coach should report`); the bus word was a quoted scope input → exam |

### probe:process → REFUSED (findings 3 and 4) — 5

| repo | scenario | old → new | why |
|---|---|---|---|
| forge | Events emitted while the bridge was down are not replayed on restart | probe:process → REFUSED | finding 3 — R2 `restart` is negated within three words (without/never/no/not/instead of) → REFUSED |
| forge | After a failure, re-running resumes at the failed step without restarting | probe:process → REFUSED | finding 3 — R2 `restarting` is negated within three words (without/never/no/not/instead of) → REFUSED |
| fleet-memory | The service recovers after a transient database outage | probe:process → REFUSED | finding 3 — R2 `restarting` is negated within three words (without/never/no/not/instead of) → REFUSED |
| specialist-agent | The verdict reflects that fine-tune wins on some axes and loses on others | probe:process → REFUSED | finding 4 — R3 `verdict should be reported` is generic without `smoke` (or `smoke\|sandbox` for the oracle idiom) in the scenario → REFUSED |
| guardkit | An oracle command that overruns its time budget is reported as timed out | probe:process → REFUSED | finding 4 — R3 `oracle time budget` is generic without `smoke` (or `smoke\|sandbox` for the oracle idiom) in the scenario → REFUSED |

### exam → REFUSED (finding 5) — 4

| repo | scenario | old → new | why |
|---|---|---|---|
| specialist-agent | Structural quality does not regress after domain fidelity additions | exam → REFUSED | finding 5 — R7 `score should be at least 0.`: the score is a Given/When INPUT (numeral / Outline column / threshold comparison), a bare `decision`, or `should score` plumbing — not a judged output → REFUSED |
| specialist-agent | Coach acceptance is computed against the same six weighted criteria as the baseline | exam → REFUSED | finding 5 — R7 `coach should score`: the score is a Given/When INPUT (numeral / Outline column / threshold comparison), a bare `decision`, or `should score` plumbing — not a judged output → REFUSED |
| study-tutor | A Player response that meets the Coach threshold is emitted to the learner | exam → REFUSED | finding 5 — R7 `coach decision should`: the score is a Given/When INPUT (numeral / Outline column / threshold comparison), a bare `decision`, or `should score` plumbing — not a judged output → REFUSED |
| study-tutor | Scores at and around the acceptance threshold drive the accept-or-revise decision | exam → REFUSED | finding 5 — R7 `coach decision should`: the score is a Given/When INPUT (numeral / Outline column / threshold comparison), a bare `decision`, or `should score` plumbing — not a judged output → REFUSED |

### operator → REFUSED (finding 6) — 1

| repo | scenario | old → new | why |
|---|---|---|---|
| forge | The executor stands fleet-memory up on the real NAS | operator → REFUSED | finding 6 — R10 `on the real nas` with an automation subject (the executor) in the When/Then → undecidable by rule → REFUSED |

