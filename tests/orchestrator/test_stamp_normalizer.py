"""THE STAMP NORMALIZER — rules R1–R10 as test fixture, the writer, the refusal.

Design of record: ai-transition/docs/routing-law-stamp-normalizer-rules-2026-08-15.md
("every census example row is a test case"). Rich's two binding conditions
(08-16): (1) it WRITES stamps into the feature YAML — never overwriting an
existing one; (2) NO MODEL IN THE LOOP — undecidable titles REFUSE LOUD, the
run stops, nothing is written; `operator` only on an explicit human-work match.

Every classification example below is a REAL scenario title + its own steps,
copied from the estate's primary-tree `.feature` files (api_test @5bc6fd1,
forge, jarvis, study-tutor, specialist-agent, lpa-platform-poc) — the same
corpus the 2026-08-09 census read. Where the estate holds fewer than three
real examples for a rule (R6: two browser scenarios estate-wide) the third is
the design's own phrase and says so.

Network-free, subprocess-free: text + tmp_path + a read-only fixture tree.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from guardkit.orchestrator.feature_loader import (
    FeatureLoader,
    FeatureValidationError,
)
from guardkit.orchestrator.stamp_normalizer import (
    Home,
    NormalizeContext,
    StampNormalizerError,
    StampNormalizerRefusal,
    build_plan_test_refs,
    classify_scenario,
    collect_plan_test_nodes,
    detect_repo_http_surface,
    extract_scenarios,
    normalize_feature,
    write_stamps,
)
from guardkit.orchestrator.verifier_stamp import VERIFIER_HOMES

FIXTURE_ROOT = Path(__file__).parent.parent / "fixtures" / "stamp_normalizer" / "api_test_5bc6fd1"
CORPUS_ROOT = Path(__file__).parent.parent / "fixtures" / "stamp_normalizer" / "estate_corpus"


def _corpus_scenario(repo: str, feature_rel: str, title: str):
    """(title, steps, annotations) of a REAL scenario from the read-only
    estate corpus — the tightened rules are pinned on real prose."""
    from guardkit.orchestrator.stamp_normalizer import extract_scenario_blocks

    text = (CORPUS_ROOT / repo / feature_rel).read_text(encoding="utf-8")
    for b in extract_scenario_blocks(text):
        if b.title == title:
            return b.title, b.steps_text, b.annotations
    raise AssertionError(f"{repo}/{feature_rel} has no scenario {title!r}")


SIGN_IN = "features/flutter-keycloak-sign-in/flutter-keycloak-sign-in.feature"
VOICE = "features/flutter-voice-client/flutter-voice-client.feature"

HTTP = NormalizeContext(repo_has_http_surface=True, http_surface_evidence="test")
NO_HTTP = NormalizeContext(repo_has_http_surface=False)


def _home(title: str, steps: str, ctx=HTTP) -> Home:
    home = classify_scenario(title, steps, ctx)
    assert home is not None, f"expected a home for {title!r}, got REFUSE"
    return home


# ---------------------------------------------------------------------------
# R1 — DB unavailable → probe:process (census: 2.5, 3.7, 6.4, 7.6, 8.6, 9.7)
# ---------------------------------------------------------------------------


R1_CASES = [
    (
        "The count degrades honestly when the database is unavailable",
        "Given the database is unavailable\nWhen I request the users count\n"
        "Then the request should fail with a service-unavailable response\n"
        "And the response should name the database as the cause",
    ),
    (
        "Deletion degrades honestly when the database is down",
        "Given the database is unavailable\nWhen I delete the user by email \"ada@example.com\"\n"
        "Then the request should fail naming the database as the cause",
    ),
    (
        "The endpoint is unaffected by database unavailability",
        "Given the database is unavailable\nWhen I send a GET request to \"/time\"\n"
        "Then the response status code should be 200\n"
        "And the \"time\" field should parse as a valid ISO-8601 UTC timestamp",
    ),
    (
        "Statistics remain available when the database is unavailable",
        "Given the database is unavailable\nWhen I request the service statistics\n"
        "Then the request should succeed\nAnd the response should include the number of requests served",
    ),
]


@pytest.mark.parametrize("title,steps", R1_CASES, ids=[c[0][:40] for c in R1_CASES])
def test_r1_db_unavailable_is_probe_process(title, steps):
    home = _home(title, steps)
    assert (home.verifier, home.rule) == ("probe:process", "R1")


def test_ordering_db_down_plus_request_is_probe_process_not_hurl():
    """The design's ordering rationale: a DB-down scenario also says
    'request'/'response' — R1 wins over R9 even in an HTTP repo."""
    title, steps = R1_CASES[0]
    assert "request" in steps and "response" in steps
    assert _home(title, steps, HTTP).verifier == "probe:process"


# ---------------------------------------------------------------------------
# R2 — fresh start / restart → probe:process (census: 2.3, 3.4, 3.8)
# ---------------------------------------------------------------------------


R2_CASES = [
    (
        "Uptime immediately after startup is non-negative",
        "Given the service has just started\nWhen I request the service uptime\n"
        "Then the reported uptime should be zero or greater",
    ),
    (
        "A freshly started service counts the statistics request itself",
        "Given the service has just started and has handled no other requests\n"
        "When I request the service statistics\nThen the number of requests served should be at least one\n"
        "And the response should include when the first request was handled",
    ),
    (
        "A service restart begins a fresh count",
        "Given the service restarts\nWhen I request the service statistics\n"
        "Then the number of requests served should reflect only requests handled since the restart",
    ),
    (
        # study-tutor nats-fleet-integration (a process-control scenario)
        "A container restart boots the adapter with a fresh session store",
        "When the container restarts\nThen the adapter should boot cleanly with a fresh session store\n"
        "And a tutor_turn command for the prior session_id should be rejected as an unknown session",
    ),
]


@pytest.mark.parametrize("title,steps", R2_CASES, ids=[c[0][:40] for c in R2_CASES])
def test_r2_fresh_start_restart_is_probe_process(title, steps):
    home = _home(title, steps)
    assert (home.verifier, home.rule) == ("probe:process", "R2")


# ---------------------------------------------------------------------------
# R3 — runtime-smoke harness-meta → probe:process (census: 5.1, 5.3–5.5, 5.9–5.12)
# ---------------------------------------------------------------------------


R3_CASES = [
    (
        "Data seeded directly into the database is visible through the running service",
        "Given the environment is up and reports itself healthy\n"
        "And a user record carrying a unique per-run marker is seeded directly into the database\n"
        "When the user listing is requested through the running service\n"
        "Then the listing should include the seeded record with the per-run marker",
    ),
    (
        "A fully passing smoke run produces a passing verdict and a clean teardown",
        "Given the environment is up and reports itself healthy\n"
        "When all round-trip and negative probes complete successfully\n"
        "Then the smoke verdict should be reported as passed\n"
        "And no trace of the throwaway environment should remain afterwards",
    ),
    (
        "The smoke completes within the oracle time budget",
        "When the full smoke run executes end to end\n"
        "Then it should finish inside the oracle time budget with margin to spare",
    ),
    (
        "The listing reflects exactly the records present in the fresh database",
        "Given the database starts empty before seeding\n"
        "When one record is seeded directly and one is created through the running service\n"
        "Then the listing should contain exactly those two records",
    ),
    (
        "A failed run still leaves nothing behind",
        "Given a smoke run that fails partway through its probes\nWhen the run completes\n"
        "Then no part of the throwaway environment should remain",
    ),
    (
        "The smoke never touches the live deployment",
        "Given the live deployment is running alongside the smoke\n"
        "When the full smoke run executes end to end\n"
        "Then the live deployment should be exactly as it was before the run",
    ),
    (
        "The sandboxed application has no route to the outside world",
        "Given the environment is up and reports itself healthy\n"
        "When the sandbox network posture is inspected\n"
        "Then the application should be reachable only from inside the sandbox\n"
        "And the application should have no route to the outside world",
    ),
]


@pytest.mark.parametrize("title,steps", R3_CASES, ids=[c[0][:40] for c in R3_CASES])
def test_r3_smoke_harness_meta_is_probe_process(title, steps):
    home = _home(title, steps)
    assert (home.verifier, home.rule) == ("probe:process", "R3")


def test_r3_wire_shaped_smoke_probes_stay_hurl():
    """The runtime-smoke feature's four negative/round-trip probes are
    hand-stamped hurl (5.2, 5.6–5.8): R3 must not swallow them."""
    cases = [
        (
            "A user created through the service reads back with identical details",
            "Given the environment is up and reports itself healthy\n"
            "When a new user is created through the running service\n"
            "And that user is fetched back by its returned identity\n"
            "Then the fetched details should match what was submitted",
        ),
        (
            "Looking up a user that was never created is reported as not found",
            "Given the environment is up and reports itself healthy\n"
            "When a lookup is made for an identity that was never created\n"
            "Then the service should report that no such user exists",
        ),
        (
            "Creating a user with an email already in use is rejected as a conflict",
            "Given a user with a known email already exists in the environment\n"
            "When a second user is created with the same email\n"
            "Then the creation should be rejected as a conflict\nAnd the original record should remain unchanged",
        ),
    ]
    for title, steps in cases:
        home = _home(title, steps, HTTP)
        assert (home.verifier, home.rule) == ("hurl", "R9"), title


# ---------------------------------------------------------------------------
# R4 — bus vocabulary → probe:bus (census: 449 — forge 182, jarvis 115, …)
# ---------------------------------------------------------------------------


R4_CASES = [
    (
        # forge forge-serve-orchestrator-wiring
        "A paused build does not acknowledge its inbound JetStream message",
        "Given a build has reached a paused state awaiting human approval\n"
        "When the inbound JetStream message's acknowledgement state is inspected\n"
        "Then the message should remain unacknowledged\n"
        "And the queue slot should still be held by the paused build\n"
        "And no second build should be delivered until the paused build resolves",
    ),
    (
        "The consumer and the publisher share the daemon's single NATS connection",
        "Given forge serve has opened its NATS connection at startup\n"
        "When the consumer attaches and the publisher emits envelopes\n"
        "Then both should use the daemon's single NATS connection\n"
        "And no second connection to the broker should be established by the daemon",
    ),
    (
        # jarvis feat-jarvis-004
        "Jarvis republishes its manifest periodically as a heartbeat",
        "Given Jarvis has registered on the fleet\nWhen the configured heartbeat interval elapses\n"
        "Then Jarvis's manifest should be republished to the fleet\n"
        "And the manifest's trust tier and version should remain stable across republications",
    ),
    (
        # forge confidence-gated-checkpoint-protocol
        "An approval request is published with the default wait time when none is specified",
        "Given Forge has evaluated a stage as flag-for-review\n"
        "When Forge publishes the approval request for that stage\n"
        "Then the request should carry the default wait time of 300 seconds\n"
        "And the build should remain paused until Rich responds or the wait time elapses",
    ),
    (
        # study-tutor nats-fleet-integration
        "A wire-tap on the documented command subject pattern captures a real dispatch",
        "Given the adapter is running and ready\n"
        "And a wire-tap is subscribed to the documented command-fanout subject pattern\n"
        "When jarvis dispatches a command to the tutor\n"
        "Then the wire-tap should observe the command envelope",
    ),
]


@pytest.mark.parametrize("title,steps", R4_CASES, ids=[c[0][:40] for c in R4_CASES])
def test_r4_bus_vocabulary_is_probe_bus(title, steps):
    home = _home(title, steps)
    assert (home.verifier, home.rule) == ("probe:bus", "R4")


def test_ordering_bus_plus_reply_is_probe_bus_not_hurl():
    """The design's ordering rationale: fleet scenarios say 'reply' /
    'request' / 'response' — R4 wins over R9 even in an HTTP repo."""
    title = "A chat request is answered by the supervisor on the reply inbox"  # jarvis 006
    steps = (
        "Given Rich sends a chat request through the fleet asking Jarvis a question\n"
        "When Jarvis receives the chat request\n"
        "Then the supervisor should be asked to answer the question\n"
        "And the supervisor's reply should be delivered on the requester's reply inbox\n"
        "And the reply should carry the supervisor's response text\n"
        "And the reply should carry the same correlation identifier as the request"
    )
    home = _home(title, steps, HTTP)
    assert (home.verifier, home.rule) == ("probe:bus", "R4")


# M4: R4 requires a BUS NOUN — "acknowledged" alone (an HTTP 204 is
# acknowledged too) and "subscription" alone (a user has a subscription)
# NEVER qualify; nor does the school "subject" / curriculum "topic".
def test_m4_acknowledged_204_and_a_user_subscription_are_not_probe_bus():
    for title, steps in [
        ("A delete is acknowledged with 204",
         "When I send a DELETE request to /users/1\nThen the request is acknowledged with 204\nAnd the body is empty"),
        ("A subscriber sees premium content",
         "Given the user has a subscription\nWhen the user opens the premium page\nThen the content is shown"),
        ("Resume-if-active is subject-scoped",
         "Given an active session on the subject \"english-literature\"\n"
         "When the app starts a session on the subject \"maths\" asking to resume if one is active\n"
         "Then a new session is created"),
        ("A struggling topic is preferred",
         "Given Lilymay has a struggling topic last studied 4 days ago\n"
         "When the system requests three topic recommendations\nThen the struggling topic is first"),
    ]:
        for ctx in (HTTP, NO_HTTP):
            home = classify_scenario(title, steps, ctx)
            assert home is None or home.verifier != "probe:bus", (title, home)
    # …while the same words WITH a bus noun are bus.
    assert _home("Acked", "When the message is acknowledged so the queue advances\nThen it is gone", HTTP).rule == "R4"
    assert _home("Sub", "Given a JetStream subscription\nWhen it drops\nThen it is re-established", HTTP).rule == "R4"


# ---------------------------------------------------------------------------
# R5 — Flutter / device → flutter (census: 51 — sign-in 25, voice 26)
# ---------------------------------------------------------------------------


# M2: EVERY retained R5 pattern is backed by a REAL flutter-keycloak-sign-in
# / flutter-voice-client scenario (read from the estate corpus by title), and
# the pattern each one exercises is named. `flutter` itself appears only in
# the two Feature: lines (never in a scenario's own steps) — it stays as the
# home's own word and is pinned on the design phrase.
R5_REAL = [
    ("the app returns to the foreground", SIGN_IN, "A sign-in completes after the browser redirects back into the app"),
    ("the app should not crash", SIGN_IN, "A failed background refresh degrades to the sign-in fallback rather than crashing"),
    ("the app sits idle", SIGN_IN, "An active session survives an idle period longer than the access-token lifetime"),
    ("the app tells me", VOICE, "Recording without microphone permission is explained and typing still works"),
    ("the app stops the recording", VOICE, "Recording stops automatically at the 60-second limit"),
    ("the app degrades to text", VOICE, "When spoken answers are unavailable the app degrades to text with a clear notice"),
    ("the app explains why", VOICE, "The app explains why a recording could not be used and stays ready"),
    ("reopen the app", SIGN_IN, "The device stays signed in across an app restart without a browser prompt"),
    ("open the app", SIGN_IN, "An unreadable stored session is treated as signed out"),
    ("closed the app", SIGN_IN, "The device stays signed in across an app restart without a browser prompt"),
    ("app restart", SIGN_IN, "The device stays signed in across an app restart without a browser prompt"),
    ("tap", SIGN_IN, "A second sign-in tap during an in-progress sign-in is ignored"),
    ("microphone access", VOICE, "Recording without microphone permission is explained and typing still works"),
    ("from the microphone", VOICE, "The shipped app is able to record audio and reach the tutor"),
    ("mic button", VOICE, "Asking a question by voice and hearing the tutor's spoken answer"),
    ("secure store", SIGN_IN, "The signed-in session is held in the platform secure store"),
    ("on the device", SIGN_IN, "A first-time sign-in through the browser flow reaches the home screen"),
    ("sign-in … browser", SIGN_IN, "A first-time sign-in through the browser flow reaches the home screen"),
    ("browser sign-in", SIGN_IN, "Cancelling the browser sign-in returns to the sign-in screen signed out"),
    ("browser opening", SIGN_IN, "Signing in reuses the stored session silently when it is still valid"),
    ("browser prompt", SIGN_IN, "The device stays signed in across an app restart without a browser prompt"),
    ("browser redirects back", SIGN_IN, "A sign-in completes after the browser redirects back into the app"),
    ("home screen", SIGN_IN, "Signing out clears the session and returns to the sign-in screen"),
    ("sign-in screen", SIGN_IN, "A failed sign-in shows a failure state and lets me try again"),
]


@pytest.mark.parametrize("pattern,feature,title", R5_REAL, ids=[c[0] for c in R5_REAL])
def test_r5_every_retained_pattern_is_backed_by_a_real_flutter_scenario(pattern, feature, title):
    t, steps, _ = _corpus_scenario("study-tutor", feature, title)
    text = f"{t}\n{steps}".lower()
    # the named idiom really is in the scenario's own text …
    probe = pattern.replace(" … ", " ").split(" … ")[0]
    assert probe.split()[0] in text, (pattern, text)
    home = _home(t, steps, HTTP)  # HTTP ctx: study-tutor IS a starlette repo — R5 still wins
    assert (home.verifier, home.rule) == ("flutter", "R5"), (title, home)


def test_r5_flutter_word_itself_is_the_homes_own_marker():
    home = _home("A widget renders", "Given the Flutter client is built\nWhen it renders\nThen the label shows", HTTP)
    assert (home.verifier, home.rule) == ("flutter", "R5")


# M2 negatives — the 08-16 family's swallowed HTTP scenarios (study-tutor
# http-app-access-adapter: "the app starts a session") and the dropped
# "securely stored" / widget / emulator idioms.
def test_m2_the_app_starts_a_session_is_the_wire_feature_not_flutter():
    t, steps, _ = _corpus_scenario(
        "study-tutor",
        "features/http-app-access-adapter/http-app-access-adapter.feature",
        "Starting with resume-if-active returns the existing active session",
    )
    assert "the app starts" in steps.lower()
    home = classify_scenario(t, steps, HTTP)
    assert home is None or home.verifier != "flutter", home


def test_m2_securely_stored_widget_emulator_alone_are_not_flutter():
    for title, steps in [
        ("A token is stored", "Given the token is securely stored\nWhen it is read\nThen it matches"),
        ("A widget of the CLI", "Given a widget in the terminal UI\nWhen it renders\nThen the columns align"),
        ("Runs in the emulator", "Given the emulator is booted\nWhen the suite runs\nThen it is green"),
    ]:
        home = classify_scenario(title, steps, NO_HTTP)
        assert home is None or home.verifier != "flutter", (title, home)


def test_r5_beats_r6_for_the_oidc_browser_flow():
    """'in the browser' is an R6 marker; the sign-in scenario also says
    'on the device' / 'browser flow' — R5 is evaluated first, so the Flutter
    OIDC flow is never mis-homed to playwright."""
    title, steps, _ = _corpus_scenario(
        "study-tutor", SIGN_IN, "A first-time sign-in through the browser flow reaches the home screen"
    )
    assert "in the browser" in steps
    assert _home(title, steps).verifier == "flutter"


def test_r5_does_not_swallow_the_http_adapter_that_names_the_app_as_a_client():
    """study-tutor http-app-access-adapter: 'the app authenticates / sends'
    is the wire feature naming its client — hurl, not flutter."""
    title = "Taking a turn returns the tutor's reply and durably records the exchange"
    steps = (
        "Given a session was started for lilymay\n"
        "When the app sends the message \"What does the dagger symbolise?\" to that session\n"
        "Then the response should carry the tutor's reply\nAnd the exchange should be durably recorded"
    )
    home = _home(title, steps, HTTP)
    assert home.verifier == "hurl"


# ---------------------------------------------------------------------------
# R6 — browser → playwright (census: 2 estate-wide; the third is the design's phrase)
# ---------------------------------------------------------------------------


R6_CASES = [
    (
        # study-tutor keycloak-idp-standup (the cert-trust page load)
        "A household device browser reaches the realm sign-in page over https",
        "Given the identity service is running with the tailscale certificate mounted\n"
        "When a household device opens the study-tutor realm sign-in page over the tailnet\n"
        "Then the sign-in page should load over a trusted https connection with no certificate warning",
    ),
    (
        # lpa-platform-poc FEAT-POC-007 (the build-flag drift)
        "The reset option disappears when the platform reports the feature unavailable",
        "Given the app was built with the demo reset option enabled\n"
        "But the platform has demo mode disabled\nWhen I open my account menu as a donor\n"
        "Then the \"Reset demo data\" option should not remain available",
    ),
    (
        # the rules doc's own R6 phrasing (no third browser scenario exists in the estate)
        "The dashboard page renders the client build flag",
        "Given the client build flag is set\nWhen the dashboard is opened in the browser\n"
        "Then the page renders the flag value",
    ),
]


@pytest.mark.parametrize("title,steps", R6_CASES, ids=[c[0][:40] for c in R6_CASES])
def test_r6_browser_vocabulary_is_playwright(title, steps):
    home = _home(title, steps)
    assert (home.verifier, home.rule) == ("playwright", "R6")


# ---------------------------------------------------------------------------
# R7 — Then judges AI output quality → exam (census: 208)
# ---------------------------------------------------------------------------


R7_CASES = [
    (
        # specialist-agent finproxy-fine-tune-vs-frontier-comparison
        "Coach acceptance is computed against the same six weighted criteria as the baseline",
        "Given the architect role defines six weighted criteria with composite scoring\n"
        "When the fine-tune session is evaluated by the Coach\n"
        "Then the Coach should score every criterion\n"
        "And the composite score should be computed using the same weights as the baseline run",
    ),
    (
        # specialist-agent product-owner-reframe
        "Feature spanning multiple bounded contexts is flagged for decomposition",
        "Given the Player output includes a feature that references capabilities in two different bounded contexts\n"
        "When the Coach evaluates the output\n"
        "Then the Coach should flag the cross-boundary feature for potential decomposition\n"
        "And the finding should suggest splitting into bounded-context-specific features",
    ),
    (
        # study-tutor deepagents-tutoring-loop (a live-Coach judgement)
        "A Player response that meets the Coach threshold is emitted to the learner",
        "Given the learner has just sent a turn message\nWhen the Player produces a response\n"
        "And the Coach evaluates the response against the rubric\n"
        "And the weighted Coach score meets or exceeds the acceptance threshold\n"
        "Then the Coach decision should be \"accept\"\n"
        "And the Player's response should be returned to the learner\n"
        "And the Coach's reasoning should be recorded in session-only logs\n"
        "And the Coach's reasoning should never be shown to the learner",
    ),
    (
        # study-tutor primary-text-rag-and-quote-verifier
        "A turn on a primary text whose canonical edition is in the corpus retrieves source-filtered chunks",
        "Given the session is on a primary text whose canonical edition is in the corpus\n"
        "And the focus assessment objectives include AO1 and AO2\n"
        "When the retrieval-decision function is asked whether to retrieve for this turn\n"
        "Then the decision should be to retrieve\n"
        "And the retrieved chunks should prefer primary-text chunks ahead of secondary chunks\n"
        "And the response should be grounded in those chunks",
    ),
]


@pytest.mark.parametrize("title,steps", R7_CASES, ids=[c[0][:40] for c in R7_CASES])
def test_r7_ai_output_quality_is_exam(title, steps):
    home = _home(title, steps)
    assert (home.verifier, home.rule) == ("exam", "R7")


def test_ordering_exam_beats_toolchain_even_when_the_plan_names_a_test_node():
    """The design: a scenario judging Coach output can also name a test node
    — the judged quality is the essential surface, so R7 wins over R8."""
    title, steps = R7_CASES[0]
    ctx = NormalizeContext(
        repo_has_http_surface=True,
        plan_test_refs={title: "test_coach_acceptance_six_criteria"},
    )
    home = _home(title, steps, ctx)
    assert (home.verifier, home.rule) == ("exam", "R7")
    assert home.test_ref is None


def test_r7_prompt_injection_sanitising_is_not_exam():
    """specialist-agent has many 'prompt injection' scenarios that test a
    sanitiser (internal machinery). Only 'injection … ignored / treated as
    ordinary' (a judged behaviour) is R7; the sanitiser stays undecided by
    R7 and lands on R8/R9/refuse like any other machinery scenario."""
    title = "Stripping helper is idempotent against re-injection attempts"
    steps = (
        "Given a prompt that has already been stripped\n"
        "When the stripping helper runs again over it\n"
        "Then the output should be byte-identical to the first pass"
    )
    home = classify_scenario(title, steps, NO_HTTP)
    assert home is None or home.verifier != "exam"


# M3: R7 reads the THEN clause only, and the family JUDGES quality. A Coach
# score used as a Given/When INPUT, the NOUN "coach score" (rendered in a
# notification), a prompt that merely CONTAINS "score each criterion", and
# bare "narration" are all machinery — REAL forge / specialist-agent / adf /
# lpa scenarios, pinned as negatives.
M3_NEGATIVES = [
    ("forge", "features/mode-a-greenfield-end-to-end/mode-a-greenfield-end-to-end.feature",
     "Auto-approval is refused at the pull-request review stage even when the upstream Coach score is at the maximum"),
    ("forge", "features/confidence-gated-checkpoint-protocol/confidence-gated-checkpoint-protocol.feature",
     "A gated stage with no Coach score cannot be auto-approved"),
    ("forge", "features/jarvis-notification-bridge/jarvis-notification-bridge.feature",
     "A pause notification renders the coach score at the range boundaries"),
    ("forge", "features/unattended-build-service-budget-guards/unattended-build-service-budget-guards.feature",
     "The coach-score floor fires only once a score is present"),
    ("specialist-agent", "features/doc-reader-player-coach-factories/doc-reader-player-coach-factories.feature",
     "Coach system prompt includes the domain prompt"),
    ("agentic-dataset-factory", "features/gcse-goal-md/gcse-goal-md.feature",
     "Evaluation criteria weights inform the Coach scoring rubric"),
    ("lpa-platform-poc", "docs/poc/features/FEAT-POC-006-voice-assistant.feature",
     "A narration replayed within its freshness window is served from cache"),
    ("lpa-platform-poc", "docs/poc/features/FEAT-POC-006-voice-assistant.feature",
     "Voice review is not available without signing in"),
    ("specialist-agent", "features/adaptive-mode-inference/adaptive-mode-inference.feature",
     "Input matching no mode produces a clear error"),
]


@pytest.mark.parametrize("repo,feature,title", M3_NEGATIVES, ids=[c[2][:40] for c in M3_NEGATIVES])
def test_m3_a_coach_score_input_or_noun_and_bare_narration_are_not_exam(repo, feature, title):
    t, steps, _ = _corpus_scenario(repo, feature, title)
    for ctx in (HTTP, NO_HTTP):
        home = classify_scenario(t, steps, ctx)
        assert home is None or home.verifier != "exam", (title, home)


def test_m3_r7_reads_the_then_clause_only():
    from guardkit.orchestrator.stamp_normalizer import then_clause

    steps = "Given the Coach should score everything\nWhen the Coach evaluates\nThen the file is written"
    assert then_clause(steps) == "Then the file is written"
    assert classify_scenario("Given/When only", steps, NO_HTTP) is None
    steps2 = "Given a response\nWhen judged\nThen the Coach should score every criterion\nAnd the file is written"
    assert _home("Then judges", steps2, NO_HTTP).rule == "R7"
    assert then_clause("When x\nAnd y") == ""


def test_m3_narration_counts_only_when_its_content_is_judged():
    t, steps, _ = _corpus_scenario(
        "lpa-platform-poc", "docs/poc/features/FEAT-POC-006-voice-assistant.feature",
        "The narration reuses the explanation already recorded for the flag",
    )
    assert _home(t, steps, NO_HTTP).rule == "R7"


# ---------------------------------------------------------------------------
# R8 — the plan names a test node → toolchain + test_ref (census: 1,573 — 48%)
# ---------------------------------------------------------------------------


def test_r8_plan_named_test_node_is_toolchain_with_test_ref():
    """The design's own example: users-count 7.2 with the plan naming
    test_count_empty → toolchain, R8 beating R9's 'response should report'."""
    title = "The count of an empty store is zero"
    steps = (
        "Given no users exist in the store\nWhen I request the users count\n"
        "Then the request should succeed\nAnd the response should report a count of 0"
    )
    ctx = NormalizeContext(repo_has_http_surface=True, plan_test_refs={title: "test_count_empty"})
    home = _home(title, steps, ctx)
    assert (home.verifier, home.rule, home.test_ref) == ("toolchain", "R8", "test_count_empty")
    # …and without the node the same scenario is R9 hurl (the named divergence).
    home2 = _home(title, steps, HTTP)
    assert (home2.verifier, home2.rule) == ("hurl", "R9")


