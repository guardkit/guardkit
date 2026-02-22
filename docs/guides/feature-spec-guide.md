# Feature Spec: BDD Specifications via Propose-Review

## Why Feature Spec Exists

### The Problem

Before `/feature-spec`, GuardKit offered `/generate-bdd` for creating Gherkin specifications. That command had three significant limitations:

1. **Single-pass generation** — the AI generated scenarios and the user received them as-is. There was no structured review cycle, so specifications often contained assumptions the user hadn't agreed to, missed important edge cases, or included implementation-level language instead of domain language.

2. **No assumption tracking** — inferred values (file size limits, retry counts, timeout durations) were silently baked into scenarios without any record of what was assumed versus what was stated. When these assumptions turned out to be wrong, there was no way to trace them back to their source.

3. **Flat, uncurated output** — scenarios were generated as a flat list without grouping by concern. Reviewing 20+ scenarios in a single pass made it difficult to accept the happy path while deferring edge cases for later.

### The Solution

`/feature-spec` replaces `/generate-bdd` with a **Propose-Review methodology** based on Gojko Adzic's *Specification by Example*. The core idea is that specifications are a **collaboration product** between AI and human, not an AI artefact. The command encodes a 6-phase cycle where:

- The AI proposes grouped scenarios (proposal-first, not question-first)
- The human curates each group independently (accept, reject, modify, add, or defer)
- Inferred values are surfaced explicitly with confidence levels
- All decisions are recorded in structured output files

### Benefits

| Before (`/generate-bdd`) | After (`/feature-spec`) |
|---------------------------|------------------------|
| AI generates, user receives | AI proposes, user curates |
| Flat list of scenarios | Grouped by Specification by Example category |
| No assumption tracking | Full YAML manifest with confidence and basis |
| `.feature` file only | `.feature` + `_assumptions.yaml` + `_summary.md` |
| No Graphiti seeding | Individual scenarios and assumptions seeded |
| No `--auto` mode | CI-friendly `--auto` for batch generation |

---

## Architecture

### How Feature Spec Fits into the GuardKit Pipeline

```
                    ┌──────────────────────┐
                    │   Feature Description │
                    │   (text, .md, .txt)   │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │    /feature-spec      │
                    │  (Propose-Review)     │
                    │                       │
                    │  Phase 1: Context     │
                    │  Phase 2: Proposal    │
                    │  Phase 3: Curation    │
                    │  Phase 4: Edge Cases  │
                    │  Phase 5: Assumptions │
                    │  Phase 6: Output      │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
   ┌──────────▼──────┐ ┌──────▼───────┐ ┌──────▼───────┐
   │  .feature file  │ │ _assumptions │ │  _summary.md │
   │  (Gherkin BDD)  │ │   .yaml      │ │              │
   └──────────┬──────┘ └──────┬───────┘ └──────┬───────┘
              │               │                │
              │               │     ┌──────────▼───────────┐
              │               │     │    /feature-plan      │
              │               │     │  (Task Decomposition) │
              │               │     └──────────┬───────────┘
              │               │                │
              │               │     ┌──────────▼───────────┐
              │               │     │    /feature-build     │
              │               │     │  (AutoBuild Player-   │
              │               │     │   Coach Workflow)     │
              │               │     └──────────────────────┘
              │               │
   ┌──────────▼───────────────▼──────────┐
   │           Graphiti Knowledge Graph   │
   │  (scenarios → feature_specs group)   │
   │  (assumptions → domain_knowledge)    │
   └─────────────────────────────────────┘
```

### Component Breakdown

| Component | Location | Purpose |
|-----------|----------|---------|
| Slash command definition | `.claude/commands/feature-spec.md` | Prompt methodology — the 6-phase Propose-Review cycle that Claude Code executes |
| Python orchestration module | `guardkit/commands/feature_spec.py` | Stack detection, codebase scanning, file I/O, Graphiti seeding |
| Unit tests | `tests/unit/commands/test_feature_spec.py` | 72 tests covering all public functions |
| Integration tests | `tests/integration/test_feature_spec_e2e.py` | 47 E2E tests across multiple stack types |
| User documentation | `docs/commands/feature-spec.md` | Reference documentation for users |

### Data Flow

1. **Input**: User provides a feature description (inline text, `--from` file, or both) plus optional `--context` files and `--stack` override.

2. **Phase 1 (Context Gathering)**: The Python module detects the technology stack via priority-ordered file checks (`pyproject.toml` > `requirements.txt` > `go.mod` > `Cargo.toml` > `package.json` > generic). It scans for existing `.feature` files, module structure, and architectural patterns. If Graphiti is available, it queries for relevant ADRs and domain warnings.

3. **Phases 2-5 (Interactive)**: These phases are executed by Claude Code interpreting the slash command definition. The AI generates grouped scenarios, the human curates them, edge cases are optionally expanded, and assumptions are resolved.

4. **Phase 6 (Output)**: The Python module writes three files to `{output_dir}/{feature-name}/`:
   - `{name}.feature` — curated Gherkin scenarios in domain language
   - `{name}_assumptions.yaml` — structured manifest of all inferred values
   - `{name}_summary.md` — human-readable summary for `/feature-plan` consumption

5. **Graphiti Seeding**: Each scenario is seeded as a separate episode to the `feature_specs` group. Each assumption is seeded to the `domain_knowledge` group. Seeding is non-blocking — failures are logged but never crash the pipeline.

### Relationship to AutoBuild

`/feature-spec` does **not** directly invoke the AutoBuild Player-Coach workflow. Instead, its outputs feed into the existing pipeline:

```
/feature-spec → .feature + _summary.md → /feature-plan → task files → /feature-build → Player ↔ Coach
```

