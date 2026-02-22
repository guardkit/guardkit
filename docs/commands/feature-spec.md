# /feature-spec Command Reference

## Purpose

The `/feature-spec` command generates BDD Gherkin specifications from natural language feature descriptions using the **Propose-Review methodology**. It bridges product intent and engineering specification by producing structured `.feature` files alongside assumptions manifests and summary documents.

The command handles the complete lifecycle: gathering context from the codebase, proposing grouped scenarios for human review, resolving inferred assumptions, and writing output artefacts ready for use with your project's BDD runner.

Key outputs:

- A Gherkin `.feature` file containing curated scenarios in domain language.
- A YAML assumptions manifest capturing inferred values that need confirmation.
- A Markdown summary suitable for feeding into `/feature-plan` or sharing with stakeholders.

---

## The Propose-Review Methodology

`/feature-spec` follows a six-phase cycle designed to keep humans in control of specification quality while offloading mechanical generation to AI.

### Phase 1: Context Gathering (AI)

The command detects the project technology stack (Python, TypeScript, Go, Rust, or Generic) by examining well-known indicator files. It then scans the codebase for existing `.feature` files, module structure, and architectural patterns (services, repositories, routes). This context is used to align generated scenarios with the project's existing vocabulary.

### Phase 2: Initial Proposal (AI Generates Grouped Scenarios)

Based on the feature description and codebase context, the AI generates an initial set of Gherkin scenarios. Scenarios are grouped by concern (happy path, error cases, edge cases, permissions) to make human review tractable.

### Phase 3: Human Curation (User Reviews Groups)

You review each group of scenarios and respond with one of five actions:

| Action | Key | Meaning |
|--------|-----|---------|
| Accept | `A` | Keep this group as-is |
| Reject | `R` | Remove this group entirely |
| Modify | `M` | Accept with inline edits |
| Add more | `+` | Generate additional scenarios for this group |
| Question | `?` | Ask a clarifying question before deciding |

### Phase 4: Edge Case Expansion (Optional)

After initial curation you can request additional edge-case scenarios. The AI uses the accepted scenarios as context to avoid duplication and to stay consistent with the chosen domain language.

### Phase 5: Assumption Resolution

During generation the AI infers values that are not explicit in the feature description (for example, maximum file sizes, retry limits, timeout values). In this phase you confirm, override, or defer each inferred assumption. Confirmed values are embedded in the scenarios; deferred assumptions are recorded in the YAML manifest for later resolution.

### Phase 6: Output Generation (Write Files)

All curated scenarios, confirmed assumptions, and the resolved feature name are written to disk in the output directory structure described in the Output Format section below.

---

## Usage Examples

Generate a feature spec from a short description:

```bash
/feature-spec "users can upload documents"
```

Specify a custom output directory:

```bash
/feature-spec "payment processing" --output features/payments/
```

Generate from an existing Markdown requirements document:

```bash
/feature-spec --from docs/features/upload.md
```

Generate from multiple input files in fully automated mode (skips curation prompts):

```bash
/feature-spec --from spec.md --from context.md --auto
```

Override stack detection and supply additional context:

```bash
/feature-spec "file uploads" --stack python --context docs/limits.md
```

---

## Flag Descriptions

| Flag | Description | Default |
|------|-------------|---------|
| `--from <file>` | Read feature description from a `.md` or `.txt` file. Can be repeated to concatenate multiple files. | None (uses inline description) |
| `--output <dir>` | Write output files to this base directory. A subdirectory named after the feature slug is created inside it. | `features/` in project root |
| `--auto` | Skip the interactive curation phases (Phases 3 and 4). Accepts all proposed scenarios and resolves assumptions to their inferred defaults. Useful for CI or first drafts. | Off (interactive) |
| `--stack <name>` | Override automatic stack detection. Accepted values: `python`, `typescript`, `go`, `rust`, `generic`. | Auto-detected |
| `--context <file>` | Provide an additional context document (domain glossary, constraints file, ADR) to guide scenario generation without merging it into the feature text. | None |

---

## Output Format

For a feature named "Document Upload" the command creates:

```
features/
  document-upload/
    document-upload.feature          # Gherkin scenarios (domain language)
    document-upload_assumptions.yaml # Inferred values and human responses
    document-upload_summary.md       # Human-readable summary for stakeholders
```

### `{feature-name}.feature`

Standard Gherkin file. Contains a `Feature:` header, narrative (`As a ... I want ... So that ...`), and curated `Scenario:` blocks. All scenarios use domain language - no implementation terms, SQL, HTTP status codes, or framework-specific vocabulary.

### `{feature-name}_assumptions.yaml`

Structured record of every assumption made during generation. Each entry captures enough context to turn an inferred value into a confirmed domain rule. See the Assumptions Manifest Format section below.

### `{feature-name}_summary.md`

Markdown document listing the detected stack, BDD runner, scenario count, assumption count, each scenario title, and all confirmed assumptions. Suitable for pull request descriptions or feeding into `/feature-plan`.

---

## Multi-Stack Support

The command auto-detects your project stack and includes the appropriate BDD runner in the summary. Detection uses a priority-ordered check of well-known indicator files.

