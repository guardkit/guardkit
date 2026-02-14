# Failure Patterns & Lessons Learned

> 6 documented failure patterns from production AutoBuild runs

## FP-001: Death by a Thousand Bug Fixes

- **Pattern**: Incremental patching of AI-first designs degrades them into rigid, script-driven approaches
- **Prevention**: When quality degrades, stop patching. Revert to clean AI-first approach. Forensic analysis before fix.
- **Example**: template-create command's AI-driven analysis was incrementally replaced with hard-coded pattern matching through successive bug fixes

## FP-002: Player Self-Report Unreliability

- **Pattern**: Player agent claims task is complete but Coach finds gaps. In g3 ablation study, removing Coach made output non-functional despite Player claiming success.
- **Prevention**: Always use independent Coach validation. Never trust player self-report of success. Coach runs its own test execution.

## FP-003: Context Loss Across Sessions

- **Pattern**: Knowledge from one Claude Code session is unavailable in the next. Developer must re-explain context.
- **Prevention**: Graphiti job-specific retrieval (GR-006). Knowledge capture at task completion. System overview provides "North Star" context.

## FP-004: Rabbit Hole Divergence

- **Pattern**: Without structured checkpoints, conversations go down rabbit holes. Tasks aren't implemented completely.
- **Prevention**: Quality gates force structured progression. Plan audit at Phase 5.5 detects scope drift. /task-refine for mid-implementation course correction.

## FP-005: Scope Creep in Implementation

- **Pattern**: Player adds unrequested features, especially when encountering related code.
- **Prevention**: Plan audit detects variance >20%. Coach validates against requirements contract only. "NEVER implement features not explicitly specified" rule.

## FP-006: Zero-Test Anomaly

- **Pattern**: Task claims completion with no tests written. Especially common with DOCUMENTATION and SCAFFOLDING tasks where tests seem optional.
- **Prevention**: Zero-test anomaly detection in quality gates. Task type determines whether tests are required. DOCUMENTATION/SCAFFOLDING exempt; all others blocked.
