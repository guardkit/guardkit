# Archived Tasks

This directory contains tasks that have been archived for reference.

## Directory Structure

### superseded/
Tasks that have been replaced by newer approaches or completed through different means.

#### agent-discovery-old-approach/ (7 tasks)
**Archived**: 2025-11-21
**Reason**: Exploratory work on agent discovery using structured templates. Superseded by simpler Phase 8 incremental approach.

**Tasks**:
- TASK-AGENT-BOUND-20251121-151631.md
- TASK-AGENT-EXAMPLES-20251121-151804.md
- TASK-AGENT-GIT-20251121-152113.md
- TASK-AGENT-STRUCT-20251121-151631.md
- TASK-AGENT-STYLE-20251121-152113.md
- TASK-AGENT-VALIDATE-20251121-160001.md
- TASK-AGENT-ENHANCER-20251121-160000.md

**Replacement**: Phase 8 INCREMENTAL specification (TASK-PHASE-8-INCREMENTAL, completed Nov 21)

**Context**: These tasks represented a detailed, template-based approach to agent enhancement with explicit guidelines for structure, boundaries, examples, Git workflow, and code style. While well-designed, this approach was determined to be over-engineered for current needs. The simpler Phase 8 incremental approach achieves the same goals with less complexity.

#### phase-7-5-approach/ (2 tasks)
**Archived**: 2025-11-21
**Reason**: Phase 7.5 batch processing approach was implemented, tested, and then removed in favor of Phase 8 incremental approach.

**Tasks**:
- TASK-PHASE-7-5-SIMPLE-specification.md
- TASK-FIX-AGENT-ENHANCEMENT-PROMPT-QUALITY.md

**Replacement**: Phase 8 INCREMENTAL specification

**Git History**:
- Commit: "feat: Implement TASK-PHASE-8-INCREMENTAL" (Nov 21)
- Commit: "feat: Complete TASK-SIMP-9ABE - Remove Phase 7.5 agent enhancement" (Nov 21)

**Context**: Phase 7.5 attempted batch processing of multiple agents simultaneously. While functional, it proved less flexible and harder to debug than the incremental approach. Phase 8 processes agents one at a time with better error handling and progress tracking. The prompt quality task was designed to improve Phase 7.5's agent_enhancer.py, which no longer exists after the removal of Phase 7.5.

#### legacy-build-rename/ (1 task)
**Archived**: 2025-11-21
**Reason**: Task no longer needed as legacy build system has been replaced.

**Tasks**:
- TASK-RENAME-LEGACY-BUILD-NEW.md

**Context**: This task was created to rename legacy build components. The work has been completed or superseded by new build infrastructure.

#### Manual Agent Population (1 task)
**Archived**: 2025-11-21
**Reason**: Manual agent enhancement superseded by `/agent-enhance` command.

**Tasks**:
- TASK-ENH-7A2D-populate-agent-files-with-examples.md

**Replacement**: `/agent-enhance` command (Phase 8 INCREMENTAL)

**Context**: This task described manually populating agent files with code examples, best practices, and anti-patterns for the net9-maui-mydrive template. This manual work (estimated 6-9 hours) is now fully automated by the `/agent-enhance` command, which uses AI to extract examples from template code and generate comprehensive agent documentation. The command is invoked automatically during template creation (via `--create-agent-tasks`) or can be run manually for incremental enhancement.

#### Agent Bridge End-to-End Testing (1 task)
**Archived**: 2025-11-21
**Reason**: Testing superseded by production validation. Bridge works, agents generated.

**Tasks**:
- TASK-BRIDGE-004-end-to-end-testing.md

**Status**: Testing would be retrospective

**Context**: This task proposed formal end-to-end testing of the Python↔Claude agent bridge (checkpoint-resume pattern with exit code 42). However, the bridge is demonstrably working: (1) Prerequisites TASK-BRIDGE-001/002/003 completed, (2) Bug fixes TASK-BRIDGE-005/006 completed, (3) AgentBridgeInvoker integrated and functioning (agent_invoker.py lines 119-126), (4) Agents actively being generated (net9-maui-mydrive has 8+ agents created Nov 21), (5) System in production use with template creation succeeding. The formal test scenarios (dotnet-maui, React TypeScript, FastAPI, error handling, performance) would be retrospective validation of a working system. Production use has validated the bridge's reliability more effectively than isolated test scenarios. Only reconsider if: (1) bridge reliability issues emerge, (2) formal test coverage required for compliance, or (3) major refactoring planned requiring baseline metrics.

#### Build Artifact Filtering (1 task)
**Archived**: 2025-11-21
**Reason**: Functionality already implemented in exclusions.py module.

**Tasks**:
- TASK-ARTIFACT-FILTER.md