| Stack | Indicator Files | BDD Runner |
|-------|----------------|------------|
| Python | `pyproject.toml`, `requirements.txt`, `setup.py` (highest priority) | pytest-bdd |
| Go | `go.mod` | godog |
| Rust | `Cargo.toml` | cucumber-rs |
| TypeScript | `package.json` (only when no Python indicators present) | cucumber-js |
| Generic | No signals detected | No scaffolding |

**Priority rule:** Python indicators always win over `package.json`. A polyglot project containing both `pyproject.toml` and `package.json` will be treated as a Python project.

The detected stack is recorded in `_summary.md` and `FeatureSpecResult.stack`. In a future release, the stack will also drive step-definition scaffolding (`.py`, `.go`, `.rs`, `.ts` step files).

---

## Assumptions Manifest Format

The `_assumptions.yaml` file follows this schema:

```yaml
source: feature-spec-command        # Who produced the manifest
assumptions:
  - id: ASSUM-001                   # Stable identifier for traceability
    scenario: "Upload a valid document"   # Scenario where assumption applies
    assumption: "Maximum file size is 50MB"  # The inferred value
    confidence: high                # AI confidence: high | medium | low
    basis: "Common web upload limit for free tiers"  # Reasoning
    human_response: confirmed       # confirmed | overridden | deferred | pending
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Stable identifier in `ASSUM-NNN` format, used for traceability in tasks and tests |
| `scenario` | string | Title of the scenario that depends on this assumption |
| `assumption` | string | The concrete inferred value or constraint |
| `confidence` | enum | AI's confidence in the inference: `high`, `medium`, or `low` |
| `basis` | string | Human-readable explanation of why this value was inferred |
| `human_response` | enum | Outcome of Phase 5 review: `confirmed`, `overridden`, `deferred`, or `pending` |

Assumptions with `human_response: deferred` or `pending` are outstanding action items. They should be resolved before the feature is implemented to avoid ambiguity in step definitions.

---

## Worked Example

**Input description:**

```
users can upload documents
```

**Phase 1 result (context gathered):**

- Stack detected: Python (pyproject.toml found)
- Existing features: none
- Patterns found: services, routes

**Phase 2 AI proposal (grouped):**

```
Group A - Happy Path (3 scenarios):
  - Upload a valid PDF
  - Upload a valid DOCX
  - View uploaded document in file list

Group B - Error Cases (2 scenarios):
  - Reject oversized file
  - Reject unsupported file type
```

**Phase 3 human curation:**

- Group A: `A` (accepted)
- Group B: `A` (accepted)

**Phase 5 assumption resolution:**

```
ASSUM-001: "Maximum file size is 50MB" — basis: industry default for free tiers
  Your response: confirmed
ASSUM-002: "Allowed types are PDF and DOCX" — basis: mentioned in description
  Your response: overridden → "PDF, DOCX, and ODT"
```

**Phase 6 outputs written:**

```
features/
  document-upload/
    document-upload.feature
    document-upload_assumptions.yaml
    document-upload_summary.md
```

The `.feature` file contains 5 scenarios in domain language, with "50MB" and "PDF, DOCX, and ODT" woven into the `Given`/`When`/`Then` steps. The assumptions YAML records both entries with their final `human_response` values.

---

## Migration from /generate-bdd

`/feature-spec` supersedes `/generate-bdd`. The differences are:

| Aspect | `/generate-bdd` | `/feature-spec` |
|--------|----------------|-----------------|
| Methodology | Single-pass generation | Propose-Review cycle |
| Human input | None | Interactive curation (Phases 3-5) |
| Scenario grouping | Flat list | Grouped by concern |
| Assumptions tracking | None | Full YAML manifest with confidence and basis |
| Output | `.feature` only | `.feature` + `_assumptions.yaml` + `_summary.md` |
| Graphiti seeding | None | Individual scenarios and assumptions seeded |

**Migrating existing workflows:**

1. Replace `/generate-bdd TASK-XXX` with `/feature-spec "description"`.
2. The `--auto` flag replicates the non-interactive behaviour of `/generate-bdd` if you need to batch-generate without curation prompts.
3. Existing `.feature` files are not modified; the scan in Phase 1 uses them as context to avoid duplication.

---

## Integration with /feature-plan

The `_summary.md` file is designed as direct input to `/feature-plan`. It contains the scenario list, assumption list, detected stack, and BDD runner in a format that the planning command can parse as structured context.

```bash
# Generate a feature spec first
/feature-spec "users can upload documents" --output features/document-upload/

# Use the summary to feed feature planning
/feature-plan "Document Upload" --context features/document-upload/document-upload_summary.md
```

This pipeline ensures that your implementation plan is grounded in confirmed BDD scenarios rather than a raw prose description. The assumptions recorded in Phase 5 surface as explicit constraints in the plan, reducing the risk of mismatched expectations between specification and implementation.

---

## See Also

- `installer/core/commands/feature-spec.md` — Slash-command definition installed into projects
- `guardkit/commands/feature_spec.py` — Python module implementing the pipeline
- `tests/unit/commands/test_feature_spec.py` — Unit test suite (85%+ coverage)
- `tests/integration/test_feature_spec_e2e.py` — End-to-end integration tests
- `docs/guides/bdd-workflow-for-agentic-systems.md` — BDD workflow guide for agentic systems