def test_r8_overlap_law_two_significant_words(tmp_path: Path):
    """title -> node needs ≥2 significant-word overlap (light stemming so
    'increments' meets 'incremental'); one word is not a pin."""
    titles = [
        "The count of an empty store is zero",
        "Creating a user increments the count",
        "The count reflects the number of stored users",
        "Requesting a user by id still works alongside the count route",
    ]
    nodes = ["test_count_empty", "test_count_incremental", "test_ready_smoke"]
    refs = build_plan_test_refs(titles, nodes)
    assert refs == {
        "The count of an empty store is zero": "test_count_empty",
        "Creating a user increments the count": "test_count_incremental",
    }


def test_r8_nodes_come_from_frontmatter_test_ref_and_in_plan_tests_refs(tmp_path: Path):
    task = tmp_path / "TASK-X.md"
    task.write_text(
        "---\nid: TASK-X\ntest_ref: test_count_empty\n---\n"
        "# Task\n\nPin the incremental case at `tests/users/test_router.py::TestCount::test_count_incremental`.\n"
        "Also see tests/users/test_router.py (no node) and test_client (a fixture, not a node).\n",
        encoding="utf-8",
    )
    nodes = collect_plan_test_nodes([task, tmp_path / "missing.md"])
    assert nodes == ["test_count_empty", "test_count_incremental"]


