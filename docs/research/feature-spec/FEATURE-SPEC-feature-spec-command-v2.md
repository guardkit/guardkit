# Feature Specification: `/feature-spec` — BDD Specification Generator

**Date:** 2026-02-21 (v2) — revised 2026-02-22  
**Author:** Rich  
**Status:** Ready for `/system-plan` — architecture review complete  
**Research Method:** Claude Desktop (Opus 4.6) → GuardKit `/feature-plan`  
**Target Repo:** `appmilla/guardkit`  
**Target Branch:** `feature/feature-spec-command`  
**Feature ID:** FEAT-XXX *(assigned by `/feature-plan`)*

> **Revision note (2026-02-22):** Pre-`/system-plan` risk analysis incorporated. Key changes: (1) all `src/guardkit/` paths corrected to `guardkit/`; (2) slash command path corrected to `.claude/commands/`; (3) Tasks 1–3 (formatter modules) deferred to v2 — design preserved in `docs/research/feature-spec/FEATURE-SPEC-v2-formatter-modules.md`; (4) Task 5 simplified to inline approach; (5) Graphiti seeding added to Task 5; (6) `/generate-bdd` learnings incorporated into Task 4; (7) stack detection simplified for GuardKit's Python-primary reality; (8) additive design constraint formalised as D11.

---

## 1. Problem Statement

GuardKit's AutoBuild Player-Coach loop needs unambiguous, machine-verifiable acceptance criteria to produce reliable output. Currently, feature specifications are hand-written prose with manually crafted acceptance criteria that vary in quality and specificity. The gap between a product owner's loose feature description and an AutoBuild-ready specification requires Rich to manually translate intent into precise, verifiable behaviour — creating a bottleneck that doesn't scale.

A `/feature-spec` command that takes vague requirements and generates comprehensive BDD Gherkin feature files would eliminate this bottleneck, producing specifications that are simultaneously human-readable documentation, machine-verifiable test cases, and Coach validation scripts.

The command must be technology-stack agnostic — GuardKit projects may use Python, TypeScript/Node, Go, Rust, C#, or any other language. Gherkin itself is language-neutral; the test scaffolding layer must adapt to whatever stack the target project uses.

The specification methodology must be **generative, not extractive** — the AI proposes concrete behavioural examples that the human curates, rather than asking elicitation questions that the human must answer from scratch. This is the core lesson from RequireKit's failure: product owners don't want to be interrogated, they want to review and refine proposals.

## 2. Decision Log

| # | Decision | Rationale | Alternatives Rejected | ADR Status |
|---|----------|-----------|----------------------|------------|
| D1 | Use Gherkin (Given/When/Then) as the specification format | Simultaneously serves as spec, test cases, and Coach validation criteria. Readable by non-technical stakeholders. Language-agnostic — Gherkin runners exist for every major language. Massive LLM training data coverage means generation quality will be high | EARS notation (never used in practice, no tooling benefit), plain prose acceptance criteria (ambiguous, not machine-executable), OpenAPI-only (covers APIs but not business logic) | Accepted |
| D2 | Implement as a GuardKit slash command (`/feature-spec`) in Claude Code, not a standalone CLI tool | Claude Code can read the actual codebase during generation — real class names, real API endpoints, real data models. This context makes Gherkin scenarios concrete rather than abstract. No separate tool to maintain | RequireKit command (RequireKit is being deprecated for Rich's workflow), standalone CLI (loses codebase context), Claude Desktop only (can't read codebase) | Accepted |
| D3 | Technology-stack detection with pluggable test scaffolding | The Gherkin `.feature` files are universal. The test scaffolding (step definitions, runner config, fixture patterns) must adapt to the target project's stack. Auto-detect from codebase signals (package.json → Node, go.mod → Go, pyproject.toml/requirements.txt → Python, etc.), with `--stack` override | Hardcode pytest-bdd only (excludes non-Python projects), generate no scaffolding (Player writes all boilerplate from scratch — error-prone for local models) | Accepted |
| D4 | Generate both `.feature` files AND stack-appropriate test scaffolding | Feature files alone aren't executable — the Player needs step definition scaffolding to implement against. Generating skeletons with correct imports and patterns for the detected stack means the Player writes implementation logic, not boilerplate | Feature files only (Player has to write all scaffolding — error-prone), full implementations (too speculative, likely wrong) | Accepted |
| D5 | Accept any unstructured text as input — no required format | The whole point is to bridge from loose ideas to precise specs. Requiring structured input defeats the purpose. The command handles: pasted text, file references, Linear ticket descriptions, voice-dictation transcripts, rough notes | Structured YAML input (too much ceremony), RequireKit prep templates (abandoned approach), mandatory fields (creates friction) | Accepted |
| D6 | **Propose-review methodology** (Specification by Example) — AI generates concrete behavioural examples, human curates | This is the inverse of RequireKit's elicitation approach. Instead of asking "what are the validation rules?", the AI proposes: "Here's what I think happens when someone uploads a 60MB file — they get a 413 with this message. Sound right?" The human accepts, rejects, or modifies. The AI does the creative work; the human curates. Much closer to how product owners naturally think | RequireKit-style question-based elicitation (product owners resist interrogation), no interaction at all (risks generating wrong behaviour), structured questionnaire (same problem as RequireKit) | Accepted |
| D7 | Output a feature summary markdown alongside Gherkin for `/feature-plan` consumption | `/feature-plan` needs more than just Gherkin — it needs a brief description, component list, and technical context to decompose into tasks properly. The summary is auto-generated from the Gherkin scenarios, not a separate authoring step | Gherkin only (insufficient for `/feature-plan`), full research template (overkill, that's for complex features needing deep research), manual summary (defeats automation) | Accepted |
| D8 | Slash command implemented as a GuardKit custom command markdown file with supporting Python module | GuardKit's slash command system uses markdown files that define the prompt/methodology, backed by Python modules for any tooling. The prompt engineering in the markdown IS the product — the Python is just file I/O | Pure Python CLI (loses the prompt methodology pattern), pure markdown (can't do file I/O for reading codebase context), MCP server (unnecessary complexity) | Accepted |
| D9 | Generate a structured **Assumptions Manifest** (YAML) alongside Gherkin | Every specification encodes assumptions — make them explicit rather than silent. The manifest lists every assumption made during spec generation with confidence levels (high/medium/low) and basis. This integrates directly with AutoBuild's Structured Uncertainty Handling: assumptions from `/feature-spec` flow into the implementation pipeline as documented, gateable decision points. The Coach validates the Player's implementation against the manifest as well as the Gherkin | No assumptions tracking (silent assumptions become bugs), inline comments only (not machine-parseable, can't gate on confidence levels) | Accepted |
| D10 | Gherkin scenarios use domain language, not implementation language | Scenarios should describe **what** happens, not **how** it's implemented. "When I upload a document" not "When I POST to /api/v1/documents". This keeps Gherkin stack-agnostic and focused on behaviour. Implementation details (endpoints, classes, methods) go in the step definitions and the summary document | Implementation-specific Gherkin (couples spec to stack, breaks if implementation changes), abstract Gherkin with no domain terms (too vague, doesn't constrain implementation enough) | Accepted |
| D11 | `/feature-spec` is purely additive — existing `/feature-plan` and AutoBuild workflows must continue to work unchanged when no Gherkin spec exists | The `JobContextRetriever` returns `[]` for the `feature_specs` group when no spec has been seeded — this is the current behaviour for every feature today. `/feature-plan` proceeds with `feature_spec = {}` via graceful degradation. No changes to retrieval logic or existing command files are permitted. | Any change that makes Gherkin a requirement would break existing workflows | Accepted |

**Warnings & Constraints:**
- Gherkin `Scenario Outline` with `Examples` tables should be used for parameterised cases — the Player is familiar with this pattern
- Feature files must use UTF-8 encoding — no BOM
- Gherkin scenarios should be specific enough that exactly one implementation satisfies them — if multiple valid implementations exist, the scenario is too vague
- The command should NOT attempt to run the generated tests — that's the Coach's job during AutoBuild
- Stack detection heuristics will need extending over time as new project types are encountered — design for easy addition of new stack profiles
- The Assumptions Manifest is a machine-readable complement to the `# [ASSUMPTION]` comments in Gherkin — both must stay in sync

