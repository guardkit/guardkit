richardwoollcott@promaxgb10-41b1:~/Projects/appmilla_github/guardkit/installer/scripts$ ./install.sh

╔════════════════════════════════════════════════════════╗
║         GuardKit Installation System                 ║
║         Version: 2.0.0                  ║
╚════════════════════════════════════════════════════════╝

ℹ Installing GuardKit to /home/richardwoollcott/.agentecflow

ℹ Checking prerequisites...
⚠ Node.js not found. Some features may be limited.
✓ Python found: Python 3.12 (>= 3.10 required)
✓ pip3 found - can install Python dependencies
ℹ Checking for Jinja2...
ℹ Jinja2 check completed (status: 0)
✓ Jinja2 already installed
ℹ Checking for python-frontmatter...
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'frontmatter'
ℹ python-frontmatter check completed (status: 1)
ℹ Installing python-frontmatter (required for plan metadata)...
ℹ This may take a moment, please wait...
Defaulting to user installation because normal site-packages is not writeable
Collecting python-frontmatter
  Downloading python_frontmatter-1.1.0-py3-none-any.whl.metadata (4.1 kB)
Requirement already satisfied: PyYAML in /usr/lib/python3/dist-packages (from python-frontmatter) (6.0.1)
Downloading python_frontmatter-1.1.0-py3-none-any.whl (9.8 kB)
Installing collected packages: python-frontmatter
Successfully installed python-frontmatter-1.1.0
✓ python-frontmatter installed successfully
ℹ Checking for pydantic...
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'pydantic'
ℹ pydantic check completed (status: 1)
ℹ Installing pydantic (required for template creation)...
ℹ This may take a moment, please wait...
Defaulting to user installation because normal site-packages is not writeable
Collecting pydantic
  Downloading pydantic-2.12.5-py3-none-any.whl.metadata (90 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 90.6/90.6 kB 2.2 MB/s eta 0:00:00
Collecting annotated-types>=0.6.0 (from pydantic)
  Downloading annotated_types-0.7.0-py3-none-any.whl.metadata (15 kB)
Collecting pydantic-core==2.41.5 (from pydantic)
  Downloading pydantic_core-2.41.5-cp312-cp312-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (7.3 kB)
Collecting typing-extensions>=4.14.1 (from pydantic)
  Downloading typing_extensions-4.15.0-py3-none-any.whl.metadata (3.3 kB)
Collecting typing-inspection>=0.4.2 (from pydantic)
  Downloading typing_inspection-0.4.2-py3-none-any.whl.metadata (2.6 kB)
Downloading pydantic-2.12.5-py3-none-any.whl (463 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 463.6/463.6 kB 5.6 MB/s eta 0:00:00
Downloading pydantic_core-2.41.5-cp312-cp312-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (1.9 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.9/1.9 MB 6.1 MB/s eta 0:00:00
Downloading annotated_types-0.7.0-py3-none-any.whl (13 kB)
Downloading typing_extensions-4.15.0-py3-none-any.whl (44 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 44.6/44.6 kB 13.7 MB/s eta 0:00:00
Downloading typing_inspection-0.4.2-py3-none-any.whl (14 kB)
Installing collected packages: typing-extensions, annotated-types, typing-inspection, pydantic-core, pydantic
Successfully installed annotated-types-0.7.0 pydantic-2.12.5 pydantic-core-2.41.5 typing-extensions-4.15.0 typing-inspection-0.4.2
✓ pydantic installed successfully
ℹ Checking for python-dotenv...
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'dotenv'
ℹ python-dotenv check completed (status: 1)
ℹ Installing python-dotenv (required for .env file loading)...
ℹ This may take a moment, please wait...
Defaulting to user installation because normal site-packages is not writeable
Collecting python-dotenv
  Downloading python_dotenv-1.2.1-py3-none-any.whl.metadata (25 kB)
Downloading python_dotenv-1.2.1-py3-none-any.whl (21 kB)
Installing collected packages: python-dotenv
  WARNING: The script dotenv is installed in '/home/richardwoollcott/.local/bin' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
Successfully installed python-dotenv-1.2.1
✓ python-dotenv installed successfully
ℹ Checking for graphiti-core...
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'graphiti_core'
ℹ graphiti-core check completed (status: 1)
ℹ Installing graphiti-core (required for knowledge graph integration)...
ℹ This may take a moment, please wait...
Defaulting to user installation because normal site-packages is not writeable
Collecting graphiti-core
  Downloading graphiti_core-0.28.1-py3-none-any.whl.metadata (33 kB)
Collecting neo4j>=5.26.0 (from graphiti-core)
  Downloading neo4j-6.1.0-py3-none-any.whl.metadata (5.3 kB)
Collecting numpy>=1.0.0 (from graphiti-core)
  Downloading numpy-2.4.2-cp312-cp312-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl.metadata (6.6 kB)
Collecting openai>=1.91.0 (from graphiti-core)
  Downloading openai-2.21.0-py3-none-any.whl.metadata (29 kB)
Collecting posthog>=3.0.0 (from graphiti-core)
  Downloading posthog-7.9.3-py3-none-any.whl.metadata (6.4 kB)
Requirement already satisfied: pydantic>=2.11.5 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from graphiti-core) (2.12.5)
Requirement already satisfied: python-dotenv>=1.0.1 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from graphiti-core) (1.2.1)
Collecting tenacity>=9.0.0 (from graphiti-core)
  Downloading tenacity-9.1.4-py3-none-any.whl.metadata (1.2 kB)
Requirement already satisfied: pytz in /usr/lib/python3/dist-packages (from neo4j>=5.26.0->graphiti-core) (2024.1)
Collecting anyio<5,>=3.5.0 (from openai>=1.91.0->graphiti-core)
  Downloading anyio-4.12.1-py3-none-any.whl.metadata (4.3 kB)
Requirement already satisfied: distro<2,>=1.7.0 in /usr/lib/python3/dist-packages (from openai>=1.91.0->graphiti-core) (1.9.0)
Collecting httpx<1,>=0.23.0 (from openai>=1.91.0->graphiti-core)
  Downloading httpx-0.28.1-py3-none-any.whl.metadata (7.1 kB)
Collecting jiter<1,>=0.10.0 (from openai>=1.91.0->graphiti-core)
  Downloading jiter-0.13.0-cp312-cp312-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (5.2 kB)
Collecting sniffio (from openai>=1.91.0->graphiti-core)
  Downloading sniffio-1.3.1-py3-none-any.whl.metadata (3.9 kB)
Collecting tqdm>4 (from openai>=1.91.0->graphiti-core)
  Downloading tqdm-4.67.3-py3-none-any.whl.metadata (57 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 57.7/57.7 kB 5.0 MB/s eta 0:00:00
Requirement already satisfied: typing-extensions<5,>=4.11 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from openai>=1.91.0->graphiti-core) (4.15.0)
Requirement already satisfied: requests<3.0,>=2.7 in /usr/lib/python3/dist-packages (from posthog>=3.0.0->graphiti-core) (2.31.0)
Requirement already satisfied: six>=1.5 in /usr/lib/python3/dist-packages (from posthog>=3.0.0->graphiti-core) (1.16.0)
Requirement already satisfied: python-dateutil>=2.2 in /usr/lib/python3/dist-packages (from posthog>=3.0.0->graphiti-core) (2.8.2)
Collecting backoff>=1.10.0 (from posthog>=3.0.0->graphiti-core)
  Downloading backoff-2.2.1-py3-none-any.whl.metadata (14 kB)
Requirement already satisfied: annotated-types>=0.6.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from pydantic>=2.11.5->graphiti-core) (0.7.0)
Requirement already satisfied: pydantic-core==2.41.5 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from pydantic>=2.11.5->graphiti-core) (2.41.5)
Requirement already satisfied: typing-inspection>=0.4.2 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from pydantic>=2.11.5->graphiti-core) (0.4.2)
Requirement already satisfied: idna>=2.8 in /usr/lib/python3/dist-packages (from anyio<5,>=3.5.0->openai>=1.91.0->graphiti-core) (3.6)
Requirement already satisfied: certifi in /usr/lib/python3/dist-packages (from httpx<1,>=0.23.0->openai>=1.91.0->graphiti-core) (2023.11.17)
Collecting httpcore==1.* (from httpx<1,>=0.23.0->openai>=1.91.0->graphiti-core)
  Downloading httpcore-1.0.9-py3-none-any.whl.metadata (21 kB)
