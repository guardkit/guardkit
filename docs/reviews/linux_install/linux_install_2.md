richardwoollcott@promaxgb10-41b1:~/Projects/appmilla_github/guardkit/installer/scripts$ ./install.sh

╔════════════════════════════════════════════════════════╗
║         GuardKit Installation System                 ║
║         Version: 2.0.0                  ║
╚════════════════════════════════════════════════════════╝

ℹ Installing GuardKit to /home/richardwoollcott/.agentecflow

ℹ Checking prerequisites...
⚠ Node.js not found. The following templates require Node.js:
    react-typescript, nextjs-fullstack, react-fastapi-monorepo
  Templates that work without Node.js: fastapi-python, default
✓ Python found: Python 3.12 (>= 3.10 required)
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
ℹ graphiti-core check completed (status: 0)
✓ graphiti-core already installed
✓ Python dependency checks complete
✓ All required prerequisites met
ℹ Installing guardkit Python package (with AutoBuild support)...
ℹ Installing from: /home/richardwoollcott/Projects/appmilla_github/guardkit
Defaulting to user installation because normal site-packages is not writeable
Obtaining file:///home/richardwoollcott/Projects/appmilla_github/guardkit
  Installing build dependencies ... done
  Checking if build backend supports build_editable ... done
  Getting requirements to build editable ... done
  Installing backend dependencies ... done
  Preparing editable metadata (pyproject.toml) ... done