The autobuild coach was not modified for this feature because the coach validates task-work quality gates, not specification quality. The coach interacts with feature-spec output indirectly when `/feature-build` creates tasks from the planned features.

---

## Usage Guide

### Prerequisites

- GuardKit installed (`pip install guardkit-py`)
- Claude Code CLI configured
- (Optional) Graphiti server running for knowledge seeding

### Basic Usage

Generate a feature spec from a description:

```bash
/feature-spec "users can upload documents to their profile"
```

This will:
1. Detect your project stack (Python, TypeScript, Go, Rust, or Generic)
2. Scan for existing `.feature` files and codebase patterns
3. Present grouped Gherkin scenarios for your review
4. Walk you through assumption resolution
5. Write output files to `features/{feature-name}/`

### Using Input Files

Read the feature description from a Markdown file:

```bash
/feature-spec --from docs/features/upload-requirements.md
```

Combine multiple input sources:

```bash
/feature-spec --from spec.md --from constraints.md --context docs/domain-glossary.md
```

The `--from` flag provides the feature description. The `--context` flag provides additional domain context without merging it into the feature text.

### Specifying Output Location

```bash
/feature-spec "payment processing" --output features/payments/
```

### Overriding Stack Detection

```bash
/feature-spec "file uploads" --stack python
```

Supported stacks: `python`, `typescript`, `go`, `rust`, `csharp`, `generic`.

### Automated Mode (CI/Batch)

Skip the interactive review phases:

```bash
/feature-spec --from spec.md --auto
```

In `--auto` mode:
- All proposed scenarios are accepted without review
- Edge case expansion is skipped
- All assumptions use proposed defaults with `confidence=low`
- Output includes `REVIEW REQUIRED: all assumptions unconfirmed`

This is useful for CI pipelines or rapid first drafts where human review happens separately.

### Step-by-Step Workflow Example

1. **Run the command**:
   ```bash
   /feature-spec "users can upload documents"
   ```

2. **Review the context summary** (Phase 1):
   ```
   Context loaded: stack=python, 3 models found, 0 existing .feature files, 1 ADR
   ```

3. **Review grouped scenarios** (Phase 2): The AI presents scenarios in four groups:
   - **Group A**: Key Examples (happy path)
   - **Group B**: Boundary Conditions (size limits, type limits)
   - **Group C**: Negative Cases (invalid input, unauthorised)
   - **Group D**: Edge Cases (concurrency, failure recovery)

4. **Curate each group** (Phase 3):
   ```
   GROUP A — Key Examples (3 scenarios): A       (accept all)
   GROUP B — Boundary Conditions (4 scenarios): M  (modify: change max size to 100MB)
   GROUP C — Negative Cases (2 scenarios): A       (accept all)
   GROUP D — Edge Cases (3 scenarios): ?           (defer for later)
   ```

5. **Optional edge case expansion** (Phase 4):
   ```
   Include additional security/concurrency scenarios? [Y/S/N]: S
   (review 2 samples, then decide)
   ```

6. **Resolve assumptions** (Phase 5):
   ```
   [1] Maximum file size: 50MB (medium confidence) → Enter "100MB"
   [2] Allowed file types: PDF, DOCX (low confidence) → Press Enter to accept
   ```

7. **Output written** (Phase 6):
   ```
   features/document-upload/document-upload.feature          (9 scenarios)
   features/document-upload/document-upload_assumptions.yaml  (2 assumptions)
   features/document-upload/document-upload_summary.md
   ```

### Feeding into Feature Plan

The summary file is designed as direct input to `/feature-plan`:

```bash
/feature-plan "Document Upload" --context features/document-upload/document-upload_summary.md
```

This ensures your implementation plan is grounded in confirmed BDD scenarios rather than raw prose.

### Troubleshooting

| Issue | Cause | Solution |
|-------|-------|---------|
| No stack detected | Project has no recognisable indicator files | Use `--stack` to specify manually |
| Graphiti seeding warnings | Graphiti server not running or not configured | Warnings are non-blocking; seeding is skipped gracefully |
| Empty output | No `Feature:` line in input | Ensure input contains valid Gherkin or a clear feature description |
| `_summary.md` shows generic stack | Known v1 limitation (Finding 2 in review) | Stack is correct in `FeatureSpecResult`; summary will be fixed in v2 |

---

## Migration from /generate-bdd

If you previously used `/generate-bdd`, the migration is straightforward:

1. Replace `/generate-bdd TASK-XXX` with `/feature-spec "description"`
2. Use `--auto` to replicate the non-interactive behaviour if needed
3. Existing `.feature` files are not modified — Phase 1 reads them as context to avoid duplication
4. The new `_assumptions.yaml` captures inferred values that were previously invisible

---

## Design Decisions

### ADR-FS-001: Gherkin Specification Format

Gherkin was chosen over prose requirements or EARS notation because it is:
- Directly executable by BDD test runners (pytest-bdd, cucumber-js, godog, cucumber-rs)
- Stack-agnostic at the specification level
- Well-understood by both technical and non-technical stakeholders

### ADR-FS-002: Stack-Agnostic Scaffolding

The command detects the project stack but generates stack-agnostic Gherkin. Step definitions and test scaffolding are deferred to v2 to keep v1 focused on specification quality.

### ADR-FS-003: Propose-Review Methodology

The Propose-Review cycle (based on Specification by Example) was chosen over:
- **Question-first**: Too many upfront questions frustrate users
- **Single-pass generation**: No human oversight of AI assumptions
- **Template-based**: Too rigid for diverse feature descriptions

The proposal-first approach lets humans review concrete scenarios rather than answering abstract questions.
