Last login: Wed Jun  3 11:56:58 on ttys009
richardwoollcott@Mac ~ % cd Projects
richardwoollcott@Mac Projects % cd app
cd: no such file or directory: app
richardwoollcott@Mac Projects % cd appmilla_github
richardwoollcott@Mac appmilla_github % cd guardkit
richardwoollcott@Mac guardkit % python scripts/canary_validation_runner.py --variant 009a --dry-run
Run plan (variant=009a, 12 runs, 0 already recorded):
  results → .guardkit/autobuild/TASK-HMIG-009A-canary-results.json
  artefacts → .guardkit/autobuild/TASK-HMIG-009A-canary/
  [TODO] sdk         TASK-FIX-A7D3         rep 1  model=qwen36-workhorse
  [TODO] sdk         TASK-FIX-A7D3         rep 2  model=qwen36-workhorse
  [TODO] sdk         TASK-FIX-A7D3         rep 3  model=qwen36-workhorse
  [TODO] sdk         TASK-DOC-267D         rep 1  model=qwen36-workhorse
  [TODO] sdk         TASK-DOC-267D         rep 2  model=qwen36-workhorse
  [TODO] sdk         TASK-DOC-267D         rep 3  model=qwen36-workhorse
  [TODO] langgraph   TASK-FIX-A7D3         rep 1  model=openai:qwen36-workhorse
  [TODO] langgraph   TASK-FIX-A7D3         rep 2  model=openai:qwen36-workhorse
  [TODO] langgraph   TASK-FIX-A7D3         rep 3  model=openai:qwen36-workhorse
  [TODO] langgraph   TASK-DOC-267D         rep 1  model=openai:qwen36-workhorse
  [TODO] langgraph   TASK-DOC-267D         rep 2  model=openai:qwen36-workhorse
  [TODO] langgraph   TASK-DOC-267D         rep 3  model=openai:qwen36-workhorse
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit % ps aux | grep -E "canary_validation_runner|autobuild task" | grep -v grep
richardwoollcott 23338   0.0  0.0 411818288  40944 s000  S+    5:38PM   0:11.66 /Library/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python /Library/Frameworks/Python.framework/Versions/3.14/bin/guardkit-py autobuild task TASK-FIX-A7D3 --max-turns 5 --sdk-timeout 1200 --model qwen36-workhorse --no-pre-loop
richardwoollcott 23335   0.0  0.0 411533824   7232 s000  S+    5:38PM   0:00.05 /Library/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python scripts/canary_validation_runner.py --variant 009a
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit % ls -la .guardkit/autobuild/TASK-HMIG-009A-canary/sdk/TASK-FIX-A7D3/run_1/ 2>/dev/null
total 80
drwxr-xr-x@ 4 richardwoollcott  staff    128 Jun  3 17:38 .
drwxr-xr-x@ 3 richardwoollcott  staff     96 Jun  3 17:38 ..
-rw-r--r--@ 1 richardwoollcott  staff  34656 Jun  3 18:48 stderr.log
-rw-r--r--@ 1 richardwoollcott  staff   3135 Jun  3 18:11 stdout.log
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit % tail -50 .guardkit/autobuild/TASK-HMIG-009A-canary/sdk/TASK-FIX-A7D3/run_1/stderr.log 2>/dev/null
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (930s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (960s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (990s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1020s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1050s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1080s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1110s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1140s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1170s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1200s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1230s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1260s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1290s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1320s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1350s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1380s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1410s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1440s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1470s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1500s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1530s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1560s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1590s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1620s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1650s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1680s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1710s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1740s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1770s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1800s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1830s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1860s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1890s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description', 'run_in_background', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description', 'run_in_background', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1920s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock TaskOutput input keys: ['block', 'task_id', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1950s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1980s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2010s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2040s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2070s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2100s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2130s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2160s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2190s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2220s elapsed)
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit % curl -s --max-time 5 http://promaxgb10-41b1:9000/v1/models | jq '.data[].id' | grep workhorse

"qwen36-workhorse"
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit % tail -f .guardkit/autobuild/TASK-HMIG-009A-canary/sdk/TASK-FIX-A7D3/run_2/stderr.log
tail: .guardkit/autobuild/TASK-HMIG-009A-canary/sdk/TASK-FIX-A7D3/run_2/stderr.log: No such file or directory
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit % tail -50 .guardkit/autobuild/TASK-HMIG-009A-canary/sdk/TASK-FIX-A7D3/run_1/stderr.log 2>/dev/null
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1800s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1830s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1860s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1890s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description', 'run_in_background', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description', 'run_in_background', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1920s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock TaskOutput input keys: ['block', 'task_id', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1950s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1980s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2010s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2040s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2070s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2100s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2130s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2160s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2190s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2220s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2250s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2280s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2310s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2340s elapsed)
WARNING:guardkit.orchestrator.specialist_invocations:run_specialist(test-orchestrator) failed for TASK-FIX-A7D3: SDKTimeoutError: Agent invocation exceeded 2340s timeout
INFO:guardkit.orchestrator.agent_invoker:Injected orchestrator specialist records into /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/task_work_results.json (merged=2, validation=violation)
INFO:guardkit.orchestrator.progress:[2026-06-03T17:50:12.733Z] Started turn 1: Coach Validation
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Loading Coach context (turn 1)...
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Coach context categories: ['similar_outcomes', 'relevant_patterns', 'architecture_context', 'warnings', 'role_constraints', 'turn_states', 'implementation_modes']
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Context loaded in 1.2s
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Coach context: 7 categories, 3121/5200 tokens
INFO:guardkit.orchestrator.autobuild:Using LLM Coach (primary) for TASK-FIX-A7D3 turn 1
INFO:guardkit.orchestrator.autobuild:[Graphiti] Coach context provided: 650 chars
INFO:guardkit.orchestrator.quality_gates.coach_validator:Quality gate evaluation complete: tests=True (required=True), coverage=True (required=True), arch=True (required=False), audit=False (required=True), ALL_PASSED=False
INFO:guardkit.orchestrator.quality_gates.coach_validator:gather_evidence: quality gates failed for TASK-FIX-A7D3; downstream (requirements, independent tests) skipped.
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] SDK timeout: 2340s (base=1200s, mode=task-work x1.5, complexity=3 x1.3)
INFO:guardkit.orchestrator.sdk_debug:sdk_debug: preserved coach prompt for TASK-FIX-A7D3 turn 1 -> /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/sdk_debug/turn_1/coach
INFO:claude_agent_sdk._internal.transport.subprocess_cli:Using bundled Claude Code CLI: /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (30s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (60s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (90s elapsed)
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit % tail -50 .guardkit/autobuild/TASK-HMIG-009A-canary/sdk/TASK-FIX-A7D3/run_1/stderr.log 2>/dev/null
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1830s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1860s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1890s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description', 'run_in_background', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description', 'run_in_background', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1920s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock TaskOutput input keys: ['block', 'task_id', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1950s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1980s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2010s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2040s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2070s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2100s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2130s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2160s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2190s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2220s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2250s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2280s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2310s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2340s elapsed)
WARNING:guardkit.orchestrator.specialist_invocations:run_specialist(test-orchestrator) failed for TASK-FIX-A7D3: SDKTimeoutError: Agent invocation exceeded 2340s timeout
INFO:guardkit.orchestrator.agent_invoker:Injected orchestrator specialist records into /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/task_work_results.json (merged=2, validation=violation)
INFO:guardkit.orchestrator.progress:[2026-06-03T17:50:12.733Z] Started turn 1: Coach Validation
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Loading Coach context (turn 1)...
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Coach context categories: ['similar_outcomes', 'relevant_patterns', 'architecture_context', 'warnings', 'role_constraints', 'turn_states', 'implementation_modes']
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Context loaded in 1.2s
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Coach context: 7 categories, 3121/5200 tokens
INFO:guardkit.orchestrator.autobuild:Using LLM Coach (primary) for TASK-FIX-A7D3 turn 1
INFO:guardkit.orchestrator.autobuild:[Graphiti] Coach context provided: 650 chars
INFO:guardkit.orchestrator.quality_gates.coach_validator:Quality gate evaluation complete: tests=True (required=True), coverage=True (required=True), arch=True (required=False), audit=False (required=True), ALL_PASSED=False
INFO:guardkit.orchestrator.quality_gates.coach_validator:gather_evidence: quality gates failed for TASK-FIX-A7D3; downstream (requirements, independent tests) skipped.
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] SDK timeout: 2340s (base=1200s, mode=task-work x1.5, complexity=3 x1.3)
INFO:guardkit.orchestrator.sdk_debug:sdk_debug: preserved coach prompt for TASK-FIX-A7D3 turn 1 -> /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/sdk_debug/turn_1/coach
INFO:claude_agent_sdk._internal.transport.subprocess_cli:Using bundled Claude Code CLI: /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (30s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (60s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (90s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (120s elapsed)
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit % tail -50 .guardkit/autobuild/TASK-HMIG-009A-canary/sdk/TASK-FIX-A7D3/run_1/stderr.log 2>/dev/null
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1860s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1890s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description', 'run_in_background', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description', 'run_in_background', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1920s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock TaskOutput input keys: ['block', 'task_id', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1950s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1980s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2010s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2040s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2070s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2100s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2130s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2160s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2190s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2220s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2250s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2280s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2310s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2340s elapsed)
WARNING:guardkit.orchestrator.specialist_invocations:run_specialist(test-orchestrator) failed for TASK-FIX-A7D3: SDKTimeoutError: Agent invocation exceeded 2340s timeout
INFO:guardkit.orchestrator.agent_invoker:Injected orchestrator specialist records into /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/task_work_results.json (merged=2, validation=violation)
INFO:guardkit.orchestrator.progress:[2026-06-03T17:50:12.733Z] Started turn 1: Coach Validation
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Loading Coach context (turn 1)...
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Coach context categories: ['similar_outcomes', 'relevant_patterns', 'architecture_context', 'warnings', 'role_constraints', 'turn_states', 'implementation_modes']
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Context loaded in 1.2s
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Coach context: 7 categories, 3121/5200 tokens
INFO:guardkit.orchestrator.autobuild:Using LLM Coach (primary) for TASK-FIX-A7D3 turn 1
INFO:guardkit.orchestrator.autobuild:[Graphiti] Coach context provided: 650 chars
INFO:guardkit.orchestrator.quality_gates.coach_validator:Quality gate evaluation complete: tests=True (required=True), coverage=True (required=True), arch=True (required=False), audit=False (required=True), ALL_PASSED=False
INFO:guardkit.orchestrator.quality_gates.coach_validator:gather_evidence: quality gates failed for TASK-FIX-A7D3; downstream (requirements, independent tests) skipped.
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] SDK timeout: 2340s (base=1200s, mode=task-work x1.5, complexity=3 x1.3)
INFO:guardkit.orchestrator.sdk_debug:sdk_debug: preserved coach prompt for TASK-FIX-A7D3 turn 1 -> /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/sdk_debug/turn_1/coach
INFO:claude_agent_sdk._internal.transport.subprocess_cli:Using bundled Claude Code CLI: /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (30s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (60s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (90s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (120s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (150s elapsed)
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit % tail -50 .guardkit/autobuild/TASK-HMIG-009A-canary/sdk/TASK-FIX-A7D3/run_1/stderr.log 2>/dev/null
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1860s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1890s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description', 'run_in_background', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description', 'run_in_background', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1920s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock TaskOutput input keys: ['block', 'task_id', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1950s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1980s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2010s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2040s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2070s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2100s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2130s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2160s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2190s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2220s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2250s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2280s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2310s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2340s elapsed)
WARNING:guardkit.orchestrator.specialist_invocations:run_specialist(test-orchestrator) failed for TASK-FIX-A7D3: SDKTimeoutError: Agent invocation exceeded 2340s timeout
INFO:guardkit.orchestrator.agent_invoker:Injected orchestrator specialist records into /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/task_work_results.json (merged=2, validation=violation)
INFO:guardkit.orchestrator.progress:[2026-06-03T17:50:12.733Z] Started turn 1: Coach Validation
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Loading Coach context (turn 1)...
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Coach context categories: ['similar_outcomes', 'relevant_patterns', 'architecture_context', 'warnings', 'role_constraints', 'turn_states', 'implementation_modes']
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Context loaded in 1.2s
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Coach context: 7 categories, 3121/5200 tokens
INFO:guardkit.orchestrator.autobuild:Using LLM Coach (primary) for TASK-FIX-A7D3 turn 1
INFO:guardkit.orchestrator.autobuild:[Graphiti] Coach context provided: 650 chars
INFO:guardkit.orchestrator.quality_gates.coach_validator:Quality gate evaluation complete: tests=True (required=True), coverage=True (required=True), arch=True (required=False), audit=False (required=True), ALL_PASSED=False
INFO:guardkit.orchestrator.quality_gates.coach_validator:gather_evidence: quality gates failed for TASK-FIX-A7D3; downstream (requirements, independent tests) skipped.
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] SDK timeout: 2340s (base=1200s, mode=task-work x1.5, complexity=3 x1.3)
INFO:guardkit.orchestrator.sdk_debug:sdk_debug: preserved coach prompt for TASK-FIX-A7D3 turn 1 -> /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/sdk_debug/turn_1/coach
INFO:claude_agent_sdk._internal.transport.subprocess_cli:Using bundled Claude Code CLI: /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (30s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (60s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (90s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (120s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (150s elapsed)
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit % tail -f .guardkit/autobuild/TASK-HMIG-009A-canary/sdk/TASK-FIX-A7D3/run_2/stderr.log
tail: .guardkit/autobuild/TASK-HMIG-009A-canary/sdk/TASK-FIX-A7D3/run_2/stderr.log: No such file or directory
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit %
richardwoollcott@Mac guardkit % tail -f .guardkit/autobuild/TASK-HMIG-009A-canary/sdk/TASK-FIX-A7D3/run_1/stderr.log
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Setting sources: ['project']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Permission mode: acceptEdits
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Max turns: 150
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] SDK timeout: 2340s
INFO:claude_agent_sdk._internal.transport.subprocess_cli:Using bundled Claude Code CLI: /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (30s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (60s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (90s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (120s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (150s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] ToolUseBlock Write input keys: ['file_path', 'content']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (180s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] SDK completed: turns=9
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Message summary: total=25, assistant=13, tools=8, results=1
WARNING:guardkit.orchestrator.agent_invoker:BDD oracle running against system pytest; worktree-local imports may fail (no .venv/bin/python[3] under /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3).
INFO:guardkit.orchestrator.agent_invoker:BDD oracle invoking run_bdd_for_task for TASK-FIX-A7D3 with python_executable=None
INFO:guardkit.orchestrator.agent_invoker:Wrote task_work_results.json to /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/task_work_results.json
INFO:guardkit.orchestrator.agent_invoker:task-work completed successfully for TASK-FIX-A7D3
INFO:guardkit.orchestrator.agent_invoker:Created Player report from task_work_results.json for TASK-FIX-A7D3 turn 2
INFO:guardkit.orchestrator.agent_invoker:Git detection added: 19 modified, 0 created files for TASK-FIX-A7D3
INFO:guardkit.orchestrator.agent_invoker:Recovered 5 completion_promises from agent-written player report for TASK-FIX-A7D3
INFO:guardkit.orchestrator.agent_invoker:Recovered 5 requirements_addressed from agent-written player report for TASK-FIX-A7D3
INFO:guardkit.orchestrator.agent_invoker:Filtered 2 orchestrator-induced ghost path(s) for TASK-FIX-A7D3: ['/Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/player_turn_2.json', 'tasks/design_approved/TASK-FIX-A7D3-fix-python-scoping-issue-with-json-import-in-enhancer-py.md']
INFO:guardkit.orchestrator.agent_invoker:Written Player report to /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/player_turn_2.json
INFO:guardkit.orchestrator.agent_invoker:Updated task_work_results.json with enriched data for TASK-FIX-A7D3
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] SDK invocation complete: 185.1s, 9 SDK turns (20.6s/turn avg)
INFO:guardkit.orchestrator.progress:[2026-06-03T17:56:44.785Z] Completed turn 2: success - 0 files created, 18 modified, 0 tests (passing)
INFO:guardkit.orchestrator.autobuild:Dropped 1 stale requirements from carry-forward
INFO:guardkit.orchestrator.autobuild:Cumulative requirements_addressed: 5 criteria (current turn: 5, carried: 0)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Mode: task-work (auto-selected, complexity=3, task_type='')
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] SDK timeout: 2340s (base=1200s, mode=task-work x1.5, complexity=3 x1.3)
INFO:guardkit.orchestrator.sdk_debug:sdk_debug: preserved player prompt for TASK-FIX-A7D3 turn 2 -> /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/sdk_debug/turn_2
INFO:claude_agent_sdk._internal.transport.subprocess_cli:Using bundled Claude Code CLI: /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (30s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (60s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (90s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (120s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (150s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (180s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (210s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (240s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (270s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (300s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (330s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock TaskOutput input keys: ['block', 'task_id', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (360s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (390s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (420s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (450s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (480s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (510s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (540s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (570s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (600s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] SDK timeout: 2340s (base=1200s, mode=task-work x1.5, complexity=3 x1.3)
INFO:guardkit.orchestrator.sdk_debug:sdk_debug: preserved coach prompt for TASK-FIX-A7D3 turn 2 -> /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/sdk_debug/turn_2/coach
INFO:claude_agent_sdk._internal.transport.subprocess_cli:Using bundled Claude Code CLI: /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation in progress... (30s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock TodoWrite input keys: ['todos']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation in progress... (60s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock TodoWrite input keys: ['todos']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation in progress... (90s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation in progress... (120s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock TodoWrite input keys: ['todos']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Read input keys: ['file_path']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation in progress... (150s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Read input keys: ['file_path', 'limit', 'offset']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Read input keys: ['file_path', 'limit', 'offset']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock TodoWrite input keys: ['todos']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation in progress... (180s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Read input keys: ['file_path']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock TodoWrite input keys: ['todos']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation in progress... (210s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Read input keys: ['file_path']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock TodoWrite input keys: ['todos']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Read input keys: ['file_path']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation in progress... (240s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation in progress... (270s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Edit input keys: ['file_path', 'new_string', 'old_string', 'replace_all']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock TodoWrite input keys: ['todos']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation in progress... (300s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:code-reviewer invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:Injected orchestrator specialist records into /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/task_work_results.json (merged=2, validation=violation)
INFO:guardkit.orchestrator.progress:[2026-06-03T18:12:28.789Z] Started turn 2: Coach Validation
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Loading Coach context (turn 2)...
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Task <Task pending name='Task-243' coro=<semaphore_gather.<locals>._wrap_coroutine() running at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/helpers.py:131> cb=[gather.<locals>._done_callback() at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/tasks.py:810]> got Future <Future pending> attached to a different loop
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    WITH rel AS e, score, startNode(rel) AS n, endNode(rel) AS m

            WITH e, score, n, m
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'query': ' (Task | Fix | Python | scoping | issue | json | import | enhancer | py)', 'limit': 20, 'routing_': 'r'}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Task <Task pending name='Task-244' coro=<semaphore_gather.<locals>._wrap_coroutine() running at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/helpers.py:131> cb=[gather.<locals>._done_callback() at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/tasks.py:810]> got Future <Future pending> attached to a different loop

        MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity)

            WITH DISTINCT e, n, m, (2 - vec.cosineDistance(e.fact_embedding, vecf32($search_vector)))/2 AS score
            WHERE score > $min_score
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'search_vector': [-0.019678272306919098, 0.04145437479019165, -0.15208914875984192, -0.08751127868890762, 0.060685936361551285, -0.011536049656569958, -0.0356954000890255, 0.06326451152563095, 0.005898250732570887, 0.03596508875489235, -0.0460776761174202, 0.059481438249349594, 0.0731963962316513, -0.0035015461035072803, -0.010767459869384766, 0.0026188043411821127, 0.042661190032958984, -0.04567542299628258, 0.005363617092370987, 0.04486007243394852, 0.017174692824482918, -0.031202269718050957, 0.016036447137594223, -0.0022920984774827957, 0.08285566419363022, 0.012536974623799324, 0.04308679699897766, 0.017869723960757256, -0.05449867248535156, 0.06715884059667587, -0.026934392750263214, 0.033227503299713135, -0.04078983888030052, 0.003484932938590646, -0.025479862466454506, -0.02652379311621189, 0.06887561082839966, 0.0005733506986871362, -0.029584350064396858, 0.03562229871749878, -0.001539326854981482, -0.020368313416838646, 0.023740852251648903, -0.03915613889694214, 0.01963983289897442, -0.004860177170485258, 0.08341535180807114, -0.00909666158258915, 0.03961418941617012, -0.02264111116528511, -0.004619008861482143, 0.035068050026893616, -0.014536296017467976, -0.04993395879864693, 0.06013113632798195, 0.0559917688369751, -0.013428007252514362, 0.0017108998727053404, 0.014681867323815823, 0.022310331463813782, 0.03381912782788277, 0.061756398528814316, -0.02037772163748741, 0.07045856863260269, 0.00499360729008913, -0.032459888607263565, 0.023036682978272438, 0.04308941960334778, 0.0240500345826149, -0.028242910280823708, -0.0029579228721559048, -0.040853410959243774, 0.008793892338871956, 0.023262470960617065, -0.03967183828353882, -0.018579205498099327, -0.06695448607206345, -0.002489942591637373, -0.02617836929857731, 0.045291196554899216, 0.004710789304226637, 0.011663787998259068, -0.0036145183257758617, -0.002416863339021802, 0.04015050455927849, -0.03343840315937996, -0.011631639674305916, -0.00844602845609188, -0.016957048326730728, 0.007057918701320887, 0.02226279303431511, 0.002995438873767853, 0.0018111851532012224, 0.0015182229690253735, -0.03973628953099251, 0.02589903399348259, -0.0006272330647334456, 0.011767647229135036, -0.0492384172976017, -0.058542363345623016, -0.014917286112904549, -0.012216508388519287, 0.013676203787326813, -0.058566536754369736, 0.03772224858403206, 0.05964180827140808, 0.0423254668712616, 0.022949479520320892, -0.022774117067456245, -0.06008358672261238, -0.03383133187890053, 0.030198698863387108, 0.03560342267155647, -0.02526315115392208, 0.008249345235526562, -0.05359608680009842, 0.019221995025873184, 0.021092142909765244, 0.016274355351924896, 0.07800885289907455, 0.017908133566379547, -0.03679491952061653, 0.011676537804305553, 0.036793000996112823, -0.017211860045790672, 0.012664657086133957, -0.06798101216554642, -0.015494957566261292, 0.053091924637556076, -0.04097888618707657, -0.03503381088376045, -0.013990537263453007, -0.015718035399913788, 0.015308920294046402, 0.0068150050938129425, 0.018288258463144302, -0.027750765904784203, -0.05620942637324333, 0.05034608766436577, 0.00658156955614686, 0.037913836538791656, 0.024165406823158264, -0.005590274930000305, 0.005106118507683277, -0.021129272878170013, -0.06092797964811325, 0.03375286981463432, -0.024518007412552834, 0.015498638153076172, -0.03766050934791565, 0.010379175655543804, 0.020013928413391113, 0.017530186101794243, 0.020746007561683655, 0.03018259070813656, -0.04491570591926575, 0.02726386860013008, 0.01579068787395954, 0.034235142171382904, 0.012131059542298317, 0.05927712097764015, 0.029664726927876472, -0.040221668779850006, 0.06505591422319412, 0.013997580856084824, 0.006343886721879244, 0.04485567286610603, -0.023017926141619682, -0.016303986310958862, 0.05887455493211746, 0.003787028370425105, -0.06779701262712479, -0.005519767291843891, -0.04536237567663193, -0.02908109314739704, 0.06589078158140182, 0.009105178527534008, -0.048932116478681564, 0.0702362060546875, 0.015577378682792187, 0.022807935252785683, -0.05566418915987015, 0.05768178403377533, 0.024182241410017014, -0.07004685699939728, -0.009858010336756706, -0.01198254432529211, -0.03954509273171425, 0.01700400933623314, -0.01538708247244358, 0.07074327766895294, 0.027945393696427345, -0.0715738981962204, -0.06478138267993927, -0.06457969546318054, -0.03879387676715851, 0.04865585267543793, -0.06224197521805763, 0.01791718602180481, -0.056931640952825546, -0.04821635037660599, -0.016800135374069214, -0.014499199576675892, -0.00016610653256066144, -0.06166314333677292, -0.013199149630963802, 0.002707129344344139, 0.028006387874484062, -0.03186313807964325, 0.027730202302336693, 0.03960445895791054, -0.026549363508820534, -0.0013489174889400601, 0.022544309496879578, -0.006144820246845484, 0.0014451746828854084, 0.021434560418128967, 0.009937262162566185, 0.00638539670035243, 0.04972505569458008, 0.010563386604189873, 0.03476741909980774, 0.0353098101913929, 0.008606175892055035, 0.05145268142223358, 0.004322201479226351, 0.007664940785616636, -0.041306138038635254, -0.035920560359954834, -0.013973681256175041, -0.023324865847826004, -0.033298611640930176, 0.027322586625814438, 2.2270212866715156e-05, 0.03547924757003784, -0.015216288156807423, 0.017451131716370583, 0.044429097324609756, -0.027702681720256805, 0.005388504825532436, -0.0013571048621088266, 0.03524407744407654, -0.023104004561901093, 0.008536252193152905, -0.01720883883535862, 0.02564302645623684, 0.03022625483572483, -0.01345042884349823, 0.026601038873195648, 0.04824414104223251, -0.034497812390327454, 0.00541694276034832, 0.02385224774479866, 0.048989731818437576, 0.019454237073659897, -0.058079589158296585, 0.032224103808403015, 0.02340812236070633, -0.013453795574605465, -0.03828400373458862, 0.00019668388995341957, -0.05886334553360939, 0.02829950489103794, -0.011681304313242435, -0.02894294075667858, -0.0156210632994771, -0.025587614625692368, -0.005355904344469309, -0.008415039628744125, 0.008364710956811905, -0.020933544263243675, 0.013845553621649742, 0.011375073343515396, 0.0034024554770439863, 0.013591719791293144, 0.03831282630562782, 0.006789857987314463, -0.016561930999159813, -0.0077067469246685505, 0.017976976931095123, -0.044922471046447754, -0.09317181259393692, -0.009833413176238537, 0.0019290000200271606, 0.008832037448883057, 0.04975416138768196, -0.005788398440927267, 0.02413789927959442, -0.006867791526019573, -0.030871326103806496, 0.0018034533131867647, -0.028147924691438675, -0.061592698097229004, 0.03471648693084717, 0.0029623613227158785, 0.04576379805803299, 0.04920250177383423, 0.0066710906103253365, 0.019879451021552086, -0.029847823083400726, 0.04213399812579155, 0.022378113120794296, 0.06034644693136215, 0.018210720270872116, -0.052402056753635406, -0.06233320012688637, 0.02748517319560051, 0.0009044610778801143, 0.03394578769803047, -0.0025600087828934193, -0.07710444182157516, -0.026959320530295372, -0.04725588113069534, 0.09587374329566956, -0.004505184479057789, 0.06266964226961136, 0.011928888969123363, 0.026125216856598854, 0.020802753046154976, -0.03790655732154846, 0.008611896075308323, -0.009999945759773254, 0.0008124966407194734, 0.0023372818250209093, -0.013930312357842922, 0.0445791594684124, -0.03707464411854744, 0.005865194834768772, -0.027623893693089485, -0.0051140510477125645, 0.03622030094265938, 0.029353415593504906, 0.014871746301651001, -0.049538563936948776, -0.0884135365486145, 0.039663538336753845, -0.006087770219892263, -0.005554589908570051, -0.018760336562991142, 0.04400838911533356, 0.06469032168388367, -0.027068525552749634, -0.014268585480749607, -0.03689954802393913, -0.04199261963367462, -0.07164203375577927, -0.02319754846394062, -0.022304972633719444, 0.06034821271896362, 0.01234059315174818, -0.05015625059604645, 0.026312967762351036, 0.024602733552455902, -0.013165849260985851, 0.026101354509592056, -0.00039741327054798603, 0.045131612569093704, -0.0011586755281314254, -0.016506563872098923, 0.008335383608937263, 0.08420206606388092, 0.007974393665790558, 0.01806117594242096, -0.04338707774877548, 0.0017254726262763143, 0.013004262000322342, 0.035513974726200104, 0.0018105749040842056, 0.03481133654713631, 0.028410300612449646, -0.005521140526980162, -0.037166062742471695, -0.009727894328534603, -0.007575748022645712, 0.031769007444381714, 0.01591692864894867, -0.07149645686149597, -0.022819383069872856, -0.025556638836860657, 0.03829556331038475, 0.03599891439080238, -0.039620354771614075, -0.052856698632240295, 0.014543462544679642, 0.029836874455213547, 0.004911733325570822, 0.006350961048156023, -0.002845192328095436, 0.01151148322969675, 0.038910895586013794, 0.019080182537436485, -0.005964197684079409, 0.013235464692115784, 0.01979215256869793, 0.028337698429822922, -0.029424462467432022, 0.0345134362578392, 0.02685575745999813, -0.10838081687688828, 0.007495822850614786, -0.03945600241422653, -0.048700157552957535, 0.029617760330438614, -0.007066475227475166, -0.029409416019916534, -0.014822331257164478, 0.020348375663161278, 0.008603030815720558, -0.005156198516488075, 0.024565963074564934, -0.004429014399647713, 0.042246244847774506, 0.006228230893611908, -0.040713973343372345, -0.006633983459323645, -0.012441592290997505, 0.06379376351833344, 0.01138747576624155, -0.05108489841222763, -0.04554334282875061, 0.000258329208008945, 0.02675539255142212, 0.015998685732483864, 0.0045121400617063046, 0.035585757344961166, -0.025728177279233932, -0.0022018083836883307, 0.025854280218482018, 0.008726329542696476, -0.08949534595012665, -0.0042279548943042755, 0.014192483387887478, 0.0033121018204838037, -0.01194020640105009, -0.007336666341871023, 0.03430375084280968, 0.010065815411508083, 0.019571145996451378, 0.02486649714410305, 0.05963717773556709, -0.002381320344284177, -0.012897028587758541, -0.05677343159914017, -0.008045922964811325, 0.030109083279967308, 0.10458984225988388, 0.06349971145391464, -0.0902666375041008, -0.0014230748638510704, 0.047629497945308685, -0.005494843702763319, -0.06622440367937088, 0.02207377552986145, 0.03912592679262161, 0.08439141511917114, -0.010423487052321434, 0.0105659868568182, -0.03800560534000397, 0.005288270302116871, 0.005335751920938492, 0.005952857900410891, 0.027864310890436172, -0.07598649710416794, -0.017360499128699303, -0.014762528240680695, -0.017516929656267166, 0.030921051278710365, -0.009271711111068726, 0.04128511995077133, 0.05822055786848068, -0.0456681065261364, -0.021587887778878212, 0.032664477825164795, 0.005013902205973864, 0.024362962692975998, 0.052013691514730453, -0.012947490438818932, 0.007668015547096729, 0.012747621163725853, 0.009064197540283203, 0.005395033396780491, -0.06471613794565201, -0.02341090328991413, -0.03957385569810867, 0.006384128239005804, 0.023038262501358986, 0.016163893043994904, 0.031970616430044174, 0.008142382837831974, -0.010445505380630493, 0.020478740334510803, 0.02267698012292385, 0.0035674618557095528, -0.04390260949730873, 0.02594989724457264, 0.004782241769134998, -0.026361459866166115, 0.05352150648832321, 0.05303672328591347, -0.0018899120623245835, 0.040250685065984726, 0.014841049909591675, -0.04965448006987572, 0.034611135721206665, 0.029163721948862076, -0.0370374396443367, 0.06107928231358528, 0.01931428350508213, -0.024129332974553108, 0.013892723247408867, -0.057689569890499115, -0.019153200089931488, 0.06274314969778061, -0.0104749770835042, 0.06092853471636772, 0.014168822206556797, 0.020315535366535187, -0.00742214685305953, -0.07249875366687775, -0.02061198092997074, 0.06763654202222824, -0.019078969955444336, -0.025485828518867493, -0.037090715020895004, -0.03748273849487305, 0.06468653678894043, 0.05475500971078873, -0.025230998173356056, 0.03658314049243927, -0.03558206930756569, 0.00412721186876297, -0.02006283588707447, -0.040070950984954834, -0.03366212919354439, 0.021284595131874084, -0.09109087288379669, -0.0617571622133255, 0.029330993071198463, -0.023756109178066254, -0.012480301782488823, 0.052574045956134796, -0.006037478800863028, 0.007189587689936161, -0.018584808334708214, -0.024014504626393318, -0.039253927767276764, -0.0019910773262381554, 0.016578208655118942, 0.002754555782303214, -0.07257606834173203, 0.06669497489929199, -0.027288293465971947, 0.03512290492653847, -0.04012216255068779, 0.0006304704584181309, -0.056184276938438416, 0.026845846325159073, 0.01171874813735485, -0.007035360671579838, -0.11059699952602386, -0.0017737774178385735, 0.0008525890298187733, 0.035708170384168625, 0.039497245103120804, 0.009014977142214775, -0.009363487362861633, -0.04452665150165558, -0.015306168235838413, 0.007775279227644205, 0.0238527562469244, -0.049062952399253845, -0.029840851202607155, 0.009884377010166645, 0.007368407677859068, 0.01218915730714798, 0.026270395144820213, 0.03921155259013176, -0.02102232351899147, -0.046590857207775116, -0.03964143246412277, -0.006222231313586235, -0.017028534784913063, 0.012820009142160416, 0.06535062193870544, -0.021741028875112534, 0.031689491122961044, 0.019865790382027626, -0.037215035408735275, 0.026745876297354698, -0.0022958426270633936, 0.0018095504492521286, -0.025574250146746635, 0.024400917813181877, 0.0044356766156852245, -0.015722671523690224, 0.0007741103763692081, -0.06032382696866989, -0.027001703158020973, -0.04074037820100784, 0.001984398579224944, 0.019667888060212135, 0.0037972789723426104, 0.08036674559116364, -0.0016786562046036124, -0.01648603193461895, 0.03937697783112526, -0.03000270389020443, -0.013990301638841629, -0.04250183328986168, -0.051923878490924835, -0.016109390184283257, -0.03339380398392677, -0.013268408365547657, 0.0020023153629153967, 0.03535597398877144, -0.08207280933856964, 0.04318299517035484, 0.042447302490472794, -0.008383109234273434, -0.0263237152248621, -0.02173841930925846, -0.04972178116440773, 0.07675917446613312, -0.02865636721253395, 0.03968397527933121, -0.011468784883618355, -0.024121342226862907, -0.03269520029425621, 0.016022393479943275, 0.043653521686792374, -0.021612973883748055, 0.04812530800700188, -0.08864858001470566, -0.030017411336302757, -0.05985622480511665, 0.06505481153726578, -0.059853170067071915, 0.04449130594730377, -0.005449226126074791, 0.09018084406852722, 0.05151943489909172, -0.04078914597630501, -0.008794245310127735, 0.00486722681671381, -0.04789615795016289, -0.006356469821184874, 0.022389404475688934, 0.0336216501891613, -0.0006719402736052871, -0.005734316539019346, 0.07507745921611786, 0.05159412696957588, 0.05322299897670746, -0.012859235517680645, 0.024618180468678474, -0.011983484029769897, 0.014492410235106945, -0.029176125302910805, -0.046488311141729355, -0.008908496238291264, -0.008766178041696548, 0.016541115939617157, -0.04279477149248123, -0.005161352455615997, 0.03063373640179634, 0.004773003049194813, 0.015471100807189941, 0.04255279153585434, -0.06804932653903961, -0.022094659507274628, -0.002926690736785531, -0.01759984903037548, -0.03391116484999657, -0.016117988154292107, 0.02803482674062252, -0.005842387676239014, 0.029265668243169785, 0.02014891430735588, -0.015048426575958729, -0.0111753661185503, 0.006005946546792984, 0.003760319435968995, 0.010096371173858643, 0.004336421377956867, -0.021158697083592415, -0.07886983454227448, 0.019743654876947403, -0.04299156740307808, 0.006879636086523533, 0.004897196311503649, -0.03199371322989464, 0.012173089198768139, 0.006098099518567324, -0.010709347203373909, 0.029287517070770264, 0.008361488580703735, -0.02357981540262699, -0.035802002996206284, 0.0030663209035992622, 0.04971461743116379, 0.007869037799537182, 0.023053284734487534, 0.006221679039299488, 0.016018914058804512, -0.0639345571398735, 0.0014233884867280722, 0.01390507910400629, -0.03822048753499985, -0.000677775009535253, -0.032367583364248276, 0.0018110964447259903, 0.028008289635181427, -0.033390216529369354, 0.04089576378464699, 0.056676290929317474, 0.04725015163421631, 0.007858541794121265, -0.005909656640142202, -0.0374026782810688, 0.0009642730001360178, 0.04712258279323578, 0.015068107284605503, -0.09084785729646683, -0.0183014627546072, -0.010378052480518818, -0.011262909509241581, 0.01483835931867361, -0.06328458338975906, 0.03158270940184593, -0.039874304085969925, 0.005887739360332489, 0.013760249130427837, -0.08227024972438812, 0.05073750391602516, -0.03333717957139015, -0.01784328557550907, -0.09434085339307785, -0.04711056128144264, -0.03830826282501221, -0.01700424589216709, -0.04848729074001312, -0.04147587716579437, 0.024607349187135696, -0.023363759741187096, -0.04393063858151436, -0.004325236193835735, -0.0268165972083807, 0.017535211518406868, 0.045535337179899216, 0.008101162500679493, 0.027319978922605515, -0.01964757591485977, -0.0500638522207737, 0.04529197886586189, -0.011926586739718914, 0.011780159547924995, 0.022706450894474983, 0.026478933170437813, 0.08566772192716599, 0.04917490482330322, 0.044006217271089554, -0.020047280937433243, 0.03049284778535366, 0.005896560847759247, 0.010716656222939491, -0.005336425732821226, -0.032737407833337784, -0.028436297550797462], 'limit': 20, 'min_score': 0.6, 'routing_': 'r'}
WARNING:guardkit.knowledge.graphiti_client:Search request failed: Task <Task pending name='Task-243' coro=<semaphore_gather.<locals>._wrap_coroutine() running at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/helpers.py:131> cb=[gather.<locals>._done_callback() at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/tasks.py:810]> got Future <Future pending> attached to a different loop
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    WITH rel AS e, score, startNode(rel) AS n, endNode(rel) AS m
     WHERE e.group_id IN $group_ids
            WITH e, score, n, m
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'query': ' (Task | Fix | Python | scoping | issue | json | import | enhancer | py)', 'limit': 20, 'routing_': 'r', 'group_ids': ['guardkit__feature_specs']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop

        MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity)
     WHERE e.group_id IN $group_ids
            WITH DISTINCT e, n, m, (2 - vec.cosineDistance(e.fact_embedding, vecf32($search_vector)))/2 AS score
            WHERE score > $min_score
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'search_vector': [-0.019678272306919098, 0.04145437479019165, -0.15208914875984192, -0.08751127868890762, 0.060685936361551285, -0.011536049656569958, -0.0356954000890255, 0.06326451152563095, 0.005898250732570887, 0.03596508875489235, -0.0460776761174202, 0.059481438249349594, 0.0731963962316513, -0.0035015461035072803, -0.010767459869384766, 0.0026188043411821127, 0.042661190032958984, -0.04567542299628258, 0.005363617092370987, 0.04486007243394852, 0.017174692824482918, -0.031202269718050957, 0.016036447137594223, -0.0022920984774827957, 0.08285566419363022, 0.012536974623799324, 0.04308679699897766, 0.017869723960757256, -0.05449867248535156, 0.06715884059667587, -0.026934392750263214, 0.033227503299713135, -0.04078983888030052, 0.003484932938590646, -0.025479862466454506, -0.02652379311621189, 0.06887561082839966, 0.0005733506986871362, -0.029584350064396858, 0.03562229871749878, -0.001539326854981482, -0.020368313416838646, 0.023740852251648903, -0.03915613889694214, 0.01963983289897442, -0.004860177170485258, 0.08341535180807114, -0.00909666158258915, 0.03961418941617012, -0.02264111116528511, -0.004619008861482143, 0.035068050026893616, -0.014536296017467976, -0.04993395879864693, 0.06013113632798195, 0.0559917688369751, -0.013428007252514362, 0.0017108998727053404, 0.014681867323815823, 0.022310331463813782, 0.03381912782788277, 0.061756398528814316, -0.02037772163748741, 0.07045856863260269, 0.00499360729008913, -0.032459888607263565, 0.023036682978272438, 0.04308941960334778, 0.0240500345826149, -0.028242910280823708, -0.0029579228721559048, -0.040853410959243774, 0.008793892338871956, 0.023262470960617065, -0.03967183828353882, -0.018579205498099327, -0.06695448607206345, -0.002489942591637373, -0.02617836929857731, 0.045291196554899216, 0.004710789304226637, 0.011663787998259068, -0.0036145183257758617, -0.002416863339021802, 0.04015050455927849, -0.03343840315937996, -0.011631639674305916, -0.00844602845609188, -0.016957048326730728, 0.007057918701320887, 0.02226279303431511, 0.002995438873767853, 0.0018111851532012224, 0.0015182229690253735, -0.03973628953099251, 0.02589903399348259, -0.0006272330647334456, 0.011767647229135036, -0.0492384172976017, -0.058542363345623016, -0.014917286112904549, -0.012216508388519287, 0.013676203787326813, -0.058566536754369736, 0.03772224858403206, 0.05964180827140808, 0.0423254668712616, 0.022949479520320892, -0.022774117067456245, -0.06008358672261238, -0.03383133187890053, 0.030198698863387108, 0.03560342267155647, -0.02526315115392208, 0.008249345235526562, -0.05359608680009842, 0.019221995025873184, 0.021092142909765244, 0.016274355351924896, 0.07800885289907455, 0.017908133566379547, -0.03679491952061653, 0.011676537804305553, 0.036793000996112823, -0.017211860045790672, 0.012664657086133957, -0.06798101216554642, -0.015494957566261292, 0.053091924637556076, -0.04097888618707657, -0.03503381088376045, -0.013990537263453007, -0.015718035399913788, 0.015308920294046402, 0.0068150050938129425, 0.018288258463144302, -0.027750765904784203, -0.05620942637324333, 0.05034608766436577, 0.00658156955614686, 0.037913836538791656, 0.024165406823158264, -0.005590274930000305, 0.005106118507683277, -0.021129272878170013, -0.06092797964811325, 0.03375286981463432, -0.024518007412552834, 0.015498638153076172, -0.03766050934791565, 0.010379175655543804, 0.020013928413391113, 0.017530186101794243, 0.020746007561683655, 0.03018259070813656, -0.04491570591926575, 0.02726386860013008, 0.01579068787395954, 0.034235142171382904, 0.012131059542298317, 0.05927712097764015, 0.029664726927876472, -0.040221668779850006, 0.06505591422319412, 0.013997580856084824, 0.006343886721879244, 0.04485567286610603, -0.023017926141619682, -0.016303986310958862, 0.05887455493211746, 0.003787028370425105, -0.06779701262712479, -0.005519767291843891, -0.04536237567663193, -0.02908109314739704, 0.06589078158140182, 0.009105178527534008, -0.048932116478681564, 0.0702362060546875, 0.015577378682792187, 0.022807935252785683, -0.05566418915987015, 0.05768178403377533, 0.024182241410017014, -0.07004685699939728, -0.009858010336756706, -0.01198254432529211, -0.03954509273171425, 0.01700400933623314, -0.01538708247244358, 0.07074327766895294, 0.027945393696427345, -0.0715738981962204, -0.06478138267993927, -0.06457969546318054, -0.03879387676715851, 0.04865585267543793, -0.06224197521805763, 0.01791718602180481, -0.056931640952825546, -0.04821635037660599, -0.016800135374069214, -0.014499199576675892, -0.00016610653256066144, -0.06166314333677292, -0.013199149630963802, 0.002707129344344139, 0.028006387874484062, -0.03186313807964325, 0.027730202302336693, 0.03960445895791054, -0.026549363508820534, -0.0013489174889400601, 0.022544309496879578, -0.006144820246845484, 0.0014451746828854084, 0.021434560418128967, 0.009937262162566185, 0.00638539670035243, 0.04972505569458008, 0.010563386604189873, 0.03476741909980774, 0.0353098101913929, 0.008606175892055035, 0.05145268142223358, 0.004322201479226351, 0.007664940785616636, -0.041306138038635254, -0.035920560359954834, -0.013973681256175041, -0.023324865847826004, -0.033298611640930176, 0.027322586625814438, 2.2270212866715156e-05, 0.03547924757003784, -0.015216288156807423, 0.017451131716370583, 0.044429097324609756, -0.027702681720256805, 0.005388504825532436, -0.0013571048621088266, 0.03524407744407654, -0.023104004561901093, 0.008536252193152905, -0.01720883883535862, 0.02564302645623684, 0.03022625483572483, -0.01345042884349823, 0.026601038873195648, 0.04824414104223251, -0.034497812390327454, 0.00541694276034832, 0.02385224774479866, 0.048989731818437576, 0.019454237073659897, -0.058079589158296585, 0.032224103808403015, 0.02340812236070633, -0.013453795574605465, -0.03828400373458862, 0.00019668388995341957, -0.05886334553360939, 0.02829950489103794, -0.011681304313242435, -0.02894294075667858, -0.0156210632994771, -0.025587614625692368, -0.005355904344469309, -0.008415039628744125, 0.008364710956811905, -0.020933544263243675, 0.013845553621649742, 0.011375073343515396, 0.0034024554770439863, 0.013591719791293144, 0.03831282630562782, 0.006789857987314463, -0.016561930999159813, -0.0077067469246685505, 0.017976976931095123, -0.044922471046447754, -0.09317181259393692, -0.009833413176238537, 0.0019290000200271606, 0.008832037448883057, 0.04975416138768196, -0.005788398440927267, 0.02413789927959442, -0.006867791526019573, -0.030871326103806496, 0.0018034533131867647, -0.028147924691438675, -0.061592698097229004, 0.03471648693084717, 0.0029623613227158785, 0.04576379805803299, 0.04920250177383423, 0.0066710906103253365, 0.019879451021552086, -0.029847823083400726, 0.04213399812579155, 0.022378113120794296, 0.06034644693136215, 0.018210720270872116, -0.052402056753635406, -0.06233320012688637, 0.02748517319560051, 0.0009044610778801143, 0.03394578769803047, -0.0025600087828934193, -0.07710444182157516, -0.026959320530295372, -0.04725588113069534, 0.09587374329566956, -0.004505184479057789, 0.06266964226961136, 0.011928888969123363, 0.026125216856598854, 0.020802753046154976, -0.03790655732154846, 0.008611896075308323, -0.009999945759773254, 0.0008124966407194734, 0.0023372818250209093, -0.013930312357842922, 0.0445791594684124, -0.03707464411854744, 0.005865194834768772, -0.027623893693089485, -0.0051140510477125645, 0.03622030094265938, 0.029353415593504906, 0.014871746301651001, -0.049538563936948776, -0.0884135365486145, 0.039663538336753845, -0.006087770219892263, -0.005554589908570051, -0.018760336562991142, 0.04400838911533356, 0.06469032168388367, -0.027068525552749634, -0.014268585480749607, -0.03689954802393913, -0.04199261963367462, -0.07164203375577927, -0.02319754846394062, -0.022304972633719444, 0.06034821271896362, 0.01234059315174818, -0.05015625059604645, 0.026312967762351036, 0.024602733552455902, -0.013165849260985851, 0.026101354509592056, -0.00039741327054798603, 0.045131612569093704, -0.0011586755281314254, -0.016506563872098923, 0.008335383608937263, 0.08420206606388092, 0.007974393665790558, 0.01806117594242096, -0.04338707774877548, 0.0017254726262763143, 0.013004262000322342, 0.035513974726200104, 0.0018105749040842056, 0.03481133654713631, 0.028410300612449646, -0.005521140526980162, -0.037166062742471695, -0.009727894328534603, -0.007575748022645712, 0.031769007444381714, 0.01591692864894867, -0.07149645686149597, -0.022819383069872856, -0.025556638836860657, 0.03829556331038475, 0.03599891439080238, -0.039620354771614075, -0.052856698632240295, 0.014543462544679642, 0.029836874455213547, 0.004911733325570822, 0.006350961048156023, -0.002845192328095436, 0.01151148322969675, 0.038910895586013794, 0.019080182537436485, -0.005964197684079409, 0.013235464692115784, 0.01979215256869793, 0.028337698429822922, -0.029424462467432022, 0.0345134362578392, 0.02685575745999813, -0.10838081687688828, 0.007495822850614786, -0.03945600241422653, -0.048700157552957535, 0.029617760330438614, -0.007066475227475166, -0.029409416019916534, -0.014822331257164478, 0.020348375663161278, 0.008603030815720558, -0.005156198516488075, 0.024565963074564934, -0.004429014399647713, 0.042246244847774506, 0.006228230893611908, -0.040713973343372345, -0.006633983459323645, -0.012441592290997505, 0.06379376351833344, 0.01138747576624155, -0.05108489841222763, -0.04554334282875061, 0.000258329208008945, 0.02675539255142212, 0.015998685732483864, 0.0045121400617063046, 0.035585757344961166, -0.025728177279233932, -0.0022018083836883307, 0.025854280218482018, 0.008726329542696476, -0.08949534595012665, -0.0042279548943042755, 0.014192483387887478, 0.0033121018204838037, -0.01194020640105009, -0.007336666341871023, 0.03430375084280968, 0.010065815411508083, 0.019571145996451378, 0.02486649714410305, 0.05963717773556709, -0.002381320344284177, -0.012897028587758541, -0.05677343159914017, -0.008045922964811325, 0.030109083279967308, 0.10458984225988388, 0.06349971145391464, -0.0902666375041008, -0.0014230748638510704, 0.047629497945308685, -0.005494843702763319, -0.06622440367937088, 0.02207377552986145, 0.03912592679262161, 0.08439141511917114, -0.010423487052321434, 0.0105659868568182, -0.03800560534000397, 0.005288270302116871, 0.005335751920938492, 0.005952857900410891, 0.027864310890436172, -0.07598649710416794, -0.017360499128699303, -0.014762528240680695, -0.017516929656267166, 0.030921051278710365, -0.009271711111068726, 0.04128511995077133, 0.05822055786848068, -0.0456681065261364, -0.021587887778878212, 0.032664477825164795, 0.005013902205973864, 0.024362962692975998, 0.052013691514730453, -0.012947490438818932, 0.007668015547096729, 0.012747621163725853, 0.009064197540283203, 0.005395033396780491, -0.06471613794565201, -0.02341090328991413, -0.03957385569810867, 0.006384128239005804, 0.023038262501358986, 0.016163893043994904, 0.031970616430044174, 0.008142382837831974, -0.010445505380630493, 0.020478740334510803, 0.02267698012292385, 0.0035674618557095528, -0.04390260949730873, 0.02594989724457264, 0.004782241769134998, -0.026361459866166115, 0.05352150648832321, 0.05303672328591347, -0.0018899120623245835, 0.040250685065984726, 0.014841049909591675, -0.04965448006987572, 0.034611135721206665, 0.029163721948862076, -0.0370374396443367, 0.06107928231358528, 0.01931428350508213, -0.024129332974553108, 0.013892723247408867, -0.057689569890499115, -0.019153200089931488, 0.06274314969778061, -0.0104749770835042, 0.06092853471636772, 0.014168822206556797, 0.020315535366535187, -0.00742214685305953, -0.07249875366687775, -0.02061198092997074, 0.06763654202222824, -0.019078969955444336, -0.025485828518867493, -0.037090715020895004, -0.03748273849487305, 0.06468653678894043, 0.05475500971078873, -0.025230998173356056, 0.03658314049243927, -0.03558206930756569, 0.00412721186876297, -0.02006283588707447, -0.040070950984954834, -0.03366212919354439, 0.021284595131874084, -0.09109087288379669, -0.0617571622133255, 0.029330993071198463, -0.023756109178066254, -0.012480301782488823, 0.052574045956134796, -0.006037478800863028, 0.007189587689936161, -0.018584808334708214, -0.024014504626393318, -0.039253927767276764, -0.0019910773262381554, 0.016578208655118942, 0.002754555782303214, -0.07257606834173203, 0.06669497489929199, -0.027288293465971947, 0.03512290492653847, -0.04012216255068779, 0.0006304704584181309, -0.056184276938438416, 0.026845846325159073, 0.01171874813735485, -0.007035360671579838, -0.11059699952602386, -0.0017737774178385735, 0.0008525890298187733, 0.035708170384168625, 0.039497245103120804, 0.009014977142214775, -0.009363487362861633, -0.04452665150165558, -0.015306168235838413, 0.007775279227644205, 0.0238527562469244, -0.049062952399253845, -0.029840851202607155, 0.009884377010166645, 0.007368407677859068, 0.01218915730714798, 0.026270395144820213, 0.03921155259013176, -0.02102232351899147, -0.046590857207775116, -0.03964143246412277, -0.006222231313586235, -0.017028534784913063, 0.012820009142160416, 0.06535062193870544, -0.021741028875112534, 0.031689491122961044, 0.019865790382027626, -0.037215035408735275, 0.026745876297354698, -0.0022958426270633936, 0.0018095504492521286, -0.025574250146746635, 0.024400917813181877, 0.0044356766156852245, -0.015722671523690224, 0.0007741103763692081, -0.06032382696866989, -0.027001703158020973, -0.04074037820100784, 0.001984398579224944, 0.019667888060212135, 0.0037972789723426104, 0.08036674559116364, -0.0016786562046036124, -0.01648603193461895, 0.03937697783112526, -0.03000270389020443, -0.013990301638841629, -0.04250183328986168, -0.051923878490924835, -0.016109390184283257, -0.03339380398392677, -0.013268408365547657, 0.0020023153629153967, 0.03535597398877144, -0.08207280933856964, 0.04318299517035484, 0.042447302490472794, -0.008383109234273434, -0.0263237152248621, -0.02173841930925846, -0.04972178116440773, 0.07675917446613312, -0.02865636721253395, 0.03968397527933121, -0.011468784883618355, -0.024121342226862907, -0.03269520029425621, 0.016022393479943275, 0.043653521686792374, -0.021612973883748055, 0.04812530800700188, -0.08864858001470566, -0.030017411336302757, -0.05985622480511665, 0.06505481153726578, -0.059853170067071915, 0.04449130594730377, -0.005449226126074791, 0.09018084406852722, 0.05151943489909172, -0.04078914597630501, -0.008794245310127735, 0.00486722681671381, -0.04789615795016289, -0.006356469821184874, 0.022389404475688934, 0.0336216501891613, -0.0006719402736052871, -0.005734316539019346, 0.07507745921611786, 0.05159412696957588, 0.05322299897670746, -0.012859235517680645, 0.024618180468678474, -0.011983484029769897, 0.014492410235106945, -0.029176125302910805, -0.046488311141729355, -0.008908496238291264, -0.008766178041696548, 0.016541115939617157, -0.04279477149248123, -0.005161352455615997, 0.03063373640179634, 0.004773003049194813, 0.015471100807189941, 0.04255279153585434, -0.06804932653903961, -0.022094659507274628, -0.002926690736785531, -0.01759984903037548, -0.03391116484999657, -0.016117988154292107, 0.02803482674062252, -0.005842387676239014, 0.029265668243169785, 0.02014891430735588, -0.015048426575958729, -0.0111753661185503, 0.006005946546792984, 0.003760319435968995, 0.010096371173858643, 0.004336421377956867, -0.021158697083592415, -0.07886983454227448, 0.019743654876947403, -0.04299156740307808, 0.006879636086523533, 0.004897196311503649, -0.03199371322989464, 0.012173089198768139, 0.006098099518567324, -0.010709347203373909, 0.029287517070770264, 0.008361488580703735, -0.02357981540262699, -0.035802002996206284, 0.0030663209035992622, 0.04971461743116379, 0.007869037799537182, 0.023053284734487534, 0.006221679039299488, 0.016018914058804512, -0.0639345571398735, 0.0014233884867280722, 0.01390507910400629, -0.03822048753499985, -0.000677775009535253, -0.032367583364248276, 0.0018110964447259903, 0.028008289635181427, -0.033390216529369354, 0.04089576378464699, 0.056676290929317474, 0.04725015163421631, 0.007858541794121265, -0.005909656640142202, -0.0374026782810688, 0.0009642730001360178, 0.04712258279323578, 0.015068107284605503, -0.09084785729646683, -0.0183014627546072, -0.010378052480518818, -0.011262909509241581, 0.01483835931867361, -0.06328458338975906, 0.03158270940184593, -0.039874304085969925, 0.005887739360332489, 0.013760249130427837, -0.08227024972438812, 0.05073750391602516, -0.03333717957139015, -0.01784328557550907, -0.09434085339307785, -0.04711056128144264, -0.03830826282501221, -0.01700424589216709, -0.04848729074001312, -0.04147587716579437, 0.024607349187135696, -0.023363759741187096, -0.04393063858151436, -0.004325236193835735, -0.0268165972083807, 0.017535211518406868, 0.045535337179899216, 0.008101162500679493, 0.027319978922605515, -0.01964757591485977, -0.0500638522207737, 0.04529197886586189, -0.011926586739718914, 0.011780159547924995, 0.022706450894474983, 0.026478933170437813, 0.08566772192716599, 0.04917490482330322, 0.044006217271089554, -0.020047280937433243, 0.03049284778535366, 0.005896560847759247, 0.010716656222939491, -0.005336425732821226, -0.032737407833337784, -0.028436297550797462], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'group_ids': ['guardkit__feature_specs']}
WARNING:guardkit.knowledge.graphiti_client:Search request failed: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
CREATE INDEX FOR (n:Entity) ON (n.uuid, n.group_id, n.name, n.created_at)
{}
ERROR:asyncio:Task exception was never retrieved
future: <Task finished name='Task-254' coro=<FalkorDriver.build_indices_and_constraints() done, defined at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:300> exception=RuntimeError('<asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop')>
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 305, in build_indices_and_constraints
    await self.execute_query(query)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 230, in execute_query
    result = await graph.query(cypher_query_, params)  # type: ignore[reportUnknownArgumentType]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 105, in query
    return await self._query(q, params=params, timeout=timeout, read_only=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 79, in _query
    response = await self.execute_command(*command)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/client.py", line 720, in execute_command
    conn = self.connection or await pool.get_connection()
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/connection.py", line 1194, in get_connection
    async with self._lock:
               ^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 14, in __aenter__
    await self.acquire()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 105, in acquire
    fut = self._get_loop().create_future()
          ~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/mixins.py", line 20, in _get_loop
    raise RuntimeError(f'{self!r} is bound to a different event loop')
RuntimeError: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop

        MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity)
     WHERE e.group_id IN $group_ids
            WITH DISTINCT e, n, m, (2 - vec.cosineDistance(e.fact_embedding, vecf32($search_vector)))/2 AS score
            WHERE score > $min_score
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'search_vector': [-0.019678272306919098, 0.04145437479019165, -0.15208914875984192, -0.08751127868890762, 0.060685936361551285, -0.011536049656569958, -0.0356954000890255, 0.06326451152563095, 0.005898250732570887, 0.03596508875489235, -0.0460776761174202, 0.059481438249349594, 0.0731963962316513, -0.0035015461035072803, -0.010767459869384766, 0.0026188043411821127, 0.042661190032958984, -0.04567542299628258, 0.005363617092370987, 0.04486007243394852, 0.017174692824482918, -0.031202269718050957, 0.016036447137594223, -0.0022920984774827957, 0.08285566419363022, 0.012536974623799324, 0.04308679699897766, 0.017869723960757256, -0.05449867248535156, 0.06715884059667587, -0.026934392750263214, 0.033227503299713135, -0.04078983888030052, 0.003484932938590646, -0.025479862466454506, -0.02652379311621189, 0.06887561082839966, 0.0005733506986871362, -0.029584350064396858, 0.03562229871749878, -0.001539326854981482, -0.020368313416838646, 0.023740852251648903, -0.03915613889694214, 0.01963983289897442, -0.004860177170485258, 0.08341535180807114, -0.00909666158258915, 0.03961418941617012, -0.02264111116528511, -0.004619008861482143, 0.035068050026893616, -0.014536296017467976, -0.04993395879864693, 0.06013113632798195, 0.0559917688369751, -0.013428007252514362, 0.0017108998727053404, 0.014681867323815823, 0.022310331463813782, 0.03381912782788277, 0.061756398528814316, -0.02037772163748741, 0.07045856863260269, 0.00499360729008913, -0.032459888607263565, 0.023036682978272438, 0.04308941960334778, 0.0240500345826149, -0.028242910280823708, -0.0029579228721559048, -0.040853410959243774, 0.008793892338871956, 0.023262470960617065, -0.03967183828353882, -0.018579205498099327, -0.06695448607206345, -0.002489942591637373, -0.02617836929857731, 0.045291196554899216, 0.004710789304226637, 0.011663787998259068, -0.0036145183257758617, -0.002416863339021802, 0.04015050455927849, -0.03343840315937996, -0.011631639674305916, -0.00844602845609188, -0.016957048326730728, 0.007057918701320887, 0.02226279303431511, 0.002995438873767853, 0.0018111851532012224, 0.0015182229690253735, -0.03973628953099251, 0.02589903399348259, -0.0006272330647334456, 0.011767647229135036, -0.0492384172976017, -0.058542363345623016, -0.014917286112904549, -0.012216508388519287, 0.013676203787326813, -0.058566536754369736, 0.03772224858403206, 0.05964180827140808, 0.0423254668712616, 0.022949479520320892, -0.022774117067456245, -0.06008358672261238, -0.03383133187890053, 0.030198698863387108, 0.03560342267155647, -0.02526315115392208, 0.008249345235526562, -0.05359608680009842, 0.019221995025873184, 0.021092142909765244, 0.016274355351924896, 0.07800885289907455, 0.017908133566379547, -0.03679491952061653, 0.011676537804305553, 0.036793000996112823, -0.017211860045790672, 0.012664657086133957, -0.06798101216554642, -0.015494957566261292, 0.053091924637556076, -0.04097888618707657, -0.03503381088376045, -0.013990537263453007, -0.015718035399913788, 0.015308920294046402, 0.0068150050938129425, 0.018288258463144302, -0.027750765904784203, -0.05620942637324333, 0.05034608766436577, 0.00658156955614686, 0.037913836538791656, 0.024165406823158264, -0.005590274930000305, 0.005106118507683277, -0.021129272878170013, -0.06092797964811325, 0.03375286981463432, -0.024518007412552834, 0.015498638153076172, -0.03766050934791565, 0.010379175655543804, 0.020013928413391113, 0.017530186101794243, 0.020746007561683655, 0.03018259070813656, -0.04491570591926575, 0.02726386860013008, 0.01579068787395954, 0.034235142171382904, 0.012131059542298317, 0.05927712097764015, 0.029664726927876472, -0.040221668779850006, 0.06505591422319412, 0.013997580856084824, 0.006343886721879244, 0.04485567286610603, -0.023017926141619682, -0.016303986310958862, 0.05887455493211746, 0.003787028370425105, -0.06779701262712479, -0.005519767291843891, -0.04536237567663193, -0.02908109314739704, 0.06589078158140182, 0.009105178527534008, -0.048932116478681564, 0.0702362060546875, 0.015577378682792187, 0.022807935252785683, -0.05566418915987015, 0.05768178403377533, 0.024182241410017014, -0.07004685699939728, -0.009858010336756706, -0.01198254432529211, -0.03954509273171425, 0.01700400933623314, -0.01538708247244358, 0.07074327766895294, 0.027945393696427345, -0.0715738981962204, -0.06478138267993927, -0.06457969546318054, -0.03879387676715851, 0.04865585267543793, -0.06224197521805763, 0.01791718602180481, -0.056931640952825546, -0.04821635037660599, -0.016800135374069214, -0.014499199576675892, -0.00016610653256066144, -0.06166314333677292, -0.013199149630963802, 0.002707129344344139, 0.028006387874484062, -0.03186313807964325, 0.027730202302336693, 0.03960445895791054, -0.026549363508820534, -0.0013489174889400601, 0.022544309496879578, -0.006144820246845484, 0.0014451746828854084, 0.021434560418128967, 0.009937262162566185, 0.00638539670035243, 0.04972505569458008, 0.010563386604189873, 0.03476741909980774, 0.0353098101913929, 0.008606175892055035, 0.05145268142223358, 0.004322201479226351, 0.007664940785616636, -0.041306138038635254, -0.035920560359954834, -0.013973681256175041, -0.023324865847826004, -0.033298611640930176, 0.027322586625814438, 2.2270212866715156e-05, 0.03547924757003784, -0.015216288156807423, 0.017451131716370583, 0.044429097324609756, -0.027702681720256805, 0.005388504825532436, -0.0013571048621088266, 0.03524407744407654, -0.023104004561901093, 0.008536252193152905, -0.01720883883535862, 0.02564302645623684, 0.03022625483572483, -0.01345042884349823, 0.026601038873195648, 0.04824414104223251, -0.034497812390327454, 0.00541694276034832, 0.02385224774479866, 0.048989731818437576, 0.019454237073659897, -0.058079589158296585, 0.032224103808403015, 0.02340812236070633, -0.013453795574605465, -0.03828400373458862, 0.00019668388995341957, -0.05886334553360939, 0.02829950489103794, -0.011681304313242435, -0.02894294075667858, -0.0156210632994771, -0.025587614625692368, -0.005355904344469309, -0.008415039628744125, 0.008364710956811905, -0.020933544263243675, 0.013845553621649742, 0.011375073343515396, 0.0034024554770439863, 0.013591719791293144, 0.03831282630562782, 0.006789857987314463, -0.016561930999159813, -0.0077067469246685505, 0.017976976931095123, -0.044922471046447754, -0.09317181259393692, -0.009833413176238537, 0.0019290000200271606, 0.008832037448883057, 0.04975416138768196, -0.005788398440927267, 0.02413789927959442, -0.006867791526019573, -0.030871326103806496, 0.0018034533131867647, -0.028147924691438675, -0.061592698097229004, 0.03471648693084717, 0.0029623613227158785, 0.04576379805803299, 0.04920250177383423, 0.0066710906103253365, 0.019879451021552086, -0.029847823083400726, 0.04213399812579155, 0.022378113120794296, 0.06034644693136215, 0.018210720270872116, -0.052402056753635406, -0.06233320012688637, 0.02748517319560051, 0.0009044610778801143, 0.03394578769803047, -0.0025600087828934193, -0.07710444182157516, -0.026959320530295372, -0.04725588113069534, 0.09587374329566956, -0.004505184479057789, 0.06266964226961136, 0.011928888969123363, 0.026125216856598854, 0.020802753046154976, -0.03790655732154846, 0.008611896075308323, -0.009999945759773254, 0.0008124966407194734, 0.0023372818250209093, -0.013930312357842922, 0.0445791594684124, -0.03707464411854744, 0.005865194834768772, -0.027623893693089485, -0.0051140510477125645, 0.03622030094265938, 0.029353415593504906, 0.014871746301651001, -0.049538563936948776, -0.0884135365486145, 0.039663538336753845, -0.006087770219892263, -0.005554589908570051, -0.018760336562991142, 0.04400838911533356, 0.06469032168388367, -0.027068525552749634, -0.014268585480749607, -0.03689954802393913, -0.04199261963367462, -0.07164203375577927, -0.02319754846394062, -0.022304972633719444, 0.06034821271896362, 0.01234059315174818, -0.05015625059604645, 0.026312967762351036, 0.024602733552455902, -0.013165849260985851, 0.026101354509592056, -0.00039741327054798603, 0.045131612569093704, -0.0011586755281314254, -0.016506563872098923, 0.008335383608937263, 0.08420206606388092, 0.007974393665790558, 0.01806117594242096, -0.04338707774877548, 0.0017254726262763143, 0.013004262000322342, 0.035513974726200104, 0.0018105749040842056, 0.03481133654713631, 0.028410300612449646, -0.005521140526980162, -0.037166062742471695, -0.009727894328534603, -0.007575748022645712, 0.031769007444381714, 0.01591692864894867, -0.07149645686149597, -0.022819383069872856, -0.025556638836860657, 0.03829556331038475, 0.03599891439080238, -0.039620354771614075, -0.052856698632240295, 0.014543462544679642, 0.029836874455213547, 0.004911733325570822, 0.006350961048156023, -0.002845192328095436, 0.01151148322969675, 0.038910895586013794, 0.019080182537436485, -0.005964197684079409, 0.013235464692115784, 0.01979215256869793, 0.028337698429822922, -0.029424462467432022, 0.0345134362578392, 0.02685575745999813, -0.10838081687688828, 0.007495822850614786, -0.03945600241422653, -0.048700157552957535, 0.029617760330438614, -0.007066475227475166, -0.029409416019916534, -0.014822331257164478, 0.020348375663161278, 0.008603030815720558, -0.005156198516488075, 0.024565963074564934, -0.004429014399647713, 0.042246244847774506, 0.006228230893611908, -0.040713973343372345, -0.006633983459323645, -0.012441592290997505, 0.06379376351833344, 0.01138747576624155, -0.05108489841222763, -0.04554334282875061, 0.000258329208008945, 0.02675539255142212, 0.015998685732483864, 0.0045121400617063046, 0.035585757344961166, -0.025728177279233932, -0.0022018083836883307, 0.025854280218482018, 0.008726329542696476, -0.08949534595012665, -0.0042279548943042755, 0.014192483387887478, 0.0033121018204838037, -0.01194020640105009, -0.007336666341871023, 0.03430375084280968, 0.010065815411508083, 0.019571145996451378, 0.02486649714410305, 0.05963717773556709, -0.002381320344284177, -0.012897028587758541, -0.05677343159914017, -0.008045922964811325, 0.030109083279967308, 0.10458984225988388, 0.06349971145391464, -0.0902666375041008, -0.0014230748638510704, 0.047629497945308685, -0.005494843702763319, -0.06622440367937088, 0.02207377552986145, 0.03912592679262161, 0.08439141511917114, -0.010423487052321434, 0.0105659868568182, -0.03800560534000397, 0.005288270302116871, 0.005335751920938492, 0.005952857900410891, 0.027864310890436172, -0.07598649710416794, -0.017360499128699303, -0.014762528240680695, -0.017516929656267166, 0.030921051278710365, -0.009271711111068726, 0.04128511995077133, 0.05822055786848068, -0.0456681065261364, -0.021587887778878212, 0.032664477825164795, 0.005013902205973864, 0.024362962692975998, 0.052013691514730453, -0.012947490438818932, 0.007668015547096729, 0.012747621163725853, 0.009064197540283203, 0.005395033396780491, -0.06471613794565201, -0.02341090328991413, -0.03957385569810867, 0.006384128239005804, 0.023038262501358986, 0.016163893043994904, 0.031970616430044174, 0.008142382837831974, -0.010445505380630493, 0.020478740334510803, 0.02267698012292385, 0.0035674618557095528, -0.04390260949730873, 0.02594989724457264, 0.004782241769134998, -0.026361459866166115, 0.05352150648832321, 0.05303672328591347, -0.0018899120623245835, 0.040250685065984726, 0.014841049909591675, -0.04965448006987572, 0.034611135721206665, 0.029163721948862076, -0.0370374396443367, 0.06107928231358528, 0.01931428350508213, -0.024129332974553108, 0.013892723247408867, -0.057689569890499115, -0.019153200089931488, 0.06274314969778061, -0.0104749770835042, 0.06092853471636772, 0.014168822206556797, 0.020315535366535187, -0.00742214685305953, -0.07249875366687775, -0.02061198092997074, 0.06763654202222824, -0.019078969955444336, -0.025485828518867493, -0.037090715020895004, -0.03748273849487305, 0.06468653678894043, 0.05475500971078873, -0.025230998173356056, 0.03658314049243927, -0.03558206930756569, 0.00412721186876297, -0.02006283588707447, -0.040070950984954834, -0.03366212919354439, 0.021284595131874084, -0.09109087288379669, -0.0617571622133255, 0.029330993071198463, -0.023756109178066254, -0.012480301782488823, 0.052574045956134796, -0.006037478800863028, 0.007189587689936161, -0.018584808334708214, -0.024014504626393318, -0.039253927767276764, -0.0019910773262381554, 0.016578208655118942, 0.002754555782303214, -0.07257606834173203, 0.06669497489929199, -0.027288293465971947, 0.03512290492653847, -0.04012216255068779, 0.0006304704584181309, -0.056184276938438416, 0.026845846325159073, 0.01171874813735485, -0.007035360671579838, -0.11059699952602386, -0.0017737774178385735, 0.0008525890298187733, 0.035708170384168625, 0.039497245103120804, 0.009014977142214775, -0.009363487362861633, -0.04452665150165558, -0.015306168235838413, 0.007775279227644205, 0.0238527562469244, -0.049062952399253845, -0.029840851202607155, 0.009884377010166645, 0.007368407677859068, 0.01218915730714798, 0.026270395144820213, 0.03921155259013176, -0.02102232351899147, -0.046590857207775116, -0.03964143246412277, -0.006222231313586235, -0.017028534784913063, 0.012820009142160416, 0.06535062193870544, -0.021741028875112534, 0.031689491122961044, 0.019865790382027626, -0.037215035408735275, 0.026745876297354698, -0.0022958426270633936, 0.0018095504492521286, -0.025574250146746635, 0.024400917813181877, 0.0044356766156852245, -0.015722671523690224, 0.0007741103763692081, -0.06032382696866989, -0.027001703158020973, -0.04074037820100784, 0.001984398579224944, 0.019667888060212135, 0.0037972789723426104, 0.08036674559116364, -0.0016786562046036124, -0.01648603193461895, 0.03937697783112526, -0.03000270389020443, -0.013990301638841629, -0.04250183328986168, -0.051923878490924835, -0.016109390184283257, -0.03339380398392677, -0.013268408365547657, 0.0020023153629153967, 0.03535597398877144, -0.08207280933856964, 0.04318299517035484, 0.042447302490472794, -0.008383109234273434, -0.0263237152248621, -0.02173841930925846, -0.04972178116440773, 0.07675917446613312, -0.02865636721253395, 0.03968397527933121, -0.011468784883618355, -0.024121342226862907, -0.03269520029425621, 0.016022393479943275, 0.043653521686792374, -0.021612973883748055, 0.04812530800700188, -0.08864858001470566, -0.030017411336302757, -0.05985622480511665, 0.06505481153726578, -0.059853170067071915, 0.04449130594730377, -0.005449226126074791, 0.09018084406852722, 0.05151943489909172, -0.04078914597630501, -0.008794245310127735, 0.00486722681671381, -0.04789615795016289, -0.006356469821184874, 0.022389404475688934, 0.0336216501891613, -0.0006719402736052871, -0.005734316539019346, 0.07507745921611786, 0.05159412696957588, 0.05322299897670746, -0.012859235517680645, 0.024618180468678474, -0.011983484029769897, 0.014492410235106945, -0.029176125302910805, -0.046488311141729355, -0.008908496238291264, -0.008766178041696548, 0.016541115939617157, -0.04279477149248123, -0.005161352455615997, 0.03063373640179634, 0.004773003049194813, 0.015471100807189941, 0.04255279153585434, -0.06804932653903961, -0.022094659507274628, -0.002926690736785531, -0.01759984903037548, -0.03391116484999657, -0.016117988154292107, 0.02803482674062252, -0.005842387676239014, 0.029265668243169785, 0.02014891430735588, -0.015048426575958729, -0.0111753661185503, 0.006005946546792984, 0.003760319435968995, 0.010096371173858643, 0.004336421377956867, -0.021158697083592415, -0.07886983454227448, 0.019743654876947403, -0.04299156740307808, 0.006879636086523533, 0.004897196311503649, -0.03199371322989464, 0.012173089198768139, 0.006098099518567324, -0.010709347203373909, 0.029287517070770264, 0.008361488580703735, -0.02357981540262699, -0.035802002996206284, 0.0030663209035992622, 0.04971461743116379, 0.007869037799537182, 0.023053284734487534, 0.006221679039299488, 0.016018914058804512, -0.0639345571398735, 0.0014233884867280722, 0.01390507910400629, -0.03822048753499985, -0.000677775009535253, -0.032367583364248276, 0.0018110964447259903, 0.028008289635181427, -0.033390216529369354, 0.04089576378464699, 0.056676290929317474, 0.04725015163421631, 0.007858541794121265, -0.005909656640142202, -0.0374026782810688, 0.0009642730001360178, 0.04712258279323578, 0.015068107284605503, -0.09084785729646683, -0.0183014627546072, -0.010378052480518818, -0.011262909509241581, 0.01483835931867361, -0.06328458338975906, 0.03158270940184593, -0.039874304085969925, 0.005887739360332489, 0.013760249130427837, -0.08227024972438812, 0.05073750391602516, -0.03333717957139015, -0.01784328557550907, -0.09434085339307785, -0.04711056128144264, -0.03830826282501221, -0.01700424589216709, -0.04848729074001312, -0.04147587716579437, 0.024607349187135696, -0.023363759741187096, -0.04393063858151436, -0.004325236193835735, -0.0268165972083807, 0.017535211518406868, 0.045535337179899216, 0.008101162500679493, 0.027319978922605515, -0.01964757591485977, -0.0500638522207737, 0.04529197886586189, -0.011926586739718914, 0.011780159547924995, 0.022706450894474983, 0.026478933170437813, 0.08566772192716599, 0.04917490482330322, 0.044006217271089554, -0.020047280937433243, 0.03049284778535366, 0.005896560847759247, 0.010716656222939491, -0.005336425732821226, -0.032737407833337784, -0.028436297550797462], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'group_ids': ['guardkit__task_outcomes']}
WARNING:guardkit.knowledge.graphiti_client:Search request failed: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
CREATE INDEX FOR (n:Entity) ON (n.uuid, n.group_id, n.name, n.created_at)
{}
ERROR:asyncio:Task exception was never retrieved
future: <Task finished name='Task-262' coro=<FalkorDriver.build_indices_and_constraints() done, defined at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:300> exception=RuntimeError('<asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop')>
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 305, in build_indices_and_constraints
    await self.execute_query(query)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 230, in execute_query
    result = await graph.query(cypher_query_, params)  # type: ignore[reportUnknownArgumentType]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 105, in query
    return await self._query(q, params=params, timeout=timeout, read_only=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 79, in _query
    response = await self.execute_command(*command)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/client.py", line 720, in execute_command
    conn = self.connection or await pool.get_connection()
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/connection.py", line 1194, in get_connection
    async with self._lock:
               ^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 14, in __aenter__
    await self.acquire()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 105, in acquire
    fut = self._get_loop().create_future()
          ~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/mixins.py", line 20, in _get_loop
    raise RuntimeError(f'{self!r} is bound to a different event loop')
RuntimeError: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
CREATE INDEX FOR (n:Saga) ON (n.uuid, n.group_id, n.name)
{}
ERROR:asyncio:Task exception was never retrieved
future: <Task finished name='Task-246' coro=<FalkorDriver.build_indices_and_constraints() done, defined at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:300> exception=RuntimeError('<asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop')>
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 305, in build_indices_and_constraints
    await self.execute_query(query)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 230, in execute_query
    result = await graph.query(cypher_query_, params)  # type: ignore[reportUnknownArgumentType]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 105, in query
    return await self._query(q, params=params, timeout=timeout, read_only=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 79, in _query
    response = await self.execute_command(*command)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/client.py", line 720, in execute_command
    conn = self.connection or await pool.get_connection()
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/connection.py", line 1194, in get_connection
    async with self._lock:
               ^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 14, in __aenter__
    await self.acquire()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 105, in acquire
    fut = self._get_loop().create_future()
          ~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/mixins.py", line 20, in _get_loop
    raise RuntimeError(f'{self!r} is bound to a different event loop')
RuntimeError: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    WITH rel AS e, score, startNode(rel) AS n, endNode(rel) AS m
     WHERE e.group_id IN $group_ids
            WITH e, score, n, m
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'query': ' (Task | Fix | Python | scoping | issue | json | import | enhancer | py)', 'limit': 20, 'routing_': 'r', 'group_ids': ['patterns']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop

        MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity)
     WHERE e.group_id IN $group_ids
            WITH DISTINCT e, n, m, (2 - vec.cosineDistance(e.fact_embedding, vecf32($search_vector)))/2 AS score
            WHERE score > $min_score
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'search_vector': [-0.019678272306919098, 0.04145437479019165, -0.15208914875984192, -0.08751127868890762, 0.060685936361551285, -0.011536049656569958, -0.0356954000890255, 0.06326451152563095, 0.005898250732570887, 0.03596508875489235, -0.0460776761174202, 0.059481438249349594, 0.0731963962316513, -0.0035015461035072803, -0.010767459869384766, 0.0026188043411821127, 0.042661190032958984, -0.04567542299628258, 0.005363617092370987, 0.04486007243394852, 0.017174692824482918, -0.031202269718050957, 0.016036447137594223, -0.0022920984774827957, 0.08285566419363022, 0.012536974623799324, 0.04308679699897766, 0.017869723960757256, -0.05449867248535156, 0.06715884059667587, -0.026934392750263214, 0.033227503299713135, -0.04078983888030052, 0.003484932938590646, -0.025479862466454506, -0.02652379311621189, 0.06887561082839966, 0.0005733506986871362, -0.029584350064396858, 0.03562229871749878, -0.001539326854981482, -0.020368313416838646, 0.023740852251648903, -0.03915613889694214, 0.01963983289897442, -0.004860177170485258, 0.08341535180807114, -0.00909666158258915, 0.03961418941617012, -0.02264111116528511, -0.004619008861482143, 0.035068050026893616, -0.014536296017467976, -0.04993395879864693, 0.06013113632798195, 0.0559917688369751, -0.013428007252514362, 0.0017108998727053404, 0.014681867323815823, 0.022310331463813782, 0.03381912782788277, 0.061756398528814316, -0.02037772163748741, 0.07045856863260269, 0.00499360729008913, -0.032459888607263565, 0.023036682978272438, 0.04308941960334778, 0.0240500345826149, -0.028242910280823708, -0.0029579228721559048, -0.040853410959243774, 0.008793892338871956, 0.023262470960617065, -0.03967183828353882, -0.018579205498099327, -0.06695448607206345, -0.002489942591637373, -0.02617836929857731, 0.045291196554899216, 0.004710789304226637, 0.011663787998259068, -0.0036145183257758617, -0.002416863339021802, 0.04015050455927849, -0.03343840315937996, -0.011631639674305916, -0.00844602845609188, -0.016957048326730728, 0.007057918701320887, 0.02226279303431511, 0.002995438873767853, 0.0018111851532012224, 0.0015182229690253735, -0.03973628953099251, 0.02589903399348259, -0.0006272330647334456, 0.011767647229135036, -0.0492384172976017, -0.058542363345623016, -0.014917286112904549, -0.012216508388519287, 0.013676203787326813, -0.058566536754369736, 0.03772224858403206, 0.05964180827140808, 0.0423254668712616, 0.022949479520320892, -0.022774117067456245, -0.06008358672261238, -0.03383133187890053, 0.030198698863387108, 0.03560342267155647, -0.02526315115392208, 0.008249345235526562, -0.05359608680009842, 0.019221995025873184, 0.021092142909765244, 0.016274355351924896, 0.07800885289907455, 0.017908133566379547, -0.03679491952061653, 0.011676537804305553, 0.036793000996112823, -0.017211860045790672, 0.012664657086133957, -0.06798101216554642, -0.015494957566261292, 0.053091924637556076, -0.04097888618707657, -0.03503381088376045, -0.013990537263453007, -0.015718035399913788, 0.015308920294046402, 0.0068150050938129425, 0.018288258463144302, -0.027750765904784203, -0.05620942637324333, 0.05034608766436577, 0.00658156955614686, 0.037913836538791656, 0.024165406823158264, -0.005590274930000305, 0.005106118507683277, -0.021129272878170013, -0.06092797964811325, 0.03375286981463432, -0.024518007412552834, 0.015498638153076172, -0.03766050934791565, 0.010379175655543804, 0.020013928413391113, 0.017530186101794243, 0.020746007561683655, 0.03018259070813656, -0.04491570591926575, 0.02726386860013008, 0.01579068787395954, 0.034235142171382904, 0.012131059542298317, 0.05927712097764015, 0.029664726927876472, -0.040221668779850006, 0.06505591422319412, 0.013997580856084824, 0.006343886721879244, 0.04485567286610603, -0.023017926141619682, -0.016303986310958862, 0.05887455493211746, 0.003787028370425105, -0.06779701262712479, -0.005519767291843891, -0.04536237567663193, -0.02908109314739704, 0.06589078158140182, 0.009105178527534008, -0.048932116478681564, 0.0702362060546875, 0.015577378682792187, 0.022807935252785683, -0.05566418915987015, 0.05768178403377533, 0.024182241410017014, -0.07004685699939728, -0.009858010336756706, -0.01198254432529211, -0.03954509273171425, 0.01700400933623314, -0.01538708247244358, 0.07074327766895294, 0.027945393696427345, -0.0715738981962204, -0.06478138267993927, -0.06457969546318054, -0.03879387676715851, 0.04865585267543793, -0.06224197521805763, 0.01791718602180481, -0.056931640952825546, -0.04821635037660599, -0.016800135374069214, -0.014499199576675892, -0.00016610653256066144, -0.06166314333677292, -0.013199149630963802, 0.002707129344344139, 0.028006387874484062, -0.03186313807964325, 0.027730202302336693, 0.03960445895791054, -0.026549363508820534, -0.0013489174889400601, 0.022544309496879578, -0.006144820246845484, 0.0014451746828854084, 0.021434560418128967, 0.009937262162566185, 0.00638539670035243, 0.04972505569458008, 0.010563386604189873, 0.03476741909980774, 0.0353098101913929, 0.008606175892055035, 0.05145268142223358, 0.004322201479226351, 0.007664940785616636, -0.041306138038635254, -0.035920560359954834, -0.013973681256175041, -0.023324865847826004, -0.033298611640930176, 0.027322586625814438, 2.2270212866715156e-05, 0.03547924757003784, -0.015216288156807423, 0.017451131716370583, 0.044429097324609756, -0.027702681720256805, 0.005388504825532436, -0.0013571048621088266, 0.03524407744407654, -0.023104004561901093, 0.008536252193152905, -0.01720883883535862, 0.02564302645623684, 0.03022625483572483, -0.01345042884349823, 0.026601038873195648, 0.04824414104223251, -0.034497812390327454, 0.00541694276034832, 0.02385224774479866, 0.048989731818437576, 0.019454237073659897, -0.058079589158296585, 0.032224103808403015, 0.02340812236070633, -0.013453795574605465, -0.03828400373458862, 0.00019668388995341957, -0.05886334553360939, 0.02829950489103794, -0.011681304313242435, -0.02894294075667858, -0.0156210632994771, -0.025587614625692368, -0.005355904344469309, -0.008415039628744125, 0.008364710956811905, -0.020933544263243675, 0.013845553621649742, 0.011375073343515396, 0.0034024554770439863, 0.013591719791293144, 0.03831282630562782, 0.006789857987314463, -0.016561930999159813, -0.0077067469246685505, 0.017976976931095123, -0.044922471046447754, -0.09317181259393692, -0.009833413176238537, 0.0019290000200271606, 0.008832037448883057, 0.04975416138768196, -0.005788398440927267, 0.02413789927959442, -0.006867791526019573, -0.030871326103806496, 0.0018034533131867647, -0.028147924691438675, -0.061592698097229004, 0.03471648693084717, 0.0029623613227158785, 0.04576379805803299, 0.04920250177383423, 0.0066710906103253365, 0.019879451021552086, -0.029847823083400726, 0.04213399812579155, 0.022378113120794296, 0.06034644693136215, 0.018210720270872116, -0.052402056753635406, -0.06233320012688637, 0.02748517319560051, 0.0009044610778801143, 0.03394578769803047, -0.0025600087828934193, -0.07710444182157516, -0.026959320530295372, -0.04725588113069534, 0.09587374329566956, -0.004505184479057789, 0.06266964226961136, 0.011928888969123363, 0.026125216856598854, 0.020802753046154976, -0.03790655732154846, 0.008611896075308323, -0.009999945759773254, 0.0008124966407194734, 0.0023372818250209093, -0.013930312357842922, 0.0445791594684124, -0.03707464411854744, 0.005865194834768772, -0.027623893693089485, -0.0051140510477125645, 0.03622030094265938, 0.029353415593504906, 0.014871746301651001, -0.049538563936948776, -0.0884135365486145, 0.039663538336753845, -0.006087770219892263, -0.005554589908570051, -0.018760336562991142, 0.04400838911533356, 0.06469032168388367, -0.027068525552749634, -0.014268585480749607, -0.03689954802393913, -0.04199261963367462, -0.07164203375577927, -0.02319754846394062, -0.022304972633719444, 0.06034821271896362, 0.01234059315174818, -0.05015625059604645, 0.026312967762351036, 0.024602733552455902, -0.013165849260985851, 0.026101354509592056, -0.00039741327054798603, 0.045131612569093704, -0.0011586755281314254, -0.016506563872098923, 0.008335383608937263, 0.08420206606388092, 0.007974393665790558, 0.01806117594242096, -0.04338707774877548, 0.0017254726262763143, 0.013004262000322342, 0.035513974726200104, 0.0018105749040842056, 0.03481133654713631, 0.028410300612449646, -0.005521140526980162, -0.037166062742471695, -0.009727894328534603, -0.007575748022645712, 0.031769007444381714, 0.01591692864894867, -0.07149645686149597, -0.022819383069872856, -0.025556638836860657, 0.03829556331038475, 0.03599891439080238, -0.039620354771614075, -0.052856698632240295, 0.014543462544679642, 0.029836874455213547, 0.004911733325570822, 0.006350961048156023, -0.002845192328095436, 0.01151148322969675, 0.038910895586013794, 0.019080182537436485, -0.005964197684079409, 0.013235464692115784, 0.01979215256869793, 0.028337698429822922, -0.029424462467432022, 0.0345134362578392, 0.02685575745999813, -0.10838081687688828, 0.007495822850614786, -0.03945600241422653, -0.048700157552957535, 0.029617760330438614, -0.007066475227475166, -0.029409416019916534, -0.014822331257164478, 0.020348375663161278, 0.008603030815720558, -0.005156198516488075, 0.024565963074564934, -0.004429014399647713, 0.042246244847774506, 0.006228230893611908, -0.040713973343372345, -0.006633983459323645, -0.012441592290997505, 0.06379376351833344, 0.01138747576624155, -0.05108489841222763, -0.04554334282875061, 0.000258329208008945, 0.02675539255142212, 0.015998685732483864, 0.0045121400617063046, 0.035585757344961166, -0.025728177279233932, -0.0022018083836883307, 0.025854280218482018, 0.008726329542696476, -0.08949534595012665, -0.0042279548943042755, 0.014192483387887478, 0.0033121018204838037, -0.01194020640105009, -0.007336666341871023, 0.03430375084280968, 0.010065815411508083, 0.019571145996451378, 0.02486649714410305, 0.05963717773556709, -0.002381320344284177, -0.012897028587758541, -0.05677343159914017, -0.008045922964811325, 0.030109083279967308, 0.10458984225988388, 0.06349971145391464, -0.0902666375041008, -0.0014230748638510704, 0.047629497945308685, -0.005494843702763319, -0.06622440367937088, 0.02207377552986145, 0.03912592679262161, 0.08439141511917114, -0.010423487052321434, 0.0105659868568182, -0.03800560534000397, 0.005288270302116871, 0.005335751920938492, 0.005952857900410891, 0.027864310890436172, -0.07598649710416794, -0.017360499128699303, -0.014762528240680695, -0.017516929656267166, 0.030921051278710365, -0.009271711111068726, 0.04128511995077133, 0.05822055786848068, -0.0456681065261364, -0.021587887778878212, 0.032664477825164795, 0.005013902205973864, 0.024362962692975998, 0.052013691514730453, -0.012947490438818932, 0.007668015547096729, 0.012747621163725853, 0.009064197540283203, 0.005395033396780491, -0.06471613794565201, -0.02341090328991413, -0.03957385569810867, 0.006384128239005804, 0.023038262501358986, 0.016163893043994904, 0.031970616430044174, 0.008142382837831974, -0.010445505380630493, 0.020478740334510803, 0.02267698012292385, 0.0035674618557095528, -0.04390260949730873, 0.02594989724457264, 0.004782241769134998, -0.026361459866166115, 0.05352150648832321, 0.05303672328591347, -0.0018899120623245835, 0.040250685065984726, 0.014841049909591675, -0.04965448006987572, 0.034611135721206665, 0.029163721948862076, -0.0370374396443367, 0.06107928231358528, 0.01931428350508213, -0.024129332974553108, 0.013892723247408867, -0.057689569890499115, -0.019153200089931488, 0.06274314969778061, -0.0104749770835042, 0.06092853471636772, 0.014168822206556797, 0.020315535366535187, -0.00742214685305953, -0.07249875366687775, -0.02061198092997074, 0.06763654202222824, -0.019078969955444336, -0.025485828518867493, -0.037090715020895004, -0.03748273849487305, 0.06468653678894043, 0.05475500971078873, -0.025230998173356056, 0.03658314049243927, -0.03558206930756569, 0.00412721186876297, -0.02006283588707447, -0.040070950984954834, -0.03366212919354439, 0.021284595131874084, -0.09109087288379669, -0.0617571622133255, 0.029330993071198463, -0.023756109178066254, -0.012480301782488823, 0.052574045956134796, -0.006037478800863028, 0.007189587689936161, -0.018584808334708214, -0.024014504626393318, -0.039253927767276764, -0.0019910773262381554, 0.016578208655118942, 0.002754555782303214, -0.07257606834173203, 0.06669497489929199, -0.027288293465971947, 0.03512290492653847, -0.04012216255068779, 0.0006304704584181309, -0.056184276938438416, 0.026845846325159073, 0.01171874813735485, -0.007035360671579838, -0.11059699952602386, -0.0017737774178385735, 0.0008525890298187733, 0.035708170384168625, 0.039497245103120804, 0.009014977142214775, -0.009363487362861633, -0.04452665150165558, -0.015306168235838413, 0.007775279227644205, 0.0238527562469244, -0.049062952399253845, -0.029840851202607155, 0.009884377010166645, 0.007368407677859068, 0.01218915730714798, 0.026270395144820213, 0.03921155259013176, -0.02102232351899147, -0.046590857207775116, -0.03964143246412277, -0.006222231313586235, -0.017028534784913063, 0.012820009142160416, 0.06535062193870544, -0.021741028875112534, 0.031689491122961044, 0.019865790382027626, -0.037215035408735275, 0.026745876297354698, -0.0022958426270633936, 0.0018095504492521286, -0.025574250146746635, 0.024400917813181877, 0.0044356766156852245, -0.015722671523690224, 0.0007741103763692081, -0.06032382696866989, -0.027001703158020973, -0.04074037820100784, 0.001984398579224944, 0.019667888060212135, 0.0037972789723426104, 0.08036674559116364, -0.0016786562046036124, -0.01648603193461895, 0.03937697783112526, -0.03000270389020443, -0.013990301638841629, -0.04250183328986168, -0.051923878490924835, -0.016109390184283257, -0.03339380398392677, -0.013268408365547657, 0.0020023153629153967, 0.03535597398877144, -0.08207280933856964, 0.04318299517035484, 0.042447302490472794, -0.008383109234273434, -0.0263237152248621, -0.02173841930925846, -0.04972178116440773, 0.07675917446613312, -0.02865636721253395, 0.03968397527933121, -0.011468784883618355, -0.024121342226862907, -0.03269520029425621, 0.016022393479943275, 0.043653521686792374, -0.021612973883748055, 0.04812530800700188, -0.08864858001470566, -0.030017411336302757, -0.05985622480511665, 0.06505481153726578, -0.059853170067071915, 0.04449130594730377, -0.005449226126074791, 0.09018084406852722, 0.05151943489909172, -0.04078914597630501, -0.008794245310127735, 0.00486722681671381, -0.04789615795016289, -0.006356469821184874, 0.022389404475688934, 0.0336216501891613, -0.0006719402736052871, -0.005734316539019346, 0.07507745921611786, 0.05159412696957588, 0.05322299897670746, -0.012859235517680645, 0.024618180468678474, -0.011983484029769897, 0.014492410235106945, -0.029176125302910805, -0.046488311141729355, -0.008908496238291264, -0.008766178041696548, 0.016541115939617157, -0.04279477149248123, -0.005161352455615997, 0.03063373640179634, 0.004773003049194813, 0.015471100807189941, 0.04255279153585434, -0.06804932653903961, -0.022094659507274628, -0.002926690736785531, -0.01759984903037548, -0.03391116484999657, -0.016117988154292107, 0.02803482674062252, -0.005842387676239014, 0.029265668243169785, 0.02014891430735588, -0.015048426575958729, -0.0111753661185503, 0.006005946546792984, 0.003760319435968995, 0.010096371173858643, 0.004336421377956867, -0.021158697083592415, -0.07886983454227448, 0.019743654876947403, -0.04299156740307808, 0.006879636086523533, 0.004897196311503649, -0.03199371322989464, 0.012173089198768139, 0.006098099518567324, -0.010709347203373909, 0.029287517070770264, 0.008361488580703735, -0.02357981540262699, -0.035802002996206284, 0.0030663209035992622, 0.04971461743116379, 0.007869037799537182, 0.023053284734487534, 0.006221679039299488, 0.016018914058804512, -0.0639345571398735, 0.0014233884867280722, 0.01390507910400629, -0.03822048753499985, -0.000677775009535253, -0.032367583364248276, 0.0018110964447259903, 0.028008289635181427, -0.033390216529369354, 0.04089576378464699, 0.056676290929317474, 0.04725015163421631, 0.007858541794121265, -0.005909656640142202, -0.0374026782810688, 0.0009642730001360178, 0.04712258279323578, 0.015068107284605503, -0.09084785729646683, -0.0183014627546072, -0.010378052480518818, -0.011262909509241581, 0.01483835931867361, -0.06328458338975906, 0.03158270940184593, -0.039874304085969925, 0.005887739360332489, 0.013760249130427837, -0.08227024972438812, 0.05073750391602516, -0.03333717957139015, -0.01784328557550907, -0.09434085339307785, -0.04711056128144264, -0.03830826282501221, -0.01700424589216709, -0.04848729074001312, -0.04147587716579437, 0.024607349187135696, -0.023363759741187096, -0.04393063858151436, -0.004325236193835735, -0.0268165972083807, 0.017535211518406868, 0.045535337179899216, 0.008101162500679493, 0.027319978922605515, -0.01964757591485977, -0.0500638522207737, 0.04529197886586189, -0.011926586739718914, 0.011780159547924995, 0.022706450894474983, 0.026478933170437813, 0.08566772192716599, 0.04917490482330322, 0.044006217271089554, -0.020047280937433243, 0.03049284778535366, 0.005896560847759247, 0.010716656222939491, -0.005336425732821226, -0.032737407833337784, -0.028436297550797462], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'group_ids': ['patterns']}
WARNING:guardkit.knowledge.graphiti_client:Search request failed: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
WARNING:guardkit.knowledge.graphiti_client:Graphiti disabled after 3 consecutive failures -- continuing without knowledge graph context
INFO:guardkit.knowledge.turn_state_operations:[TurnState] Loaded from local file: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/turn_state_turn_1.json (2006 chars)
INFO:guardkit.knowledge.autobuild_context_loader:[TurnState] Turn continuation loaded: 2006 chars for turn 2
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Coach context categories: []
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Context loaded in 0.1s
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Coach context: 0 categories, 0/7892 tokens
INFO:guardkit.orchestrator.autobuild:Using LLM Coach (primary) for TASK-FIX-A7D3 turn 2
INFO:guardkit.orchestrator.autobuild:[Graphiti] Coach context provided: 2055 chars
WARNING:guardkit.orchestrator.quality_gates.coach_validator:gather_evidence: honesty produced 15 must_fix issue(s) for TASK-FIX-A7D3; downstream gathering skipped.
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] SDK timeout: 2340s (base=1200s, mode=task-work x1.5, complexity=3 x1.3)
INFO:guardkit.orchestrator.sdk_debug:sdk_debug: preserved coach prompt for TASK-FIX-A7D3 turn 2 -> /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/sdk_debug/turn_2/coach
INFO:claude_agent_sdk._internal.transport.subprocess_cli:Using bundled Claude Code CLI: /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (30s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (60s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (90s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (120s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (150s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (180s elapsed)
INFO:guardkit.orchestrator.progress:[2026-06-03T18:15:45.931Z] Completed turn 2: feedback - Feedback: The Player claims to have implemented the fix for TASK-FIX-A7D3 (Python scoping ...
INFO:guardkit.orchestrator.autobuild:Turn state saved to local file: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/turn_state_turn_2.json
INFO:guardkit.orchestrator.autobuild:Turn 2 honesty: 0.38 (19 discrepancies)
INFO:guardkit.orchestrator.autobuild:Criteria Progress (Turn 2): 0/1 verified (0%)
INFO:guardkit.orchestrator.autobuild:Criteria: 0 verified, 0 rejected, 1 pending
INFO:guardkit.orchestrator.worktree_checkpoints:Creating checkpoint for TASK-FIX-A7D3 turn 2 (tests: fail, count: 0)
INFO:guardkit.orchestrator.worktree_checkpoints:Created checkpoint: 03d13a43 for turn 2 (2 total)
INFO:guardkit.orchestrator.autobuild:Checkpoint created: 03d13a43 for turn 2
INFO:guardkit.orchestrator.autobuild:Coach provided feedback on turn 2
INFO:guardkit.orchestrator.autobuild:Executing turn 3/5
INFO:guardkit.orchestrator.autobuild:Perspective reset triggered at turn 3 (scheduled reset)
INFO:guardkit.orchestrator.progress:[2026-06-03T18:15:46.161Z] Started turn 3: Player Implementation
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Loading Player context (turn 3)...
INFO:guardkit.knowledge.turn_state_operations:[TurnState] Loaded from local file: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/turn_state_turn_2.json (2215 chars)
INFO:guardkit.knowledge.autobuild_context_loader:[TurnState] Turn continuation loaded: 2215 chars for turn 3
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Context loaded in 0.0s
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Player context: 0 categories, 0/7892 tokens
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] SDK timeout: 2340s (base=1200s, mode=task-work x1.5, complexity=3 x1.3)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Mode: task-work (auto-selected, complexity=3, task_type='')
INFO:guardkit.orchestrator.agent_invoker:Invoking Player via task-work delegation for TASK-FIX-A7D3 (turn 3)
INFO:guardkit.orchestrator.agent_invoker:Ensuring task TASK-FIX-A7D3 is in design_approved state
INFO:guardkit.tasks.state_bridge.TASK-FIX-A7D3:Ensuring task TASK-FIX-A7D3 is in design_approved state
INFO:guardkit.tasks.state_bridge.TASK-FIX-A7D3:Task TASK-FIX-A7D3 already in design_approved state
INFO:guardkit.orchestrator.agent_invoker:Task TASK-FIX-A7D3 state verified: design_approved
INFO:guardkit.orchestrator.agent_invoker:Executing inline implement protocol for TASK-FIX-A7D3 (mode=tdd)
INFO:guardkit.orchestrator.agent_invoker:Working directory: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3
INFO:guardkit.orchestrator.agent_invoker:Inline protocol size: 20680 bytes (variant=full, multiplier=1.0x)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Max turns: 150 (base=100, complexity=3 x1.3, floored from 130 to 150)
INFO:guardkit.orchestrator.sdk_debug:sdk_debug: preserved player prompt for TASK-FIX-A7D3 turn 3 -> /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/sdk_debug/turn_3
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] SDK invocation starting
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Working directory: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Allowed tools: ['Read', 'Write', 'Edit', 'Bash', 'Grep', 'Glob', 'Task']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Setting sources: ['project']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Permission mode: acceptEdits
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Max turns: 150
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] SDK timeout: 2340s
INFO:claude_agent_sdk._internal.transport.subprocess_cli:Using bundled Claude Code CLI: /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (30s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (60s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (90s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (120s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (150s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (180s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (210s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (240s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (270s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (300s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (330s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (360s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (390s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (420s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (450s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (480s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (510s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (540s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (570s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (600s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (630s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (660s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (690s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (720s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (750s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (780s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (810s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (840s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (870s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (900s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (930s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (960s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (990s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (1020s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (1050s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (1080s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (1110s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] task-work implementation in progress... (1140s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] ToolUseBlock Write input keys: ['file_path', 'content']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] SDK completed: turns=43
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Message summary: total=131, assistant=61, tools=42, results=1
WARNING:guardkit.orchestrator.agent_invoker:BDD oracle running against system pytest; worktree-local imports may fail (no .venv/bin/python[3] under /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3).
INFO:guardkit.orchestrator.agent_invoker:BDD oracle invoking run_bdd_for_task for TASK-FIX-A7D3 with python_executable=None
INFO:guardkit.orchestrator.agent_invoker:Wrote task_work_results.json to /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/task_work_results.json
INFO:guardkit.orchestrator.agent_invoker:task-work completed successfully for TASK-FIX-A7D3
INFO:guardkit.orchestrator.agent_invoker:Created Player report from task_work_results.json for TASK-FIX-A7D3 turn 3
INFO:guardkit.orchestrator.agent_invoker:Git detection added: 19 modified, 0 created files for TASK-FIX-A7D3
INFO:guardkit.orchestrator.agent_invoker:Recovered 5 requirements_addressed from agent-written player report for TASK-FIX-A7D3
INFO:guardkit.orchestrator.agent_invoker:Generated 1 file-existence promises for TASK-FIX-A7D3 (agent did not produce promises)
INFO:guardkit.orchestrator.agent_invoker:Filtered 2 orchestrator-induced ghost path(s) for TASK-FIX-A7D3: ['/Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/player_turn_3.json', 'tasks/design_approved/TASK-FIX-A7D3-fix-python-scoping-issue-with-json-import-in-enhancer-py.md']
INFO:guardkit.orchestrator.agent_invoker:Written Player report to /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/player_turn_3.json
INFO:guardkit.orchestrator.agent_invoker:Updated task_work_results.json with enriched data for TASK-FIX-A7D3
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] SDK invocation complete: 1165.7s, 43 SDK turns (27.1s/turn avg)
INFO:guardkit.orchestrator.progress:[2026-06-03T18:35:11.991Z] Completed turn 3: success - 0 files created, 18 modified, 0 tests (passing)
INFO:guardkit.orchestrator.autobuild:Dropped 2 stale requirements from carry-forward
INFO:guardkit.orchestrator.autobuild:Carried forward 3 requirements from previous turns
INFO:guardkit.orchestrator.autobuild:Cumulative requirements_addressed: 8 criteria (current turn: 5, carried: 3)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Mode: task-work (auto-selected, complexity=3, task_type='')
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] SDK timeout: 2340s (base=1200s, mode=task-work x1.5, complexity=3 x1.3)
INFO:guardkit.orchestrator.sdk_debug:sdk_debug: preserved player prompt for TASK-FIX-A7D3 turn 3 -> /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/sdk_debug/turn_3
INFO:claude_agent_sdk._internal.transport.subprocess_cli:Using bundled Claude Code CLI: /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (30s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (60s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock Bash input keys: ['command', 'description', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (90s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (120s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (150s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (180s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (210s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (240s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (270s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (300s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (330s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (360s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock TaskOutput input keys: ['block', 'task_id', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (390s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (420s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (450s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (480s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (510s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (540s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (570s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (600s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (630s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (660s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock TaskOutput input keys: ['block', 'task_id', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (690s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (720s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (750s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (780s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (810s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (840s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (870s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (900s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (930s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (960s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock TaskOutput input keys: ['block', 'task_id', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (990s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1020s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1050s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1080s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1110s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1140s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1170s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1200s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1230s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1260s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock TaskOutput input keys: ['block', 'task_id', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1290s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1320s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1350s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1380s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1410s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1440s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1470s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1500s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1530s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1560s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock TaskOutput input keys: ['block', 'task_id', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1590s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1620s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1650s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1680s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1710s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1740s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1770s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1800s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1830s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1860s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock TaskOutput input keys: ['block', 'task_id', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1890s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1920s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1950s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (1980s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2010s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2040s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2070s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2100s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2130s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2160s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2190s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation ToolUseBlock TaskOutput input keys: ['block', 'task_id', 'timeout']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2220s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2250s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2280s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2310s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] specialist:test-orchestrator invocation in progress... (2340s elapsed)
WARNING:guardkit.orchestrator.specialist_invocations:run_specialist(test-orchestrator) failed for TASK-FIX-A7D3: SDKTimeoutError: Agent invocation exceeded 2340s timeout
INFO:guardkit.orchestrator.agent_invoker:Injected orchestrator specialist records into /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/task_work_results.json (merged=2, validation=violation)
INFO:guardkit.orchestrator.progress:[2026-06-03T19:14:17.261Z] Started turn 3: Coach Validation
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Loading Coach context (turn 3)...
INFO:guardkit.knowledge.graphiti_client:Circuit breaker reset after 3708s (half-open)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Task <Task pending name='Task-300' coro=<semaphore_gather.<locals>._wrap_coroutine() running at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/helpers.py:131> cb=[gather.<locals>._done_callback() at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/tasks.py:810]> got Future <Future pending> attached to a different loop
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    WITH rel AS e, score, startNode(rel) AS n, endNode(rel) AS m

            WITH e, score, n, m
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'query': ' (Task | Fix | Python | scoping | issue | json | import | enhancer | py)', 'limit': 20, 'routing_': 'r'}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Task <Task pending name='Task-301' coro=<semaphore_gather.<locals>._wrap_coroutine() running at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/helpers.py:131> cb=[gather.<locals>._done_callback() at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/tasks.py:810]> got Future <Future pending> attached to a different loop

        MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity)

            WITH DISTINCT e, n, m, (2 - vec.cosineDistance(e.fact_embedding, vecf32($search_vector)))/2 AS score
            WHERE score > $min_score
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'search_vector': [-0.019678272306919098, 0.04145437479019165, -0.15208914875984192, -0.08751127868890762, 0.060685936361551285, -0.011536049656569958, -0.0356954000890255, 0.06326451152563095, 0.005898250732570887, 0.03596508875489235, -0.0460776761174202, 0.059481438249349594, 0.0731963962316513, -0.0035015461035072803, -0.010767459869384766, 0.0026188043411821127, 0.042661190032958984, -0.04567542299628258, 0.005363617092370987, 0.04486007243394852, 0.017174692824482918, -0.031202269718050957, 0.016036447137594223, -0.0022920984774827957, 0.08285566419363022, 0.012536974623799324, 0.04308679699897766, 0.017869723960757256, -0.05449867248535156, 0.06715884059667587, -0.026934392750263214, 0.033227503299713135, -0.04078983888030052, 0.003484932938590646, -0.025479862466454506, -0.02652379311621189, 0.06887561082839966, 0.0005733506986871362, -0.029584350064396858, 0.03562229871749878, -0.001539326854981482, -0.020368313416838646, 0.023740852251648903, -0.03915613889694214, 0.01963983289897442, -0.004860177170485258, 0.08341535180807114, -0.00909666158258915, 0.03961418941617012, -0.02264111116528511, -0.004619008861482143, 0.035068050026893616, -0.014536296017467976, -0.04993395879864693, 0.06013113632798195, 0.0559917688369751, -0.013428007252514362, 0.0017108998727053404, 0.014681867323815823, 0.022310331463813782, 0.03381912782788277, 0.061756398528814316, -0.02037772163748741, 0.07045856863260269, 0.00499360729008913, -0.032459888607263565, 0.023036682978272438, 0.04308941960334778, 0.0240500345826149, -0.028242910280823708, -0.0029579228721559048, -0.040853410959243774, 0.008793892338871956, 0.023262470960617065, -0.03967183828353882, -0.018579205498099327, -0.06695448607206345, -0.002489942591637373, -0.02617836929857731, 0.045291196554899216, 0.004710789304226637, 0.011663787998259068, -0.0036145183257758617, -0.002416863339021802, 0.04015050455927849, -0.03343840315937996, -0.011631639674305916, -0.00844602845609188, -0.016957048326730728, 0.007057918701320887, 0.02226279303431511, 0.002995438873767853, 0.0018111851532012224, 0.0015182229690253735, -0.03973628953099251, 0.02589903399348259, -0.0006272330647334456, 0.011767647229135036, -0.0492384172976017, -0.058542363345623016, -0.014917286112904549, -0.012216508388519287, 0.013676203787326813, -0.058566536754369736, 0.03772224858403206, 0.05964180827140808, 0.0423254668712616, 0.022949479520320892, -0.022774117067456245, -0.06008358672261238, -0.03383133187890053, 0.030198698863387108, 0.03560342267155647, -0.02526315115392208, 0.008249345235526562, -0.05359608680009842, 0.019221995025873184, 0.021092142909765244, 0.016274355351924896, 0.07800885289907455, 0.017908133566379547, -0.03679491952061653, 0.011676537804305553, 0.036793000996112823, -0.017211860045790672, 0.012664657086133957, -0.06798101216554642, -0.015494957566261292, 0.053091924637556076, -0.04097888618707657, -0.03503381088376045, -0.013990537263453007, -0.015718035399913788, 0.015308920294046402, 0.0068150050938129425, 0.018288258463144302, -0.027750765904784203, -0.05620942637324333, 0.05034608766436577, 0.00658156955614686, 0.037913836538791656, 0.024165406823158264, -0.005590274930000305, 0.005106118507683277, -0.021129272878170013, -0.06092797964811325, 0.03375286981463432, -0.024518007412552834, 0.015498638153076172, -0.03766050934791565, 0.010379175655543804, 0.020013928413391113, 0.017530186101794243, 0.020746007561683655, 0.03018259070813656, -0.04491570591926575, 0.02726386860013008, 0.01579068787395954, 0.034235142171382904, 0.012131059542298317, 0.05927712097764015, 0.029664726927876472, -0.040221668779850006, 0.06505591422319412, 0.013997580856084824, 0.006343886721879244, 0.04485567286610603, -0.023017926141619682, -0.016303986310958862, 0.05887455493211746, 0.003787028370425105, -0.06779701262712479, -0.005519767291843891, -0.04536237567663193, -0.02908109314739704, 0.06589078158140182, 0.009105178527534008, -0.048932116478681564, 0.0702362060546875, 0.015577378682792187, 0.022807935252785683, -0.05566418915987015, 0.05768178403377533, 0.024182241410017014, -0.07004685699939728, -0.009858010336756706, -0.01198254432529211, -0.03954509273171425, 0.01700400933623314, -0.01538708247244358, 0.07074327766895294, 0.027945393696427345, -0.0715738981962204, -0.06478138267993927, -0.06457969546318054, -0.03879387676715851, 0.04865585267543793, -0.06224197521805763, 0.01791718602180481, -0.056931640952825546, -0.04821635037660599, -0.016800135374069214, -0.014499199576675892, -0.00016610653256066144, -0.06166314333677292, -0.013199149630963802, 0.002707129344344139, 0.028006387874484062, -0.03186313807964325, 0.027730202302336693, 0.03960445895791054, -0.026549363508820534, -0.0013489174889400601, 0.022544309496879578, -0.006144820246845484, 0.0014451746828854084, 0.021434560418128967, 0.009937262162566185, 0.00638539670035243, 0.04972505569458008, 0.010563386604189873, 0.03476741909980774, 0.0353098101913929, 0.008606175892055035, 0.05145268142223358, 0.004322201479226351, 0.007664940785616636, -0.041306138038635254, -0.035920560359954834, -0.013973681256175041, -0.023324865847826004, -0.033298611640930176, 0.027322586625814438, 2.2270212866715156e-05, 0.03547924757003784, -0.015216288156807423, 0.017451131716370583, 0.044429097324609756, -0.027702681720256805, 0.005388504825532436, -0.0013571048621088266, 0.03524407744407654, -0.023104004561901093, 0.008536252193152905, -0.01720883883535862, 0.02564302645623684, 0.03022625483572483, -0.01345042884349823, 0.026601038873195648, 0.04824414104223251, -0.034497812390327454, 0.00541694276034832, 0.02385224774479866, 0.048989731818437576, 0.019454237073659897, -0.058079589158296585, 0.032224103808403015, 0.02340812236070633, -0.013453795574605465, -0.03828400373458862, 0.00019668388995341957, -0.05886334553360939, 0.02829950489103794, -0.011681304313242435, -0.02894294075667858, -0.0156210632994771, -0.025587614625692368, -0.005355904344469309, -0.008415039628744125, 0.008364710956811905, -0.020933544263243675, 0.013845553621649742, 0.011375073343515396, 0.0034024554770439863, 0.013591719791293144, 0.03831282630562782, 0.006789857987314463, -0.016561930999159813, -0.0077067469246685505, 0.017976976931095123, -0.044922471046447754, -0.09317181259393692, -0.009833413176238537, 0.0019290000200271606, 0.008832037448883057, 0.04975416138768196, -0.005788398440927267, 0.02413789927959442, -0.006867791526019573, -0.030871326103806496, 0.0018034533131867647, -0.028147924691438675, -0.061592698097229004, 0.03471648693084717, 0.0029623613227158785, 0.04576379805803299, 0.04920250177383423, 0.0066710906103253365, 0.019879451021552086, -0.029847823083400726, 0.04213399812579155, 0.022378113120794296, 0.06034644693136215, 0.018210720270872116, -0.052402056753635406, -0.06233320012688637, 0.02748517319560051, 0.0009044610778801143, 0.03394578769803047, -0.0025600087828934193, -0.07710444182157516, -0.026959320530295372, -0.04725588113069534, 0.09587374329566956, -0.004505184479057789, 0.06266964226961136, 0.011928888969123363, 0.026125216856598854, 0.020802753046154976, -0.03790655732154846, 0.008611896075308323, -0.009999945759773254, 0.0008124966407194734, 0.0023372818250209093, -0.013930312357842922, 0.0445791594684124, -0.03707464411854744, 0.005865194834768772, -0.027623893693089485, -0.0051140510477125645, 0.03622030094265938, 0.029353415593504906, 0.014871746301651001, -0.049538563936948776, -0.0884135365486145, 0.039663538336753845, -0.006087770219892263, -0.005554589908570051, -0.018760336562991142, 0.04400838911533356, 0.06469032168388367, -0.027068525552749634, -0.014268585480749607, -0.03689954802393913, -0.04199261963367462, -0.07164203375577927, -0.02319754846394062, -0.022304972633719444, 0.06034821271896362, 0.01234059315174818, -0.05015625059604645, 0.026312967762351036, 0.024602733552455902, -0.013165849260985851, 0.026101354509592056, -0.00039741327054798603, 0.045131612569093704, -0.0011586755281314254, -0.016506563872098923, 0.008335383608937263, 0.08420206606388092, 0.007974393665790558, 0.01806117594242096, -0.04338707774877548, 0.0017254726262763143, 0.013004262000322342, 0.035513974726200104, 0.0018105749040842056, 0.03481133654713631, 0.028410300612449646, -0.005521140526980162, -0.037166062742471695, -0.009727894328534603, -0.007575748022645712, 0.031769007444381714, 0.01591692864894867, -0.07149645686149597, -0.022819383069872856, -0.025556638836860657, 0.03829556331038475, 0.03599891439080238, -0.039620354771614075, -0.052856698632240295, 0.014543462544679642, 0.029836874455213547, 0.004911733325570822, 0.006350961048156023, -0.002845192328095436, 0.01151148322969675, 0.038910895586013794, 0.019080182537436485, -0.005964197684079409, 0.013235464692115784, 0.01979215256869793, 0.028337698429822922, -0.029424462467432022, 0.0345134362578392, 0.02685575745999813, -0.10838081687688828, 0.007495822850614786, -0.03945600241422653, -0.048700157552957535, 0.029617760330438614, -0.007066475227475166, -0.029409416019916534, -0.014822331257164478, 0.020348375663161278, 0.008603030815720558, -0.005156198516488075, 0.024565963074564934, -0.004429014399647713, 0.042246244847774506, 0.006228230893611908, -0.040713973343372345, -0.006633983459323645, -0.012441592290997505, 0.06379376351833344, 0.01138747576624155, -0.05108489841222763, -0.04554334282875061, 0.000258329208008945, 0.02675539255142212, 0.015998685732483864, 0.0045121400617063046, 0.035585757344961166, -0.025728177279233932, -0.0022018083836883307, 0.025854280218482018, 0.008726329542696476, -0.08949534595012665, -0.0042279548943042755, 0.014192483387887478, 0.0033121018204838037, -0.01194020640105009, -0.007336666341871023, 0.03430375084280968, 0.010065815411508083, 0.019571145996451378, 0.02486649714410305, 0.05963717773556709, -0.002381320344284177, -0.012897028587758541, -0.05677343159914017, -0.008045922964811325, 0.030109083279967308, 0.10458984225988388, 0.06349971145391464, -0.0902666375041008, -0.0014230748638510704, 0.047629497945308685, -0.005494843702763319, -0.06622440367937088, 0.02207377552986145, 0.03912592679262161, 0.08439141511917114, -0.010423487052321434, 0.0105659868568182, -0.03800560534000397, 0.005288270302116871, 0.005335751920938492, 0.005952857900410891, 0.027864310890436172, -0.07598649710416794, -0.017360499128699303, -0.014762528240680695, -0.017516929656267166, 0.030921051278710365, -0.009271711111068726, 0.04128511995077133, 0.05822055786848068, -0.0456681065261364, -0.021587887778878212, 0.032664477825164795, 0.005013902205973864, 0.024362962692975998, 0.052013691514730453, -0.012947490438818932, 0.007668015547096729, 0.012747621163725853, 0.009064197540283203, 0.005395033396780491, -0.06471613794565201, -0.02341090328991413, -0.03957385569810867, 0.006384128239005804, 0.023038262501358986, 0.016163893043994904, 0.031970616430044174, 0.008142382837831974, -0.010445505380630493, 0.020478740334510803, 0.02267698012292385, 0.0035674618557095528, -0.04390260949730873, 0.02594989724457264, 0.004782241769134998, -0.026361459866166115, 0.05352150648832321, 0.05303672328591347, -0.0018899120623245835, 0.040250685065984726, 0.014841049909591675, -0.04965448006987572, 0.034611135721206665, 0.029163721948862076, -0.0370374396443367, 0.06107928231358528, 0.01931428350508213, -0.024129332974553108, 0.013892723247408867, -0.057689569890499115, -0.019153200089931488, 0.06274314969778061, -0.0104749770835042, 0.06092853471636772, 0.014168822206556797, 0.020315535366535187, -0.00742214685305953, -0.07249875366687775, -0.02061198092997074, 0.06763654202222824, -0.019078969955444336, -0.025485828518867493, -0.037090715020895004, -0.03748273849487305, 0.06468653678894043, 0.05475500971078873, -0.025230998173356056, 0.03658314049243927, -0.03558206930756569, 0.00412721186876297, -0.02006283588707447, -0.040070950984954834, -0.03366212919354439, 0.021284595131874084, -0.09109087288379669, -0.0617571622133255, 0.029330993071198463, -0.023756109178066254, -0.012480301782488823, 0.052574045956134796, -0.006037478800863028, 0.007189587689936161, -0.018584808334708214, -0.024014504626393318, -0.039253927767276764, -0.0019910773262381554, 0.016578208655118942, 0.002754555782303214, -0.07257606834173203, 0.06669497489929199, -0.027288293465971947, 0.03512290492653847, -0.04012216255068779, 0.0006304704584181309, -0.056184276938438416, 0.026845846325159073, 0.01171874813735485, -0.007035360671579838, -0.11059699952602386, -0.0017737774178385735, 0.0008525890298187733, 0.035708170384168625, 0.039497245103120804, 0.009014977142214775, -0.009363487362861633, -0.04452665150165558, -0.015306168235838413, 0.007775279227644205, 0.0238527562469244, -0.049062952399253845, -0.029840851202607155, 0.009884377010166645, 0.007368407677859068, 0.01218915730714798, 0.026270395144820213, 0.03921155259013176, -0.02102232351899147, -0.046590857207775116, -0.03964143246412277, -0.006222231313586235, -0.017028534784913063, 0.012820009142160416, 0.06535062193870544, -0.021741028875112534, 0.031689491122961044, 0.019865790382027626, -0.037215035408735275, 0.026745876297354698, -0.0022958426270633936, 0.0018095504492521286, -0.025574250146746635, 0.024400917813181877, 0.0044356766156852245, -0.015722671523690224, 0.0007741103763692081, -0.06032382696866989, -0.027001703158020973, -0.04074037820100784, 0.001984398579224944, 0.019667888060212135, 0.0037972789723426104, 0.08036674559116364, -0.0016786562046036124, -0.01648603193461895, 0.03937697783112526, -0.03000270389020443, -0.013990301638841629, -0.04250183328986168, -0.051923878490924835, -0.016109390184283257, -0.03339380398392677, -0.013268408365547657, 0.0020023153629153967, 0.03535597398877144, -0.08207280933856964, 0.04318299517035484, 0.042447302490472794, -0.008383109234273434, -0.0263237152248621, -0.02173841930925846, -0.04972178116440773, 0.07675917446613312, -0.02865636721253395, 0.03968397527933121, -0.011468784883618355, -0.024121342226862907, -0.03269520029425621, 0.016022393479943275, 0.043653521686792374, -0.021612973883748055, 0.04812530800700188, -0.08864858001470566, -0.030017411336302757, -0.05985622480511665, 0.06505481153726578, -0.059853170067071915, 0.04449130594730377, -0.005449226126074791, 0.09018084406852722, 0.05151943489909172, -0.04078914597630501, -0.008794245310127735, 0.00486722681671381, -0.04789615795016289, -0.006356469821184874, 0.022389404475688934, 0.0336216501891613, -0.0006719402736052871, -0.005734316539019346, 0.07507745921611786, 0.05159412696957588, 0.05322299897670746, -0.012859235517680645, 0.024618180468678474, -0.011983484029769897, 0.014492410235106945, -0.029176125302910805, -0.046488311141729355, -0.008908496238291264, -0.008766178041696548, 0.016541115939617157, -0.04279477149248123, -0.005161352455615997, 0.03063373640179634, 0.004773003049194813, 0.015471100807189941, 0.04255279153585434, -0.06804932653903961, -0.022094659507274628, -0.002926690736785531, -0.01759984903037548, -0.03391116484999657, -0.016117988154292107, 0.02803482674062252, -0.005842387676239014, 0.029265668243169785, 0.02014891430735588, -0.015048426575958729, -0.0111753661185503, 0.006005946546792984, 0.003760319435968995, 0.010096371173858643, 0.004336421377956867, -0.021158697083592415, -0.07886983454227448, 0.019743654876947403, -0.04299156740307808, 0.006879636086523533, 0.004897196311503649, -0.03199371322989464, 0.012173089198768139, 0.006098099518567324, -0.010709347203373909, 0.029287517070770264, 0.008361488580703735, -0.02357981540262699, -0.035802002996206284, 0.0030663209035992622, 0.04971461743116379, 0.007869037799537182, 0.023053284734487534, 0.006221679039299488, 0.016018914058804512, -0.0639345571398735, 0.0014233884867280722, 0.01390507910400629, -0.03822048753499985, -0.000677775009535253, -0.032367583364248276, 0.0018110964447259903, 0.028008289635181427, -0.033390216529369354, 0.04089576378464699, 0.056676290929317474, 0.04725015163421631, 0.007858541794121265, -0.005909656640142202, -0.0374026782810688, 0.0009642730001360178, 0.04712258279323578, 0.015068107284605503, -0.09084785729646683, -0.0183014627546072, -0.010378052480518818, -0.011262909509241581, 0.01483835931867361, -0.06328458338975906, 0.03158270940184593, -0.039874304085969925, 0.005887739360332489, 0.013760249130427837, -0.08227024972438812, 0.05073750391602516, -0.03333717957139015, -0.01784328557550907, -0.09434085339307785, -0.04711056128144264, -0.03830826282501221, -0.01700424589216709, -0.04848729074001312, -0.04147587716579437, 0.024607349187135696, -0.023363759741187096, -0.04393063858151436, -0.004325236193835735, -0.0268165972083807, 0.017535211518406868, 0.045535337179899216, 0.008101162500679493, 0.027319978922605515, -0.01964757591485977, -0.0500638522207737, 0.04529197886586189, -0.011926586739718914, 0.011780159547924995, 0.022706450894474983, 0.026478933170437813, 0.08566772192716599, 0.04917490482330322, 0.044006217271089554, -0.020047280937433243, 0.03049284778535366, 0.005896560847759247, 0.010716656222939491, -0.005336425732821226, -0.032737407833337784, -0.028436297550797462], 'limit': 20, 'min_score': 0.6, 'routing_': 'r'}
WARNING:guardkit.knowledge.graphiti_client:Search request failed: Task <Task pending name='Task-300' coro=<semaphore_gather.<locals>._wrap_coroutine() running at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/helpers.py:131> cb=[gather.<locals>._done_callback() at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/tasks.py:810]> got Future <Future pending> attached to a different loop
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop

        MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity)
     WHERE e.group_id IN $group_ids
            WITH DISTINCT e, n, m, (2 - vec.cosineDistance(e.fact_embedding, vecf32($search_vector)))/2 AS score
            WHERE score > $min_score
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'search_vector': [-0.019678272306919098, 0.04145437479019165, -0.15208914875984192, -0.08751127868890762, 0.060685936361551285, -0.011536049656569958, -0.0356954000890255, 0.06326451152563095, 0.005898250732570887, 0.03596508875489235, -0.0460776761174202, 0.059481438249349594, 0.0731963962316513, -0.0035015461035072803, -0.010767459869384766, 0.0026188043411821127, 0.042661190032958984, -0.04567542299628258, 0.005363617092370987, 0.04486007243394852, 0.017174692824482918, -0.031202269718050957, 0.016036447137594223, -0.0022920984774827957, 0.08285566419363022, 0.012536974623799324, 0.04308679699897766, 0.017869723960757256, -0.05449867248535156, 0.06715884059667587, -0.026934392750263214, 0.033227503299713135, -0.04078983888030052, 0.003484932938590646, -0.025479862466454506, -0.02652379311621189, 0.06887561082839966, 0.0005733506986871362, -0.029584350064396858, 0.03562229871749878, -0.001539326854981482, -0.020368313416838646, 0.023740852251648903, -0.03915613889694214, 0.01963983289897442, -0.004860177170485258, 0.08341535180807114, -0.00909666158258915, 0.03961418941617012, -0.02264111116528511, -0.004619008861482143, 0.035068050026893616, -0.014536296017467976, -0.04993395879864693, 0.06013113632798195, 0.0559917688369751, -0.013428007252514362, 0.0017108998727053404, 0.014681867323815823, 0.022310331463813782, 0.03381912782788277, 0.061756398528814316, -0.02037772163748741, 0.07045856863260269, 0.00499360729008913, -0.032459888607263565, 0.023036682978272438, 0.04308941960334778, 0.0240500345826149, -0.028242910280823708, -0.0029579228721559048, -0.040853410959243774, 0.008793892338871956, 0.023262470960617065, -0.03967183828353882, -0.018579205498099327, -0.06695448607206345, -0.002489942591637373, -0.02617836929857731, 0.045291196554899216, 0.004710789304226637, 0.011663787998259068, -0.0036145183257758617, -0.002416863339021802, 0.04015050455927849, -0.03343840315937996, -0.011631639674305916, -0.00844602845609188, -0.016957048326730728, 0.007057918701320887, 0.02226279303431511, 0.002995438873767853, 0.0018111851532012224, 0.0015182229690253735, -0.03973628953099251, 0.02589903399348259, -0.0006272330647334456, 0.011767647229135036, -0.0492384172976017, -0.058542363345623016, -0.014917286112904549, -0.012216508388519287, 0.013676203787326813, -0.058566536754369736, 0.03772224858403206, 0.05964180827140808, 0.0423254668712616, 0.022949479520320892, -0.022774117067456245, -0.06008358672261238, -0.03383133187890053, 0.030198698863387108, 0.03560342267155647, -0.02526315115392208, 0.008249345235526562, -0.05359608680009842, 0.019221995025873184, 0.021092142909765244, 0.016274355351924896, 0.07800885289907455, 0.017908133566379547, -0.03679491952061653, 0.011676537804305553, 0.036793000996112823, -0.017211860045790672, 0.012664657086133957, -0.06798101216554642, -0.015494957566261292, 0.053091924637556076, -0.04097888618707657, -0.03503381088376045, -0.013990537263453007, -0.015718035399913788, 0.015308920294046402, 0.0068150050938129425, 0.018288258463144302, -0.027750765904784203, -0.05620942637324333, 0.05034608766436577, 0.00658156955614686, 0.037913836538791656, 0.024165406823158264, -0.005590274930000305, 0.005106118507683277, -0.021129272878170013, -0.06092797964811325, 0.03375286981463432, -0.024518007412552834, 0.015498638153076172, -0.03766050934791565, 0.010379175655543804, 0.020013928413391113, 0.017530186101794243, 0.020746007561683655, 0.03018259070813656, -0.04491570591926575, 0.02726386860013008, 0.01579068787395954, 0.034235142171382904, 0.012131059542298317, 0.05927712097764015, 0.029664726927876472, -0.040221668779850006, 0.06505591422319412, 0.013997580856084824, 0.006343886721879244, 0.04485567286610603, -0.023017926141619682, -0.016303986310958862, 0.05887455493211746, 0.003787028370425105, -0.06779701262712479, -0.005519767291843891, -0.04536237567663193, -0.02908109314739704, 0.06589078158140182, 0.009105178527534008, -0.048932116478681564, 0.0702362060546875, 0.015577378682792187, 0.022807935252785683, -0.05566418915987015, 0.05768178403377533, 0.024182241410017014, -0.07004685699939728, -0.009858010336756706, -0.01198254432529211, -0.03954509273171425, 0.01700400933623314, -0.01538708247244358, 0.07074327766895294, 0.027945393696427345, -0.0715738981962204, -0.06478138267993927, -0.06457969546318054, -0.03879387676715851, 0.04865585267543793, -0.06224197521805763, 0.01791718602180481, -0.056931640952825546, -0.04821635037660599, -0.016800135374069214, -0.014499199576675892, -0.00016610653256066144, -0.06166314333677292, -0.013199149630963802, 0.002707129344344139, 0.028006387874484062, -0.03186313807964325, 0.027730202302336693, 0.03960445895791054, -0.026549363508820534, -0.0013489174889400601, 0.022544309496879578, -0.006144820246845484, 0.0014451746828854084, 0.021434560418128967, 0.009937262162566185, 0.00638539670035243, 0.04972505569458008, 0.010563386604189873, 0.03476741909980774, 0.0353098101913929, 0.008606175892055035, 0.05145268142223358, 0.004322201479226351, 0.007664940785616636, -0.041306138038635254, -0.035920560359954834, -0.013973681256175041, -0.023324865847826004, -0.033298611640930176, 0.027322586625814438, 2.2270212866715156e-05, 0.03547924757003784, -0.015216288156807423, 0.017451131716370583, 0.044429097324609756, -0.027702681720256805, 0.005388504825532436, -0.0013571048621088266, 0.03524407744407654, -0.023104004561901093, 0.008536252193152905, -0.01720883883535862, 0.02564302645623684, 0.03022625483572483, -0.01345042884349823, 0.026601038873195648, 0.04824414104223251, -0.034497812390327454, 0.00541694276034832, 0.02385224774479866, 0.048989731818437576, 0.019454237073659897, -0.058079589158296585, 0.032224103808403015, 0.02340812236070633, -0.013453795574605465, -0.03828400373458862, 0.00019668388995341957, -0.05886334553360939, 0.02829950489103794, -0.011681304313242435, -0.02894294075667858, -0.0156210632994771, -0.025587614625692368, -0.005355904344469309, -0.008415039628744125, 0.008364710956811905, -0.020933544263243675, 0.013845553621649742, 0.011375073343515396, 0.0034024554770439863, 0.013591719791293144, 0.03831282630562782, 0.006789857987314463, -0.016561930999159813, -0.0077067469246685505, 0.017976976931095123, -0.044922471046447754, -0.09317181259393692, -0.009833413176238537, 0.0019290000200271606, 0.008832037448883057, 0.04975416138768196, -0.005788398440927267, 0.02413789927959442, -0.006867791526019573, -0.030871326103806496, 0.0018034533131867647, -0.028147924691438675, -0.061592698097229004, 0.03471648693084717, 0.0029623613227158785, 0.04576379805803299, 0.04920250177383423, 0.0066710906103253365, 0.019879451021552086, -0.029847823083400726, 0.04213399812579155, 0.022378113120794296, 0.06034644693136215, 0.018210720270872116, -0.052402056753635406, -0.06233320012688637, 0.02748517319560051, 0.0009044610778801143, 0.03394578769803047, -0.0025600087828934193, -0.07710444182157516, -0.026959320530295372, -0.04725588113069534, 0.09587374329566956, -0.004505184479057789, 0.06266964226961136, 0.011928888969123363, 0.026125216856598854, 0.020802753046154976, -0.03790655732154846, 0.008611896075308323, -0.009999945759773254, 0.0008124966407194734, 0.0023372818250209093, -0.013930312357842922, 0.0445791594684124, -0.03707464411854744, 0.005865194834768772, -0.027623893693089485, -0.0051140510477125645, 0.03622030094265938, 0.029353415593504906, 0.014871746301651001, -0.049538563936948776, -0.0884135365486145, 0.039663538336753845, -0.006087770219892263, -0.005554589908570051, -0.018760336562991142, 0.04400838911533356, 0.06469032168388367, -0.027068525552749634, -0.014268585480749607, -0.03689954802393913, -0.04199261963367462, -0.07164203375577927, -0.02319754846394062, -0.022304972633719444, 0.06034821271896362, 0.01234059315174818, -0.05015625059604645, 0.026312967762351036, 0.024602733552455902, -0.013165849260985851, 0.026101354509592056, -0.00039741327054798603, 0.045131612569093704, -0.0011586755281314254, -0.016506563872098923, 0.008335383608937263, 0.08420206606388092, 0.007974393665790558, 0.01806117594242096, -0.04338707774877548, 0.0017254726262763143, 0.013004262000322342, 0.035513974726200104, 0.0018105749040842056, 0.03481133654713631, 0.028410300612449646, -0.005521140526980162, -0.037166062742471695, -0.009727894328534603, -0.007575748022645712, 0.031769007444381714, 0.01591692864894867, -0.07149645686149597, -0.022819383069872856, -0.025556638836860657, 0.03829556331038475, 0.03599891439080238, -0.039620354771614075, -0.052856698632240295, 0.014543462544679642, 0.029836874455213547, 0.004911733325570822, 0.006350961048156023, -0.002845192328095436, 0.01151148322969675, 0.038910895586013794, 0.019080182537436485, -0.005964197684079409, 0.013235464692115784, 0.01979215256869793, 0.028337698429822922, -0.029424462467432022, 0.0345134362578392, 0.02685575745999813, -0.10838081687688828, 0.007495822850614786, -0.03945600241422653, -0.048700157552957535, 0.029617760330438614, -0.007066475227475166, -0.029409416019916534, -0.014822331257164478, 0.020348375663161278, 0.008603030815720558, -0.005156198516488075, 0.024565963074564934, -0.004429014399647713, 0.042246244847774506, 0.006228230893611908, -0.040713973343372345, -0.006633983459323645, -0.012441592290997505, 0.06379376351833344, 0.01138747576624155, -0.05108489841222763, -0.04554334282875061, 0.000258329208008945, 0.02675539255142212, 0.015998685732483864, 0.0045121400617063046, 0.035585757344961166, -0.025728177279233932, -0.0022018083836883307, 0.025854280218482018, 0.008726329542696476, -0.08949534595012665, -0.0042279548943042755, 0.014192483387887478, 0.0033121018204838037, -0.01194020640105009, -0.007336666341871023, 0.03430375084280968, 0.010065815411508083, 0.019571145996451378, 0.02486649714410305, 0.05963717773556709, -0.002381320344284177, -0.012897028587758541, -0.05677343159914017, -0.008045922964811325, 0.030109083279967308, 0.10458984225988388, 0.06349971145391464, -0.0902666375041008, -0.0014230748638510704, 0.047629497945308685, -0.005494843702763319, -0.06622440367937088, 0.02207377552986145, 0.03912592679262161, 0.08439141511917114, -0.010423487052321434, 0.0105659868568182, -0.03800560534000397, 0.005288270302116871, 0.005335751920938492, 0.005952857900410891, 0.027864310890436172, -0.07598649710416794, -0.017360499128699303, -0.014762528240680695, -0.017516929656267166, 0.030921051278710365, -0.009271711111068726, 0.04128511995077133, 0.05822055786848068, -0.0456681065261364, -0.021587887778878212, 0.032664477825164795, 0.005013902205973864, 0.024362962692975998, 0.052013691514730453, -0.012947490438818932, 0.007668015547096729, 0.012747621163725853, 0.009064197540283203, 0.005395033396780491, -0.06471613794565201, -0.02341090328991413, -0.03957385569810867, 0.006384128239005804, 0.023038262501358986, 0.016163893043994904, 0.031970616430044174, 0.008142382837831974, -0.010445505380630493, 0.020478740334510803, 0.02267698012292385, 0.0035674618557095528, -0.04390260949730873, 0.02594989724457264, 0.004782241769134998, -0.026361459866166115, 0.05352150648832321, 0.05303672328591347, -0.0018899120623245835, 0.040250685065984726, 0.014841049909591675, -0.04965448006987572, 0.034611135721206665, 0.029163721948862076, -0.0370374396443367, 0.06107928231358528, 0.01931428350508213, -0.024129332974553108, 0.013892723247408867, -0.057689569890499115, -0.019153200089931488, 0.06274314969778061, -0.0104749770835042, 0.06092853471636772, 0.014168822206556797, 0.020315535366535187, -0.00742214685305953, -0.07249875366687775, -0.02061198092997074, 0.06763654202222824, -0.019078969955444336, -0.025485828518867493, -0.037090715020895004, -0.03748273849487305, 0.06468653678894043, 0.05475500971078873, -0.025230998173356056, 0.03658314049243927, -0.03558206930756569, 0.00412721186876297, -0.02006283588707447, -0.040070950984954834, -0.03366212919354439, 0.021284595131874084, -0.09109087288379669, -0.0617571622133255, 0.029330993071198463, -0.023756109178066254, -0.012480301782488823, 0.052574045956134796, -0.006037478800863028, 0.007189587689936161, -0.018584808334708214, -0.024014504626393318, -0.039253927767276764, -0.0019910773262381554, 0.016578208655118942, 0.002754555782303214, -0.07257606834173203, 0.06669497489929199, -0.027288293465971947, 0.03512290492653847, -0.04012216255068779, 0.0006304704584181309, -0.056184276938438416, 0.026845846325159073, 0.01171874813735485, -0.007035360671579838, -0.11059699952602386, -0.0017737774178385735, 0.0008525890298187733, 0.035708170384168625, 0.039497245103120804, 0.009014977142214775, -0.009363487362861633, -0.04452665150165558, -0.015306168235838413, 0.007775279227644205, 0.0238527562469244, -0.049062952399253845, -0.029840851202607155, 0.009884377010166645, 0.007368407677859068, 0.01218915730714798, 0.026270395144820213, 0.03921155259013176, -0.02102232351899147, -0.046590857207775116, -0.03964143246412277, -0.006222231313586235, -0.017028534784913063, 0.012820009142160416, 0.06535062193870544, -0.021741028875112534, 0.031689491122961044, 0.019865790382027626, -0.037215035408735275, 0.026745876297354698, -0.0022958426270633936, 0.0018095504492521286, -0.025574250146746635, 0.024400917813181877, 0.0044356766156852245, -0.015722671523690224, 0.0007741103763692081, -0.06032382696866989, -0.027001703158020973, -0.04074037820100784, 0.001984398579224944, 0.019667888060212135, 0.0037972789723426104, 0.08036674559116364, -0.0016786562046036124, -0.01648603193461895, 0.03937697783112526, -0.03000270389020443, -0.013990301638841629, -0.04250183328986168, -0.051923878490924835, -0.016109390184283257, -0.03339380398392677, -0.013268408365547657, 0.0020023153629153967, 0.03535597398877144, -0.08207280933856964, 0.04318299517035484, 0.042447302490472794, -0.008383109234273434, -0.0263237152248621, -0.02173841930925846, -0.04972178116440773, 0.07675917446613312, -0.02865636721253395, 0.03968397527933121, -0.011468784883618355, -0.024121342226862907, -0.03269520029425621, 0.016022393479943275, 0.043653521686792374, -0.021612973883748055, 0.04812530800700188, -0.08864858001470566, -0.030017411336302757, -0.05985622480511665, 0.06505481153726578, -0.059853170067071915, 0.04449130594730377, -0.005449226126074791, 0.09018084406852722, 0.05151943489909172, -0.04078914597630501, -0.008794245310127735, 0.00486722681671381, -0.04789615795016289, -0.006356469821184874, 0.022389404475688934, 0.0336216501891613, -0.0006719402736052871, -0.005734316539019346, 0.07507745921611786, 0.05159412696957588, 0.05322299897670746, -0.012859235517680645, 0.024618180468678474, -0.011983484029769897, 0.014492410235106945, -0.029176125302910805, -0.046488311141729355, -0.008908496238291264, -0.008766178041696548, 0.016541115939617157, -0.04279477149248123, -0.005161352455615997, 0.03063373640179634, 0.004773003049194813, 0.015471100807189941, 0.04255279153585434, -0.06804932653903961, -0.022094659507274628, -0.002926690736785531, -0.01759984903037548, -0.03391116484999657, -0.016117988154292107, 0.02803482674062252, -0.005842387676239014, 0.029265668243169785, 0.02014891430735588, -0.015048426575958729, -0.0111753661185503, 0.006005946546792984, 0.003760319435968995, 0.010096371173858643, 0.004336421377956867, -0.021158697083592415, -0.07886983454227448, 0.019743654876947403, -0.04299156740307808, 0.006879636086523533, 0.004897196311503649, -0.03199371322989464, 0.012173089198768139, 0.006098099518567324, -0.010709347203373909, 0.029287517070770264, 0.008361488580703735, -0.02357981540262699, -0.035802002996206284, 0.0030663209035992622, 0.04971461743116379, 0.007869037799537182, 0.023053284734487534, 0.006221679039299488, 0.016018914058804512, -0.0639345571398735, 0.0014233884867280722, 0.01390507910400629, -0.03822048753499985, -0.000677775009535253, -0.032367583364248276, 0.0018110964447259903, 0.028008289635181427, -0.033390216529369354, 0.04089576378464699, 0.056676290929317474, 0.04725015163421631, 0.007858541794121265, -0.005909656640142202, -0.0374026782810688, 0.0009642730001360178, 0.04712258279323578, 0.015068107284605503, -0.09084785729646683, -0.0183014627546072, -0.010378052480518818, -0.011262909509241581, 0.01483835931867361, -0.06328458338975906, 0.03158270940184593, -0.039874304085969925, 0.005887739360332489, 0.013760249130427837, -0.08227024972438812, 0.05073750391602516, -0.03333717957139015, -0.01784328557550907, -0.09434085339307785, -0.04711056128144264, -0.03830826282501221, -0.01700424589216709, -0.04848729074001312, -0.04147587716579437, 0.024607349187135696, -0.023363759741187096, -0.04393063858151436, -0.004325236193835735, -0.0268165972083807, 0.017535211518406868, 0.045535337179899216, 0.008101162500679493, 0.027319978922605515, -0.01964757591485977, -0.0500638522207737, 0.04529197886586189, -0.011926586739718914, 0.011780159547924995, 0.022706450894474983, 0.026478933170437813, 0.08566772192716599, 0.04917490482330322, 0.044006217271089554, -0.020047280937433243, 0.03049284778535366, 0.005896560847759247, 0.010716656222939491, -0.005336425732821226, -0.032737407833337784, -0.028436297550797462], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'group_ids': ['guardkit__feature_specs']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
CREATE INDEX FOR (n:Community) ON (n.uuid)
{}
ERROR:asyncio:Task exception was never retrieved
future: <Task finished name='Task-303' coro=<FalkorDriver.build_indices_and_constraints() done, defined at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:300> exception=RuntimeError('<asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop')>
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 305, in build_indices_and_constraints
    await self.execute_query(query)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 230, in execute_query
    result = await graph.query(cypher_query_, params)  # type: ignore[reportUnknownArgumentType]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 105, in query
    return await self._query(q, params=params, timeout=timeout, read_only=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 79, in _query
    response = await self.execute_command(*command)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/client.py", line 720, in execute_command
    conn = self.connection or await pool.get_connection()
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/connection.py", line 1194, in get_connection
    async with self._lock:
               ^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 14, in __aenter__
    await self.acquire()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 105, in acquire
    fut = self._get_loop().create_future()
          ~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/mixins.py", line 20, in _get_loop
    raise RuntimeError(f'{self!r} is bound to a different event loop')
RuntimeError: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
WARNING:guardkit.knowledge.graphiti_client:Search request failed: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
CREATE INDEX FOR (n:Entity) ON (n.uuid, n.group_id, n.name, n.created_at)
{}
ERROR:asyncio:Task exception was never retrieved
future: <Task finished name='Task-311' coro=<FalkorDriver.build_indices_and_constraints() done, defined at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:300> exception=RuntimeError('<asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop')>
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 305, in build_indices_and_constraints
    await self.execute_query(query)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 230, in execute_query
    result = await graph.query(cypher_query_, params)  # type: ignore[reportUnknownArgumentType]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 105, in query
    return await self._query(q, params=params, timeout=timeout, read_only=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 79, in _query
    response = await self.execute_command(*command)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/client.py", line 720, in execute_command
    conn = self.connection or await pool.get_connection()
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/connection.py", line 1194, in get_connection
    async with self._lock:
               ^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 14, in __aenter__
    await self.acquire()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 105, in acquire
    fut = self._get_loop().create_future()
          ~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/mixins.py", line 20, in _get_loop
    raise RuntimeError(f'{self!r} is bound to a different event loop')
RuntimeError: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Task <Task pending name='Task-325' coro=<semaphore_gather.<locals>._wrap_coroutine() running at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/helpers.py:131> cb=[gather.<locals>._done_callback() at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/tasks.py:810]> got Future <Future pending> attached to a different loop

        MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity)
     WHERE e.group_id IN $group_ids
            WITH DISTINCT e, n, m, (2 - vec.cosineDistance(e.fact_embedding, vecf32($search_vector)))/2 AS score
            WHERE score > $min_score
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'search_vector': [-0.019678272306919098, 0.04145437479019165, -0.15208914875984192, -0.08751127868890762, 0.060685936361551285, -0.011536049656569958, -0.0356954000890255, 0.06326451152563095, 0.005898250732570887, 0.03596508875489235, -0.0460776761174202, 0.059481438249349594, 0.0731963962316513, -0.0035015461035072803, -0.010767459869384766, 0.0026188043411821127, 0.042661190032958984, -0.04567542299628258, 0.005363617092370987, 0.04486007243394852, 0.017174692824482918, -0.031202269718050957, 0.016036447137594223, -0.0022920984774827957, 0.08285566419363022, 0.012536974623799324, 0.04308679699897766, 0.017869723960757256, -0.05449867248535156, 0.06715884059667587, -0.026934392750263214, 0.033227503299713135, -0.04078983888030052, 0.003484932938590646, -0.025479862466454506, -0.02652379311621189, 0.06887561082839966, 0.0005733506986871362, -0.029584350064396858, 0.03562229871749878, -0.001539326854981482, -0.020368313416838646, 0.023740852251648903, -0.03915613889694214, 0.01963983289897442, -0.004860177170485258, 0.08341535180807114, -0.00909666158258915, 0.03961418941617012, -0.02264111116528511, -0.004619008861482143, 0.035068050026893616, -0.014536296017467976, -0.04993395879864693, 0.06013113632798195, 0.0559917688369751, -0.013428007252514362, 0.0017108998727053404, 0.014681867323815823, 0.022310331463813782, 0.03381912782788277, 0.061756398528814316, -0.02037772163748741, 0.07045856863260269, 0.00499360729008913, -0.032459888607263565, 0.023036682978272438, 0.04308941960334778, 0.0240500345826149, -0.028242910280823708, -0.0029579228721559048, -0.040853410959243774, 0.008793892338871956, 0.023262470960617065, -0.03967183828353882, -0.018579205498099327, -0.06695448607206345, -0.002489942591637373, -0.02617836929857731, 0.045291196554899216, 0.004710789304226637, 0.011663787998259068, -0.0036145183257758617, -0.002416863339021802, 0.04015050455927849, -0.03343840315937996, -0.011631639674305916, -0.00844602845609188, -0.016957048326730728, 0.007057918701320887, 0.02226279303431511, 0.002995438873767853, 0.0018111851532012224, 0.0015182229690253735, -0.03973628953099251, 0.02589903399348259, -0.0006272330647334456, 0.011767647229135036, -0.0492384172976017, -0.058542363345623016, -0.014917286112904549, -0.012216508388519287, 0.013676203787326813, -0.058566536754369736, 0.03772224858403206, 0.05964180827140808, 0.0423254668712616, 0.022949479520320892, -0.022774117067456245, -0.06008358672261238, -0.03383133187890053, 0.030198698863387108, 0.03560342267155647, -0.02526315115392208, 0.008249345235526562, -0.05359608680009842, 0.019221995025873184, 0.021092142909765244, 0.016274355351924896, 0.07800885289907455, 0.017908133566379547, -0.03679491952061653, 0.011676537804305553, 0.036793000996112823, -0.017211860045790672, 0.012664657086133957, -0.06798101216554642, -0.015494957566261292, 0.053091924637556076, -0.04097888618707657, -0.03503381088376045, -0.013990537263453007, -0.015718035399913788, 0.015308920294046402, 0.0068150050938129425, 0.018288258463144302, -0.027750765904784203, -0.05620942637324333, 0.05034608766436577, 0.00658156955614686, 0.037913836538791656, 0.024165406823158264, -0.005590274930000305, 0.005106118507683277, -0.021129272878170013, -0.06092797964811325, 0.03375286981463432, -0.024518007412552834, 0.015498638153076172, -0.03766050934791565, 0.010379175655543804, 0.020013928413391113, 0.017530186101794243, 0.020746007561683655, 0.03018259070813656, -0.04491570591926575, 0.02726386860013008, 0.01579068787395954, 0.034235142171382904, 0.012131059542298317, 0.05927712097764015, 0.029664726927876472, -0.040221668779850006, 0.06505591422319412, 0.013997580856084824, 0.006343886721879244, 0.04485567286610603, -0.023017926141619682, -0.016303986310958862, 0.05887455493211746, 0.003787028370425105, -0.06779701262712479, -0.005519767291843891, -0.04536237567663193, -0.02908109314739704, 0.06589078158140182, 0.009105178527534008, -0.048932116478681564, 0.0702362060546875, 0.015577378682792187, 0.022807935252785683, -0.05566418915987015, 0.05768178403377533, 0.024182241410017014, -0.07004685699939728, -0.009858010336756706, -0.01198254432529211, -0.03954509273171425, 0.01700400933623314, -0.01538708247244358, 0.07074327766895294, 0.027945393696427345, -0.0715738981962204, -0.06478138267993927, -0.06457969546318054, -0.03879387676715851, 0.04865585267543793, -0.06224197521805763, 0.01791718602180481, -0.056931640952825546, -0.04821635037660599, -0.016800135374069214, -0.014499199576675892, -0.00016610653256066144, -0.06166314333677292, -0.013199149630963802, 0.002707129344344139, 0.028006387874484062, -0.03186313807964325, 0.027730202302336693, 0.03960445895791054, -0.026549363508820534, -0.0013489174889400601, 0.022544309496879578, -0.006144820246845484, 0.0014451746828854084, 0.021434560418128967, 0.009937262162566185, 0.00638539670035243, 0.04972505569458008, 0.010563386604189873, 0.03476741909980774, 0.0353098101913929, 0.008606175892055035, 0.05145268142223358, 0.004322201479226351, 0.007664940785616636, -0.041306138038635254, -0.035920560359954834, -0.013973681256175041, -0.023324865847826004, -0.033298611640930176, 0.027322586625814438, 2.2270212866715156e-05, 0.03547924757003784, -0.015216288156807423, 0.017451131716370583, 0.044429097324609756, -0.027702681720256805, 0.005388504825532436, -0.0013571048621088266, 0.03524407744407654, -0.023104004561901093, 0.008536252193152905, -0.01720883883535862, 0.02564302645623684, 0.03022625483572483, -0.01345042884349823, 0.026601038873195648, 0.04824414104223251, -0.034497812390327454, 0.00541694276034832, 0.02385224774479866, 0.048989731818437576, 0.019454237073659897, -0.058079589158296585, 0.032224103808403015, 0.02340812236070633, -0.013453795574605465, -0.03828400373458862, 0.00019668388995341957, -0.05886334553360939, 0.02829950489103794, -0.011681304313242435, -0.02894294075667858, -0.0156210632994771, -0.025587614625692368, -0.005355904344469309, -0.008415039628744125, 0.008364710956811905, -0.020933544263243675, 0.013845553621649742, 0.011375073343515396, 0.0034024554770439863, 0.013591719791293144, 0.03831282630562782, 0.006789857987314463, -0.016561930999159813, -0.0077067469246685505, 0.017976976931095123, -0.044922471046447754, -0.09317181259393692, -0.009833413176238537, 0.0019290000200271606, 0.008832037448883057, 0.04975416138768196, -0.005788398440927267, 0.02413789927959442, -0.006867791526019573, -0.030871326103806496, 0.0018034533131867647, -0.028147924691438675, -0.061592698097229004, 0.03471648693084717, 0.0029623613227158785, 0.04576379805803299, 0.04920250177383423, 0.0066710906103253365, 0.019879451021552086, -0.029847823083400726, 0.04213399812579155, 0.022378113120794296, 0.06034644693136215, 0.018210720270872116, -0.052402056753635406, -0.06233320012688637, 0.02748517319560051, 0.0009044610778801143, 0.03394578769803047, -0.0025600087828934193, -0.07710444182157516, -0.026959320530295372, -0.04725588113069534, 0.09587374329566956, -0.004505184479057789, 0.06266964226961136, 0.011928888969123363, 0.026125216856598854, 0.020802753046154976, -0.03790655732154846, 0.008611896075308323, -0.009999945759773254, 0.0008124966407194734, 0.0023372818250209093, -0.013930312357842922, 0.0445791594684124, -0.03707464411854744, 0.005865194834768772, -0.027623893693089485, -0.0051140510477125645, 0.03622030094265938, 0.029353415593504906, 0.014871746301651001, -0.049538563936948776, -0.0884135365486145, 0.039663538336753845, -0.006087770219892263, -0.005554589908570051, -0.018760336562991142, 0.04400838911533356, 0.06469032168388367, -0.027068525552749634, -0.014268585480749607, -0.03689954802393913, -0.04199261963367462, -0.07164203375577927, -0.02319754846394062, -0.022304972633719444, 0.06034821271896362, 0.01234059315174818, -0.05015625059604645, 0.026312967762351036, 0.024602733552455902, -0.013165849260985851, 0.026101354509592056, -0.00039741327054798603, 0.045131612569093704, -0.0011586755281314254, -0.016506563872098923, 0.008335383608937263, 0.08420206606388092, 0.007974393665790558, 0.01806117594242096, -0.04338707774877548, 0.0017254726262763143, 0.013004262000322342, 0.035513974726200104, 0.0018105749040842056, 0.03481133654713631, 0.028410300612449646, -0.005521140526980162, -0.037166062742471695, -0.009727894328534603, -0.007575748022645712, 0.031769007444381714, 0.01591692864894867, -0.07149645686149597, -0.022819383069872856, -0.025556638836860657, 0.03829556331038475, 0.03599891439080238, -0.039620354771614075, -0.052856698632240295, 0.014543462544679642, 0.029836874455213547, 0.004911733325570822, 0.006350961048156023, -0.002845192328095436, 0.01151148322969675, 0.038910895586013794, 0.019080182537436485, -0.005964197684079409, 0.013235464692115784, 0.01979215256869793, 0.028337698429822922, -0.029424462467432022, 0.0345134362578392, 0.02685575745999813, -0.10838081687688828, 0.007495822850614786, -0.03945600241422653, -0.048700157552957535, 0.029617760330438614, -0.007066475227475166, -0.029409416019916534, -0.014822331257164478, 0.020348375663161278, 0.008603030815720558, -0.005156198516488075, 0.024565963074564934, -0.004429014399647713, 0.042246244847774506, 0.006228230893611908, -0.040713973343372345, -0.006633983459323645, -0.012441592290997505, 0.06379376351833344, 0.01138747576624155, -0.05108489841222763, -0.04554334282875061, 0.000258329208008945, 0.02675539255142212, 0.015998685732483864, 0.0045121400617063046, 0.035585757344961166, -0.025728177279233932, -0.0022018083836883307, 0.025854280218482018, 0.008726329542696476, -0.08949534595012665, -0.0042279548943042755, 0.014192483387887478, 0.0033121018204838037, -0.01194020640105009, -0.007336666341871023, 0.03430375084280968, 0.010065815411508083, 0.019571145996451378, 0.02486649714410305, 0.05963717773556709, -0.002381320344284177, -0.012897028587758541, -0.05677343159914017, -0.008045922964811325, 0.030109083279967308, 0.10458984225988388, 0.06349971145391464, -0.0902666375041008, -0.0014230748638510704, 0.047629497945308685, -0.005494843702763319, -0.06622440367937088, 0.02207377552986145, 0.03912592679262161, 0.08439141511917114, -0.010423487052321434, 0.0105659868568182, -0.03800560534000397, 0.005288270302116871, 0.005335751920938492, 0.005952857900410891, 0.027864310890436172, -0.07598649710416794, -0.017360499128699303, -0.014762528240680695, -0.017516929656267166, 0.030921051278710365, -0.009271711111068726, 0.04128511995077133, 0.05822055786848068, -0.0456681065261364, -0.021587887778878212, 0.032664477825164795, 0.005013902205973864, 0.024362962692975998, 0.052013691514730453, -0.012947490438818932, 0.007668015547096729, 0.012747621163725853, 0.009064197540283203, 0.005395033396780491, -0.06471613794565201, -0.02341090328991413, -0.03957385569810867, 0.006384128239005804, 0.023038262501358986, 0.016163893043994904, 0.031970616430044174, 0.008142382837831974, -0.010445505380630493, 0.020478740334510803, 0.02267698012292385, 0.0035674618557095528, -0.04390260949730873, 0.02594989724457264, 0.004782241769134998, -0.026361459866166115, 0.05352150648832321, 0.05303672328591347, -0.0018899120623245835, 0.040250685065984726, 0.014841049909591675, -0.04965448006987572, 0.034611135721206665, 0.029163721948862076, -0.0370374396443367, 0.06107928231358528, 0.01931428350508213, -0.024129332974553108, 0.013892723247408867, -0.057689569890499115, -0.019153200089931488, 0.06274314969778061, -0.0104749770835042, 0.06092853471636772, 0.014168822206556797, 0.020315535366535187, -0.00742214685305953, -0.07249875366687775, -0.02061198092997074, 0.06763654202222824, -0.019078969955444336, -0.025485828518867493, -0.037090715020895004, -0.03748273849487305, 0.06468653678894043, 0.05475500971078873, -0.025230998173356056, 0.03658314049243927, -0.03558206930756569, 0.00412721186876297, -0.02006283588707447, -0.040070950984954834, -0.03366212919354439, 0.021284595131874084, -0.09109087288379669, -0.0617571622133255, 0.029330993071198463, -0.023756109178066254, -0.012480301782488823, 0.052574045956134796, -0.006037478800863028, 0.007189587689936161, -0.018584808334708214, -0.024014504626393318, -0.039253927767276764, -0.0019910773262381554, 0.016578208655118942, 0.002754555782303214, -0.07257606834173203, 0.06669497489929199, -0.027288293465971947, 0.03512290492653847, -0.04012216255068779, 0.0006304704584181309, -0.056184276938438416, 0.026845846325159073, 0.01171874813735485, -0.007035360671579838, -0.11059699952602386, -0.0017737774178385735, 0.0008525890298187733, 0.035708170384168625, 0.039497245103120804, 0.009014977142214775, -0.009363487362861633, -0.04452665150165558, -0.015306168235838413, 0.007775279227644205, 0.0238527562469244, -0.049062952399253845, -0.029840851202607155, 0.009884377010166645, 0.007368407677859068, 0.01218915730714798, 0.026270395144820213, 0.03921155259013176, -0.02102232351899147, -0.046590857207775116, -0.03964143246412277, -0.006222231313586235, -0.017028534784913063, 0.012820009142160416, 0.06535062193870544, -0.021741028875112534, 0.031689491122961044, 0.019865790382027626, -0.037215035408735275, 0.026745876297354698, -0.0022958426270633936, 0.0018095504492521286, -0.025574250146746635, 0.024400917813181877, 0.0044356766156852245, -0.015722671523690224, 0.0007741103763692081, -0.06032382696866989, -0.027001703158020973, -0.04074037820100784, 0.001984398579224944, 0.019667888060212135, 0.0037972789723426104, 0.08036674559116364, -0.0016786562046036124, -0.01648603193461895, 0.03937697783112526, -0.03000270389020443, -0.013990301638841629, -0.04250183328986168, -0.051923878490924835, -0.016109390184283257, -0.03339380398392677, -0.013268408365547657, 0.0020023153629153967, 0.03535597398877144, -0.08207280933856964, 0.04318299517035484, 0.042447302490472794, -0.008383109234273434, -0.0263237152248621, -0.02173841930925846, -0.04972178116440773, 0.07675917446613312, -0.02865636721253395, 0.03968397527933121, -0.011468784883618355, -0.024121342226862907, -0.03269520029425621, 0.016022393479943275, 0.043653521686792374, -0.021612973883748055, 0.04812530800700188, -0.08864858001470566, -0.030017411336302757, -0.05985622480511665, 0.06505481153726578, -0.059853170067071915, 0.04449130594730377, -0.005449226126074791, 0.09018084406852722, 0.05151943489909172, -0.04078914597630501, -0.008794245310127735, 0.00486722681671381, -0.04789615795016289, -0.006356469821184874, 0.022389404475688934, 0.0336216501891613, -0.0006719402736052871, -0.005734316539019346, 0.07507745921611786, 0.05159412696957588, 0.05322299897670746, -0.012859235517680645, 0.024618180468678474, -0.011983484029769897, 0.014492410235106945, -0.029176125302910805, -0.046488311141729355, -0.008908496238291264, -0.008766178041696548, 0.016541115939617157, -0.04279477149248123, -0.005161352455615997, 0.03063373640179634, 0.004773003049194813, 0.015471100807189941, 0.04255279153585434, -0.06804932653903961, -0.022094659507274628, -0.002926690736785531, -0.01759984903037548, -0.03391116484999657, -0.016117988154292107, 0.02803482674062252, -0.005842387676239014, 0.029265668243169785, 0.02014891430735588, -0.015048426575958729, -0.0111753661185503, 0.006005946546792984, 0.003760319435968995, 0.010096371173858643, 0.004336421377956867, -0.021158697083592415, -0.07886983454227448, 0.019743654876947403, -0.04299156740307808, 0.006879636086523533, 0.004897196311503649, -0.03199371322989464, 0.012173089198768139, 0.006098099518567324, -0.010709347203373909, 0.029287517070770264, 0.008361488580703735, -0.02357981540262699, -0.035802002996206284, 0.0030663209035992622, 0.04971461743116379, 0.007869037799537182, 0.023053284734487534, 0.006221679039299488, 0.016018914058804512, -0.0639345571398735, 0.0014233884867280722, 0.01390507910400629, -0.03822048753499985, -0.000677775009535253, -0.032367583364248276, 0.0018110964447259903, 0.028008289635181427, -0.033390216529369354, 0.04089576378464699, 0.056676290929317474, 0.04725015163421631, 0.007858541794121265, -0.005909656640142202, -0.0374026782810688, 0.0009642730001360178, 0.04712258279323578, 0.015068107284605503, -0.09084785729646683, -0.0183014627546072, -0.010378052480518818, -0.011262909509241581, 0.01483835931867361, -0.06328458338975906, 0.03158270940184593, -0.039874304085969925, 0.005887739360332489, 0.013760249130427837, -0.08227024972438812, 0.05073750391602516, -0.03333717957139015, -0.01784328557550907, -0.09434085339307785, -0.04711056128144264, -0.03830826282501221, -0.01700424589216709, -0.04848729074001312, -0.04147587716579437, 0.024607349187135696, -0.023363759741187096, -0.04393063858151436, -0.004325236193835735, -0.0268165972083807, 0.017535211518406868, 0.045535337179899216, 0.008101162500679493, 0.027319978922605515, -0.01964757591485977, -0.0500638522207737, 0.04529197886586189, -0.011926586739718914, 0.011780159547924995, 0.022706450894474983, 0.026478933170437813, 0.08566772192716599, 0.04917490482330322, 0.044006217271089554, -0.020047280937433243, 0.03049284778535366, 0.005896560847759247, 0.010716656222939491, -0.005336425732821226, -0.032737407833337784, -0.028436297550797462], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'group_ids': ['patterns']}
WARNING:guardkit.knowledge.graphiti_client:Search request failed: Task <Task pending name='Task-325' coro=<semaphore_gather.<locals>._wrap_coroutine() running at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/helpers.py:131> cb=[gather.<locals>._done_callback() at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/tasks.py:810]> got Future <Future pending> attached to a different loop
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
CREATE INDEX FOR (n:Saga) ON (n.uuid, n.group_id, n.name)
{}
ERROR:asyncio:Task exception was never retrieved
future: <Task finished name='Task-319' coro=<FalkorDriver.build_indices_and_constraints() done, defined at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:300> exception=RuntimeError('<asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop')>
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 305, in build_indices_and_constraints
    await self.execute_query(query)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 230, in execute_query
    result = await graph.query(cypher_query_, params)  # type: ignore[reportUnknownArgumentType]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 105, in query
    return await self._query(q, params=params, timeout=timeout, read_only=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 79, in _query
    response = await self.execute_command(*command)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/client.py", line 720, in execute_command
    conn = self.connection or await pool.get_connection()
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/connection.py", line 1194, in get_connection
    async with self._lock:
               ^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 14, in __aenter__
    await self.acquire()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 105, in acquire
    fut = self._get_loop().create_future()
          ~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/mixins.py", line 20, in _get_loop
    raise RuntimeError(f'{self!r} is bound to a different event loop')
RuntimeError: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
CALL db.idx.fulltext.createNodeIndex(
                                                {
                                                    label: 'Entity',
                                                    stopwords: ['a', 'is', 'the', 'an', 'and', 'are', 'as', 'at', 'be', 'but', 'by', 'for', 'if', 'in', 'into', 'it', 'no', 'not', 'of', 'on', 'or', 'such', 'that', 'their', 'then', 'there', 'these', 'they', 'this', 'to', 'was', 'will', 'with']
                                                },
                                                'name', 'summary', 'group_id'
                                                )
{}
ERROR:asyncio:Task exception was never retrieved
future: <Task finished name='Task-327' coro=<FalkorDriver.build_indices_and_constraints() done, defined at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:300> exception=RuntimeError('<asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop')>
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 305, in build_indices_and_constraints
    await self.execute_query(query)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 230, in execute_query
    result = await graph.query(cypher_query_, params)  # type: ignore[reportUnknownArgumentType]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 105, in query
    return await self._query(q, params=params, timeout=timeout, read_only=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 79, in _query
    response = await self.execute_command(*command)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/client.py", line 720, in execute_command
    conn = self.connection or await pool.get_connection()
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/connection.py", line 1194, in get_connection
    async with self._lock:
               ^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 14, in __aenter__
    await self.acquire()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 105, in acquire
    fut = self._get_loop().create_future()
          ~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/mixins.py", line 20, in _get_loop
    raise RuntimeError(f'{self!r} is bound to a different event loop')
RuntimeError: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
CREATE INDEX FOR ()-[e:HAS_EPISODE]-() ON (e.uuid, e.group_id)
{}
ERROR:asyncio:Task exception was never retrieved
future: <Task finished name='Task-335' coro=<FalkorDriver.build_indices_and_constraints() done, defined at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:300> exception=RuntimeError('<asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop')>
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 305, in build_indices_and_constraints
    await self.execute_query(query)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 230, in execute_query
    result = await graph.query(cypher_query_, params)  # type: ignore[reportUnknownArgumentType]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 105, in query
    return await self._query(q, params=params, timeout=timeout, read_only=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 79, in _query
    response = await self.execute_command(*command)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/client.py", line 720, in execute_command
    conn = self.connection or await pool.get_connection()
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/connection.py", line 1194, in get_connection
    async with self._lock:
               ^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 14, in __aenter__
    await self.acquire()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 105, in acquire
    fut = self._get_loop().create_future()
          ~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/mixins.py", line 20, in _get_loop
    raise RuntimeError(f'{self!r} is bound to a different event loop')
RuntimeError: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
CREATE INDEX FOR ()-[e:HAS_EPISODE]-() ON (e.uuid, e.group_id)
{}
ERROR:asyncio:Task exception was never retrieved
future: <Task finished name='Task-359' coro=<FalkorDriver.build_indices_and_constraints() done, defined at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:300> exception=RuntimeError('<asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop')>
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 305, in build_indices_and_constraints
    await self.execute_query(query)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 230, in execute_query
    result = await graph.query(cypher_query_, params)  # type: ignore[reportUnknownArgumentType]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 105, in query
    return await self._query(q, params=params, timeout=timeout, read_only=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 79, in _query
    response = await self.execute_command(*command)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/client.py", line 720, in execute_command
    conn = self.connection or await pool.get_connection()
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/connection.py", line 1194, in get_connection
    async with self._lock:
               ^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 14, in __aenter__
    await self.acquire()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 105, in acquire
    fut = self._get_loop().create_future()
          ~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/mixins.py", line 20, in _get_loop
    raise RuntimeError(f'{self!r} is bound to a different event loop')
RuntimeError: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
CREATE INDEX FOR (n:Saga) ON (n.uuid, n.group_id, n.name)
{}
ERROR:asyncio:Task exception was never retrieved
future: <Task finished name='Task-367' coro=<FalkorDriver.build_indices_and_constraints() done, defined at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:300> exception=RuntimeError('<asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop')>
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 305, in build_indices_and_constraints
    await self.execute_query(query)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 230, in execute_query
    result = await graph.query(cypher_query_, params)  # type: ignore[reportUnknownArgumentType]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 105, in query
    return await self._query(q, params=params, timeout=timeout, read_only=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 79, in _query
    response = await self.execute_command(*command)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/client.py", line 720, in execute_command
    conn = self.connection or await pool.get_connection()
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/connection.py", line 1194, in get_connection
    async with self._lock:
               ^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 14, in __aenter__
    await self.acquire()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 105, in acquire
    fut = self._get_loop().create_future()
          ~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/mixins.py", line 20, in _get_loop
    raise RuntimeError(f'{self!r} is bound to a different event loop')
RuntimeError: <asyncio.locks.Lock object at 0x12ae18d70 [locked]> is bound to a different event loop
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:guardkit.knowledge.turn_state_operations:[TurnState] Loaded from local file: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/turn_state_turn_2.json (2215 chars)
INFO:guardkit.knowledge.autobuild_context_loader:[TurnState] Turn continuation loaded: 2215 chars for turn 3
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Coach context categories: ['similar_outcomes', 'architecture_context', 'warnings', 'role_constraints', 'turn_states', 'implementation_modes']
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Context loaded in 0.9s
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Coach context: 6 categories, 2765/7892 tokens
INFO:guardkit.orchestrator.autobuild:Using LLM Coach (primary) for TASK-FIX-A7D3 turn 3
INFO:guardkit.orchestrator.autobuild:[Graphiti] Coach context provided: 2801 chars
WARNING:guardkit.orchestrator.quality_gates.coach_validator:gather_evidence: honesty produced 15 must_fix issue(s) for TASK-FIX-A7D3; downstream gathering skipped.
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] SDK timeout: 2340s (base=1200s, mode=task-work x1.5, complexity=3 x1.3)
INFO:guardkit.orchestrator.sdk_debug:sdk_debug: preserved coach prompt for TASK-FIX-A7D3 turn 3 -> /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-FIX-A7D3/.guardkit/autobuild/TASK-FIX-A7D3/sdk_debug/turn_3/coach
INFO:claude_agent_sdk._internal.transport.subprocess_cli:Using bundled Claude Code CLI: /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (30s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (60s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (90s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (120s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (150s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-A7D3] Coach invocation in progress... (180s elapsed)