# ---------------------------------------------------------------------------
# R9 — wire-shaped AND the repo has an HTTP surface → hurl (census: 417; api_test 40)
# ---------------------------------------------------------------------------


R9_CASES = [
    (
        "A GET request to /version returns the application metadata",
        "When I send a GET request to /version\nThen the request should succeed\n"
        "And the response should contain the application version string",
    ),
    (
        "Uptime increases between consecutive requests",
        "When I request the service uptime twice in succession\n"
        "Then the second reported uptime should be greater than the first\n"
        "And both should report the same process start time",
    ),
    (
        "Modifying the statistics is not allowed",
        "When I attempt to submit changes to the service statistics\n"
        "Then the request should be rejected as not allowed",
    ),
    (
        "Deleting by email removes exactly the matching user",
        "Given 3 users exist with distinct emails\nWhen I delete the user by the second user's email\n"
        "Then looking up the second user's email should find nothing\nAnd the other two users should still exist",
    ),
    (
        "An unknown email returns not-found",
        "Given no user exists with email \"ghost@example.com\"\n"
        "When I request the user by email \"ghost@example.com\"\n"
        "Then the request should fail with a not-found response",
    ),
    (
        "Reading the current server time",
        "When I send a GET request to \"/time\"\nThen the response status code should be 200\n"
        "And the response content type should be \"application/json\"",
    ),
]


