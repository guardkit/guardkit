richardwoollcott@Richards-MBP scripts % ./install.sh

╔════════════════════════════════════════════════════════╗
║         GuardKit Installation System                 ║
║         Version: 2.0.0                  ║
╚════════════════════════════════════════════════════════╝

ℹ Installing GuardKit to /Users/richardwoollcott/.agentecflow

ℹ Checking prerequisites...
✓ Node.js found: v20.19.3
✓ Python found: Python 3.14 (>= 3.10 required)
✓ pip3 found - can install Python dependencies
ℹ Checking for Jinja2...
ℹ Jinja2 check completed (status: 0)
✓ Jinja2 already installed
ℹ Checking for python-frontmatter...
ℹ python-frontmatter check completed (status: 0)
✓ python-frontmatter already installed
ℹ Checking for pydantic...
ℹ pydantic check completed (status: 0)
✓ pydantic already installed
ℹ Checking for python-dotenv...
ℹ python-dotenv check completed (status: 0)
✓ python-dotenv already installed
ℹ Checking for graphiti-core...
ℹ Using Python: /usr/local/bin/python3 (Python 3.14.2)
✓ graphiti-core already installed and verified
✓ Python dependency checks complete
✓ All required prerequisites met
ℹ Installing guardkit Python package (with AutoBuild support)...
ℹ Installing from: /Users/richardwoollcott/Projects/appmilla_github/guardkit
Obtaining file:///Users/richardwoollcott/Projects/appmilla_github/guardkit
  Installing build dependencies ... done
  Checking if build backend supports build_editable ... done
  Getting requirements to build editable ... done
  Installing backend dependencies ... done
  Preparing editable metadata (pyproject.toml) ... done