Collecting h11>=0.16 (from httpcore==1.*->httpx<1,>=0.23.0->openai>=1.91.0->graphiti-core)
  Downloading h11-0.16.0-py3-none-any.whl.metadata (8.3 kB)
Downloading graphiti_core-0.28.1-py3-none-any.whl (311 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 311.6/311.6 kB 6.5 MB/s eta 0:00:00
Downloading neo4j-6.1.0-py3-none-any.whl (325 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 325.3/325.3 kB 8.2 MB/s eta 0:00:00
Downloading numpy-2.4.2-cp312-cp312-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl (15.7 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 15.7/15.7 MB 9.2 MB/s eta 0:00:00
Downloading openai-2.21.0-py3-none-any.whl (1.1 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.1/1.1 MB 3.9 MB/s eta 0:00:00
Downloading posthog-7.9.3-py3-none-any.whl (197 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 197.8/197.8 kB 11.2 MB/s eta 0:00:00
Downloading tenacity-9.1.4-py3-none-any.whl (28 kB)
Downloading anyio-4.12.1-py3-none-any.whl (113 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 113.6/113.6 kB 6.2 MB/s eta 0:00:00
Downloading backoff-2.2.1-py3-none-any.whl (15 kB)
Downloading httpx-0.28.1-py3-none-any.whl (73 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 73.5/73.5 kB 7.9 MB/s eta 0:00:00
Downloading httpcore-1.0.9-py3-none-any.whl (78 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 78.8/78.8 kB 11.0 MB/s eta 0:00:00
Downloading jiter-0.13.0-cp312-cp312-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (348 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 348.8/348.8 kB 5.0 MB/s eta 0:00:00
Downloading tqdm-4.67.3-py3-none-any.whl (78 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 78.4/78.4 kB 14.6 MB/s eta 0:00:00
Downloading sniffio-1.3.1-py3-none-any.whl (10 kB)
Downloading h11-0.16.0-py3-none-any.whl (37 kB)
Installing collected packages: tqdm, tenacity, sniffio, numpy, neo4j, jiter, h11, backoff, anyio, posthog, httpcore, httpx, openai, graphiti-core
  WARNING: The script tqdm is installed in '/home/richardwoollcott/.local/bin' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
  WARNING: The scripts f2py and numpy-config are installed in '/home/richardwoollcott/.local/bin' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
  WARNING: The script httpx is installed in '/home/richardwoollcott/.local/bin' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
  WARNING: The script openai is installed in '/home/richardwoollcott/.local/bin' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
Successfully installed anyio-4.12.1 backoff-2.2.1 graphiti-core-0.28.1 h11-0.16.0 httpcore-1.0.9 httpx-0.28.1 jiter-0.13.0 neo4j-6.1.0 numpy-2.4.2 openai-2.21.0 posthog-7.9.3 sniffio-1.3.1 tenacity-9.1.4 tqdm-4.67.3
✓ graphiti-core installed successfully
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
Collecting claude-agent-sdk>=0.1.0 (from guardkit-py==0.1.0)
  Downloading claude_agent_sdk-0.1.39-py3-none-manylinux_2_17_aarch64.whl.metadata (12 kB)
Requirement already satisfied: anyio>=4.0.0 in /home/richardwoollcott/.local/lib/python3.12/site-packages (from claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (4.12.1)
Collecting mcp>=0.1.0 (from claude-agent-sdk>=0.1.0->guardkit-py==0.1.0)
  Downloading mcp-1.26.0-py3-none-any.whl.metadata (89 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 89.5/89.5 kB 1.7 MB/s eta 0:00:00
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
Collecting httpx-sse>=0.4 (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0)
  Downloading httpx_sse-0.4.3-py3-none-any.whl.metadata (9.7 kB)
Collecting jsonschema>=4.20.0 (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0)
  Downloading jsonschema-4.26.0-py3-none-any.whl.metadata (7.6 kB)
Collecting pydantic-settings>=2.5.2 (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0)
  Downloading pydantic_settings-2.13.1-py3-none-any.whl.metadata (3.4 kB)
Collecting pyjwt>=2.10.1 (from pyjwt[crypto]>=2.10.1->mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0)
  Downloading pyjwt-2.11.0-py3-none-any.whl.metadata (4.0 kB)
Collecting python-multipart>=0.0.9 (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0)
  Downloading python_multipart-0.0.22-py3-none-any.whl.metadata (1.8 kB)
Collecting sse-starlette>=1.6.1 (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0)
  Downloading sse_starlette-3.2.0-py3-none-any.whl.metadata (12 kB)
Collecting starlette>=0.27 (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0)
  Downloading starlette-0.52.1-py3-none-any.whl.metadata (6.3 kB)
Collecting uvicorn>=0.31.1 (from mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0)
  Downloading uvicorn-0.41.0-py3-none-any.whl.metadata (6.7 kB)
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
Collecting jsonschema-specifications>=2023.03.6 (from jsonschema>=4.20.0->mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0)
  Downloading jsonschema_specifications-2025.9.1-py3-none-any.whl.metadata (2.9 kB)
Collecting referencing>=0.28.4 (from jsonschema>=4.20.0->mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0)
  Downloading referencing-0.37.0-py3-none-any.whl.metadata (2.8 kB)
Collecting rpds-py>=0.25.0 (from jsonschema>=4.20.0->mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0)
  Downloading rpds_py-0.30.0-cp312-cp312-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (4.1 kB)
Requirement already satisfied: cryptography>=3.4.0 in /usr/lib/python3/dist-packages (from pyjwt[crypto]>=2.10.1->mcp>=0.1.0->claude-agent-sdk>=0.1.0->guardkit-py==0.1.0) (41.0.7)
Downloading claude_agent_sdk-0.1.39-py3-none-manylinux_2_17_aarch64.whl (70.0 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 70.0/70.0 MB 5.5 MB/s eta 0:00:00
Downloading mcp-1.26.0-py3-none-any.whl (233 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 233.6/233.6 kB 5.8 MB/s eta 0:00:00
Downloading httpx_sse-0.4.3-py3-none-any.whl (9.0 kB)
Downloading jsonschema-4.26.0-py3-none-any.whl (90 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 90.6/90.6 kB 9.5 MB/s eta 0:00:00
Downloading pydantic_settings-2.13.1-py3-none-any.whl (58 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 58.9/58.9 kB 7.9 MB/s eta 0:00:00
Downloading pyjwt-2.11.0-py3-none-any.whl (28 kB)
Downloading python_multipart-0.0.22-py3-none-any.whl (24 kB)
Downloading sse_starlette-3.2.0-py3-none-any.whl (12 kB)
Downloading starlette-0.52.1-py3-none-any.whl (74 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 74.3/74.3 kB 6.3 MB/s eta 0:00:00
Downloading uvicorn-0.41.0-py3-none-any.whl (68 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 68.8/68.8 kB 6.2 MB/s eta 0:00:00
Downloading jsonschema_specifications-2025.9.1-py3-none-any.whl (18 kB)
Downloading referencing-0.37.0-py3-none-any.whl (26 kB)
Downloading rpds_py-0.30.0-cp312-cp312-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (390 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 390.8/390.8 kB 4.9 MB/s eta 0:00:00
Checking if build backend supports build_editable ... done
Building wheels for collected packages: guardkit-py
  Building editable for guardkit-py (pyproject.toml) ... done
  Created wheel for guardkit-py: filename=guardkit_py-0.1.0-py3-none-any.whl size=9010 sha256=16605e1fb39f3e00a06ecd299996c39a9f6ad99e4b3c93742026dec450223b3b
  Stored in directory: /tmp/pip-ephem-wheel-cache-8n0hj9cu/wheels/48/fe/10/ecf9d7ff60251264de584539a3a2fe684426e90409b5a9d2a7
Successfully built guardkit-py
Installing collected packages: uvicorn, rpds-py, python-multipart, pyjwt, httpx-sse, starlette, referencing, sse-starlette, pydantic-settings, jsonschema-specifications, jsonschema, mcp, guardkit-py, claude-agent-sdk
  WARNING: The script uvicorn is installed in '/home/richardwoollcott/.local/bin' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
  WARNING: The script jsonschema is installed in '/home/richardwoollcott/.local/bin' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
  WARNING: The script mcp is installed in '/home/richardwoollcott/.local/bin' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
  WARNING: The script guardkit-py is installed in '/home/richardwoollcott/.local/bin' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
Successfully installed claude-agent-sdk-0.1.39 guardkit-py-0.1.0 httpx-sse-0.4.3 jsonschema-4.26.0 jsonschema-specifications-2025.9.1 mcp-1.26.0 pydantic-settings-2.13.1 pyjwt-2.11.0 python-multipart-0.0.22 referencing-0.37.0 rpds-py-0.30.0 sse-starlette-3.2.0 starlette-0.52.1 uvicorn-0.41.0
✓ guardkit package installed successfully (with AutoBuild)
✓ guardkit Python package is importable
✓ Claude Agent SDK is available (AutoBuild ready)
⚠ guardkit-py CLI not found in PATH
ℹ You may need to restart your shell or add ~/.local/bin to PATH
⚠ Found existing installations: .claude
ℹ Creating backup of .claude at /home/richardwoollcott/.claude.backup.20260222_122430
✓ Backup created: /home/richardwoollcott/.claude.backup.20260222_122430
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
✓ Shell integration added to /home/richardwoollcott/.bashrc
ℹ Please restart your shell or run: source /home/richardwoollcott/.bashrc
ℹ Creating global configuration...
✓ Global configuration created
ℹ Installing shell completions...
✓ Shell completions installed
ℹ Setting up version management...
ln: failed to create symbolic link '/home/richardwoollcott/.agentecflow/versions/latest' -> '': No such file or directory
richardwoollcott@promaxgb10-41b1:~/Projects/appmilla_github/guardkit/installer/scripts$ 