Requirement already satisfied: click>=8.0.0 in /usr/lib/python3/dist-packages (from guardkit-py==0.1.0) (8.1.6)
Requirement already satisfied: graphiti-core>=0.5.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from guardkit-py==0.1.0) (0.28.1)
Requirement already satisfied: httpx>=0.25.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from guardkit-py==0.1.0) (0.28.1)
Requirement already satisfied: jinja2>=3.1.0 in /usr/lib/python3/dist-packages (from guardkit-py==0.1.0) (3.1.2)
Requirement already satisfied: pydantic>=2.0.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from guardkit-py==0.1.0) (2.12.5)
Requirement already satisfied: python-dotenv>=1.0.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from guardkit-py==0.1.0) (1.2.1)
Requirement already satisfied: python-frontmatter>=1.0.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from guardkit-py==0.1.0) (1.1.0)
Requirement already satisfied: pyyaml>=6.0.0 in /usr/lib/python3/dist-packages (from guardkit-py==0.1.0) (6.0.1)
Requirement already satisfied: rich>=13.0.0 in /usr/lib/python3/dist-packages (from guardkit-py==0.1.0) (13.7.1)
Requirement already satisfied: claude-agent-sdk>=0.1.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from guardkit-py==0.1.0) (0.1.39)
Requirement already satisfied: anyio>=4.0.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (4.12.1)
Requirement already satisfied: mcp>=0.1.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (1.26.0)
Requirement already satisfied: neo4j>=5.26.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from graphiti-core>=0.5.0->guardkit-py==0.1.0) (6.1.0)
Requirement already satisfied: numpy>=1.0.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from graphiti-core>=0.5.0->guardkit-py==0.1.0) (2.4.2)
Requirement already satisfied: openai>=1.91.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from graphiti-core>=0.5.0->guardkit-py==0.1.0) (2.21.0)
Requirement already satisfied: posthog>=3.0.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from graphiti-core>=0.5.0->guardkit-py==0.1.0) (7.9.3)
Requirement already satisfied: tenacity>=9.0.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from graphiti-core>=0.5.0->guardkit-py==0.1.0) (9.1.4)
Requirement already satisfied: certifi in /usr/lib/python3/dist-packages (from httpx>=0.25.0->guardkit-py==0.1.0) (2023.11.17)
Requirement already satisfied: httpcore==1.* in /home/richardwoollcott/.local/lib/python3.12/site-packages (from httpx>=0.25.0->guardkit-py==0.1.0) (1.0.9)
Requirement already satisfied: idna in /usr/lib/python3/dist-packages (from httpx>=0.25.0->guardkit-py==0.1.0) (3.6)
Requirement already satisfied: h11>=0.16 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from httpcore==1.*->httpx>=0.25.0->guardkit-py==0.1.0) (0.16.0)
Requirement already satisfied: annotated-types>=0.6.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from pydantic>=2.0.0->guardkit-py==0.1.0) (0.7.0)
Requirement already satisfied: pydantic-core==2.41.5 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from pydantic>=2.0.0->guardkit-py==0.1.0) (2.41.5)
Requirement already satisfied: typing-extensions>=4.14.1 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from pydantic>=2.0.0->guardkit-py==0.1.0) (4.15.0)
Requirement already satisfied: typing-inspection>=0.4.2 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from pydantic>=2.0.0->guardkit-py==0.1.0) (0.4.2)
Requirement already satisfied: markdown-it-py>=2.2.0 in /usr/lib/python3/dist-packages (from rich>=13.0.0->guardkit-py==0.1.0) (3.0.0)
Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /usr/lib/python3/dist-packages (from rich>=13.0.0->guardkit-py==0.1.0) (2.17.2)
Requirement already satisfied: mdurl~=0.1 in /usr/lib/python3/dist-packages (from markdown-it-py>=2.2.0->rich>=13.0.0->guardkit-py==0.1.0) (0.1.2)
Requirement already satisfied: httpx-sse>=0.4 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (0.4.3)
Requirement already satisfied: jsonschema>=4.20.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (4.26.0)
Requirement already satisfied: pydantic-settings>=2.5.2 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (2.13.1)
Requirement already satisfied: pyjwt>=2.10.1 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from pyjwt[crypto]>=2.10.1->mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (2.11.0)
Requirement already satisfied: python-multipart>=0.0.9 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (0.0.22)
Requirement already satisfied: sse-starlette>=1.6.1 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (3.2.0)
Requirement already satisfied: starlette>=0.27 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (0.52.1)
Requirement already satisfied: uvicorn>=0.31.1 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (0.41.0)
Requirement already satisfied: pytz in /usr/lib/python3/dist-packages (from neo4j>=5.26.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (2024.1)
Requirement already satisfied: distro<2,>=1.7.0 in /usr/lib/python3/dist-packages (from openai>=1.91.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (1.9.0)
Requirement already satisfied: jiter<1,>=0.10.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from openai>=1.91.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (0.13.0)
Requirement already satisfied: sniffio in /home/richardwoollcott/.local/lib/python3.12/site-packages (from openai>=1.91.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (1.3.1)
Requirement already satisfied: tqdm>4 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from openai>=1.91.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (4.67.3)
Requirement already satisfied: requests<3.0,>=2.7 in /usr/lib/python3/dist-packages (from posthog>=3.0.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (2.31.0)
Requirement already satisfied: six>=1.5 in /usr/lib/python3/dist-packages (from posthog>=3.0.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (1.16.0)
Requirement already satisfied: python-dateutil>=2.2 in /usr/lib/python3/dist-packages (from posthog>=3.0.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (2.8.2)
Requirement already satisfied: backoff>=1.10.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from posthog>=3.0.0->graphiti-core>=0.5.0->guardkit-py==0.1.0) (2.2.1)
Requirement already satisfied: attrs>=22.2.0 in /usr/lib/python3/dist-packages (from jsonschema>=4.20.0->mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (23.2.0)
Requirement already satisfied: jsonschema-specifications>=2023.03.6 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from jsonschema>=4.20.0->mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (2025.9.1)
Requirement already satisfied: referencing>=0.28.4 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from jsonschema>=4.20.0->mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (0.37.0)
Requirement already satisfied: rpds-py>=0.25.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from jsonschema>=4.20.0->mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (0.30.0)
Requirement already satisfied: cryptography>=3.4.0 in /usr/lib/python3/dist-packages (from pyjwt[crypto]>=2.10.1->mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (41.0.7)
Checking if build backend supports build_editable ... done
Building wheels for collected packages: guardkit-py
  Building editable for guardkit-py (pyproject.toml) ... done
  Created wheel for guardkit-py: filename=guardkit_py-0.1.0-py3-none-any.whl size=9010 sha256=16605e1fb39f3e00a06ecd299996c39a9f6ad99e4b3c93742026dec450223b3b
  Stored in directory: /tmp/pip-ephem-wheel-cache-zzn751ts/wheels/48/fe/10/ecf9d7ff60251264de584539a3a2fe684426e90409b5a9d2a7
Successfully built guardkit-py
Installing collected packages: guardkit-py
  Attempting uninstall: guardkit-py
    Found existing installation: guardkit-py 0.1.0
    Uninstalling guardkit-py-0.1.0:
      Successfully uninstalled guardkit-py-0.1.0
  WARNING: The script guardkit-py is installed in '/home/richardwoollcott/.local/bin' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
Successfully installed guardkit-py-0.1.0
✓ guardkit package installed successfully (with AutoBuild)
✓ guardkit Python package is importable
✓ Claude Agent SDK is available (AutoBuild ready)
⚠ guardkit-py CLI not found in PATH
ℹ You may need to restart your shell or add ~/.local/bin to PATH
⚠ Found existing installations: .agentecflow .claude
ℹ Creating backup of .agentecflow at /home/richardwoollcott/.agentecflow.backup.20260222_130244
✓ Backup created: /home/richardwoollcott/.agentecflow.backup.20260222_130244
ℹ Creating backup of .claude at /home/richardwoollcott/.claude.backup.20260222_130244
✓ Backup created: /home/richardwoollcott/.claude.backup.20260222_130244
ℹ Creating complete directory structure...
✓ Complete directory structure created
ℹ Installing global files...
✓ Installed methodology instructions
✓ Installed project templates
✓ Installed global Python libraries (135 modules)
✓ Installed Jinja2 templates for plan rendering
✓ Installed review_modes for task-review command
✓ Installed review_templates for task-review command
✓ Installed commands with lib (90 Python modules, production only)
✓ Installed documentation
✓ Installed initialization script
✓ Global files installed
ℹ Installing global AI agents...
✓ Installed core global agents
✓   ✓ Installed clarification-questioner agent
✓ Installed default stack agents
✓ Installed fastapi-python stack agents
✓ Installed mcp-typescript stack agents
✓ Installed nextjs-fullstack stack agents
✓ Installed react-fastapi-monorepo stack agents
✓ Installed react-typescript stack agents
✓ Installed 62 total agents (30 global + 32 stack-specific)
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
ℹ Setting up shell integration...
ℹ Detected bash shell
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
richardwoollcott@promaxgb10-41b1:~/Projects/appmilla_github/guardkit/installer/scripts$ 
