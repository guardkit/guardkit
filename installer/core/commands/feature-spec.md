---
name: feature-spec
description: "Generate BDD Gherkin specifications using Propose-Review methodology"
arguments:
  description: "Feature description (positional, quoted string)"
flags:
  --from: "Path to input file(s). Repeatable."
  --output: "Output directory. Default: features/"
  --auto: "Skip interactive review, accept all AI proposals"
  --stack: "Override detected stack: python|typescript|go|rust|csharp|generic"
  --context: "Additional context files. Repeatable."
---

# Feature Spec - BDD Specification via Propose-Review

Generate complete, curated Gherkin specifications from loose feature descriptions using the Propose-Review methodology (Specification by Example, Gojko Adžić). This command produces living documentation that drives test automation — not scaffolding, not stub files, but fully reasoned behavioural specifications ready for review.

## Command Syntax

```bash
/feature-spec "feature description"
/feature-spec "feature description" --output features/auth/
/feature-spec --from docs/features/upload.md
/feature-spec --from spec.md --from context.md --auto
/feature-spec "file uploads" --stack python --context docs/limits.md
```

## Available Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--from <path>` | Read feature description from file. Repeatable. | - |
| `--output <dir>` | Output directory for generated files | `features/` |
| `--auto` | Skip interactive review (phases 3-5), mark everything as assumptions | false |
| `--stack <name>` | Override stack detection: `python`, `typescript`, `go`, `rust`, `csharp`, `generic` | auto-detect |
| `--context <path>` | Additional context file. Repeatable. | - |

---

## The Propose-Review Methodology

This command encodes six sequential phases derived from Specification by Example. The methodology treats specifications as a collaboration product, not an AI artefact. Each phase has a defined owner (AI or Human) and a clear hand-off point.

```
Phase 1: Context Gathering     (AI only, no interaction)
         ↓
Phase 2: Initial Proposal      (AI → Human)
         ↓
Phase 3: Human Curation        (Human → AI)
         ↓
Phase 4: Edge Case Expansion   (AI → Human, optional)
         ↓
Phase 5: Assumption Resolution (AI proposes, Human confirms)
         ↓
Phase 6: Output Generation     (AI writes files)
```

---

### Phase 1: Context Gathering

**Owner**: AI. No human interaction in this phase.

Before proposing any scenarios, gather all available context silently:

**1a. Stack detection** — use this priority order (stop at first match):

| Priority | Signal | Stack |
|----------|--------|-------|
| 1 | `pyproject.toml` or `setup.py` present | `python` |
| 2 | `requirements.txt` present | `python` |
| 3 | `go.mod` present | `go` |
| 4 | `Cargo.toml` present | `rust` |
| 5 | `*.csproj` or `*.sln` present | `csharp` |
| 6 | `package.json` present (only if no Python/Go/Rust signals) | `typescript` |
| 7 | None of the above | `generic` |

If `--stack` is provided, use that value regardless of auto-detection.

**1b. Codebase scan** — read these locations if they exist:

- Any existing `.feature` files (especially those from `/generate-bdd`) to understand prior conventions and avoid duplication
- Domain models: `src/models/`, `app/models/`, `lib/models/`, or equivalent for the detected stack
- API definitions: `src/api/`, `openapi.yaml`, `schema.graphql`, or equivalent
- Configuration files for limits/thresholds (e.g., `settings.py`, `config.ts`, `.env.example`)

**1c. Graphiti context** — if Graphiti is available, query for:

- ADRs (architectural decisions relevant to this feature)
- Domain warnings from past implementations
- Feature outcomes for related areas

**1d. Read --context files** — read all files passed via `--context` in order.

**1e. Read --from files** — if `--from` was used instead of a positional description, read those files now as the feature description source.

After gathering, output a single summary line:

```
Context loaded: stack=python, 3 models found, 2 existing .feature files, 1 ADR
```

---

### Phase 2: Initial Proposal

**Owner**: AI generates; Human receives.

Generate a complete set of Gherkin scenarios grouped by Specification by Example category. Present ALL scenarios at once — do not ask questions first. The human curates what you produce, not vice versa.

**Grouping structure:**

```
GROUP A: Key Examples — core happy-path behaviour
GROUP B: Boundary Conditions — values at exact limits
GROUP C: Negative Cases — invalid inputs, unauthorised access
GROUP D: Edge Cases — concurrency, failure recovery, unusual sequences
```

**Annotation format** — add a brief reasoning comment above each scenario:

```gherkin
  # Why: Core upload path — defines the expected outcome for a valid file
  @key-example @smoke
  Scenario: Uploading a valid document succeeds
    ...
```

**Tag reference:**

| Tag | Meaning |
|-----|---------|
| `@key-example` | Core happy-path behaviour (minimal complete definition of the feature) |
| `@boundary` | Value at an exact boundary (0, 1, max, max+1, empty, null) |
| `@negative` | Invalid input, unauthorised access, unsupported operation |
| `@edge-case` | Unusual situation, concurrency, failure recovery |
| `@smoke` | Minimal set the Coach must verify on every build |
| `@regression` | Protecting against a previously-observed failure |

**Gherkin rules for this phase:**

- Use `Background:` for context shared across ALL scenarios in a Feature block. Do not repeat setup steps in every scenario.
- Use `Scenario Outline` with `Examples:` tables when the same behaviour applies to multiple distinct input values. Do not create separate identical scenarios differing only in one value.
- Write in domain language. See the Domain Language section below.
- For every input that has documented bounds, generate BOTH a just-inside AND a just-outside boundary pair as `@boundary` scenarios.
- Do NOT include implementation hints in scenario steps.
- Do NOT reference HTTP status codes, SQL statements, file paths, or test IDs.

**Proposal output format:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC PROPOSAL: {feature name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Feature: {Feature Name}
  {user story: As a ... I want ... So that ...}

  Background:
    {shared setup steps}

━━ GROUP A: Key Examples ({N} scenarios) ━━

  # Why: {reasoning}
  @key-example @smoke
  Scenario: {scenario title}
    Given ...
    When ...
    Then ...

━━ GROUP B: Boundary Conditions ({N} scenarios) ━━

  # Why: Just-inside boundary — {bound description}
  @boundary
  Scenario Outline: {title}
    ...
    Examples:
      | value | result |
      | {at boundary} | {expected} |
      | {just inside} | {expected} |

  # Why: Just-outside boundary — should be rejected
  @boundary @negative
  Scenario: {title when value exceeds boundary}
    ...

━━ GROUP C: Negative Cases ({N} scenarios) ━━
  ...

━━ GROUP D: Edge Cases ({N} scenarios) ━━
  ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: {N} scenarios across {M} groups
Inferred assumptions: {K} (will be resolved in Phase 5)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### Phase 3: Human Curation

**Owner**: Human reviews; AI records decisions.

Present the curation interface AFTER the full proposal. Do NOT ask questions before showing the proposal.

**Curation actions per group:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURATION: Review each group
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each group, you may:

  [A] Accept  — include all scenarios in this group as-is
  [R] Reject  — exclude all scenarios in this group
  [M] Modify  — accept but specify changes (provide inline)
  [+] Add     — accept and add additional scenarios you describe
  [?] Defer   — mark group for future specification; excluded from output

Fast path: type "A A A A" to accept all four groups at once.

GROUP A — Key Examples ({N} scenarios): _
GROUP B — Boundary Conditions ({N} scenarios): _
GROUP C — Negative Cases ({N} scenarios): _
GROUP D — Edge Cases ({N} scenarios): _
```

**Modify workflow** — when human chooses [M] for a group, they provide inline text:

```
GROUP B: M
Change: maximum file size should be 100MB not 50MB
```

AI records the modification and applies it during output generation. No back-and-forth required.

**Add workflow** — when human chooses [+]:

```
GROUP A: +
Add: scenario where the user uploads a file that replaces an existing document with the same name
```

AI adds a `@key-example` scenario matching the description.

**If --auto flag is set**: skip this phase entirely. Mark all proposals as accepted. Every inferred value becomes an assumption with `confidence=low`.

---

### Phase 4: Edge Case Expansion

**Owner**: AI proposes additional scenarios; Human decides.

After curation, AI generates a SEPARATE set of scenarios covering:

- **Security**: authorisation bypass attempts, injection via filename or content, privilege escalation
- **Concurrency**: simultaneous uploads of the same resource, race conditions on limits
- **Data integrity**: partial failure mid-operation, retry after timeout, duplicate detection
- **Integration boundaries**: behaviour when a downstream service is unavailable, response when storage is full

Present as an optional offer, not a mandatory review:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EDGE CASE EXPANSION (optional)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

I've identified {N} additional scenarios covering security,
concurrency, and integration boundaries. Include them?

[Y] Yes — show and curate them (same A/R/M/+/? actions)
[S] Sample — show 2 examples, then decide
[N] No — skip and proceed to Phase 5

Your choice [Y/S/N]:
```

If **--auto** is set: skip this phase. No edge cases are added.

---

### Phase 5: Assumption Resolution

**Owner**: AI proposes defaults with confidence; Human confirms or overrides.

Every value that was inferred (not stated explicitly in the description or context files) must be surfaced here. This includes:

- Numeric limits that were assumed (file size, rate limits, retry counts)
- Time values (session duration, timeout, expiry)
- Enumerated sets where only some members were mentioned
- Default states not explicitly described

**Assumption format in output Gherkin:**

```gherkin
  # [ASSUMPTION: confidence=medium] Maximum upload size is 50MB based on common web defaults
  @boundary
  Scenario: Uploading a file at the size limit succeeds
    Given a document of exactly 50MB
    ...
```

**Resolution interface:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ASSUMPTION RESOLUTION ({N} items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each assumption has a proposed default. Press Enter to accept,
or type the actual value.

[1] Maximum file size
    Proposed: 50MB  Confidence: medium  Basis: common web default
    Accept or enter value: _

[2] Allowed file types
    Proposed: PDF, DOCX, PNG, JPG  Confidence: low  Basis: document management convention
    Accept or enter value: _

[3] Upload timeout
    Proposed: 30 seconds  Confidence: low  Basis: typical HTTP timeout
    Accept or enter value: _
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Confidence levels:**

| Level | Meaning | Gating |
|-------|---------|--------|
| `high` | Derived from explicit spec, codebase config, or ADR | Auto-proceed |
| `medium` | Derived from domain convention or similar features | Coach reviews |
| `low` | Inferred from general knowledge only | Mandatory human review |

**Gating rule:** If any assumption has `confidence=low` after Phase 5, the output summary will include a `REVIEW REQUIRED` flag. The Coach is expected to verify all low-confidence assumptions before accepting the specification.

If **--auto** is set: all assumptions use proposed defaults. All are marked `confidence=low`. The output summary will include `REVIEW REQUIRED: all assumptions unconfirmed`.

---

### Phase 6: Output Generation

**Owner**: AI writes files. No further interaction.

**Output directory:** `{--output}/` (default: `features/`)

**Subdirectory naming:** `{kebab-case-feature-name}/`

**Files written:**

```
features/
└── {feature-name}/
    ├── {feature-name}.feature
    ├── {feature-name}_assumptions.yaml
    └── {feature-name}_summary.md
```

**File 1: `{feature-name}.feature`**

Valid Gherkin, UTF-8, no BOM. Contains only accepted and modified scenarios. Rejected and deferred scenarios are excluded. Assumption annotations are included as comments above the affected scenario step.

```gherkin
# Generated by /feature-spec
# Feature: {Feature Name}
# Stack: {detected stack}
# Assumptions: {N} (see {feature-name}_assumptions.yaml)
# Generated: {ISO 8601 timestamp}

@{feature-tag}
Feature: {Feature Name}
  As a {actor}
  I want to {goal}
  So that {outcome}

  Background:
    {shared steps}

  # [ASSUMPTION: confidence=high] User must be authenticated before uploading
  @key-example @smoke
  Scenario: ...
```

**File 2: `{feature-name}_assumptions.yaml`**

Structured manifest of all resolved and unresolved assumptions.

```yaml
# Assumptions manifest for {feature-name}.feature
# Generated by /feature-spec

feature: "{Feature Name}"
generated: "{ISO 8601 timestamp}"
stack: "{detected stack}"
review_required: {true|false}

assumptions:
  - id: "ASSUM-001"
    scenario: "Uploading a file at the size limit succeeds"
    assumption: "Maximum file size is 50MB"
    confidence: medium
    basis: "Common web application default; not stated in feature description"
    human_response: "confirmed"

  - id: "ASSUM-002"
    scenario: "Uploading a file with a disallowed type is rejected"
    assumption: "Allowed types are PDF, DOCX, PNG, JPG"
    confidence: low
    basis: "Inferred from document management context"
    human_response: "overridden: PDF, DOCX only"
```

**Assumptions manifest schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique assumption ID (ASSUM-NNN) |
| `scenario` | string | Yes | Title of the scenario this assumption appears in |
| `assumption` | string | Yes | The assumed value or behaviour |
| `confidence` | string | Yes | `high`, `medium`, or `low` |
| `basis` | string | Yes | Why this value was assumed |
| `human_response` | string | Yes | `confirmed`, `overridden: {value}`, or `deferred` |

**File 3: `{feature-name}_summary.md`**

Human-readable summary intended for consumption by `/feature-plan`.

```markdown
# Feature Spec Summary: {Feature Name}

**Stack**: {detected stack}
**Generated**: {ISO 8601 timestamp}
**Scenarios**: {N} total ({smoke count} smoke, {regression count} regression)
**Assumptions**: {N} total ({high} high / {medium} medium / {low} low confidence)
**Review required**: {Yes / No}

## Scope

{2-3 sentence description of what the specification covers}

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | {N} |
| Boundary conditions (@boundary) | {N} |
| Negative cases (@negative) | {N} |
| Edge cases (@edge-case) | {N} |

## Deferred Items

{List of any scenarios or groups marked [?] Defer, with notes}

## Open Assumptions (low confidence)

{List of ASSUM-IDs with confidence=low that need human verification}

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "{Feature Name}" --context features/{feature-name}/{feature-name}_summary.md
```

---

## Domain Language

Write scenarios in the language of the business domain, not the implementation. This is the sharpest quality distinction between good and bad Gherkin.

### Contrasting Examples

**Correct (domain language):**

```gherkin
Then the upload should succeed
Then the error should indicate the file is too large
Then the document should be queued for categorisation
Then the user should be notified that their session has expired
Then the duplicate should be silently discarded
```

**Incorrect (implementation language):**

```gherkin
Then the server returns 201
Then response body contains {"error": "FILE_TOO_LARGE"}
Then INSERT INTO processing_queue
Then the JWT token expiry timestamp is in the past
Then Redis SETNX returns 0
```

**Why this matters:** Implementation-language Gherkin breaks when the technology changes (and it always does). Domain-language Gherkin stays valid across rewrites. It also serves as documentation for non-technical stakeholders.

### Domain Language Patterns

| Anti-pattern | Correction |
|--------------|------------|
| `the server returns 200` | `the request should succeed` |
| `the database contains 0 rows` | `no records should exist` |
| `the response body matches the schema` | `the returned details should be complete` |
| `the HTTP request times out after 30s` | `the operation should fail if the service is unavailable` |
| `the S3 key is overwritten` | `the previous version should be replaced` |

---

## Gherkin Pattern Reference

### Background for Shared Context

Use `Background:` when ALL scenarios in the Feature block share the same initial state. Do not use it for setup that only applies to some scenarios.

```gherkin
Feature: Document Upload

  Background:
    Given I am logged in as an authenticated user
    And the document storage service is available
```

### Scenario Outline for Parameterised Behaviour

Use `Scenario Outline` + `Examples:` when identical behaviour applies to distinct values. The Examples table makes the parameterisation explicit and reviewable.

```gherkin
  @boundary
  Scenario Outline: Files within the size limit are accepted
    Given a file of <size>
    When I upload the file
    Then the upload should succeed

    Examples:
      | size  |
      | 1KB   |
      | 1MB   |
      | 50MB  |

  @boundary @negative
  Scenario: A file exceeding the size limit is rejected
    Given a file of 50.1MB
    When I upload the file
    Then the upload should be rejected
    And the error should indicate the file is too large
```

### Assumption Annotation

Use the `# [ASSUMPTION: confidence=level]` comment immediately above the first step the assumption affects:

```gherkin
  @boundary
  Scenario: Uploading at the exact rate limit succeeds
    Given I have made 99 upload requests in the last minute
    # [ASSUMPTION: confidence=medium] Rate limit is 100 requests per minute based on API convention
    When I upload one more file
    Then the upload should succeed
```

---

## Worked Examples

### Example A: Full Propose-Review Trace

**Input:**

```
/feature-spec "users can upload documents to their profile"
```

**Phase 1 output:**

```
Context loaded: stack=python, 4 models found (User, Document, StorageQuota, UploadLog),
0 existing .feature files, 1 ADR (ADR-004: storage backend is S3-compatible)
```

**Phase 2 output (excerpt):**

```
GROUP A: Key Examples (3 scenarios)

  # Why: Core path — valid authenticated upload
  @key-example @smoke
  Scenario: A user uploads a valid document to their profile
    Given I am logged in
    And I have a 2MB PDF document
    When I upload the document
    Then the document should appear in my profile
    And I should receive confirmation that the upload succeeded

  # Why: Demonstrates replace behaviour for same-named file
  @key-example
  Scenario: Uploading a document with the same name replaces the previous version
    Given I have previously uploaded a document named "cv.pdf"
    When I upload a new document also named "cv.pdf"
    Then the previous version should be replaced
    And only one document named "cv.pdf" should appear in my profile

GROUP B: Boundary Conditions (4 scenarios)

  # Why: Just-inside boundary — file at exact limit
  @boundary
  Scenario Outline: Files within the allowed size are accepted
    Given a document of <size>
    When I upload the document
    Then the upload should succeed
    Examples:
      | size  |
      | 1KB   |
      | 50MB  |

  # Why: Just-outside boundary — file exceeding limit
  @boundary @negative
  Scenario: A document that exceeds the maximum size is rejected
    Given a document of 50.1MB
    When I upload the document
    Then the upload should be rejected
    And the error should indicate the file is too large
```

**Phase 3 curation:**

```
GROUP A: A
GROUP B: M
  Change: maximum file size is 100MB, not 50MB
GROUP C: A
GROUP D: ?
  Defer: concurrency scenarios pending load testing decisions
```

**Phase 4 (edge case expansion):**

```
Include additional security and integration scenarios? [Y/S/N]: S

Sample:
  @edge-case
  Scenario: Uploading a file with a malicious filename is handled safely
    Given a document with the filename "../../../etc/passwd"
    When I upload the document
    Then the upload should be rejected
    And no system files should be affected

  @edge-case
  Scenario: Upload fails gracefully when storage is unavailable
    Given the document storage service is unavailable
    When I upload a valid document
    Then I should be informed that the upload could not be completed
    And my other profile data should be unaffected

Include all {N} security/concurrency/integration scenarios? [Y/N]: Y
```

**Phase 5 (assumption resolution):**

```
[1] Maximum file size
    Proposed: 50MB  Confidence: medium
    Accept or enter value: 100MB

[2] Allowed file types
    Proposed: PDF, DOCX, PNG, JPG  Confidence: low
    Accept or enter value: PDF, DOCX

[3] Maximum documents per profile
    Proposed: 100  Confidence: low
    Accept or enter value: [Enter — accepted]
```

**Phase 6 files written:**

```
features/document-upload/document-upload.feature          (18 scenarios)
features/document-upload/document-upload_assumptions.yaml (3 assumptions)
features/document-upload/document-upload_summary.md
```

---

### Example B: Assumption Resolution Detail

**Situation:** Description says "users can upload files" with no size limits mentioned.

**AI proposes during Phase 5:**

```
[1] Maximum file size
    Proposed: 50MB
    Confidence: low
    Basis: General web convention; not stated in description or codebase config
    Accept or enter value: 25MB
```

**Human overrides to 25MB.**

**Resulting assumption in `.feature` file:**

```gherkin
  # [ASSUMPTION: confidence=low] Maximum file size overridden to 25MB by human
  @boundary @negative
  Scenario: A file larger than 25MB is rejected
    Given a file of 25.1MB
    When I upload the file
    Then the upload should be rejected
    And the error should indicate the file is too large
```

**Resulting assumption in `_assumptions.yaml`:**

```yaml
  - id: "ASSUM-001"
    scenario: "A file larger than 25MB is rejected"
    assumption: "Maximum file size is 25MB"
    confidence: low
    basis: "Not stated in description or codebase; overridden from 50MB default"
    human_response: "overridden: 25MB"
```

---

### Example C: Edge Case Expansion

**After initial curation of a payment feature, AI offers:**

```
EDGE CASE EXPANSION (optional)

I've identified 6 additional scenarios:

Security (2):
  - Payment with a stolen card number that passes Luhn check
  - Simultaneous payment attempts for the same order

Concurrency (2):
  - Two users apply the same single-use discount code at the same time
  - Payment confirmation arrives after order is marked as abandoned

Integration boundaries (2):
  - Payment gateway returns an ambiguous response (neither success nor failure)
  - Order total changes between checkout initiation and payment confirmation

Include them? [Y/S/N]: Y
```

**After inclusion, all 6 are presented for Group curation using the same A/R/M/+/? interface.**

---

## Anti-Patterns to Avoid

These patterns appeared in `/generate-bdd` and are explicitly prohibited here.

| Anti-pattern | Why it is wrong | Correct approach |
|--------------|-----------------|-----------------|
| `# Implementation: tests/e2e/auth.spec.ts::testLogin` | Couples spec to test file location; breaks on rename | Omit implementation references entirely |
| Skipping the curation phase | Removes human judgement from specification | Always present Phase 3 unless `--auto` |
| `Then the server returns 201` | Exposes HTTP concern in domain spec | Write `Then the request should succeed` |
| `Then INSERT INTO queue WHERE ...` | Exposes SQL in domain spec | Write `Then the item should be queued for processing` |
| Generating a flat list without grouping | Makes curation difficult | Always group by Specification by Example category |
| Generating scaffold files (step definitions, support code) | Out of scope for v1; pollutes output | Write `.feature` files only |

---

## Output Summary Format

After Phase 6 completes, display:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC COMPLETE: {Feature Name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files written:
  features/{feature-name}/{feature-name}.feature
  features/{feature-name}/{feature-name}_assumptions.yaml
  features/{feature-name}/{feature-name}_summary.md

Scenarios: {N} total
  @key-example: {N}   @boundary: {N}
  @negative: {N}      @edge-case: {N}
  @smoke: {N}         @regression: {N}

Assumptions: {N} total
  high: {N} (auto-proceed)
  medium: {N} (Coach review recommended)
  low: {N} (human review required)

{If any low-confidence assumptions:}
REVIEW REQUIRED: {N} low-confidence assumptions need verification
  See: features/{feature-name}/{feature-name}_assumptions.yaml

Deferred: {N} scenario groups (not included in output)

Next steps:
  Review: features/{feature-name}/{feature-name}.feature
  Pass to feature-plan: /feature-plan "{Feature Name}" \
    --context features/{feature-name}/{feature-name}_summary.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Execution Instructions for Claude

When the user runs `/feature-spec`, execute the six phases in sequence. This is an **interactive specification command** — you present proposals and wait for human input at phases 3, 4, and 5.

### Step-by-step execution

1. **Parse arguments.** Extract the positional description (if provided) and all flags. If `--from` is used, read those files as the description source. If both a positional description and `--from` are provided, concatenate them.

2. **Execute Phase 1** silently. Detect stack (respect `--stack` override). Scan codebase. Read `--context` files. Output the single summary line.

3. **Execute Phase 2.** Generate the complete grouped scenario proposal. Present it with the full formatting shown above. Then display the Phase 3 curation interface.

4. **Wait for Phase 3 input.** Record each group decision (A/R/M/+/?). Apply modifications and additions as described. If `--auto` is set, skip this wait — accept all groups automatically.

5. **Execute Phase 4.** Generate the additional edge case scenarios. Present the offer. Wait for Y/S/N response. If `--auto`, skip entirely.

6. **Execute Phase 5.** List all inferred assumptions. For each, state the proposed default, confidence, and basis. Wait for confirmation or override. If `--auto`, accept all defaults and mark all as `confidence=low`.

7. **Execute Phase 6.** Assemble all accepted scenarios (including modifications, additions, and edge cases). Apply assumption annotations. Write all three output files to `{--output}/{kebab-feature-name}/`. Display the output summary.

### Behavioural rules

- **Never ask questions before showing the proposal.** The proposal comes first; curation follows.
- **Never generate step definitions, support files, or test scaffolding.** Output is `.feature`, `_assumptions.yaml`, and `_summary.md` only.
- **Never reference implementation files** (no `# Implementation:` comments).
- **Never skip Phase 3** unless `--auto` is set. The interactive review cycle is the product.
- **Always produce just-inside and just-outside boundary pairs** for every documented numeric or enumerated limit.
- **Always annotate inferred values** with `# [ASSUMPTION: confidence=level]` in the Gherkin output.
- **Always write domain language.** If you find yourself writing an HTTP status code, a SQL fragment, or a file path into a scenario step, rewrite it in domain terms.
- **This command is purely additive.** It does not modify existing `.feature` files, task files, or any other workflow artefacts. It only creates new files in the output directory.

### --auto mode summary

When `--auto` is set:
- Phase 3: all groups accepted without review
- Phase 4: edge cases skipped
- Phase 5: all proposed defaults accepted; all confidence levels set to `low`
- Output includes `REVIEW REQUIRED: all assumptions unconfirmed (--auto mode)`
- Suitable for CI pipelines or rapid iteration where human review happens separately

### Error handling

| Condition | Behaviour |
|-----------|-----------|
| No description and no `--from` | Display usage error with syntax examples |
| `--from` file not found | Warn and skip that file; continue if other input exists |
| `--context` file not found | Warn and continue without that context |
| `--output` directory not writable | Display error with suggested fix |
| Stack detection finds no signals | Use `generic` stack; note in output summary |
| Description is very short (< 10 words) | Proceed but note in summary that more context may improve scenario quality |