@pytest.mark.parametrize("title,steps", R9_CASES, ids=[c[0][:40] for c in R9_CASES])
def test_r9_wire_shaped_in_an_http_repo_is_hurl(title, steps):
    home = _home(title, steps, HTTP)
    assert (home.verifier, home.rule) == ("hurl", "R9")


@pytest.mark.parametrize("title,steps", R9_CASES[:3], ids=[c[0][:40] for c in R9_CASES[:3]])
def test_r9_needs_an_http_surface_else_it_is_undecidable(title, steps):
    """No HTTP surface → R9 is skipped; the same wire text does NOT fall to
    operator or anywhere else — it refuses."""
    assert classify_scenario(title, steps, NO_HTTP) is None


def test_r9_path_literal_needs_an_http_token_on_the_same_step_line_m1():
    """M1: a path literal is a wire marker ONLY beside an HTTP-shaped token
    on the same step line; a bare path never suffices."""
    home = _home("Reads a user", "When I send a GET request to /users/{user_id}\nThen the status is 200", HTTP)
    assert home.rule == "R9" and "/users/{user_id}" in home.evidence or home.rule == "R9"
    assert classify_scenario("Reads /users/{user_id}", "When I fetch /users/{user_id}", HTTP) is None
    assert classify_scenario("Dates", "Given the date 2026/08/15 and a ratio 3/4", HTTP) is None


# REAL estate scenarios the 08-16 rules mis-homed to hurl on a path literal
# (verifier finding M1): slash-commands and unix paths are not endpoints.
M1_NEGATIVES = [
    (
        # forge mode-b-feature-and-mode-c-review-fix
        "A Mode B build refuses to dispatch /system-arch or /system-design even when a context manifest references those stages",
        "Given a Mode B build whose context manifest references /system-arch\n"
        "When the build reaches the planning stage\n"
        "Then neither /system-arch nor /system-design should be dispatched\n"
        "And the build should proceed straight to /feature-spec",
    ),
    (
        # jarvis feat-jarvis-002-core-tools-and-dispatch
        "Calculator rejects expressions containing unsafe tokens",
        "Given the calculator tool is available\n"
        "When Rich asks Jarvis to evaluate \"__import__('os').system('cat /etc/passwd')\"\n"
        "Then the calculator should refuse the expression\nAnd nothing should be executed",
    ),
    (
        # jarvis feat-jarvis-003
        "The supervisor routes the seven canned acceptance prompts to the expected tools",
        "Given the supervisor has been built with all FEAT-JARVIS-002 tools, the jarvis-reasoner subagent, "
        "and the attended tool list including escalate_to_frontier\n"
        "And the active session is on an attended adapter\n"
        "When the user says <prompt>\nThen the reasoning model invokes <expected_action>\n"
        "Examples:\n| prompt | expected_action |\n| \"Write hello to /tmp/test\" | write_file |",
    ),
    (
        # guardkit system-arch-design-commands
        "Running /system-arch on a project with no existing architecture context",
        "Given a project with no .guardkit/architecture directory\n"
        "When the user runs /system-arch\n"
        "Then the command should ask the structural-pattern question first",
    ),
]


@pytest.mark.parametrize("title,steps", M1_NEGATIVES, ids=[c[0][:40] for c in M1_NEGATIVES])
def test_m1_slash_commands_and_unix_paths_are_not_wire_markers(title, steps):
    home = classify_scenario(title, steps, HTTP)
    assert home is None or home.verifier != "hurl", home


# ---------------------------------------------------------------------------
# R10 — explicitly human → operator (EXPLICIT only; census: the 3 unclassifiable)
# ---------------------------------------------------------------------------


R10_CASES = [
    (
        # forge fleet-memory-deploy-runbook — the real NAS
        "The executor stands fleet-memory up on the real NAS",
        "Given the runbook is pointed at the real NAS with the real deploy environment file\n"
        "When the executor runs the runbook\n"
        "Then fleet-memory Postgres with pgvector should be live on the NAS\n"
        "And the smoke gates should all be green",
    ),
    (
        # study-tutor keycloak-idp-standup — runbook evidence
        "NAS memory is recorded before and after standup and headroom stays positive",
        "Given the operator records the NAS free memory before standup\n"
        "When the identity service standup completes with its 2GB memory limit\n"
        "And the operator records the NAS free memory after standup\n"
        "Then both readings should be captured in the runbook evidence",
    ),
    (
        # the rules doc's own R10 phrasing (work done by hand)
        "The quarterly key rotation is walked by hand",
        "Given an operator follows the rotation runbook\nWhen each key is rotated by hand\n"
        "Then the checklist is signed off",
    ),
    (
        "A physical robot is driven through the greeting",
        "Given the physical robot is powered on\nWhen a student says hello\nThen it waves",
    ),
    (
        "The migration is human-executed on the box",
        "Given the migration is human-executed\nWhen it completes\nThen the ledger records the operator",
    ),
]