Requirement already satisfied: click>=8.0.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from guardkit-py==0.1.0) (8.3.1)
Requirement already satisfied: graphiti-core>=0.5.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from guardkit-py==0.1.0) (0.26.3)
Requirement already satisfied: httpx>=0.25.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from guardkit-py==0.1.0) (0.28.1)
Requirement already satisfied: jinja2>=3.1.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from guardkit-py==0.1.0) (3.1.6)
Requirement already satisfied: pydantic>=2.0.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from guardkit-py==0.1.0) (2.12.5)
Requirement already satisfied: python-dotenv>=1.0.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from guardkit-py==0.1.0) (1.2.1)
Requirement already satisfied: python-frontmatter>=1.0.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from guardkit-py==0.1.0) (1.1.0)
Requirement already satisfied: pyyaml>=6.0.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from guardkit-py==0.1.0) (6.0.3)
Requirement already satisfied: rich>=13.0.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from guardkit-py==0.1.0) (14.2.0)
Requirement already satisfied: claude-agent-sdk>=0.1.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from guardkit-py==0.1.0) (0.1.37)
Requirement already satisfied: anyio>=4.0.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (4.12.0)
Requirement already satisfied: mcp>=0.1.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (1.25.0)
Requirement already satisfied: idna>=2.8 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from anyio>=4.0.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (3.11)
Requirement already satisfied: diskcache>=5.6.3 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from graphiti-core>=0.5.0->guardkit-py==0.1.0) (5.6.3)
Requirement already satisfied: neo4j>=5.26.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from graphiti-core>=0.5.0->guardkit-py==0.1.0) (6.1.0)
Requirement already satisfied: numpy>=1.0.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from graphiti-core>=0.5.0->guardkit-py==0.1.0) (2.4.1)
Requirement already satisfied: openai>=1.91.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from graphiti-core>=0.5.0->guardkit-py==0.1.0) (2.16.0)
Requirement already satisfied: posthog>=3.0.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from graphiti-core>=0.5.0->guardkit-py==0.1.0) (7.7.0)
Requirement already satisfied: tenacity>=9.0.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from graphiti-core>=0.5.0->guardkit-py==0.1.0) (9.1.2)
Requirement already satisfied: certifi in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from httpx>=0.25.0->guardkit-py==0.1.0) (2025.11.12)
Requirement already satisfied: httpcore==1.* in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from httpx>=0.25.0->guardkit-py==0.1.0) (1.0.9)
Requirement already satisfied: h11>=0.16 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from httpcore==1.*->httpx>=0.25.0->guardkit-py==0.1.0) (0.16.0)
Requirement already satisfied: MarkupSafe>=2.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from jinja2>=3.1.0->guardkit-py==0.1.0) (3.0.3)
Requirement already satisfied: httpx-sse>=0.4 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (0.4.3)
Requirement already satisfied: jsonschema>=4.20.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (4.25.1)
Requirement already satisfied: pydantic-settings>=2.5.2 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (2.12.0)
Requirement already satisfied: pyjwt>=2.10.1 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from pyjwt[crypto]>=2.10.1->mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (2.10.1)
Requirement already satisfied: python-multipart>=0.0.9 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (0.0.21)
Requirement already satisfied: sse-starlette>=1.6.1 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (3.1.2)
Requirement already satisfied: starlette>=0.27 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (0.50.0)
Requirement already satisfied: typing-extensions>=4.9.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (4.15.0)
Requirement already satisfied: typing-inspection>=0.4.1 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (0.4.2)
Requirement already satisfied: uvicorn>=0.31.1 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (0.40.0)
Requirement already satisfied: annotated-types>=0.6.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from pydantic>=2.0.0->guardkit-py==0.1.0) (0.7.0)
Requirement already satisfied: pydantic-core==2.41.5 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from pydantic>=2.0.0->guardkit-py==0.1.0) (2.41.5)
Requirement already satisfied: attrs>=22.2.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from jsonschema>=4.20.0->mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (25.4.0)
Requirement already satisfied: jsonschema-specifications>=2023.03.6 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from jsonschema>=4.20.0->mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (2025.9.1)
Requirement already satisfied: referencing>=0.28.4 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from jsonschema>=4.20.0->mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (0.37.0)
Requirement already satisfied: rpds-py>=0.7.1 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from jsonschema>=4.20.0->mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (0.30.0)
Requirement already satisfied: pytz in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from neo4j>=5.26.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (2025.2)
Requirement already satisfied: distro<2,>=1.7.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from openai>=1.91.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (1.9.0)
Requirement already satisfied: jiter<1,>=0.10.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from openai>=1.91.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (0.12.0)
Requirement already satisfied: sniffio in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from openai>=1.91.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (1.3.1)
Requirement already satisfied: tqdm>4 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from openai>=1.91.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (4.67.1)
Requirement already satisfied: requests<3.0,>=2.7 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from posthog>=3.0.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (2.32.5)
Requirement already satisfied: six>=1.5 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from posthog>=3.0.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (1.17.0)
Requirement already satisfied: python-dateutil>=2.2 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from posthog>=3.0.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (2.9.0.post0)
Requirement already satisfied: backoff>=1.10.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from posthog>=3.0.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (2.2.1)
Requirement already satisfied: charset_normalizer<4,>=2 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from requests<3.0,>=2.7->posthog>=3.0.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (3.4.4)
Requirement already satisfied: urllib3<3,>=1.21.1 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from requests<3.0,>=2.7->posthog>=3.0.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (2.6.3)
Requirement already satisfied: cryptography>=3.4.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from pyjwt[crypto]>=2.10.1->mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (46.0.3)
Requirement already satisfied: cffi>=2.0.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from cryptography>=3.4.0->pyjwt[crypto]>=2.10.1->mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (2.0.0)
Requirement already satisfied: pycparser in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography>=3.4.0->pyjwt[crypto]>=2.10.1->mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (2.23)
Requirement already satisfied: markdown-it-py>=2.2.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from rich>=13.0.0->guardkit-py==0.1.0) (4.0.0)
Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from rich>=13.0.0->guardkit-py==0.1.0) (2.19.2)
Requirement already satisfied: mdurl~=0.1 in /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich>=13.0.0->guardkit-py==0.1.0) (0.1.2)
Building wheels for collected packages: guardkit-py
  Building editable for guardkit-py (pyproject.toml) ... done
  Created wheel for guardkit-py: filename=guardkit_py-0.1.0-py3-none-any.whl size=9012 sha256=9e6408eefe18a2d4820fdc47d98c2cd7758668d600e741c45ec76ca15df04041
  Stored in directory: /private/var/folders/75/prgjl4_x0k3_6tj58k39db1r0000gn/T/pip-ephem-wheel-cache-6tyvkgux/wheels/2b/0f/3b/55f03b7449b767f09dcb50d5db67060f17ca2e457f18cacf85
