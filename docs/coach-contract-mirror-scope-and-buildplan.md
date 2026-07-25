# Coach contract-mirror — scope + buildplan (FEAT-CV4M)
## 2026-07-25 night · the serve-side mirror of the coach-ft-v4 training contract · binding spec

## 1. Why (receipts)

coach-ft-v4 is trained, gated, and examined: merged-gen 12/12 raw, serve gate 8/8 clean
UNFENCED parse, the frozen fleet-evals v2 bar 6/6 reps (see fleet-evals
`runs/coach-heldout/coach-ft-v4-2026-07-25/RESULTS-coach-heldout-v2bar-2026-07-25.md`).
Its wire contract is:

```
{"verdict": "approve" | "reject", "findings": [{"locus": "<the specific in-bundle signal>"}]}
```

RAW UNFENCED JSON — the entire response is the JSON object. `approve` ⇒ `findings: []`;
`reject` ⇒ ≥1 finding whose `locus` names the exact bundle field/value/symbol.

Production guardkit today prompts and parses the OLD COACHSPLIT grammar (fenced
` ```json ` block, `decision: approve|feedback`, `issues[]`, `criteria_verification[]`).
Flipping the coach model without this mirror breaks parsing; shipping the mirror without
the switch breaks today's coach. Hence: **capability + explicit switch, default OFF
(byte-identical legacy behaviour), flip after merge.**

## 2. The one law: adapt at the wire, never refactor the internals

Downstream consumers keep reading the EXISTING internal verdict object unchanged:
the loop branches on `decision` (`approve`/`feedback`), the fix-loop reads
`issues[].{description,location,suggestion,type,severity}`
(`agent_invoker.py:7200-7254`), AC rollup reads `criteria_verification`
(`autobuild.py:5798`, tolerant `.get(..., [])`), COACHSF01 substring-matches the parser
exception strings (`autobuild.py:5676`), qav_shadow normalizes `decision`
(`qav_shadow.py:568-575`). NONE of these change. The v4 wire shape is ADAPTED into that
internal object at parse time.

**Normative v4→internal mapping:**
- `task_id`, `turn`: injected from the orchestrator call-site context (the wire carries
  neither — by design).
- `decision`: `"approve"` if `verdict == "approve"` else `"feedback"`.
- `issues`: one entry per finding —
  `{"type": "finding", "severity": "major", "description": <locus>, "suggestion": "", "requirement": ""}`
  (severity `major` so findings land in the fix-loop's must-fix bucket — verify the
  bucketing boundary in `_parse_coach_feedback` and pin it in a test).
- `criteria_verification`: `[]` (rollup is tolerant).
- `rationale`: `""`.
- Plus provenance keys: `contract: "v4"` and `findings: <the raw findings list>`.

## 3. The switch

`GUARDKIT_COACH_CONTRACT` env ∈ {`coachsplit`, `v4`}; fallback to `.guardkit/config.yaml`
`autobuild.coach.contract`; default `coachsplit`. Precedence mirrors
`_get_coach_test_model` (`quality_gates/coach_validator.py:2077-2099`). With the switch
at default, EVERY existing behaviour and test stays byte-identical — that is an
acceptance criterion, not a hope.

## 4. The three changes (task-sized)

### Fix A — parser: v4-first extraction + adapter (TASK-CMIR-001)
`guardkit/orchestrator/coach_output_parser.py` (`extract_and_write`, :191-337). When the
active contract is `v4`: try (1) `json.loads` of the full stripped assistant text; else
(2) the LAST balanced JSON object containing a `"verdict"` key; on success validate the
v4 shape (verdict enum; findings list; approve⇒empty; reject⇒≥1 non-empty locus) and
ADAPT to the internal object per §2, then write `coach_turn_{turn}.json` exactly as
today and return it. On v4-parse failure fall through to the UNCHANGED legacy fenced
path (a transition safety net, logged). When the contract is `coachsplit`, behaviour is
byte-identical to today. Every parse logs which path fired
(`contract=v4 path=raw|balanced|legacy-fallback`). Exception classes and their message
substrings (`Coach decision not found` / `Coach decision invalid`) are UNCHANGED
(COACHSF01 coupling).

### Fix B — prompt: the v4 Decision Format + vocabulary (TASK-CMIR-002)
`agent_invoker.py::_build_coach_prompt` (:3003-3339) +
`_render_absence_of_failure_guards` (:3899). Under `v4`, the prompt's Decision Format
section is replaced with EXACTLY this normative block (train==serve parity with the
corpus instruction — adf `domains/coach-agent/build_v4_sft.py::V4_DECISION_FORMAT`):

```
## Decision Format

Respond with the verdict as a SINGLE RAW JSON object — no ```json fence, no
code fence of any kind, no prose before or after it. Your entire response is
the JSON object and nothing else; the orchestrator parses your response text
directly as JSON. Do **NOT** use Bash to write a file.

The exact contract:

{"verdict": "approve" | "reject", "findings": [{"locus": "<the specific in-bundle signal>"}]}

- "verdict": "approve" when the deterministic evidence supports every
  acceptance criterion; "reject" when any signal in the bundle defeats or
  fails to support approval.
- "approve" REQUIRES "findings": [] (empty list).
- "reject" REQUIRES at least one finding. Each finding's "locus" must name the
  exact bundle field, value, file path, or symbol that carries the defeating
  signal, quoting the bundle's own text (e.g. "bdd.scenarios_attempted=0 while
  bdd.feature_files lists \"features/x.feature\""). A generic locus
  ("not safe", "tests insufficient") is a contract violation.
- No other keys: no class, no task_id, no rationale — the two keys above are
  the entire contract.
```

And these vocabulary substitutions apply to the v4-rendered prompt (the corpus's
`VOCAB_FIXES`, serve-side mirror — legacy rendering untouched):
- `5. Either APPROVE or provide specific FEEDBACK` → `5. Either APPROVE or REJECT with specific findings`
- `when the evidence for a criterion is missing, that is FEEDBACK, not approval` → `… that is a REJECT, not approval`
- `Verify EACH criterion and create a criteria_verification entry:` → `Verify EACH criterion against the evidence:`
- `Surface a "feedback" decision` → `Surface a "reject" verdict`
- `Surface as feedback` → `Surface as a reject finding`
- `verbatim in the rationale` → `verbatim in the finding locus`
The `criteria_verification` example blocks (`verification_example`, :3148-3161) and the
approve/feedback JSON examples (:3281-3322) do not render under v4 (the block above is
the whole output instruction). The "LAST fenced block" note (:3329-3332) does not render
under v4.

### Fix C — switch plumbing + v4 grammar (TASK-CMIR-003)
Resolve the contract per §3 and thread it to the prompt builder, the parser call site,
and grammar selection. New `guardkit/orchestrator/grammars/coach-verdict-v4.gbnf`
enforcing exactly the v4 shape (optional leading whitespace; top-level object with
`"verdict"` then `"findings"` in that order; verdict enum; findings = array of
one-key `{"locus": string}` objects; no other keys; forced end) — mirrored to the
`docs/research/dgx-spark/grammars/` twin per the existing parity convention
(grammar assertions live in `tests/orchestrator/test_coach_synthesis_split.py`). `load_coach_verdict_grammar` grows a
contract-aware selection; under `coachsplit` the existing grammar files and behaviour
are byte-identical. `COACH_DECISION_SCHEMA` (:820-824) is UNCHANGED (internal shape).

## 5. Done means

- All three lane suites green + zero net-new failures on the full suite vs main.
- With the switch OFF: legacy behaviour byte-identical (existing coach tests pass
  unmodified; a test asserts the legacy prompt string is unchanged).
- With the switch ON (hermetic): a canned v4 raw reply parses via the raw path into the
  §2 internal object; a canned legacy fenced reply still parses via the fallback; the v4
  prompt contains the normative block verbatim and none of the legacy vocabulary.
- The flip itself (env/config + `--coach-model coach-ft-v4` + live smoke) is the
  COORDINATOR'S post-merge step, not part of this build.

## 6. Fences

Normal topology for the BUILD itself (qwen36-workhorse player + gemma4-coach coach —
the build runs under the LEGACY contract while building the v4 capability; self-hosting
is safe pre-merge). No model swaps. No llama-swap config edits inside the build.