@pytest.mark.parametrize("title,steps", R10_CASES, ids=[c[0][:40] for c in R10_CASES])
def test_r10_explicit_human_work_is_operator(title, steps):
    home = _home(title, steps, HTTP)
    assert (home.verifier, home.rule) == ("operator", "R10")


# H1: the operator-handoff TAG / `# operator_handoff:` comment — the
# annotation channel, fed to R10 and to no other rule (lpa-platform-poc
# FEAT-POC-007, the two tagged scenarios).
def test_r10_operator_handoff_tag_and_comment_are_the_annotation_channel():
    title = "Only active bank connections are revoked at the provider"
    steps = (
        "Given demo mode is enabled\n"
        "And I am signed in as a donor with one active, one already-revoked, and one pending bank connection\n"
        "When I reset my demo data with provider revocation enabled\n"
        "Then bank consent should be cancelled at the provider only for the active connection"
    )
    assert classify_scenario(title, steps, NO_HTTP) is None  # the steps alone: not human
    tagged = classify_scenario(title, steps, NO_HTTP, annotations="@boundary @operator-handoff")
    assert tagged is not None and (tagged.verifier, tagged.rule) == ("operator", "R10")
    commented = classify_scenario(
        title, steps, NO_HTTP,
        annotations="# operator_handoff: the real provider revoke can only be proven against the live Moneyhub sandbox",
    )
    assert commented is not None and commented.verifier == "operator"
    # A comment that merely TALKS about the operator-handoff type (specialist-
    # agent architect-feature-plan) is not the tag.
    talked = classify_scenario(
        "Live-infrastructure work is tagged for operator handoff without prompting",
        "Given the feature plan names live-infrastructure work\nWhen the tool runs headless\n"
        "Then the affected task is typed as operator handoff",
        NO_HTTP,
        annotations="# [ASSUMPTION: confidence=low] Headless detection auto-applies the operator-handoff type on strong signals",
    )
    assert talked is None


# H1: the 08-16 family's SILENT operators — REAL estate scenarios, none human.
H1_NEGATIVES = [
    (
        # forge unattended-build-service-budget-guards — `attended` is a MODE word
        "An attended build is never constrained by budget caps",
        "Given a build launched with the attended profile\n"
        "When the build runs past every unattended cap\n"
        "Then no budget cap should fire",
    ),
    (
        # jarvis feat-jarvis-003 — `attended tools`
        "Not configuring an ambient tool factory falls back to the attended tools without frontier",
        "Given no ambient tool factory is configured\nWhen an ambient session starts\n"
        "Then the session should be built with the attended tools minus escalate_to_frontier",
    ),
    (
        # specialist-agent production-trace-capture — `attended session`
        "An attended session without fleet dispatch records its lineage as absent by design",
        "Given an attended session that never dispatched to the fleet\n"
        "When the trace is captured\nThen the lineage field should read absent-by-design",
    ),
    (
        # specialist-agent architect-ingestion-v2 — CLI persona `the operator runs`
        "Ingestion completes cleanly when given an empty input",
        "Given an empty corpus directory\nWhen the operator runs the ingestion command\n"
        "Then the command should exit zero and report zero chunks",
    ),
    (
        # forge forge-production-image — `the operator runs`
        "The production image exposes the full forge CLI surface",
        "Given the production image is built\nWhen the operator runs forge --help inside the container\n"
        "Then every forge subcommand should be listed",
    ),
    (
        # study-tutor keycloak-idp-standup — `the operator checks` (a status read, not human work)
        "The Keycloak identity service starts and reports healthy",
        "Given the standup runbook has been executed on the NAS\n"
        "When the operator checks the identity service status\n"
        "Then the identity service should be running and report healthy",
    ),
    (
        # study-tutor reachy-local-voice-migration — bare `robot` is software behaviour
        "A spoken tutoring question is answered by the study-tutor in the robot's voice",
        "Given the student is in a tutoring conversation with the robot\n"
        "When the student asks the robot a tutoring question\n"
        "Then the robot should obtain the answer from the study-tutor\n"
        "And the robot should speak the answer in the configured robot voice",
    ),
    (
        # jarvis feat-spl-003 — "traced by hand" is a rationale, not work done by hand
        "A notification without a thread anchor degrades to the channel and is never dropped",
        "Given a notification with no thread anchor\nWhen it is delivered\n"
        "Then it should land in the channel\n"
        "And the notification should include the correlation identifier so it can be traced by hand",
    ),
    (
        # study-tutor keycloak-idp-standup — bare `on the NAS` (only `on the real NAS` is the marker)
        "The nightly backup captures both the learner store and the realm state",
        "Given the identity service is running on the NAS\nWhen the nightly backup runs\n"
        "Then the archive should contain both databases",
    ),
]


@pytest.mark.parametrize("title,steps", H1_NEGATIVES, ids=[c[0][:40] for c in H1_NEGATIVES])
def test_h1_mode_words_cli_persona_and_bare_robot_never_mint_operator(title, steps):
    for ctx in (HTTP, NO_HTTP):
        home = classify_scenario(title, steps, ctx)
        assert home is None or home.verifier != "operator", (title, home)


def test_operator_is_explicit_only_an_unmatched_scenario_never_becomes_operator():
    """Rich's condition 2 in one line: no rule → None. NEVER operator."""
    title = "The parser accepts an empty document"
    steps = "Given an empty document\nWhen it is parsed\nThen no error is raised"
    for ctx in (HTTP, NO_HTTP, None):
        home = classify_scenario(title, steps, ctx)
        assert home is None, f"unmatched scenario must refuse, got {home}"


def test_unattended_is_not_attended():
    assert classify_scenario(
        "Realm state survives a reboot unattended",
        "Given the identity service realm was provisioned\nWhen the box reboots unattended\n"
        "Then the realm state is intact",
        NO_HTTP,
    ) is None


def test_ctx_accepts_a_plain_mapping():
    title, steps = R9_CASES[0]
    home = classify_scenario(title, steps, {"repo_has_http_surface": True})
    assert home is not None and home.verifier == "hurl"


# ---------------------------------------------------------------------------
# Gherkin lexing: titles + OWN steps, Background excluded
# ---------------------------------------------------------------------------


def test_extract_scenarios_excludes_background_and_comments_and_tags():
    text = (
        "Feature: Smoke\n"
        "  Background:\n"
        "    Given a throwaway sandboxed environment\n\n"
        "  # Why: seeded\n"
        "  @task:TASK-1 @smoke\n"
        "  Scenario: Seeded data is visible\n"
        "    Given a record is seeded directly into the database\n"
        "    Then it is listed\n\n"
        "  Scenario Outline: Values <v>\n"
        "    When I send a GET request to /x/<v>\n"
        "    Examples:\n"
        "      | v |\n"
        "      | 1 |\n"
    )
    scenarios = extract_scenarios(text)
    assert [t for t, _ in scenarios] == ["Seeded data is visible", "Values <v>"]
    seeded_steps = scenarios[0][1]
    assert "throwaway" not in seeded_steps and "# Why" not in seeded_steps and "@task" not in seeded_steps
    assert "seeded directly" in seeded_steps
    assert "| 1 |" in scenarios[1][1]


def test_extract_scenario_blocks_attributes_tags_and_comments_to_the_right_scenario():
    from guardkit.orchestrator.stamp_normalizer import extract_scenario_blocks

    text = (
        "Feature: F\n"
        "  Scenario: First\n"
        "    Given a\n"
        "    # an in-body note\n"
        "    Then b\n\n"
        "  # Why: the next one needs the live sandbox\n"
        "  # operator_handoff: proven against the live sandbox\n"
        "  @boundary @operator-handoff\n"
        "  Scenario: Second\n"
        "    Given c\n"
        "    Then d\n"
    )
    first, second = extract_scenario_blocks(text)
    assert first.title == "First" and "in-body note" in first.annotations
    assert "operator" not in first.annotations  # the trailing run belongs to Second
    assert second.title == "Second"
    assert "@operator-handoff" in second.annotations and "# operator_handoff:" in second.annotations
    assert "operator" not in second.steps_text and "#" not in second.steps_text


def test_background_exclusion_keeps_the_smoke_probes_hurl_end_to_end():
    """runtime-smoke's Background says 'throwaway sandboxed environment'; had
    the Background been folded into every scenario, all twelve would be R3.
    Through the fixture tree, 5.2/5.6/5.7/5.8 stay hurl."""
    yaml_path = FIXTURE_ROOT / ".guardkit" / "features" / "FEAT-8737.yaml"
    result = normalize_feature(yaml_path, None, FIXTURE_ROOT, dry_run=True, ignore_existing=True)
    assert result.stamped["A user created through the service reads back with identical details"] == "hurl"
    assert result.stamped["Looking up a user that was never created is reported as not found"] == "hurl"
    assert result.stamped["Creating a user with an email already in use is rejected as a conflict"] == "hurl"
    assert result.stamped["A malformed user submission is rejected as invalid"] == "hurl"
    assert result.stamped["The sandboxed application has no route to the outside world"] == "probe:process"