---

## 3. Specification Methodology: Propose-Review (Specification by Example)

This section defines the core methodology that the `/feature-spec` command encodes. This is the product — everything else is supporting infrastructure.

### 3.1 Why Propose-Review, Not Elicitation

RequireKit's structured elicitation failed because it asked the product owner to generate answers to questions. This requires the human to do the creative work of imagining the system's behaviour from scratch, under interrogation. Product owners resist this — it feels like an exam.

Specification by Example (Gojko Adžić) inverts this: the specifier generates **concrete examples** of the system's behaviour, and the stakeholder says "yes, that's right" or "no, it should be like this instead." The creative burden shifts to the AI. The human's job is curation — a much lower-friction activity that maps to how product owners naturally think.

### 3.2 The Propose-Review Cycle

```
Phase 1: Context Gathering (no human interaction)
    AI reads codebase structure, existing patterns, Graphiti ADRs/warnings
    AI reads the loose input description
    AI builds internal model of the feature's domain
         │
         ▼
Phase 2: Initial Proposal (AI → Human)
    AI generates a COMPLETE set of Gherkin scenarios organised by category:
    
    KEY EXAMPLES — The minimal set that completely defines the happy path
      "Here's what I think the core behaviour looks like..."
    
    BOUNDARY EXAMPLES — Values at exact boundaries (0, 1, max, max+1)
      "Here's what happens at the edges..."
    
    NEGATIVE EXAMPLES — What should NOT happen (invalid input, unauthorised access)
      "Here's what I think should be rejected..."
    
    ILLUSTRATIVE EXAMPLES — Edge cases and unusual situations
      "Here are some tricky cases I think we should handle..."
    
    The AI presents ALL scenarios at once, grouped and annotated.
    Each scenario has a brief natural-language annotation explaining the AI's reasoning.
         │
         ▼
Phase 3: Human Curation (Human → AI)
    For each scenario group, the human can:
    
    ✓ ACCEPT   — "Yes, that's right" (most scenarios — this is the fast path)
    ✗ REJECT   — "No, remove that" (AI proposed behaviour that's not wanted)
    ✎ MODIFY   — "Close, but the limit should be 100MB not 50MB"
    + ADD      — "You missed this case: what about concurrent uploads?"
    ? DEFER    — "I don't know yet, mark as assumption"
    
    The human does NOT need to review every scenario individually.
    They can accept entire groups: "Happy path looks good, edge cases look good,
    but change the error messages in the validation group."
         │
         ▼
Phase 4: AI-Driven Edge Case Expansion (AI → Human)
    After human curation, the AI generates ADDITIONAL scenarios 
    the human likely didn't consider:
    
    - Security implications (authentication, authorisation, injection)
    - Concurrency/race conditions
    - Data integrity (what if the database is down mid-operation?)
    - Integration boundaries (what events should be published?)
    
    These are presented as: "I've thought of some additional cases you might 
    want to cover. These are optional — accept or reject each one."
         │
         ▼
Phase 5: Assumption Resolution
    Any scenario marked DEFER or where the AI had to infer behaviour
    gets a final pass:
    
    AI proposes a sensible default for each, with reasoning:
      "For the file size limit, I'm assuming 50MB based on common web app 
       defaults. I'll mark this as [ASSUMPTION: confidence=medium]."
    
    Human can accept the default or specify the actual value.
    All assumptions get recorded in the Assumptions Manifest with 
    confidence levels that feed into AutoBuild's gating rules.
         │
         ▼
Phase 6: Output Generation
    - {name}.feature              — Final Gherkin with [ASSUMPTION] annotations
    - {name}_assumptions.yaml     — Structured assumptions manifest
    - {name}_scaffolding/         — Stack-appropriate test scaffolding
    - {name}_summary.md           — Feature summary for /feature-plan
```

### 3.3 Scenario Categories (Specification by Example)

The methodology uses Gojko Adžić's example categories, adapted for AI-generated specs:

| Category | Purpose | AI Generation Strategy |
|----------|---------|----------------------|
| **Key Examples** | The minimal set that completely specifies the core behaviour | Generated first. These define the happy path. If these are wrong, everything else is wrong. Presented to human for validation before proceeding. |
| **Boundary Examples** | Values at exact boundaries — 0, 1, max, max+1, empty string, null | AI systematically identifies every input that has bounds and generates pairs: just-inside and just-outside the boundary. |
| **Negative Examples** | What should NOT happen — invalid input, unauthorised access, unsupported operations | AI generates based on: what types does each input accept? What access controls exist? What operations are explicitly excluded? |
| **Illustrative Examples** | Edge cases, unusual combinations, concurrent operations, failure recovery | AI's highest-value contribution — generating cases the human wouldn't think of. Data integrity failures, race conditions, partial success states. |

### 3.4 How This Differs from RequireKit