Successfully built guardkit-py
Installing collected packages: guardkit-py
  Attempting uninstall: guardkit-py
    Found existing installation: guardkit-py 0.1.0
    Uninstalling guardkit-py-0.1.0:
      Successfully uninstalled guardkit-py-0.1.0
Successfully installed guardkit-py-0.1.0
✓ guardkit package installed successfully (with AutoBuild)
✓ guardkit Python package is importable
✓ Claude Agent SDK is available (AutoBuild ready)
⚠ Found existing installations: .agentecflow .claude
ℹ Creating backup of .agentecflow at /Users/richardwoollcott/.agentecflow.backup.20260317_101318
✓ Backup created: /Users/richardwoollcott/.agentecflow.backup.20260317_101318
ℹ Creating backup of .claude at /Users/richardwoollcott/.claude.backup.20260317_101318
✓ Backup created: /Users/richardwoollcott/.claude.backup.20260317_101318
ℹ Creating complete directory structure...
✓ Complete directory structure created
ℹ Installing global files...
✓ Installed methodology instructions
✓ Installed project templates
✓ Installed global Python libraries (     135 modules)
✓ Installed Jinja2 templates for plan rendering
✓ Installed review_modes for task-review command
✓ Installed review_templates for task-review command
✓ Installed commands with lib (      90 Python modules, production only)
✓ Installed documentation
✓ Installed initialization script
✓ Global files installed
ℹ Installing global AI agents...
✓ Installed core global agents
✓   ✓ Installed clarification-questioner agent
✓ Installed default stack agents
✓ Installed fastapi-python stack agents
✓ Installed langchain-deepagents stack agents
✓ Installed mcp-typescript stack agents
✓ Installed nextjs-fullstack stack agents
✓ Installed react-fastapi-monorepo stack agents
✓ Installed react-typescript stack agents
✓ Installed 70 total agents (      31 global +       39 stack-specific)
  Global agents:
    - agent-content-enhancer-ext
    - agent-content-enhancer
    - architectural-reviewer-ext
    - architectural-reviewer
    - autobuild-coach
    - autobuild-player
    - build-validator-ext
    - build-validator
    - clarification-questioner
    - code-reviewer-ext
    - code-reviewer
    - complexity-evaluator-ext
    - complexity-evaluator
    - database-specialist-ext
    - database-specialist
    - debugging-specialist-ext
    - debugging-specialist
    - devops-specialist-ext
    - devops-specialist
    - git-workflow-manager-ext
    - git-workflow-manager
    - pattern-advisor-ext
    - pattern-advisor
    - security-specialist-ext
    - security-specialist
    - task-manager-ext
    - task-manager
    - test-orchestrator-ext
    - test-orchestrator
    - test-verifier-ext
    - test-verifier
ℹ Creating CLI commands...
✓ Created guardkit-init command
✓ Created CLI commands (guardkit, guardkit-init, gk, gki)
✓ Created graphiti-check wrapper
ℹ Setting up shell integration...
ℹ Detected zsh shell
ℹ Shell integration already configured
ℹ Creating global configuration...
✓ Global configuration created
ℹ Installing shell completions...
✓ Shell completions installed
ℹ Setting up version management...
✓ Version management configured
ℹ Setting up cache directories...
✓ Cache directories created
ℹ Setting up Claude Code integration...
✓ Created ~/.claude directory
✓ Claude Code integration configured successfully
ℹ   Commands: ~/.claude/commands → ~/.agentecflow/commands
ℹ   Agents: ~/.claude/agents → ~/.agentecflow/agents