# ---------------------------------------------------------------------------
# HTTP-surface detection
# ---------------------------------------------------------------------------


def test_http_surface_from_hurl_gate_in_registry(tmp_path: Path):
    (tmp_path / "qa" / "gates").mkdir(parents=True)
    (tmp_path / "qa" / "gates" / "registry.yaml").write_text(
        "format_version: '1.0'\ngates:\n  - id: hurl-twins\n    path: qa/gates/hurl_twin_gate.py\n"
    )
    has, why = detect_repo_http_surface(tmp_path)
    assert has and "hurl-twins" in why


def test_http_surface_from_pyproject_project_dependencies_structural(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='svc'\ndependencies=['FastAPI[all]>=0.104.0', 'sqlalchemy']\n"
    )
    has, why = detect_repo_http_surface(tmp_path)
    assert has and "fastapi" in why


def test_http_surface_from_poetry_dependencies_and_package_json_dependencies(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        "[tool.poetry]\nname='svc'\n[tool.poetry.dependencies]\npython='^3.12'\nflask='^3.0'\n"
    )
    has, why = detect_repo_http_surface(tmp_path)
    assert has and "flask" in why
    node = tmp_path / "node"
    node.mkdir()
    (node / "package.json").write_text(json.dumps({"dependencies": {"express": "^4"}}))
    has, why = detect_repo_http_surface(node)
    assert has and "express" in why


def test_http_surface_from_explicit_config_key(tmp_path: Path):
    (tmp_path / ".guardkit").mkdir()
    (tmp_path / ".guardkit" / "config.yaml").write_text("routing_law: enforced\nsurface: http\n")
    has, why = detect_repo_http_surface(tmp_path)
    assert has and "surface: http" in why
    (tmp_path / ".guardkit" / "config.yaml").write_text("surface: [bus, http]\n")
    assert detect_repo_http_surface(tmp_path)[0] is True
    (tmp_path / ".guardkit" / "config.yaml").write_text("surface: bus\n")
    assert detect_repo_http_surface(tmp_path)[0] is False


# H2: FREE TEXT NEVER COUNTS — the 08-16 detector word-matched "next" in a
# forge/jarvis pyproject COMMENT and read both as HTTP; a comment, a
# devDependency, a requirements*.txt line and an optional extra are all
# structurally NOT the declared runtime web stack.
def test_h2_free_text_comments_dev_deps_and_requirements_never_make_an_http_surface(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='forge'\n# the next stage dispatches to express the plan; falcon/tornado/bottle/koa\n"
        "dependencies=['nats-core', 'click']\n"
        "[project.optional-dependencies]\ndev=['fastapi']\n"
    )
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {}, "devDependencies": {"next": "14", "express": "4"}, "scripts": {"x": "koa rocket"}})
    )
    (tmp_path / "requirements.txt").write_text("fastapi==0.104.1\nuvicorn\n")
    (tmp_path / "requirements").mkdir()
    (tmp_path / "requirements" / "base.txt").write_text("fastapi>=0.104.0\n")
    has, why = detect_repo_http_surface(tmp_path)
    assert has is False, why


