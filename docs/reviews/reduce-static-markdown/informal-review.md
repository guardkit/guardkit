Review Summary: guardkit init Output & Graphiti Content
What worked well
Template application - 3 agents, 12 rules, 5 commands, 2 configs copied correctly (no -ext.md files)
Config copy (--copy-graphiti-from) - FalkorDB connection settings properly copied with project_id replaced to vllm-profiling
FalkorDB connection - Successfully connected to whitestocks:6379 via Tailscale
vLLM inference - LLM on promaxgb10-41b1:8000 and embeddings on promaxgb10-41b1:8001 both worked
Project overview seeding - 7 episodes completed, 10 facts returned when queried
Issues found
1. Role constraints & implementation modes: 0 query results
The seeding log reported success:


OK role_constraints: Seeded Player and Coach constraints
OK implementation_modes: Seeded 3 modes
But queries returned 0 results. Root cause: These are system-scoped groups (unprefixed group IDs: role_constraints, implementation_modes), but the query was searching in project-prefixed groups (vllm-profiling__product_knowledge).

The correct group IDs to query are:

role_constraints (not vllm-profiling__role_constraints)
implementation_modes (not vllm-profiling__implementation_modes)
This is by design in constants.py - system groups are shared across all projects.

2. FalkorDB "Max pending queries exceeded"
During episodes 3-4, FalkorDB returned capacity errors. The seeding continued and recovered but this may have caused partial data loss in those episodes. This is a FalkorDB concurrency limit issue - graphiti-core fires many parallel queries during entity extraction.

Mitigation options:

Increase FalkorDB MAX_QUEUED_QUERIES setting on the Synology container
Add query throttling in graphiti-core (upstream change)
3. Step 2.5 template sync "incomplete results"
The template sync step reported incomplete results. This likely means some template content couldn't be synced to Graphiti, possibly related to the FalkorDB capacity issues during earlier seeding.

4. ~~OPENAI_API_KEY required by graphiti-core~~ **[RESOLVED]**
~~Even when using vLLM providers, graphiti-core's Graphiti() constructor requires OPENAI_API_KEY in the environment. Current workaround: OPENAI_API_KEY=dummy. This is an upstream graphiti-core issue - the key is validated at constructor time but never used when vLLM providers are configured.~~ Verified unnecessary — GuardKit injects custom LLM/embedding clients, bypassing the default OpenAI constructor. No `OPENAI_API_KEY` needed for vLLM configurations.

5. "Connection closed by server" during index building
FalkorDB closed the connection during build_indices_and_constraints(). Non-blocking - the query client recovered.

Recommendations
Query fix: When searching role_constraints and implementation_modes, use the unprefixed group IDs directly - this is working as designed
FalkorDB tuning: Increase max pending queries on the Synology FalkorDB container to handle graphiti-core's parallel query pattern
~~OPENAI_API_KEY: Set OPENAI_API_KEY=dummy in project .env when using vLLM to avoid the constructor error~~ **[RESOLVED]** Verified unnecessary — GuardKit's `GraphitiClient.initialize()` injects custom LLM/embedding clients that bypass the OpenAI constructor entirely when `llm_provider != "openai"`. No dummy key needed. See TASK-REV-21D3 review report for evidence chain.
TASK-4B7F Status
The --copy-graphiti / --copy-graphiti-from feature is functionally complete:

Click option split works correctly
Config loading from .guardkit/graphiti.yaml fixed
Auto-discovery walks parent dirs; explicit path for siblings
All 83 tests pass
Would you like me to run /task-complete TASK-4B7F, or would you prefer to address the FalkorDB capacity / OPENAI_API_KEY issues first?