richardwoollcott@Mac appmilla_github % cd youtube-transcript-mcp
richardwoollcott@Mac youtube-transcript-mcp % guardkit init mcp-server-python

╔════════════════════════════════════════════════════════╗
║         GuardKit Project Initialization              ║
║         Template: mcp-server-python            ║
╚════════════════════════════════════════════════════════╝

ℹ Using GuardKit from: /Users/richardwoollcott/.agentecflow
ℹ Creating project structure...
✓ Created test directories
✓ Project structure created
⚠ Template 'mcp-server-python' not found, using default
ℹ Using template: default
✓ Copied project context file (from .claude/)
✓ Copied template-specific agents
✓ Added 31 global agent(s)
✓ Copied template files
✓ Copied rules structure for Claude Code
✓ Rules structure verified (3 rule files)
ℹ Creating project configuration...
✓ Created project configuration
ℹ Creating initial documentation...
✓ Created initial documentation

════════════════════════════════════════════════════════
✅ GuardKit successfully initialized!
════════════════════════════════════════════════════════

📁 Project Structure Created:
  .claude/       - GuardKit configuration
  docs/          - Documentation and ADRs
  tasks/         - Task workflow (backlog → in_progress → in_review → blocked → completed)

Project Configuration:
  🎨 Template: default
  🔍 Detected Type: unknown

AI Agents:
  🤖 agent-content-enhancer-ext
  🤖 agent-content-enhancer
  🤖 architectural-reviewer-ext
  🤖 architectural-reviewer
  🤖 autobuild-coach
  🤖 autobuild-player
  🤖 build-validator-ext
  🤖 build-validator
  🤖 clarification-questioner
  🤖 code-reviewer-ext
  🤖 code-reviewer
  🤖 complexity-evaluator-ext
  🤖 complexity-evaluator
  🤖 database-specialist-ext
  🤖 database-specialist
  🤖 debugging-specialist-ext
  🤖 debugging-specialist
  🤖 devops-specialist-ext
  🤖 devops-specialist
  🤖 git-workflow-manager-ext
  🤖 git-workflow-manager
  🤖 pattern-advisor-ext
  🤖 pattern-advisor
  🤖 security-specialist-ext
  🤖 security-specialist
  🤖 task-manager-ext
  🤖 task-manager
  🤖 test-orchestrator-ext
  🤖 test-orchestrator
  🤖 test-verifier-ext
  🤖 test-verifier

GuardKit Workflow:

  Simple Task Management:
    /task-create      - Create a new task
    /task-work        - Work on task (with quality gates)
    /task-complete    - Complete and archive task
    /task-status      - View task status
    /task-refine      - Iterative refinement

  Design-First Workflow (complex tasks):
    /task-work --design-only      - Plan approval checkpoint
    /task-work --implement-only   - Implement approved plan

  Utilities:
    /debug            - Troubleshoot issues

Using AI Agents:
  AI agents are invoked automatically during /task-work
  They handle architectural review, testing, and code review

Need Requirements Management?
  For EARS notation, BDD, epics, and portfolio management:
  Install require-kit: https://github.com/requirekit/require-kit

⚠️  Important - If using VS Code:
  Reload VS Code window to enable slash commands:
  • Press Cmd+Shift+P (macOS) or Ctrl+Shift+P (Windows/Linux)
  • Type 'Developer: Reload Window' and press Enter
  • Or close and reopen VS Code

Ready to start development!
richardwoollcott@Mac youtube-transcript-mcp %