✓ All guardkit commands now available in Claude Code!
ℹ Compatible with Conductor.build for parallel development
ℹ Setting up Python command script symlinks...
ℹ Found 93 Python command script(s)
ℹ   Created: agent-format → agent-format.py
ℹ   Created: agent-enhance → agent-enhance.py
ℹ   Created: agent-validate → agent-validate.py
ℹ   Created: phase-gate-validator → phase_gate_validator.py
ℹ   Created: template-merger → template_merger.py
ℹ   Created: graphiti-diagnose-v3 → graphiti_diagnose_v3.py
ℹ   Created: spec-drift-detector → spec_drift_detector.py
ℹ   Created: error-messages → error_messages.py
ℹ   Created: demo-phase-gate-integration → demo_phase_gate_integration.py
ℹ   Created: library-context → library_context.py
ℹ   Created: demo-template-qa → demo_template_qa.py
ℹ   Created: graphiti-diagnose-v2 → graphiti_diagnose_v2.py
ℹ   Created: plan-audit → plan_audit.py
ℹ   Created: worktree-cleanup → worktree_cleanup.py
ℹ   Created: upfront-complexity-adapter → upfront_complexity_adapter.py
ℹ   Created: version-manager → version_manager.py
ℹ   Created: plan-markdown-parser → plan_markdown_parser.py
ℹ   Created: plan-persistence → plan_persistence.py
ℹ   Created: agent-utils → agent_utils.py
ℹ   Created: library-detector → library_detector.py
ℹ   Created: user-interaction → user_interaction.py
ℹ   Created: demo-agent-tracker-integration → demo_agent_tracker_integration.py
ℹ   Created: template-create-orchestrator → template_create_orchestrator.py
ℹ   Created: task-completion-helper → task_completion_helper.py
ℹ   Created: api-call-preview → api_call_preview.py
ℹ   Created: template-qa-persistence → template_qa_persistence.py
ℹ   Created: constants → constants.py
ℹ   Created: graphiti-diagnose → graphiti_diagnose.py
ℹ   Created: template-versioning → template_versioning.py
ℹ   Created: plan-modifier → plan_modifier.py
ℹ   Created: micro-task-workflow → micro_task_workflow.py
ℹ   Created: review-modes → review_modes.py
ℹ   Created: git-state-helper → git_state_helper.py
ℹ   Created: visualization → visualization.py
ℹ   Created: checkpoint-display → checkpoint_display.py
ℹ   Created: review-mode-executor → review_mode_executor.py
ℹ   Created: review-report-generator → review_report_generator.py
ℹ   Created: review-router → review_router.py
ℹ   Created: qa-manager → qa_manager.py
ℹ   Created: complexity-factors → complexity_factors.py
ℹ   Created: template-qa-questions → template_qa_questions.py
ℹ   Created: task-review-orchestrator → task_review_orchestrator.py
ℹ   Created: modification-session → modification_session.py
ℹ   Created: graphiti-context-loader → graphiti_context_loader.py
ℹ   Created: pager-display → pager_display.py
ℹ   Created: template-validate-cli → template_validate_cli.py
ℹ   Created: modification-applier → modification_applier.py
ℹ   Created: modification-persistence → modification_persistence.py
ℹ   Created: plan-markdown-renderer → plan_markdown_renderer.py
ℹ   Created: micro-task-detector → micro_task_detector.py
ℹ   Created: refinement-handler → refinement_handler.py
ℹ   Created: agent-invocation-validator → agent_invocation_validator.py
ℹ   Created: split-models → split_models.py
ℹ   Created: generate-feature-yaml → generate_feature_yaml.py
ℹ   Created: demo-plan-markdown → demo_plan_markdown.py
ℹ   Created: agent-invocation-tracker → agent_invocation_tracker.py
ℹ   Created: task-utils → task_utils.py
ℹ   Created: change-tracker → change_tracker.py
ℹ   Created: greenfield-qa-session → greenfield_qa_session.py
ℹ   Created: duplicate-detector → duplicate_detector.py
ℹ   Created: agent-discovery → agent_discovery.py
ℹ   Created: template-qa-session → template_qa_session.py
ℹ   Created: feature-detection → feature_detection.py
ℹ   Created: task-breakdown → task_breakdown.py
ℹ   Created: task-split-advisor → task_split_advisor.py
ℹ   Created: flag-validator → flag_validator.py
ℹ   Created: template-qa-display → template_qa_display.py
ℹ   Created: distribution-helpers → distribution_helpers.py
ℹ   Created: breakdown-strategies → breakdown_strategies.py
ℹ   Created: template-qa-validator → template_qa_validator.py
ℹ   Created: phase-execution → phase_execution.py
ℹ   Created: complexity-calculator → complexity_calculator.py
ℹ   Created: template-packager → template_packager.py
ℹ   Created: upfront-complexity-cli → upfront_complexity_cli.py
ℹ   Created: complexity-models → complexity_models.py