**Status**: Completed (implemented Nov 12, 2025)

**Context**: This task proposed creating an `exclusion_patterns.py` module to filter build artifacts (obj/, bin/, node_modules/, etc.) from codebase analysis. However, this functionality ALREADY EXISTS in `installer/core/lib/codebase_analyzer/exclusions.py` (created Nov 12): (1) DEFAULT_EXCLUSIONS list contains all proposed patterns (.NET: obj/bin/packages, Node: node_modules, Python: __pycache__/venv, Java: target, Generic: build/dist/.git), (2) should_exclude_path() function implements pattern matching, (3) get_source_files() function integrates filtering, (4) stratified_sampler.py uses get_source_files() at line 571, (5) System actively filtering artifacts during template creation. The module was implemented as part of TASK-002 (AI-Powered Codebase Analysis) which replaced algorithmic approaches. The task description exactly matches what's already in production.

#### Smart Defaults Detector (2 tasks)
**Archived**: 2025-11-21
**Reason**: Entire approach superseded by AI-native workflow in TASK-51B2.

**Tasks**:
- TASK-9039-remove-qa-from-template-create-use-smart-defaults.md
- TASK-9039B-integrate-smart-defaults-detector-into-template-create.md

**Status**: Implementation deleted (Jan 12, 2025)

**Context**: TASK-9039 created a smart defaults detector module (1,045 LOC: 531 detector + 514 tests) to remove Q&A from template creation. The detector used pattern matching to identify languages (9 supported), frameworks (12+ supported), and configuration. However, this was over-engineering: AI can ALREADY analyze codebases directly without helper code. TASK-51B2 (completed Jan 12, 2025) reverted to AI-native template creation by DELETING all 1,045 LOC of detector code and replacing it with direct AI analysis. The current Phase 1 (`_phase1_ai_analysis`) lets AI infer language from file extensions, framework from dependencies, architecture from folder structure - no pattern matching needed. TASK-9039B proposed integrating the detector into the orchestrator, but both the detector code and the integration work were superseded by the simpler AI-native approach. Template creation now works non-interactively without any detector infrastructure.

#### Template Validate Advanced Features (1 task)
**Archived**: 2025-11-21
**Reason**: Features already implemented in TASK-044 MVP.

**Tasks**:
- TASK-064-template-validate-advanced-features.md

**Status**: Completed (implemented Nov 8, 2025)

**Context**: TASK-064 proposed adding "advanced features" to `/template-validate` after the MVP (TASK-044): session persistence (--resume), inline fix automation (--auto-fix), non-interactive batch mode (--non-interactive), and metrics tracking. However, TASK-044's MVP implementation (completed Nov 8) ALREADY included 3 of these 4 features: (1) Session persistence: AuditSession.save()/load() with --resume flag works, (2) Inline fixes: _apply_fix() method with --auto-fix flag and issue.auto_fix callable, (3) Non-interactive mode: --non-interactive flag with batch execution. Only metrics tracking (Feature 4: MetricsTracker, ValidationMetrics, session history) is not implemented. The "MVP" was more feature-complete than expected. The task estimated 2-3 days (16-24 hours) but 75% of work was already done. If metrics tracking is needed later, create a focused task for just that feature.

### future-enhancements/
Tasks for future phases or optional features not currently prioritized.

#### External Agent Discovery (2 tasks)
**Archived**: 2025-11-21
**Reason**: Phase 2 optional feature. Current focus is Phase 1 (core template creation).

**Tasks**:
- TASK-004-REDESIGN-ai-agent-discovery.md (External discovery)
- TASK-004A-ai-agent-generator.md (Agent generation)

**Status**: Deferred to Phase 2

**Context**: These tasks explore external agent discovery mechanisms (discovering agents from other projects, repositories, or sources). While potentially valuable for advanced use cases, they are not required for core template creation functionality. May be revisited in Phase 2 if there's demand for cross-project agent sharing.

#### Batch Agent Enhancement (1 task)
**Archived**: 2025-11-21
**Reason**: Low priority optimization. Current incremental approach works well despite requiring multiple command invocations.

**Tasks**:
- TASK-ENH-9F2A-batch-enhancement-capability.md

**Status**: Future enhancement (LOW priority)

**Context**: This task proposes parallel batch processing of multiple agents in one command. While technically feasible (4 hours estimated), it's high-risk given the Phase 7.5 batch processing issues encountered earlier. The current incremental approach (`/agent-enhance` once per agent) works reliably and is only needed once per project. The added complexity of batch processing isn't justified by the minor convenience gain. May be reconsidered if user demand increases significantly.