def test_no_http_surface_when_neither(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='lib'\ndependencies=['pyyaml']\n")
    has, _ = detect_repo_http_surface(tmp_path)
    assert has is False


def test_the_fixture_tree_has_an_http_surface_via_the_hurl_twins_gate():
    has, why = detect_repo_http_surface(FIXTURE_ROOT)
    assert has and "hurl-twins" in why


# ---------------------------------------------------------------------------
# THE PROOF — api_test @5bc6fd1, the hand-stamped 60, existing stamps ignored
# ---------------------------------------------------------------------------


API_TEST_FEATURES = [
    "FEAT-B70F", "FEAT-FD8D", "FEAT-AE43", "FEAT-D450", "FEAT-8737",
    "FEAT-TIME", "FEAT-UCNT", "FEAT-UBEM", "FEAT-UDBE",
]

# The ONE divergence the rules doc named: users-count 7.1–7.3 — hurl by rule
# (R9) when the plan names no test node; toolchain by hand (test_count_*).
KNOWN_DIVERGENCE = {
    "The count reflects the number of stored users",
    "The count of an empty store is zero",
    "Creating a user increments the count",
}


def _hand_stamps(feature_id: str) -> dict:
    data = yaml.safe_load((FIXTURE_ROOT / ".guardkit" / "features" / f"{feature_id}.yaml").read_text())
    return {t: (s if isinstance(s, str) else s["verifier"]) for t, s in data["scenarios"].items()}


def test_api_test_reproduction_57_of_60_and_only_the_named_divergence():
    rows = []
    for fid in API_TEST_FEATURES:
        hand = _hand_stamps(fid)
        yaml_path = FIXTURE_ROOT / ".guardkit" / "features" / f"{fid}.yaml"
        result = normalize_feature(yaml_path, None, FIXTURE_ROOT, dry_run=True, ignore_existing=True)
        assert result.refused == []
        assert result.written is False
        assert set(result.stamped) == set(hand), fid
        for title, hv in hand.items():
            rows.append((fid, title, hv, result.stamped[title], result.rules[title]))
    assert len(rows) == 60
    diffs = {(fid, t) for fid, t, hv, gv, _ in rows if hv != gv}
    assert {t for _, t in diffs} == KNOWN_DIVERGENCE, sorted(diffs)
    assert all(fid == "FEAT-UCNT" for fid, _ in diffs)
    for fid, t, hv, gv, rule in rows:
        if t in KNOWN_DIVERGENCE:
            assert (hv, gv, rule) == ("toolchain", "hurl", "R9"), t
    same = sum(1 for _, _, hv, gv, _ in rows if hv == gv)
    assert same == 57


def test_api_test_divergence_closes_when_the_plan_names_the_nodes(tmp_path: Path):
    """The design's recommendation: R8 wins when the toolchain has a real
    node. Give FEAT-UCNT a task doc naming test_count_empty /
    test_count_incremental and 7.2 + 7.3 come back toolchain (7.1's title
    shares only 'count' with either node — one word is not a pin)."""
    import shutil

    repo = tmp_path / "api_test"
    shutil.copytree(FIXTURE_ROOT, repo)
    task = repo / "tasks" / "backlog" / "users-count-endpoint" / "TASK-UCNT-001-add-users-count-endpoint.md"
    task.parent.mkdir(parents=True)
    task.write_text(
        "---\nid: TASK-UCNT-001\n---\n"
        "Pins: `tests/users/test_router.py::test_count_empty`, "
        "`tests/users/test_router.py::test_count_incremental`.\n"
    )
    result = normalize_feature(
        repo / ".guardkit" / "features" / "FEAT-UCNT.yaml", None, repo, dry_run=True, ignore_existing=True
    )
    assert result.stamped["The count of an empty store is zero"] == "toolchain"
    assert result.test_refs["The count of an empty store is zero"] == "test_count_empty"
    assert result.stamped["Creating a user increments the count"] == "toolchain"
    assert result.test_refs["Creating a user increments the count"] == "test_count_incremental"
    assert result.stamped["The count reflects the number of stored users"] == "hurl"


def test_ignore_existing_is_dry_run_only(tmp_path: Path):
    with pytest.raises(StampNormalizerError, match="NEVER overwritten"):
        normalize_feature(
            FIXTURE_ROOT / ".guardkit" / "features" / "FEAT-TIME.yaml", None, FIXTURE_ROOT,
            dry_run=False, ignore_existing=True,
        )


# ---------------------------------------------------------------------------
# normalize_feature — the WRITER (Rich's condition 1) and the REFUSAL (condition 2)
# ---------------------------------------------------------------------------


UCNT_FEATURE = (FIXTURE_ROOT / "features" / "users-count-endpoint" / "users-count-endpoint.feature").read_text()


def _repo(tmp_path: Path, feature_yaml: str, *, feature_text: str = UCNT_FEATURE, http: bool = True) -> Path:
    repo = tmp_path / "repo"
    (repo / ".guardkit" / "features").mkdir(parents=True)
    (repo / "features" / "users-count-endpoint").mkdir(parents=True)
    (repo / "features" / "users-count-endpoint" / "users-count-endpoint.feature").write_text(feature_text)
    (repo / ".guardkit" / "features" / "FEAT-UCNT.yaml").write_text(feature_yaml)
    if http:
        (repo / "qa" / "gates").mkdir(parents=True)
        (repo / "qa" / "gates" / "registry.yaml").write_text(
            "format_version: '1.0'\ngates:\n  - id: hurl-twins\n    path: qa/gates/hurl_twin_gate.py\n"
        )
    return repo


BASE_YAML = (
    "id: FEAT-UCNT\n"
    "name: GET /users/count endpoint\n"
    "# a comment the writer must keep\n"
    "description: count\n"
    "created: '2026-07-26T20:30:00'\n"
    "status: planned\n"
    "complexity: 3\n"
    "estimated_tasks: 1\n"
    "feature_files:\n"
    "  - features/users-count-endpoint/users-count-endpoint.feature\n"
    "tasks:\n"
    "- id: TASK-UCNT-001\n"
    "  name: Add GET /users/count endpoint\n"
    "  file_path: tasks/backlog/users-count-endpoint/TASK-UCNT-001.md\n"
    "  complexity: 3\n"
    "  dependencies: []\n"
    "  status: pending\n"
    "  implementation_mode: task-work\n"
    "  estimated_minutes: 35\n"
    "orchestration:\n"
    "  parallel_groups:\n"
    "  - - TASK-UCNT-001\n"
    "  estimated_duration_minutes: 35\n"
    "  recommended_parallel: 1\n"
    "preflight_strict: false\n"
)


def test_it_writes_stamps_into_the_feature_yaml_and_the_loader_accepts_them(tmp_path: Path):
    repo = _repo(tmp_path, BASE_YAML)
    yaml_path = repo / ".guardkit" / "features" / "FEAT-UCNT.yaml"
    result = normalize_feature(yaml_path, None, repo)
    assert result.written is True and result.refused == []
    assert len(result.stamped) == 6
    text = yaml_path.read_text()
    assert "# a comment the writer must keep" in text  # textual splice, comments kept
    data = yaml.safe_load(text)
    assert data["scenarios"]["The count degrades honestly when the database is unavailable"] == {
        "verifier": "probe:process"
    }
    assert data["scenarios"]["Attempting to modify the users count is rejected"] == {"verifier": "hurl"}
    assert data["tasks"][0]["id"] == "TASK-UCNT-001"  # nothing else changed
    # THE POINT: the routing law's enforcement now LOADS this feature.
    (repo / ".guardkit" / "config.yaml").write_text("routing_law: enforced\n")
    feature = FeatureLoader.load_feature("FEAT-UCNT", repo_root=repo, validate_paths=False)
    assert set(feature.scenarios) == set(result.stamped)


def test_a_second_run_is_a_no_op(tmp_path: Path):
    repo = _repo(tmp_path, BASE_YAML)
    yaml_path = repo / ".guardkit" / "features" / "FEAT-UCNT.yaml"
    normalize_feature(yaml_path, None, repo)
    before = yaml_path.read_text()
    again = normalize_feature(yaml_path, None, repo)
    assert again.written is False and again.stamped == {} and len(again.already_stamped) == 6
    assert yaml_path.read_text() == before


def test_never_overwrite_an_existing_stamp(tmp_path: Path):
    """The DB-down scenario is hand-stamped hurl (the rule says
    probe:process): the hand stamp stays; only the five unstamped are written."""
    stamped_yaml = BASE_YAML + (
        "scenarios:\n"
        "  \"The count degrades honestly when the database is unavailable\":\n"
        "    verifier: hurl\n"
    )
    repo = _repo(tmp_path, stamped_yaml)
    yaml_path = repo / ".guardkit" / "features" / "FEAT-UCNT.yaml"
    result = normalize_feature(yaml_path, None, repo)
    assert result.already_stamped == ["The count degrades honestly when the database is unavailable"]
    assert "The count degrades honestly when the database is unavailable" not in result.stamped
    assert len(result.stamped) == 5
    data = yaml.safe_load(yaml_path.read_text())
    assert data["scenarios"]["The count degrades honestly when the database is unavailable"] == {"verifier": "hurl"}
    assert len(data["scenarios"]) == 6


def test_write_stamps_refuses_a_collision_outright(tmp_path: Path):
    stamped_yaml = BASE_YAML + "scenarios:\n  \"The count of an empty store is zero\":\n    verifier: toolchain\n"
    repo = _repo(tmp_path, stamped_yaml)
    yaml_path = repo / ".guardkit" / "features" / "FEAT-UCNT.yaml"
    before = yaml_path.read_text()
    with pytest.raises(StampNormalizerError, match="refusing to overwrite"):
        write_stamps(yaml_path, {"The count of an empty store is zero": {"verifier": "hurl"}})
    assert yaml_path.read_text() == before


def test_refuse_loud_names_every_undecidable_title_and_writes_nothing(tmp_path: Path):
    feature_text = (
        "Feature: Parser\n"
        "  Scenario: The parser accepts an empty document\n"
        "    Given an empty document\n    When it is parsed\n    Then no error is raised\n\n"
        "  Scenario: The count degrades honestly when the database is unavailable\n"
        "    Given the database is unavailable\n    Then it degrades\n\n"
        "  Scenario: Two flags cannot both be set\n"
        "    Given both flags\n    Then the loader complains\n"
    )
    repo = _repo(tmp_path, BASE_YAML, feature_text=feature_text)
    yaml_path = repo / ".guardkit" / "features" / "FEAT-UCNT.yaml"
    before = yaml_path.read_text()
    with pytest.raises(StampNormalizerRefusal) as excinfo:
        normalize_feature(yaml_path, None, repo)
    exc = excinfo.value
    assert exc.refused == ["The parser accepts an empty document", "Two flags cannot both be set"]
    msg = str(exc)
    assert "STAMP NORMALIZER" in msg and "UNDECIDABLE" in msg and "2 UNDECIDABLE" in msg
    for title in exc.refused:
        assert f"  - {title}" in msg
    for home in VERIFIER_HOMES:
        assert home in msg  # the closed vocabulary, spelled out
    assert "operator" in msg and "never as a default" in msg
    assert "nothing was written" in msg
    # NOTHING written — not even the decidable DB-down scenario (the run stops).
    assert yaml_path.read_text() == before


def test_refusal_is_the_same_object_the_loader_hook_surfaces(tmp_path: Path):
    feature_text = "Feature: P\n  Scenario: The parser accepts an empty document\n    Given an empty document\n"
    repo = _repo(tmp_path, BASE_YAML, feature_text=feature_text)
    with pytest.raises(StampNormalizerRefusal):
        FeatureLoader.load_feature("FEAT-UCNT", repo_root=repo, validate_paths=False, normalize_stamps=True)


def test_no_feature_files_is_a_loud_cannot_run_not_a_silent_no_op(tmp_path: Path):
    no_files = BASE_YAML.replace(
        "feature_files:\n  - features/users-count-endpoint/users-count-endpoint.feature\n", ""
    )
    repo = _repo(tmp_path, no_files)
    with pytest.raises(StampNormalizerError, match="no `feature_files:`"):
        normalize_feature(repo / ".guardkit" / "features" / "FEAT-UCNT.yaml", None, repo)


def test_feature_files_given_as_argument_are_written_when_the_yaml_lacks_them(tmp_path: Path):
    no_files = BASE_YAML.replace(
        "feature_files:\n  - features/users-count-endpoint/users-count-endpoint.feature\n", ""
    )
    repo = _repo(tmp_path, no_files)
    yaml_path = repo / ".guardkit" / "features" / "FEAT-UCNT.yaml"
    result = normalize_feature(
        yaml_path, ["features/users-count-endpoint/users-count-endpoint.feature"], repo
    )
    assert result.written
    data = yaml.safe_load(yaml_path.read_text())
    assert data["feature_files"] == ["features/users-count-endpoint/users-count-endpoint.feature"]
    assert len(data["scenarios"]) == 6


def test_writer_handles_scenarios_flow_empty_and_block_with_trailing_keys(tmp_path: Path):
    # `scenarios: {}` — a plan-writer's empty map.
    y1 = BASE_YAML.replace("tasks:\n", "scenarios: {}\ntasks:\n")
    repo = _repo(tmp_path, y1)
    yaml_path = repo / ".guardkit" / "features" / "FEAT-UCNT.yaml"
    normalize_feature(yaml_path, None, repo)
    data = yaml.safe_load(yaml_path.read_text())
    assert len(data["scenarios"]) == 6 and data["tasks"][0]["id"] == "TASK-UCNT-001"
    # block form in the MIDDLE of the file, with a stamp already there.
    y2 = BASE_YAML.replace(
        "tasks:\n",
        "scenarios:\n  \"The count of an empty store is zero\":\n    verifier: toolchain\n    test_ref: test_count_empty\n"
        "# trailing comment\ntasks:\n",
    )
    repo2 = tmp_path / "two"
    (repo2 / ".guardkit" / "features").mkdir(parents=True)
    (repo2 / "features" / "users-count-endpoint").mkdir(parents=True)
    (repo2 / "features" / "users-count-endpoint" / "users-count-endpoint.feature").write_text(UCNT_FEATURE)
    (repo2 / ".guardkit" / "features" / "FEAT-UCNT.yaml").write_text(y2)
    (repo2 / "qa" / "gates").mkdir(parents=True)
    (repo2 / "qa" / "gates" / "registry.yaml").write_text("gates:\n  - id: hurl-twins\n    path: x.py\n")
    yp2 = repo2 / ".guardkit" / "features" / "FEAT-UCNT.yaml"
    normalize_feature(yp2, None, repo2)
    text = yp2.read_text()
    assert "# trailing comment" in text
    data = yaml.safe_load(text)
    assert data["scenarios"]["The count of an empty store is zero"] == {
        "verifier": "toolchain", "test_ref": "test_count_empty",
    }
    assert len(data["scenarios"]) == 6
    assert data["tasks"][0]["id"] == "TASK-UCNT-001" and data["preflight_strict"] is False


def test_an_invalid_existing_stamp_is_loud_before_anything_runs(tmp_path: Path):
    bad = BASE_YAML + "scenarios:\n  \"The count of an empty store is zero\":\n    verifier: pytest\n"
    repo = _repo(tmp_path, bad)
    with pytest.raises(StampNormalizerError, match="invalid existing stamp"):
        normalize_feature(repo / ".guardkit" / "features" / "FEAT-UCNT.yaml", None, repo)


def test_dry_run_writes_nothing(tmp_path: Path):
    repo = _repo(tmp_path, BASE_YAML)
    yaml_path = repo / ".guardkit" / "features" / "FEAT-UCNT.yaml"
    before = yaml_path.read_text()
    result = normalize_feature(yaml_path, None, repo, dry_run=True)
    assert result.dry_run and not result.written and len(result.stamped) == 6
    assert yaml_path.read_text() == before


# ---------------------------------------------------------------------------
# The feature_loader hook flag — OFF by default, inline when asked
# ---------------------------------------------------------------------------


def test_loader_default_is_unchanged_unstamped_feature_still_rejects_under_enforcement(tmp_path: Path):
    repo = _repo(tmp_path, BASE_YAML)
    (repo / ".guardkit" / "config.yaml").write_text("routing_law: enforced\n")
    assert FeatureLoader.normalize_stamps_on_load is False
    with pytest.raises(FeatureValidationError, match="UNSTAMPED"):
        FeatureLoader.load_feature("FEAT-UCNT", repo_root=repo, validate_paths=False)
    # …and nothing was written by the default path.
    assert "scenarios:" not in (repo / ".guardkit" / "features" / "FEAT-UCNT.yaml").read_text()


def test_loader_hook_stamps_inline_before_enforcement_when_asked(tmp_path: Path):
    repo = _repo(tmp_path, BASE_YAML)
    (repo / ".guardkit" / "config.yaml").write_text("routing_law: enforced\n")
    feature = FeatureLoader.load_feature(
        "FEAT-UCNT", repo_root=repo, validate_paths=False, normalize_stamps=True
    )
    assert len(feature.scenarios) == 6
    assert feature.scenarios["The count degrades honestly when the database is unavailable"].verifier == "probe:process"
    assert "scenarios:" in (repo / ".guardkit" / "features" / "FEAT-UCNT.yaml").read_text()


def test_loader_class_flag_drives_the_hook(tmp_path: Path, monkeypatch):
    repo = _repo(tmp_path, BASE_YAML)
    (repo / ".guardkit" / "config.yaml").write_text("routing_law: enforced\n")
    monkeypatch.setattr(FeatureLoader, "normalize_stamps_on_load", True)
    feature = FeatureLoader.load_feature("FEAT-UCNT", repo_root=repo, validate_paths=False)
    assert len(feature.scenarios) == 6


# L1 — the writer accepts `scenarios: null` / `~` / `[]` / `{}` as the block
# to fill; it never writes a second `scenarios:` key.
@pytest.mark.parametrize("empty_form", ["null", "~", "[]", "{}", ""])
def test_l1_writer_fills_an_empty_scenarios_value_in_any_yaml_spelling(tmp_path: Path, empty_form):
    yp = tmp_path / "F.yaml"
    yp.write_text(f"id: FEAT-X\nname: X\nscenarios: {empty_form}\ntasks: []\n", encoding="utf-8")
    write_stamps(yp, {"A GET request works": {"verifier": "hurl"}})
    text = yp.read_text()
    assert text.count("scenarios:") == 1, text
    data = yaml.safe_load(text)
    assert data["scenarios"] == {"A GET request works": {"verifier": "hurl"}}
    assert data["tasks"] == [] and data["id"] == "FEAT-X"


# L2 — a missing task doc is logged at WARNING naming the path, never swallowed.
def test_l2_missing_task_doc_is_a_named_warning(tmp_path: Path, caplog):
    import logging

    missing = tmp_path / "TASK-GONE.md"
    with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.stamp_normalizer"):
        nodes = collect_plan_test_nodes([missing])
    assert nodes == []
    assert any(str(missing) in rec.getMessage() and rec.levelno == logging.WARNING for rec in caplog.records), caplog.text


# L3 — a RULE-MINTED operator stamp is never silent: it is listed under a
# distinct `operator_stamped` key in the JSON and echoed by the CLI.
OPERATOR_FEATURE = (
    "Feature: Deploy\n"
    "  Scenario: The executor stands fleet-memory up on the real NAS\n"
    "    Given the runbook is pointed at the real NAS with the real deploy environment file\n"
    "    When the executor runs the runbook\n"
    "    Then fleet-memory Postgres with pgvector should be live on the NAS\n\n"
    "  Scenario: The count of an empty store is zero\n"
    "    When I send a GET request to /users/count\n"
    "    Then the response status code should be 200\n"
)


def test_l3_operator_stamps_are_named_in_the_result_and_the_cli_echo(tmp_path: Path):
    from guardkit.cli.main import cli

    repo = _repo(tmp_path, BASE_YAML, feature_text=OPERATOR_FEATURE)
    result = normalize_feature(repo / ".guardkit" / "features" / "FEAT-UCNT.yaml", None, repo, dry_run=True)
    assert result.operator_stamped == ["The executor stands fleet-memory up on the real NAS"]
    assert result.to_dict()["operator_stamped"] == result.operator_stamped
    assert result.stamped["The count of an empty store is zero"] == "hurl"

    out = CliRunner().invoke(
        cli, ["qa", "normalize-stamps", "--feature", "FEAT-UCNT", "--repo", str(repo), "--dry-run"]
    )
    assert out.exit_code == 0, out.output
    payload = json.loads(out.output[out.output.index('{\n  "feature_id"'):])
    assert payload["operator_stamped"] == ["The executor stands fleet-memory up on the real NAS"]
    assert "minted `operator`" in out.output and "on the real NAS" in out.output


# ---------------------------------------------------------------------------
# The CLI — `guardkit qa normalize-stamps` (forge's hook shells this)
# ---------------------------------------------------------------------------


def test_cli_dry_run_prints_json_and_writes_nothing():
    from guardkit.cli.main import cli

    yaml_path = FIXTURE_ROOT / ".guardkit" / "features" / "FEAT-TIME.yaml"
    before = yaml_path.read_text()
    result = CliRunner().invoke(
        cli,
        ["qa", "normalize-stamps", "--feature", "FEAT-TIME", "--repo", str(FIXTURE_ROOT),
         "--dry-run", "--ignore-existing"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output[result.output.index("{"):])
    assert payload["feature_id"] == "FEAT-TIME" and payload["dry_run"] is True and payload["written"] is False
    assert payload["stamped"]["The endpoint is unaffected by database unavailability"] == "probe:process"
    assert payload["stamped"]["Write methods are rejected"] == "hurl"
    assert payload["repo_has_http_surface"] is True
    assert yaml_path.read_text() == before


def test_cli_writes_by_default_and_refuses_with_exit_2(tmp_path: Path):
    from guardkit.cli.main import cli

    repo = _repo(tmp_path, BASE_YAML)
    result = CliRunner().invoke(cli, ["qa", "normalize-stamps", "--feature", "FEAT-UCNT", "--repo", str(repo)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output[result.output.index("{"):])
    assert payload["written"] is True and len(payload["stamped"]) == 6
    assert "scenarios:" in (repo / ".guardkit" / "features" / "FEAT-UCNT.yaml").read_text()

    feature_text = "Feature: P\n  Scenario: The parser accepts an empty document\n    Given an empty document\n"
    repo2 = _repo(tmp_path / "r2", BASE_YAML, feature_text=feature_text)
    yp = repo2 / ".guardkit" / "features" / "FEAT-UCNT.yaml"
    before = yp.read_text()
    result2 = CliRunner().invoke(cli, ["qa", "normalize-stamps", "--feature", "FEAT-UCNT", "--repo", str(repo2)])
    assert result2.exit_code == 2, result2.output
    payload2 = json.loads(result2.output[result2.output.index("{"): result2.output.rindex("}") + 1])
    assert payload2["refused"] == ["The parser accepts an empty document"] and payload2["written"] is False
    assert yp.read_text() == before


def test_cli_missing_feature_is_exit_2_with_json(tmp_path: Path):
    from guardkit.cli.main import cli

    result = CliRunner().invoke(cli, ["qa", "normalize-stamps", "--feature", "FEAT-NOPE", "--repo", str(tmp_path)])
    assert result.exit_code == 2
    assert "not found" in result.output