✓ Python command symlinks configured successfully
ℹ   Created: 75
ℹ   Updated: 0
ℹ   Skipped: 18
ℹ   Location: /Users/richardwoollcott/.agentecflow/bin
ℹ Commands can now be executed from any directory
ℹ Creating marker file for package detection...
✓ Marker file created: /Users/richardwoollcott/.agentecflow/guardkit.marker.json
ℹ   Package: guardkit (standalone + optional require-kit integration)
ℹ   Install method: git-clone
ℹ   Model: Bidirectional optional integration
ℹ   ℹ Install require-kit for requirements management features
ℹ Validating installation...
✅ Python imports validated successfully
✓ Installation validated successfully
✓ guardkit-py CLI is available in PATH

════════════════════════════════════════════════════════
✅ GuardKit installation complete!
════════════════════════════════════════════════════════

Installation Summary:
  📁 Home Directory: /Users/richardwoollcott/.agentecflow
  🔧 Configuration: /Users/richardwoollcott/.config/agentecflow
  📦 Version: 2.0.0

Installed Components:
  🤖 AI Agents: 70 (including clarification-questioner)
  📋 Templates:        8
  ⚡ Commands:       31

Available Commands:
  • guardkit-init [template]  - Initialize a project
  • guardkit init             - Alternative initialization
  • guardkit doctor           - Check system health
  • gk                          - Short for guardkit
  • gki                         - Short for guardkit-init

Available Templates:
  • default - Language-agnostic foundation (Go, Rust, Ruby, PHP, etc.)
  • fastapi-python - FastAPI backend with layered architecture (9+/10)
  • fastmcp-python - FastMCP Python server with tool registration and async patterns
  • langchain-deepagents
  • mcp-typescript - MCP TypeScript server with @modelcontextprotocol/sdk and Zod validation
  • nextjs-fullstack - Next.js App Router full-stack (9+/10)
  • react-fastapi-monorepo - React + FastAPI monorepo with type safety (9.2/10)
  • react-typescript - React frontend with feature-based architecture (9+/10)

Claude Code Integration:
  ✓ Commands available in Claude Code (via symlink)
  ✓ Agents available in Claude Code (via symlink)
  ✓ Compatible with Conductor.build for parallel development

AutoBuild Configuration:
  ⚠ ANTHROPIC_API_KEY not set
      AutoBuild requires API credentials or Claude Code authentication
      Run 'guardkit doctor' to check configuration

⚠ Next Steps:
  1. Restart your shell or run: source ~/.bashrc (or ~/.zshrc)
  2. Navigate to your project directory
  3. Run: guardkit-init [template]  # e.g., react-typescript, fastapi-python, nextjs-fullstack
  4. (Optional) Install Conductor.build for parallel development

📚 Documentation: /Users/richardwoollcott/.agentecflow/docs/
❓ Check health: guardkit doctor
🔗 Conductor: https://conductor.build
richardwoollcott@Richards-MBP scripts %