| Aspect | RequireKit (Elicitation) | /feature-spec (Propose-Review) |
|--------|------------------------|-------------------------------|
| Who does the creative work | Human (answers questions) | AI (proposes examples) |
| Human's role | Author | Curator |
| Interaction pattern | Q&A interrogation | Review & approve |
| Failure mode | Human abandons session (James's experience) | Human quickly accepts/rejects batches |
| Output format | Prose requirements | Executable Gherkin scenarios |
| Assumption handling | Implicit (hidden in prose) | Explicit (manifest with confidence levels) |
| Duration | 30-60 minutes of Q&A | 5-10 minutes of review |

---

## 4. Structured Uncertainty Integration

### 4.1 Defence-in-Depth Stack

`/feature-spec` is the **upstream** layer in a defence-in-depth strategy against silent assumptions. It works in concert with the Structured Uncertainty Handling architecture (see `structured-uncertainty-handling.md`):

```
Layer 1: /feature-spec (UPSTREAM — specification time)
    Generates comprehensive Gherkin → reduces ambiguity surface
    Captures known assumptions in Assumptions Manifest
    Human curates before implementation begins
         │
         ▼
Layer 2: Mandatory Assumptions Document (IMPLEMENTATION — AutoBuild execution)
    Player produces assumptions YAML before writing code
    Catches implementation-level ambiguity Gherkin didn't cover
    (which library? what retry strategy? what log format?)
         │
         ▼
Layer 3: Coach Ambiguity Detection (VALIDATION — AutoBuild review)
    Coach compares Player's code against Gherkin source
    Detects: concepts not in spec, self-posed-then-answered questions,
    APIs/patterns not in Graphiti context
    Coach publishes pipeline.assumptions-challenged event
         │
         ▼
Layer 4: Graphiti Coverage Gating (CONTEXT — before execution)
    Low knowledge-graph coverage for task domain tags → pause
    Prevents execution when the system doesn't have enough context
```

Each layer catches what the previous one missed. The Gherkin scenarios from `/feature-spec` give the Coach (Layer 3) something concrete to validate against — "the Player assumed retry logic but no scenario mentions retries" is a detectable divergence.

### 4.2 Assumptions Manifest Schema

Generated alongside the Gherkin `.feature` file:

```yaml
# {feature_name}_assumptions.yaml
# Generated by /feature-spec on 2026-02-21
# Source: "Users need to upload documents and have them categorised"

feature: Document Upload and Categorisation
generated_by: /feature-spec
date: 2026-02-21

assumptions:
  - id: ASM-001
    scenario: "Reject file exceeding maximum size"
    assumption: "Maximum file size is 50MB"
    confidence: medium
    basis: "Common web application default — not specified in input"
    human_response: defer  # accept | reject | modify | defer
    
  - id: ASM-002
    scenario: "Low confidence categorisation triggers review"
    assumption: "Confidence threshold for auto-categorisation is 0.7"
    confidence: medium
    basis: "Standard ML classification threshold — not specified in input"
    human_response: accept
    
  - id: ASM-003
    scenario: "Handle concurrent uploads from same user"
    assumption: "Concurrent uploads are allowed, no per-user queue"
    confidence: low
    basis: "Input didn't mention concurrency — assumed permissive by default"
    human_response: defer

summary:
  total: 3
  high_confidence: 0
  medium_confidence: 2
  low_confidence: 1
  
# AutoBuild gating:
# - All high → auto-proceed
# - Any medium → Coach reviews, may auto-approve
# - Any low → mandatory human review before implementation
# - If total assumptions > 5 → flag feature as underspecified
```

### 4.3 How Assumptions Flow Through the Pipeline

```
/feature-spec generates assumptions manifest
    ↓
Rich reviews assumptions during Gherkin curation
    ↓ (accepted/modified assumptions stay, rejected ones update the Gherkin)
    ↓
/feature-plan reads assumptions manifest
    ↓ (flags low-confidence assumptions in task metadata)
    ↓
AutoBuild Player reads assumptions as part of Graphiti context
    ↓ (Player's Mandatory Assumptions Document references /feature-spec assumptions)
    ↓
Coach validates Player's implementation against BOTH Gherkin AND assumptions
    ↓ (detects if Player silently changed an assumption without flagging it)
    ↓
Approved assumptions → seeded to Graphiti for future context
```

---

## 5. Architecture

### 5.1 System Context

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Claude Code (MacBook Pro)                        │
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │  /feature-    │────▶│  /feature-   │────▶│  /feature-   │        │
│  │   spec        │     │   plan       │     │   build      │        │
│  │              │     │              │     │  (AutoBuild)  │        │
│  │ Loose ideas  │     │ Gherkin +    │     │  on Dell      │        │
│  │ → Gherkin    │     │ summary →    │     │  ProMax       │        │
│  │ + assumptions│     │ FEAT-XXX     │     │              │        │
│  │ + scaffolding│     │ with tasks   │     └──────────────┘        │
│  └──────────────┘     └──────────────┘                              │
│         │                                                            │
│         ▼                                                            │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  Output Files (stack-agnostic core + stack-specific scaff) │     │
│  │  features/document-upload/                                  │     │
│  │  ├── document_upload.feature          (Gherkin — universal)│     │
│  │  ├── document_upload_assumptions.yaml (assumptions manifest)│    │
│  │  ├── document_upload_summary.md       (for /feature-plan)  │     │
│  │  └── scaffolding/                     (stack-specific)     │     │
│  │      ├── steps.py          (if Python)                     │     │
│  │      ├── steps.ts          (if TypeScript)                 │     │
│  │      ├── steps_test.go     (if Go)                         │     │
│  │      └── conftest.py / setup.ts / etc.                     │     │
│  └────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Stack Detection and Scaffolding

The command auto-detects the project's technology stack using a **priority-based rule** — earlier signals win:

| Priority | Signal | Detected Stack | BDD Runner | Step File Extension |
|----------|--------|---------------|------------|-------------------|
| 1 (highest) | `pyproject.toml` | Python | pytest-bdd | `_steps.py` |
| 2 | `requirements.txt` or `setup.py` | Python | pytest-bdd | `_steps.py` |
| 3 | `go.mod` | Go | godog | `_steps_test.go` |
| 4 | `Cargo.toml` | Rust | cucumber-rs | `_steps.rs` |
| 5 | `package.json` (no Python signals present) | TypeScript/Node | cucumber-js | `_steps.ts` |
| None | No signals found | Generic | No scaffolding — Gherkin only | N/A |

**Priority matters for polyglot repositories.** If `pyproject.toml` and `package.json` both exist at root (as in GuardKit itself, which has TypeScript test infrastructure alongside its Python package), Python is correctly detected. A `package.json` alone without Python signals indicates a TypeScript-primary project.

> **GuardKit-specific note:** GuardKit's `tsconfig.json` and `vitest.config.ts` at the repo root exist to support TypeScript integration test harnesses (`figma-to-react-workflow.test.ts`, `zeplin-to-maui-workflow.test.ts`). These are being deprecated. Once removed, the root-level TypeScript signals will disappear, making detection unambiguous. Until then, `pyproject.toml` ensures GuardKit is correctly detected as Python regardless. When running `/feature-spec` inside the GuardKit repo, stack will always resolve to Python. Use `--stack <target>` to override if speccing a feature for a different project's stack.

When no stack is detected (or `--stack generic`), the command generates **Gherkin only** with no test scaffolding. The Gherkin is the universal artefact; scaffolding is a convenience layer.

The `--stack` flag overrides detection: `--stack python`, `--stack typescript`, `--stack go`, etc.

### 5.3 Component Design

**v1 scope** (this implementation):

| Component | File Path | Purpose | New/Modified |
|-----------|-----------|---------|-------------|
| Slash command definition | `.claude/commands/feature-spec.md` | Prompt methodology — the propose-review cycle | New |
| Feature spec orchestration module | `guardkit/commands/feature_spec.py` | Stack detection, codebase scanning, file I/O, Graphiti seeding | New |
| Unit tests | `tests/test_feature_spec_command.py` | Tests for orchestration module | New |
| Integration tests | `tests/integration/test_feature_spec_e2e.py` | End-to-end pipeline tests | New |
| User documentation | `docs/commands/feature-spec.md` | Command reference and methodology guide | New |

> **Installer note:** For global distribution, `feature-spec.md` must also be added to `installer/core/commands/feature-spec.md`. The installer's `setup_claude_integration()` function symlinks `~/.claude/commands` → `~/.agentecflow/commands`, making the global commands available in all Claude Code sessions.

**v2 scope** (deferred — implement when usage evidence warrants):

| Component | File Path | Purpose |
|-----------|-----------|--------|
| Gherkin formatter/validator | `guardkit/formatters/gherkin.py` | Validate AI-generated Gherkin syntax | 
| Stack detector class | `guardkit/formatters/stack_detector.py` | Full `StackInfo` dataclass with confidence scoring |
| Scaffolding generator | `guardkit/formatters/scaffolding.py` | Stack-specific step definition generation |
| Assumptions generator class | `guardkit/formatters/assumptions.py` | Validated YAML manifest generation |
| Feature summary generator class | `guardkit/formatters/feature_summary.py` | Structured markdown generation |
| BDD templates | `guardkit/formatters/templates/` | Per-stack Python modules — `python.py`, `typescript.py`, `go.py`, `generic.py` (NOT `guardkit/templates/bdd/` — that directory holds Jinja2 `.j2` system templates; NOT a `bdd/` subdirectory — keep flat alongside the formatter code that uses them) |

Full v2 design is in `docs/research/feature-spec/FEATURE-SPEC-v2-formatter-modules.md`.

### 5.4 Data Flow (with Propose-Review)

```
1. User runs /feature-spec with loose description
         │
         ▼
2. Context gathering (no human interaction):
   a. Stack detection — scan for pyproject.toml, package.json, go.mod, etc.
   b. Codebase structure — module tree, source file patterns
   c. Existing patterns — scan for data models, API definitions, existing tests
      (language-agnostic: look for common patterns like class definitions,
       route handlers, schema declarations regardless of language)
   d. Graphiti context — relevant ADRs, patterns, warnings, domain knowledge
   e. Existing .feature files — avoid contradicting established scenarios
         │
         ▼
3. PROPOSE: AI generates complete Gherkin scenario set
   Organised by Specification by Example categories:
   - Key Examples (happy path — core behaviour)
   - Boundary Examples (0, 1, max, max+1, empty, null)
   - Negative Examples (invalid input, unauthorised, unsupported)
   - Illustrative Examples (edge cases, concurrency, failure recovery)
   
   Each scenario annotated with:
   - Category tag
   - AI's reasoning (brief natural-language note)
   - Assumption markers where AI inferred behaviour
         │
         ▼
4. REVIEW: Human curates the proposal
   Per scenario or per group:
   ✓ Accept  |  ✗ Reject  |  ✎ Modify  |  + Add  |  ? Defer
   
   Fast path: "Happy path looks good. Edge cases look good.
               Change the file size limit to 100MB in the validation group."
         │
         ▼
5. EXPAND: AI generates additional scenarios human didn't consider
   - Security implications
   - Concurrency/race conditions  
   - Data integrity under failure
   - Integration boundary events
   
   Presented as optional additions: "I've thought of these — want them?"
         │
         ▼
6. RESOLVE: Assumption resolution
   Each deferred or inferred item gets an AI-proposed default:
   "For file size limit, I'm assuming 50MB. Sound right?"
   
   Human accepts or specifies actual value.
   All assumptions recorded in manifest with confidence levels.
         │
         ▼
7. OUTPUT: Files written
   - {name}.feature                    — Gherkin (universal)
   - {name}_assumptions.yaml           — Structured assumptions manifest
   - {name}_summary.md                 — Feature summary for /feature-plan
   - scaffolding/{stack-specific files} — Test scaffolding (if stack detected)
```

### 5.5 Output Examples

**Gherkin Feature File** (stack-agnostic — works for any language):
```gherkin
# features/document_upload.feature
# Generated by /feature-spec on 2026-02-21
# Source: "Users need to upload documents and have them categorised"
# Stack: Python (detected) — scaffolding generated for pytest-bdd

Feature: Document Upload and Categorisation
  As a user
  I want to upload documents and have them automatically categorised
  So that I can find relevant documents without manual organisation

  Background:
    Given the application is running
    And I am an authenticated user

  # === KEY EXAMPLES (core behaviour) ===

  @key-example
  Scenario: Successfully upload a PDF document
    When I upload a file "report.pdf" of type "application/pdf"
    Then the upload should succeed
    And I should receive a document identifier
    And the document should be stored in the repository

  @key-example
  Scenario: Uploaded document is automatically categorised
    Given I have uploaded a document "invoice-2024.pdf"
    When the categorisation completes
    Then the document should have a category assigned
    And the confidence score should be above the threshold

  # === BOUNDARY EXAMPLES ===

  @boundary
  Scenario: Upload a file at exactly the maximum size
    When I upload a file of exactly 50 megabytes
    Then the upload should succeed

  # [ASSUMPTION: confidence=medium] Maximum file size is 50MB
  @boundary
  Scenario: Reject a file one byte over maximum size
    When I upload a file of 50 megabytes plus one byte
    Then the upload should be rejected
    And the error should indicate the file exceeds the size limit

  @boundary
  Scenario: Handle a zero-byte file
    When I upload an empty file
    Then the upload should be rejected
    And the error should indicate the file is empty

  # === NEGATIVE EXAMPLES ===

  @negative
  Scenario: Reject upload from unauthenticated user
    Given I am not authenticated
    When I attempt to upload a file
    Then the request should be rejected as unauthorised

  @negative
  Scenario: Reject unsupported file type
    When I upload a file "script.exe" of type "application/x-executable"
    Then the upload should be rejected
    And the error should indicate the file type is not supported

  # === ILLUSTRATIVE EXAMPLES (edge cases) ===

  @edge-case
  Scenario: Handle upload when categorisation service is unavailable
    Given the categorisation service is not responding
    When I upload a document
    Then the upload should still succeed
    And the document should be queued for categorisation
    And the document status should be "pending_categorisation"

  # [ASSUMPTION: confidence=low] Concurrent uploads allowed without queueing
  @edge-case
  Scenario: Concurrent uploads from the same user
    Given I have an upload in progress
    When I start a second upload simultaneously
    Then both uploads should complete independently

  # [ASSUMPTION: confidence=medium] Confidence threshold is 0.7
  @edge-case
  Scenario: Low confidence categorisation triggers manual review
    Given a document that could match multiple categories
    When the highest confidence score is below the threshold
    Then the document should be flagged for manual review
    And the document status should be "pending_review"
```

Note: scenarios describe behaviour using domain language ("the upload should succeed", "flagged for manual review"), not implementation language ("status code 201", "INSERT INTO documents"). This keeps the Gherkin valid regardless of whether the implementation is a REST API, GraphQL, gRPC, CLI, or message queue consumer.

**Python Step Skeleton** (generated when stack=python):
```python
"""Step definitions for Document Upload and Categorisation.

Generated by /feature-spec. Implement the step bodies.
The Coach will run these during AutoBuild validation.
"""
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

scenarios("../document_upload.feature")

# --- Background ---

@given("the application is running")
def app_running(test_client):
    """Verify application is available."""
    raise NotImplementedError

@given("I am an authenticated user")
def authenticated_user(auth_headers):
    """Set up authenticated session."""
    raise NotImplementedError

# --- Key Examples ---

@when(parsers.parse('I upload a file "{filename}" of type "{content_type}"'))
def upload_file(test_client, filename, content_type):
    """Upload a file to the document endpoint."""
    raise NotImplementedError

@then("the upload should succeed")
def upload_succeeded(response):
    """Verify upload was accepted."""
    raise NotImplementedError

# ... (continued for all steps)
```

**TypeScript Step Skeleton** (generated when stack=typescript):
```typescript
// Step definitions for Document Upload and Categorisation
// Generated by /feature-spec. Implement the step bodies.

import { Given, When, Then } from '@cucumber/cucumber';

// --- Background ---

Given('the application is running', async function () {
  // TODO: Implement — verify application is available
  throw new Error('Not implemented');
});

Given('I am an authenticated user', async function () {
  // TODO: Implement — set up authenticated session
  throw new Error('Not implemented');
});

// --- Key Examples ---

When('I upload a file {string} of type {string}', async function (filename: string, contentType: string) {
  // TODO: Implement — upload file to document endpoint
  throw new Error('Not implemented');
});

Then('the upload should succeed', async function () {
  // TODO: Implement — verify upload was accepted
  throw new Error('Not implemented');
});

// ... (continued for all steps)
```

**Go Step Skeleton** (generated when stack=go):
```go
package features

// Step definitions for Document Upload and Categorisation
// Generated by /feature-spec. Implement the step bodies.

import (
    "context"
    "github.com/cucumber/godog"
)

func InitializeScenario(ctx *godog.ScenarioContext) {
    // --- Background ---
    ctx.Given(`^the application is running$`, theApplicationIsRunning)
    ctx.Given(`^I am an authenticated user$`, iAmAnAuthenticatedUser)

    // --- Key Examples ---
    ctx.When(`^I upload a file "([^"]*)" of type "([^"]*)"$`, iUploadAFile)
    ctx.Then(`^the upload should succeed$`, theUploadShouldSucceed)
}

func theApplicationIsRunning(ctx context.Context) error {
    // TODO: Implement — verify application is available
    return godog.ErrPending
}

// ... (continued for all steps)
```

**Feature Summary** (`_summary.md`) — consumed by `/feature-plan`:
```markdown
# Feature: Document Upload and Categorisation

**Generated by:** /feature-spec  
**Date:** 2026-02-21  
**Source:** "Users need to upload documents and have them categorised"  
**Detected stack:** Python (pytest-bdd scaffolding generated)  
**Gherkin file:** features/document-upload/document_upload.feature  
**Assumptions manifest:** features/document-upload/document_upload_assumptions.yaml

## Scenario Coverage

| Category | Count | Examples |
|----------|-------|---------|
| Key examples | 2 | Successful upload, auto-categorisation |
| Boundary examples | 3 | Max size, over-max, zero-byte |
| Negative examples | 2 | Unauthenticated, unsupported file type |
| Illustrative (edge cases) | 3 | Service unavailable, concurrent uploads, low confidence |
| **Total** | **10** | |

## Assumptions (3)

| ID | Assumption | Confidence | Gating |
|----|-----------|-----------|--------|
| ASM-001 | Maximum file size is 50MB | medium | Coach review |
| ASM-002 | Confidence threshold is 0.7 | medium | Coach review |
| ASM-003 | Concurrent uploads allowed without queueing | low | **Human review required** |

## Components Affected

| Component | Action | Reason |
|-----------|--------|--------|
| Document upload handler | New | Core upload logic |
| Categorisation service | New | ML-based document classification |
| Document data model | New | Document entity with status tracking |
| Document repository | New | Storage abstraction |

## Test Execution

Detected stack: Python (pytest-bdd)
```bash
pytest tests/features/document_upload_steps.py -v
```
```

## 6. API Contracts

### 6.1 Slash Command Interface

**Command:** `/feature-spec`

**Usage:**
```bash
# From pasted/typed description
/feature-spec "Users need to upload documents and have them auto-categorised"

# From a file (Linear export, proposal doc, rough notes)
/feature-spec --from docs/ideas/document-upload.md

# From multiple input sources
/feature-spec --from docs/ideas/upload.md --from docs/ideas/categorisation-notes.txt

# With explicit output directory
/feature-spec "description" --output features/document-upload/

# Skip interactive propose-review cycle (accept all AI proposals)
/feature-spec "description" --auto

# Override detected stack
/feature-spec "description" --stack typescript

# Generate Gherkin only, no test scaffolding
/feature-spec "description" --stack generic

# With explicit context files
/feature-spec "description" --context features/existing-auth.feature
```

**Flags:**

| Flag | Description | Default |
|------|-------------|---------|
| `--from <path>` | Path to input file(s). Repeatable. Accepts .md, .txt, .pdf, .yaml | None (use positional arg) |
| `--output <dir>` | Output directory for generated files | `features/` relative to repo root |
| `--auto` | Skip propose-review cycle — AI makes all decisions, marks as assumptions | `false` |
| `--stack <name>` | Override detected technology stack. Options: `python`, `typescript`, `go`, `rust`, `csharp`, `generic` | Auto-detected from codebase |
| `--context <path>` | Additional context files (e.g., existing feature files, API docs). Repeatable | Auto-detected from codebase |
| `--scenarios` | Target scenario categories | `key,boundary,negative,illustrative` |

**Edge Cases:**
- Empty or near-empty input: command asks for more detail rather than generating empty Gherkin
- Input references features that already have `.feature` files: command notes existing coverage and generates only new/different scenarios
- Input is already partially Gherkin: command preserves existing scenarios and extends gaps
- Codebase has no detectable stack: generates Gherkin only (no scaffolding), prompts user to specify `--stack` if scaffolding desired
- Multiple stacks detected (monorepo): prompts user to specify which stack, or uses `--stack`

### 6.2 Output File Contract

All output files written to `{output_dir}/{feature_name}/`:

| File | Always Generated | Content |
|------|-----------------|---------|
| `{name}.feature` | Yes | Valid Gherkin syntax, UTF-8, no BOM, stack-agnostic |
| `{name}_assumptions.yaml` | Yes | Structured assumptions manifest with confidence levels |
| `{name}_summary.md` | Yes | Feature summary for `/feature-plan` consumption |
| `scaffolding/` directory | Only if stack detected/specified | Stack-specific step definitions, config, fixtures |

## 7. Implementation Tasks

### Task Metadata Guide

Each task includes metadata that drives GuardKit's job-specific context retrieval pipeline:
1. **Complexity** → determines Graphiti token budget (low: ~2000, medium: ~4000, high: ~6000+ tokens)
2. **Type** → influences which context categories are prioritised
3. **Domain tags** → semantic search keys for retrieving relevant ADRs, patterns, and warnings from Graphiti
4. **Relevant decisions** → explicit cross-references to Decision Log entries

### ~~Task 1: Gherkin Formatter and Validator Module~~ — Deferred to v2

> **Deferred.** Full design preserved in `docs/research/feature-spec/FEATURE-SPEC-v2-formatter-modules.md`. Trigger conditions for starting v2: local models (Qwen3-Coder) producing malformed Gherkin in >20% of runs, OR multi-stack usage requiring TypeScript/Go scaffolding beyond what inline generation provides. v1 trusts Claude's generation and validates through integration tests.

### ~~Task 2: Stack Detector and Scaffolding Generator~~ — Deferred to v2

> **Deferred.** Full design preserved in `docs/research/feature-spec/FEATURE-SPEC-v2-formatter-modules.md`. Note on templates: when v2 is implemented, BDD templates go in `guardkit/formatters/templates/bdd/` — **not** `guardkit/templates/bdd/`. The existing `guardkit/templates/` directory holds Jinja2 `.j2` system templates; mixing Python module templates there would create a confusing dual-purpose directory.

### ~~Task 3: Assumptions Manifest and Feature Summary Generators~~ — Deferred to v2

> **Deferred.** Full design preserved in `docs/research/feature-spec/FEATURE-SPEC-v2-formatter-modules.md`. v1 generates assumptions YAML and the feature summary inline in the Task 4 orchestration module using `yaml.dump()` and string formatting. pyyaml is already in `pyproject.toml` — no dependency changes needed.

### Task 4: `/feature-spec` Slash Command Definition (Methodology)

- **Task ID:** TASK-XXX
- **Complexity:** high
- **Type:** implementation
- **Domain tags:** `slash-command, prompt-engineering, bdd, gherkin, methodology, specification-by-example`
- **Files to create/modify:**
  - `.claude/commands/feature-spec.md` (new — project-local, for dogfooding inside GuardKit repo)
  - `installer/core/commands/feature-spec.md` (new — for global distribution via install.sh)
- **Files NOT to touch:** Any existing command files (especially `feature-plan.md`, `system-plan.md`), any Python source files
- **Dependencies:** None (this is a prompt/methodology file)
- **Inputs:** GuardKit's existing slash command format and conventions (study `.claude/commands/feature-plan.md`)
- **Outputs:** The complete slash command definition encoding the propose-review methodology
- **Relevant decisions:** D1, D2, D5, D6, D9, D10
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `.claude/commands/feature-spec.md`
  - [ ] File exists: `installer/core/commands/feature-spec.md` (identical content)
  - [ ] File contains YAML frontmatter with: `name`, `description`, `arguments`, `flags`
  - [ ] File defines the Propose-Review methodology with all 6 phases: Context Gathering → Initial Proposal → Human Curation → Edge Case Expansion → Assumption Resolution → Output Generation
  - [ ] File includes Specification by Example categories: `@key-example`, `@boundary`, `@negative`, `@edge-case`
  - [ ] File includes `@smoke` and `@regression` cross-cutting tags — scenarios tagged `@smoke` are the minimal set the Coach must verify; `@regression` marks scenarios protecting against previously-observed failures
  - [ ] File instructs AI to generate `Background:` sections where shared context applies across scenarios in a Feature block
  - [ ] File instructs AI to use `Scenario Outline` with `Examples` tables for parameterised cases
  - [ ] File includes the propose-review interaction pattern: AI presents grouped scenarios, human responds with accept/reject/modify/add/defer per group
  - [ ] File includes the edge case expansion phase where AI generates scenarios the human didn't consider
  - [ ] File includes assumption resolution with confidence levels and the "propose default" pattern
  - [ ] File includes instructions to use domain language (not implementation language) in Gherkin scenarios
  - [ ] File includes instructions to read codebase context in a stack-agnostic way (check for `pyproject.toml`, `go.mod`, `package.json` in priority order — see Section 5.2)
  - [ ] File includes instruction to check for existing `.feature` files from `/generate-bdd` and avoid generating contradictory scenarios
  - [ ] File includes 2-3 worked examples showing: (a) input → proposal → human curation → output, (b) assumption resolution flow, (c) edge case expansion
  - [ ] File specifies output file naming convention and structure (`features/{kebab-case-name}/`)
  - [ ] File specifies output directory convention so `/feature-plan` can scan for `.feature` files deterministically
  - [ ] File size > 5000 bytes (methodology must be substantial)
- **Implementation notes:** **This is the most important file in the entire feature.** The prompt methodology IS the product. The propose-review cycle must be clearly structured so Claude Code follows it consistently. Key principles to encode: (1) AI does the creative work of imagining behaviour, human curates; (2) scenarios use domain language — "the upload should succeed" not "return 201"; (3) boundary examples are systematic — for every input with bounds, generate just-inside AND just-outside; (4) assumptions are NEVER silent — every inference gets an `[ASSUMPTION]` tag with confidence; (5) the human can accept entire groups at once for speed. Include contrasting examples of good vs bad scenarios (concrete vs abstract, domain vs implementation language). **Learnings from `/generate-bdd` (being retired):** Do NOT include implementation hints in Gherkin comments (e.g. `# Implementation: tests/e2e/auth.spec.ts::testLogin`) — this was a pattern in `/generate-bdd` that couples spec to implementation and violates D10. Do NOT carry over the lack of interactive review from `/generate-bdd`; the propose-review cycle is the key improvement.
- **Player constraints:** Do not modify any existing command files. Study `.claude/commands/feature-plan.md` for format conventions but do not change it.
- **Coach validation commands:**
  ```bash
  python -c "
  import yaml
  with open('.claude/commands/feature-spec.md') as f:
      content = f.read()
      fm = content.split('---')[1]
      data = yaml.safe_load(fm)
      assert 'name' in data, 'Missing name'
      assert 'description' in data, 'Missing description'
      print('Frontmatter OK')
  "
  python -c "
  import os
  size = os.path.getsize('.claude/commands/feature-spec.md')
  assert size > 5000, f'Command definition too short ({size} bytes) — methodology needs more detail'
  print(f'Size OK: {size} bytes')
  "
  python -c "
  content = open('.claude/commands/feature-spec.md').read()
  required = ['Propose', 'Review', 'Boundary', 'Assumption', 'domain language', '@smoke', 'Background']
  for term in required:
      assert term.lower() in content.lower(), f'Missing methodology section: {term}'
  print('Methodology sections OK')
  "
  python -c "
  import filecmp
  assert filecmp.cmp('.claude/commands/feature-spec.md', 'installer/core/commands/feature-spec.md'), 'Files differ'
  print('Installer copy matches')
  "
  ```

### Task 5: Feature Spec Python Module (Orchestration)

- **Task ID:** TASK-XXX
- **Complexity:** medium
- **Type:** implementation
- **Domain tags:** `commands, file-io, codebase-scanning, orchestration, graphiti`
- **Files to create/modify:**
  - `guardkit/commands/feature_spec.py` (new)
  - `tests/test_feature_spec_command.py` (new)
- **Files NOT to touch:** All existing command modules, all existing Graphiti modules — this task only adds new files
- **Dependencies:** None (v1 uses inline implementation — no formatter module dependencies)
- **Inputs:** Codebase root path, input text/files, options dict
- **Outputs:** The orchestration module: stack detection, codebase scanning, file I/O, Graphiti seeding
- **Relevant decisions:** D2, D3, D5, D8, D11
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `guardkit/commands/feature_spec.py`
  - [ ] `detect_stack(root: Path) -> dict` function implementing the priority-based detection from Section 5.2: check `pyproject.toml` first (Python), then `requirements.txt`/`setup.py` (Python), then `go.mod` (Go), then `Cargo.toml` (Rust), then `package.json` (TypeScript) only if no Python signals present; returns `{"stack": str, "bdd_runner": str | None, "step_extension": str | None}`
  - [ ] `scan_codebase(root: Path, stack: dict) -> dict` function extracting: module tree, existing `.feature` files (for `/generate-bdd` migration awareness), and language-appropriate patterns
  - [ ] `write_outputs(feature_content: str, assumptions: list[dict], source: str, output_dir: Path) -> dict[str, Path]` function that: creates `{output_dir}/{feature_name}/`, writes `{name}.feature`, serialises assumptions to `{name}_assumptions.yaml` via `yaml.dump()`, writes `{name}_summary.md` as formatted markdown string
  - [ ] `seed_to_graphiti(feature_id: str, feature_content: str, assumptions: list[dict], output_paths: dict) -> None` function that: seeds feature spec overview to `feature_specs` group, seeds individual scenarios as distinct episodes (not the whole file as one blob), seeds assumptions to `domain_knowledge` group; logs warning and continues if Graphiti unavailable (non-blocking)
  - [ ] `FeatureSpecCommand` class with `execute(input_text: str, options: dict) -> FeatureSpecResult` method orchestrating the above
  - [ ] `FeatureSpecResult` dataclass with fields: `feature_file: Path`, `assumptions_file: Path`, `summary_file: Path`, `scaffolding_files: dict[str, Path]`, `scenarios_count: int`, `assumptions_count: int`, `stack: str`
  - [ ] File input handling: reads `.md`, `.txt` files; concatenates multiple `--from` inputs
  - [ ] Tests pass: `pytest tests/test_feature_spec_command.py -v`
  - [ ] Lint passes: `ruff check guardkit/commands/feature_spec.py`
- **Implementation notes:** Stack detection is ~10 lines of `if (root / 'pyproject.toml').exists()` checks in priority order — do not over-engineer. File I/O uses `pathlib.Path` throughout. `yaml.dump()` for assumptions (pyyaml already in `pyproject.toml`). The `seed_to_graphiti()` call goes at the end of Phase 6 (after files written and human has reviewed assumptions) — this is the right moment because assumptions have been resolved. Seeding individual scenarios as distinct episodes (not the whole `.feature` file as one blob) is critical: Coach can then query "what scenarios cover file upload validation?" and get specific, targeted results rather than a full file blob. Seeding assumptions to `domain_knowledge` prevents future features from silently re-making the same assumptions. The `scan_codebase()` function should detect existing `.feature` files left by the now-deprecated `/generate-bdd` command and surface them so the AI can avoid generating contradictory scenarios.
- **Player constraints:** Do not modify any existing command modules, formatter modules, or Graphiti integration code
- **Coach validation commands:**
  ```bash
  pytest tests/test_feature_spec_command.py -v
  ruff check guardkit/commands/feature_spec.py
  python -c "from guardkit.commands.feature_spec import FeatureSpecCommand, FeatureSpecResult, detect_stack, scan_codebase; print('Import OK')"
  ```

### Task 6: Integration Tests and Documentation

- **Task ID:** TASK-XXX
- **Complexity:** medium
- **Type:** integration
- **Domain tags:** `testing, integration, documentation, e2e, multi-language`
- **Files to create/modify:**
  - `tests/integration/test_feature_spec_e2e.py` (new)
  - `docs/commands/feature-spec.md` (new)
- **Files NOT to touch:** Any source files — this task only creates tests and docs
- **Dependencies:** Tasks 1-5 (tests the complete pipeline)
- **Inputs:** All modules from Tasks 1-5
- **Outputs:** End-to-end tests proving the pipeline works across stacks, and user-facing documentation
- **Relevant decisions:** D1, D3, D4, D5, D6, D9, D10
- **Acceptance criteria (machine-verifiable):**
  - [ ] File exists: `tests/integration/test_feature_spec_e2e.py`
  - [ ] E2E test: given a sample loose description, generate Gherkin → validate syntax → verify scaffolding is valid for detected stack → verify summary contains expected sections → verify assumptions manifest is valid YAML
  - [ ] E2E test: Python stack → generates pytest-bdd step definitions
  - [ ] E2E test: TypeScript stack → generates cucumber-js step definitions
  - [ ] E2E test: Generic/unknown stack → generates Gherkin only, no scaffolding
  - [ ] E2E test: `--auto` flag generates output without interactive prompts, with assumptions marked
  - [ ] E2E test: Gherkin scenarios use domain language, not implementation-specific terms
  - [ ] File exists: `docs/commands/feature-spec.md`
  - [ ] Documentation includes: purpose, the propose-review methodology, usage examples, flag descriptions, output format description, multi-stack support, assumptions manifest format, worked examples showing input → output
  - [ ] Tests pass: `pytest tests/integration/test_feature_spec_e2e.py -v`
- **Implementation notes:** Use temporary directories with minimal fake codebases for each stack (a Python project with `pyproject.toml`, a Node project with `package.json`, a Go project with `go.mod`) for E2E tests. Key scenario to test: Python project with both `pyproject.toml` and `package.json` at root (the current GuardKit structure before the figma-to-react/zeplin-to-maui cleanup) — must detect Python, not TypeScript. The documentation should explain the propose-review methodology clearly. Include a section on how assumptions flow into AutoBuild's structured uncertainty handling, and a migration note for users coming from `/generate-bdd`.
- **Player constraints:** Do not modify any source files. Read-only access to `guardkit/` for understanding patterns.
- **Coach validation commands:**
  ```bash
  pytest tests/integration/test_feature_spec_e2e.py -v
  python -c "
  import os
  size = os.path.getsize('docs/commands/feature-spec.md')
  assert size > 2000, f'Documentation too short ({size} bytes)'
  print(f'Docs OK: {size} bytes')
  "
  ```

## 8. Test Strategy

### Unit Tests

| Test File | Covers | Key Assertions |
|-----------|--------|---------------|
| `tests/test_feature_spec_command.py` | Stack detection, codebase scanning, file I/O, Graphiti seeding | `detect_stack()` returns Python for `pyproject.toml`; Python wins over TypeScript when both signals present; `write_outputs()` creates correct directory structure; `seed_to_graphiti()` is non-blocking if Graphiti unavailable; multiple `--from` inputs concatenated correctly |

> **v2 unit tests** (added when formatter modules are built): `tests/test_gherkin_formatter.py`, `tests/test_stack_detector.py`, `tests/test_scaffolding.py`, `tests/test_assumptions.py`, `tests/test_feature_summary.py` — designs preserved in `docs/research/feature-spec/FEATURE-SPEC-v2-formatter-modules.md`.

### Integration Tests

| Test File | Covers | Key Scenarios |
|-----------|--------|---------------|
| `tests/integration/test_feature_spec_e2e.py` | Full pipeline across stacks, priority-based detection | Python project (pyproject.toml only) → Python detected; Polyglot project (pyproject.toml + package.json) → Python wins; TypeScript project (package.json only) → TypeScript detected; No signals → Generic; output files created with correct names; valid YAML assumptions; Graphiti seeding does not raise on unavailable connection |

### Manual Verification

| Check | How to Verify |
|-------|--------------|
| Generated Gherkin is human-readable and uses domain language | Rich reviews output for 3 different feature descriptions |
| Propose-review cycle feels natural | Rich runs the full interactive cycle on a real feature |
| Assumptions manifest integrates with AutoBuild gating | Feed manifest into AutoBuild and verify gating behaviour |
| Summary is accepted by `/feature-plan` | Run `/feature-plan --from-spec` against generated summary |
| Multi-stack scaffolding compiles in target language | Manually verify generated TypeScript and Go snippets compile |
| `--auto` mode produces reasonable defaults | Run with `--auto` and review assumption quality |

## 9. Dependencies & Setup

### Python Dependencies

**No new dependencies.** `pyyaml>=6.0` is already present in `pyproject.toml`. All functionality uses standard library (`pathlib`, `re`, `datetime`) plus pyyaml.

### No New System Dependencies

- No BDD runner dependencies in GuardKit itself — those are in the TARGET project
- No database, no Docker, no external services required beyond the existing Graphiti/FalkorDB stack (and seeding is non-blocking if unavailable)
- All functionality is pure Python file I/O and string processing

### Development Dependencies (already present)

```
pytest>=7.0.0   # already in pyproject.toml
pyyaml>=6.0     # already in pyproject.toml
ruff            # already in pyproject.toml
```

## 10. File Tree (Target State — v1)

```
guardkit/                                    # Package root (no src/ prefix)
├── .claude/
│   └── commands/
│       ├── feature-plan.md              # Existing — unchanged
│       ├── feature-spec.md              # NEW — Task 4 (project-local for dogfooding)
│       └── ... (other existing commands)
├── installer/
│   └── core/
│       └── commands/
│           ├── feature-spec.md          # NEW — Task 4 (identical, for global install)
│           └── ... (other commands)
├── guardkit/                            # Python package
│   ├── commands/
│   │   ├── feature_spec.py              # NEW — Task 5 (orchestration + Graphiti seeding)
│   │   └── ... (existing commands)
│   └── ... (existing modules — unchanged)
├── tests/
│   ├── test_feature_spec_command.py     # NEW — Task 5 unit tests
│   └── integration/
│       ├── test_feature_spec_e2e.py     # NEW — Task 6
│       └── ... (existing integration tests)
├── docs/
│   ├── commands/
│   │   └── feature-spec.md              # NEW — Task 6 (user docs)
│   ├── adr/
│   │   ├── ADR-FS-001-gherkin-format.md            # NEW — seeded to Graphiti
│   │   ├── ADR-FS-002-stack-agnostic-scaffolding.md # NEW — seeded to Graphiti
│   │   └── ADR-FS-003-propose-review-methodology.md # NEW — seeded to Graphiti
│   └── research/
│       └── feature-spec/
│           ├── FEATURE-SPEC-feature-spec-command-v2.md  # This file
│           └── FEATURE-SPEC-v2-formatter-modules.md     # v2 planning
└── pyproject.toml                        # Unchanged — pyyaml already present

# v2 additions (when formatter modules are built — see FEATURE-SPEC-v2-formatter-modules.md):
# guardkit/formatters/__init__.py
# guardkit/formatters/gherkin.py
# guardkit/formatters/stack_detector.py
# guardkit/formatters/scaffolding.py
# guardkit/formatters/assumptions.py
# guardkit/formatters/feature_summary.py
# guardkit/formatters/templates/         (NOT guardkit/templates/bdd/ — avoid Jinja2 collision; flat Python modules, no bdd/ subdir)
```

## 11. Out of Scope

- **Running the generated tests** — that's the Coach's job during AutoBuild, not `/feature-spec`'s job
- **Full Gherkin parser library** — regex-based validation is sufficient for v1; v2 adds `GherkinFormatter` if Claude's generation quality proves unreliable
- **Integration with Linear/NATS** — this is a local Claude Code command, not a pipeline component
- **RequireKit integration** — RequireKit is deprecated for Rich's workflow; this command supersedes it
- **Automatic codebase modification** — `/feature-spec` generates specification files only; implementation is AutoBuild's job via `/feature-plan` → `/feature-build`
- **Voice input handling** — if James voice-dictates, the text output is pasted into `/feature-spec`; no special voice handling needed
- **Full scaffolding generation (v1)** — scaffolding generation is deferred to v2; v1 produces Gherkin + assumptions + summary, the slash command instructs the Player to write step definitions
- **AutoBuild Mandatory Assumptions Document integration** — the manifest format is defined here, but wiring it into AutoBuild's gating pipeline is a separate feature (builds on `structured-uncertainty-handling.md`)
- **Deprecating figma-to-react and zeplin-to-maui TypeScript test harnesses** — tracked separately; once removed, root-level `tsconfig.json` and `vitest.config.ts` disappear and the stack detector becomes unambiguous for GuardKit

## 12. Open Questions (Resolved)

| Question | Resolution |
|----------|-----------|
| Should `/feature-spec` use extended thinking (Opus) or standard (Sonnet)? | Sonnet is sufficient. Gherkin generation is methodical, not creative. The quality comes from the prompt methodology and codebase context, not raw reasoning depth. Save Opus for novel architecture problems. |
| Should the command attempt to deduplicate steps across features? | No — each feature file should be self-contained. Shared steps can be refactored later. Premature deduplication creates coupling. |
| How should the command handle features that span multiple services? | Generate one `.feature` file per service boundary. The command should ask during the proposal: "This seems to touch both the API and the worker — should I generate separate feature files?" |
| What if the codebase uses a stack not yet supported? | Generate Gherkin only (no scaffolding). Log a message suggesting `--stack` if the user knows their stack. The Gherkin is the universal artefact. |
| Should assumptions be tracked beyond Gherkin comments? | Yes — the `_assumptions.yaml` manifest lists all assumptions with confidence levels and gating implications. This feeds into AutoBuild's structured uncertainty handling pipeline. |
| How does this connect to the Structured Uncertainty Handling architecture? | `/feature-spec` is Layer 1 (upstream defence). It reduces ambiguity surface. Remaining gaps hit AutoBuild's Mandatory Assumptions Document (Layer 2), Coach detection (Layer 3), and Graphiti coverage gating (Layer 4). See Section 4. |
| Should Gherkin use implementation-specific terms like HTTP status codes? | No. Gherkin should use domain language ("upload should succeed", "error should indicate file is too large"). Implementation details go in step definitions. This keeps Gherkin stack-agnostic and behaviour-focused. |
| What prevents the propose-review cycle from becoming another interrogation? | Two things: (1) AI presents everything at once, grouped — human reviews batches, not individual items; (2) the interaction model is accept/reject/modify, not author-from-scratch. Fastest path: accept all, modify a few. |

---

## 13. Graphiti ADR Seeding

### ADR Files to Create

**`docs/adr/ADR-FS-001-gherkin-specification-format.md`:**
```markdown
# ADR-FS-001: Gherkin as Specification Format for AutoBuild

**Status:** Accepted  
**Date:** 2026-02-21  
**Context:** AutoBuild's Player-Coach loop needs unambiguous, machine-verifiable acceptance criteria. Prose specifications are subjective. The format must be technology-stack agnostic since GuardKit targets multiple languages.  
**Decision:** Use Gherkin (Given/When/Then) as the primary specification format. Scenarios use domain language, not implementation language.  
**Rationale:** Gherkin is language-neutral with runners for every major stack. It collapses spec, tests, and acceptance criteria into one artefact. Scenarios are independently executable. The Coach validates by running the appropriate BDD runner for the detected stack.  
**Alternatives Rejected:** EARS notation (no tooling), OpenAPI (APIs only), prose acceptance criteria (ambiguous, not executable).  
**Consequences:** All features specified via `/feature-spec` produce `.feature` files. Gherkin scenarios describe WHAT, not HOW. Step definitions provide the stack-specific implementation bridge.
```

**`docs/adr/ADR-FS-002-stack-agnostic-scaffolding.md`:**
```markdown
# ADR-FS-002: Stack-Agnostic Scaffolding with Pluggable Language Support

**Status:** Accepted  
**Date:** 2026-02-21  
**Context:** GuardKit targets projects in multiple languages. Generated test scaffolding must adapt to the target project's stack.  
**Decision:** Auto-detect technology stack from codebase signals (package.json, go.mod, pyproject.toml, etc.), generate stack-appropriate BDD step definitions. The Gherkin .feature file is universal; scaffolding is a convenience layer.  
**Rationale:** Gherkin itself is language-neutral. The step definitions that bind Gherkin to executable code are necessarily language-specific. By detecting the stack and using templates, we generate useful scaffolding without coupling the core specification format to any particular language.  
**Alternatives Rejected:** Python-only (excludes non-Python projects), no scaffolding (Player writes all boilerplate).  
**Consequences:** Adding support for a new language requires only a new template Python module in `guardkit/formatters/templates/` (e.g. `typescript.py`, `go.py`). Stack detection heuristics live in `StackDetector` and are extensible. Templates are NOT placed in `guardkit/templates/bdd/` (that directory holds Jinja2 `.j2` system templates and must not be mixed with BDD code templates).
```

**`docs/adr/ADR-FS-003-propose-review-methodology.md`:**
```markdown
# ADR-FS-003: Propose-Review Specification Methodology

**Status:** Accepted  
**Date:** 2026-02-21  
**Context:** RequireKit's elicitation-based approach failed because it required the product owner to author answers from scratch under interrogation. A different interaction model is needed.  
**Decision:** Use a Propose-Review methodology based on Specification by Example. The AI generates concrete behavioural examples (Gherkin scenarios), the human curates them (accept/reject/modify). AI does the creative work; human does quality control.  
**Rationale:** Curation is lower-friction than authoring. Product owners naturally think in terms of "yes that's right" or "no it should be like this" rather than generating requirements from scratch. The AI's edge case generation (boundary, negative, illustrative examples) adds scenarios the human wouldn't have considered.  
**Alternatives Rejected:** Question-based elicitation (RequireKit's failed approach), no interaction (risks wrong behaviour), structured questionnaire (same problem as elicitation).  
**Consequences:** The /feature-spec command follows a 6-phase cycle: Context → Propose → Curate → Expand → Resolve → Output. Assumptions are explicitly tracked with confidence levels feeding into AutoBuild's structured uncertainty gating.
```

### Seeding Commands

```bash
guardkit graphiti add-context docs/adr/ADR-FS-001-gherkin-specification-format.md
guardkit graphiti add-context docs/adr/ADR-FS-002-stack-agnostic-scaffolding.md
guardkit graphiti add-context docs/adr/ADR-FS-003-propose-review-methodology.md
guardkit graphiti add-context docs/features/FEATURE-SPEC-feature-spec-command.md
guardkit graphiti verify --verbose
```

### Quality Gate Configuration

```yaml
# .guardkit/quality-gates/FEAT-XXX.yaml
feature_id: FEAT-XXX
quality_gates:
  lint:
    command: "ruff check guardkit/commands/feature_spec.py"
    required: true
  unit_tests:
    command: "pytest tests/test_feature_spec_command.py -v --tb=short"
    required: true
  integration_tests:
    command: "pytest tests/integration/test_feature_spec_e2e.py -v"
    required: true
  import_check:
    command: "python -c \"from guardkit.commands.feature_spec import FeatureSpecCommand, FeatureSpecResult, detect_stack, scan_codebase; print('All imports OK')\""
    required: true
  # v2 quality gates (add when formatter modules are built):
  # lint_v2:        ruff check guardkit/formatters/
  # unit_tests_v2:  pytest tests/test_gherkin_formatter.py tests/test_stack_detector.py tests/test_scaffolding.py tests/test_assumptions.py tests/test_feature_summary.py -v
  # import_check_v2: python -c "from guardkit.formatters.gherkin import GherkinFormatter; from guardkit.formatters.stack_detector import StackDetector; ..."
```

---

## Phase 2 Execution Workflow

```bash
# On Dell ProMax — vLLM serving local model

guardkit feature-build FEAT-XXX
# → Player receives Graphiti context INCLUDING assumptions manifest
# → Player produces Mandatory Assumptions Document (Layer 2)
#    referencing /feature-spec assumptions where relevant
# → Coach validates against Gherkin scenarios + assumptions
# → Up to 5 turns per task before escalation

cd .guardkit/worktrees/FEAT-XXX && git diff main
guardkit feature-complete FEAT-XXX
```

---

## Pipeline Integration: The Complete Defence-in-Depth Flow

```
BEFORE (current):
  Loose idea → Rich manually writes spec → /feature-plan → AutoBuild
  (bottleneck: Rich writes spec by hand, silent assumptions everywhere)

AFTER (with /feature-spec + structured uncertainty):
  Loose idea
       ↓
  /feature-spec (Layer 1 — upstream)
       ↓  AI proposes Gherkin scenarios (Spec by Example categories)
       ↓  Rich reviews: accept / reject / modify / add / defer
       ↓  AI expands with edge cases Rich didn't consider
       ↓  Assumptions captured with confidence levels
       ↓
  Output: .feature + _assumptions.yaml + _summary.md + scaffolding/
       ↓  (Rich reviews ~5-10 mins — curating, not authoring)
       ↓
  /feature-plan --from-spec
       ↓  Decomposes into AutoBuild tasks
       ↓  Low-confidence assumptions flagged in task metadata
       ↓
  AutoBuild on Dell ProMax (Layers 2-4 — downstream)
       ↓  Layer 2: Player produces Mandatory Assumptions Document
       ↓  Layer 3: Coach detects divergence from Gherkin + assumptions
       ↓  Layer 4: Graphiti coverage gates task execution
       ↓
  Rich reviews PR, merges
```