#### Template Externalization (1 task)
**Archived**: 2025-11-21
**Reason**: YAGNI (You Aren't Gonna Need It). Current f-string approach is simple and sufficient.

**Tasks**:
- TASK-ENH-8B4C-externalize-task-template.md

**Status**: Future enhancement (LOW priority)

**Context**: This task proposes extracting the 44-line task template from an f-string to an external Jinja2 file. While technically cleaner, it adds complexity (dependency, file I/O, error handling) for minimal benefit. The f-string template is simple, readable, co-located with code, and rarely changes. Adding Jinja2 is premature optimization. Only reconsider if the template grows significantly (100+ lines) or needs multiple variations.

#### Serialize Value Refactoring (1 task)
**Archived**: 2025-11-21
**Reason**: Premature optimization. Current implementation is well-documented and functional.

**Tasks**:
- TASK-ENH-6D9B-refactor-serialize-value.md

**Status**: Future enhancement (LOW priority)

**Context**: This task proposes splitting the 114-line `_serialize_value` method into 8 smaller type-specific methods. While this would improve testability, the current implementation is already well-structured with comprehensive docstrings (30 lines), clear sequential logic, cycle detection, and error handling. The method was already refactored in Phase 7.5 (marked as "DRY improvement +6 SOLID points"). The proposed refactoring would add ~87 lines of code (8 methods with docstrings) for marginal testability improvement when integration tests already verify serialization works correctly. This is textbook premature optimization - breaking up a working method because it's "long" without a clear problem to solve. Only reconsider if: (1) serialization bugs become frequent, (2) adding new types becomes painful, or (3) test coverage gaps are identified.

#### State Format Versioning (1 task)
**Archived**: 2025-11-21
**Reason**: YAGNI. Version field exists, migration infrastructure not needed until format actually changes.

**Tasks**:
- TASK-ENH-3A7F-state-format-versioning.md

**Status**: Future enhancement (LOW priority)

**Context**: This task proposes building a complete version migration framework (compatibility checks, migration chain, version bumping logic) for the checkpoint/resume state system. However, the infrastructure is premature: (1) Version field ALREADY exists (state_manager.py line 108: `version="1.0"`), (2) State format has been stable with no breaking changes, (3) Checkpoint/resume works reliably, (4) The task proposes 80+ lines of migration code before any migrations are needed. This is YAGNI - building complex infrastructure before any actual need. The version field provides basic forward compatibility. Only implement migration logic when: (1) a breaking state format change is actually needed, (2) users encounter compatibility issues, or (3) state structure evolves beyond v1.0. At that point, implement the specific migration needed rather than a generic framework.

#### Dynamic Task Priority Logic (1 task)
**Archived**: 2025-11-21
**Reason**: Low-value optimization without clear user benefit. Manual priority adjustment works fine.

**Tasks**:
- TASK-ENH-2F9D-task-priority-logic.md

**Status**: Future enhancement (LOW priority)

**Context**: This task proposes reading agent priority from frontmatter and dynamically setting task priority during agent enhancement task creation. However, this is low-value: (1) Agent enhancements are batch work done once per template, (2) All agents equally important for template quality (no urgency differentiation), (3) Users can manually edit task priority if needed (simple workaround), (4) Agent priority metadata is inconsistent across agents (would need standardization first), (5) Single use case (only during `/template-create --create-agent-tasks`). While technically feasible (1 hour), the ROI is minimal. Current approach (all tasks MEDIUM priority) works fine. Only reconsider if: (1) users frequently request priority differentiation, (2) agent priority metadata becomes standardized, or (3) task management system adds priority-based workflows requiring accurate initial priorities.

#### CLAUDE.md Agent Section Enhancement (1 task)
**Archived**: 2025-11-21
**Reason**: Cosmetic polish task. Agent sections already populated, AI enhancement is nice-to-have.

**Tasks**:
- TASK-CLAUDE-MD-AGENTS.md

**Status**: Future enhancement (LOW priority)

**Context**: This task proposes using AI to enhance "When to Use" sections in generated CLAUDE.md files for better agent guidance. However, this is low-priority polish: (1) Agent sections ARE already populated with Purpose from agent descriptions, (2) The information exists in agent files (users can read them), (3) Current output is functional even if not perfectly polished, (4) 30 min-1 hour task that doesn't fix anything broken, (5) Template creation works fine without this enhancement. While the AI-first approach is well-designed (avoiding hard-coded mappings), it's optimizing something that already works. Only reconsider if: (1) users frequently complain about unclear agent guidance, (2) agent adoption is low due to poor documentation, or (3) as part of broader CLAUDE.md quality improvements.

#### Hash ID System Integration Testing (1 task)
**Archived**: 2025-11-21
**Reason**: Core system working reliably in production. Additional tests would be nice-to-have safety features.

**Tasks**:
- TASK-9A1A-integration-testing.md

**Status**: Future enhancement (LOW priority)

**Context**: This task proposes comprehensive integration tests and rollback scripts for the hash-based ID system. However, the system is ALREADY working reliably in production: (1) 234+ hash-based tasks created with zero collisions, (2) 154 existing tests (unit + integration) covering hash generation, PM tool mapping, persistence, (3) test_id_generator.py has 23 tests including 10,000 ID collision test, performance tests, uniqueness tests, (4) test_external_id_mapper.py tests JIRA/Azure DevOps/Linear/GitHub mapping, (5) Production validation proves system works. Missing pieces are edge-case safety features: (1) True parallel concurrent tests (current test is sequential but production has no collision issues), (2) Rollback script (system is stable, no rollbacks needed yet), (3) Cross-reference migration tests (migration not actively used), (4) Conductor.build worktree tests (theoretical concern, no issues in practice). This is 6/10 complexity for 1-2 days work on safety features for a system that's already proven reliable. Only reconsider if: (1) collision issues emerge in production, (2) planning major rollback, (3) implementing large-scale migration, or (4) Conductor.build integration becomes critical requirement.

#### Agent Enhancement Documentation & Testing (5 tasks)
**Archived**: 2025-11-21
**Reason**: Agent enhancement working in production. Command spec exists, system validated through actual usage.

**Tasks**:
- TASK-DOC-4F8A-agent-enhance-command-spec.md (superseded - spec EXISTS at installer/core/commands/agent-enhance.md, 10.6KB)
- TASK-DOC-F3A3-documentation-suite-agent-enhancement.md (superseded - meta task, sub-tasks handled individually)
- TASK-DOC-5B3E-phase-7-5-vs-8-comparison.md (future-enhancements - historical comparison, Phase 7.5 removed)
- TASK-E2E-97EB-end-to-end-validation-agent-enhancement.md (future-enhancements - system working in production)
- TASK-TEST-87F4-comprehensive-test-suite-agent-enhancement.md (future-enhancements - basic tests exist, agents being generated successfully)

**Status**: Core functionality complete and production-validated

**Context**: The `/agent-enhance` command is implemented and working. Evidence: (1) Command spec exists (installer/core/commands/agent-enhance.md, 10,641 bytes), (2) AI integration complete using anthropic_sdk.task() API (TASK-AI-2B37 completed), (3) Agents being generated in production (net9-maui-mydrive has 8+ agents), (4) Basic tests exist (test_ai_agent_generator.py, test_template_create_agent_documentation.py), (5) Enhancement strategies working (ai/static/hybrid). Archived tasks propose: (1) TASK-DOC-4F8A - command spec that ALREADY EXISTS, (2) TASK-DOC-F3A3 - meta wrapper task, (3) TASK-DOC-5B3E - Phase 7.5 comparison (7.5 removed, comparison is historical), (4) TASK-E2E-97EB - formal E2E validation (system validated through actual production use), (5) TASK-TEST-87F4 - comprehensive test suite (basic tests exist, 4-5 days effort for exhaustive coverage). The only KEPT task is TASK-DOC-1E7B (incremental enhancement workflow guide - legitimate documentation gap). System works reliably without comprehensive test suite. Only reconsider testing tasks if: (1) agent quality issues emerge, (2) enhancement failures occur, (3) compliance requires formal test coverage, or (4) planning major refactoring.

## When to Review Archived Tasks

- **Learning**: Understand evolution of approaches (why certain designs were rejected)
- **Historical context**: Reference for design decisions
- **Feature resurrection**: If requirements change, archived features might become relevant again
- **Avoiding repetition**: Don't recreate the same solutions that were previously explored

## Do NOT Use These Tasks

Tasks in this directory are archived for reference only. Do not implement them unless:
1. Requirements have changed significantly
2. New context makes the approach viable
3. You've discussed with the team and updated the task
4. You've created a new task in backlog/ referencing the archived work

For current work, see:
- **Active tasks**: `tasks/backlog/` (organized by initiative)
- **Completed tasks**: `tasks/completed/` (finished work)

## Archive Organization Principles

Tasks are archived (not deleted) because:
1. They contain valuable analysis and design work
2. They document "roads not taken" for future reference
3. They prevent repeating the same exploration
4. They provide context for current implementations

## Statistics

**Total archived**: 30 tasks
- Superseded approaches: 18 tasks
- Future enhancements: 12 tasks

**Archive date**: 2025-11-21
**Part of**: Backlog cleanup initiative
- Backlog: 80 → 31 files (61.25% reduction)
- Completed (moved): 2 files (TASK-CLEANUP-20251121, TASK-AI-2B37)
- In Review: 28 → 27 files
