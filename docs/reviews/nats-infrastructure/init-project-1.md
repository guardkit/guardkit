richardwoollcott@Mac nats-infrastructure % guardkit init nats-asyncio-service
Initializing GuardKit in
/Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure
  Project: nats-infrastructure
  Template: nats-asyncio-service

Step 1: Applying template...
INFO:guardkit.cli.init:Applying template layer: nats-asyncio-service
INFO:guardkit.cli.init:Skipping agent faststream-nats-broker-specialist-ext.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/agents/faststream-nats-broker-specialist-ext.md
INFO:guardkit.cli.init:Skipping agent faststream-nats-broker-specialist.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/agents/faststream-nats-broker-specialist.md
INFO:guardkit.cli.init:Skipping agent faststream-test-natsbroker-specialist-ext.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/agents/faststream-test-natsbroker-specialist-ext.md
INFO:guardkit.cli.init:Skipping agent faststream-test-natsbroker-specialist.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/agents/faststream-test-natsbroker-specialist.md
INFO:guardkit.cli.init:Skipping agent nats-docker-integration-test-specialist-ext.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/agents/nats-docker-integration-test-specialist-ext.md
INFO:guardkit.cli.init:Skipping agent nats-docker-integration-test-specialist.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/agents/nats-docker-integration-test-specialist.md
INFO:guardkit.cli.init:Skipping agent nats-handler-service-separation-specialist-ext.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/agents/nats-handler-service-separation-specialist-ext.md
INFO:guardkit.cli.init:Skipping agent nats-handler-service-separation-specialist.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/agents/nats-handler-service-separation-specialist.md
INFO:guardkit.cli.init:Skipping agent pydantic-nats-schema-specialist-ext.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/agents/pydantic-nats-schema-specialist-ext.md
INFO:guardkit.cli.init:Skipping agent pydantic-nats-schema-specialist.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/agents/pydantic-nats-schema-specialist.md
INFO:guardkit.cli.init:Skipping agent pydantic-settings-config-specialist-ext.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/agents/pydantic-settings-config-specialist-ext.md
INFO:guardkit.cli.init:Skipping agent pydantic-settings-config-specialist.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/agents/pydantic-settings-config-specialist.md
INFO:guardkit.cli.init:Skipping agent pytest-asyncio-service-unit-test-specialist-ext.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/agents/pytest-asyncio-service-unit-test-specialist-ext.md
INFO:guardkit.cli.init:Skipping agent pytest-asyncio-service-unit-test-specialist.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/agents/pytest-asyncio-service-unit-test-specialist.md
INFO:guardkit.cli.init:Skipping rule code-style.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/rules/code-style.md
INFO:guardkit.cli.init:Skipping rule guidance/faststream-nats-broker-specialist.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/rules/guidance/faststream-nats-broker-specialist.md
INFO:guardkit.cli.init:Skipping rule guidance/faststream-test-natsbroker-specialist.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/rules/guidance/faststream-test-natsbroker-specialist.md
INFO:guardkit.cli.init:Skipping rule guidance/nats-docker-integration-test-specialist.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/rules/guidance/nats-docker-integration-test-specialist.md
INFO:guardkit.cli.init:Skipping rule guidance/nats-handler-service-separation-specialist.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/rules/guidance/nats-handler-service-separation-specialist.md
INFO:guardkit.cli.init:Skipping rule guidance/pydantic-nats-schema-specialist.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/rules/guidance/pydantic-nats-schema-specialist.md
INFO:guardkit.cli.init:Skipping rule guidance/pydantic-settings-config-specialist.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/rules/guidance/pydantic-settings-config-specialist.md
INFO:guardkit.cli.init:Skipping rule guidance/pytest-asyncio-service-unit-test-specialist.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/rules/guidance/pytest-asyncio-service-unit-test-specialist.md
INFO:guardkit.cli.init:Skipping rule patterns/correlation-id-linking-for-request/response-tracing.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/rules/patterns/correlation-id-linking-for-request/response-tracing.md
INFO:guardkit.cli.init:Skipping rule patterns/environment-variable-configuration-via-pydantic-settings.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/rules/patterns/environment-variable-configuration-via-pydantic-settings.md
INFO:guardkit.cli.init:Skipping rule patterns/explicit-unidirectional-dependency-flow-(handler-->-service).md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/rules/patterns/explicit-unidirectional-dependency-flow-(handler-->-service).md
INFO:guardkit.cli.init:Skipping rule patterns/factory-function-pattern-for-test-data.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/rules/patterns/factory-function-pattern-for-test-data.md
INFO:guardkit.cli.init:Skipping rule patterns/handler/service-separation.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/rules/patterns/handler/service-separation.md
INFO:guardkit.cli.init:Skipping rule patterns/in-memory-broker-testing-via-testnatsbroker.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/rules/patterns/in-memory-broker-testing-via-testnatsbroker.md
INFO:guardkit.cli.init:Skipping rule patterns/lifespan-context-manager-for-startup/shutdown.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/rules/patterns/lifespan-context-manager-for-startup/shutdown.md
INFO:guardkit.cli.init:Skipping rule patterns/marker-gated-integration-tests.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/rules/patterns/marker-gated-integration-tests.md
INFO:guardkit.cli.init:Skipping rule patterns/module-level-singleton-for-service-instances.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/rules/patterns/module-level-singleton-for-service-instances.md
INFO:guardkit.cli.init:Skipping rule patterns/pub/sub-messaging.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/rules/patterns/pub/sub-messaging.md
INFO:guardkit.cli.init:Skipping rule testing.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/rules/testing.md
INFO:guardkit.cli.init:Skipping .claude/CLAUDE.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/CLAUDE.md
INFO:guardkit.cli.init:Skipping manifest.json: already exists at /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.claude/manifest.json
INFO:guardkit.cli.init:Applied template 'nats-asyncio-service' to /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure
  Applied template: nats-asyncio-service

Found existing graphiti.yaml at
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/.guardkit/graphiti
.yaml
Copy infrastructure config to this project? [y/n] (y): n
INFO:guardkit.cli.init:Written project_id 'nats-infrastructure' to /Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.guardkit/graphiti.yaml
  Written project_id to .guardkit/graphiti.yaml

Step 2: Seeding project knowledge to Graphiti...
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
  Seeding episode 1/1...INFO:graphiti_core.graphiti:Completed add_episode in 69110.11290550232 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [project_architecture_nats-infrastructure]: nodes=6, edges=8, invalidated=0
 done (69.3s)
  Project knowledge seeded successfully (69.3s total)
    OK project_overview: Seeded from README.md
Seed system knowledge now? (recommended for AutoBuild) [y/n] (y): y

Step 3: Seeding system knowledge...
INFO:graphiti_core.graphiti:Completed add_episode in 130504.70805168152 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [template_nats-asyncio-service]: nodes=6, edges=5, invalidated=0
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced template 'nats-asyncio-service'
INFO:graphiti_core.graphiti:Completed add_episode in 180416.08500480652 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [agent_nats-asyncio-service_nats-docker-integration-test-specialist]: nodes=7, edges=6, invalidated=0
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced agent 'nats-docker-integration-test-specialist'
INFO:graphiti_core.graphiti:Completed add_episode in 151823.1701850891 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [agent_nats-asyncio-service_pytest-asyncio-service-unit-test-specialist]: nodes=5, edges=4, invalidated=0
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced agent 'pytest-asyncio-service-unit-test-specialist'
INFO:graphiti_core.graphiti:Completed add_episode in 152114.2439842224 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [agent_nats-asyncio-service_nats-handler-service-separation-specialist]: nodes=4, edges=4, invalidated=0
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced agent 'nats-handler-service-separation-specialist'
INFO:graphiti_core.graphiti:Completed add_episode in 191708.1241607666 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [agent_nats-asyncio-service_faststream-test-natsbroker-specialist]: nodes=5, edges=7, invalidated=0
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced agent 'faststream-test-natsbroker-specialist'
INFO:graphiti_core.graphiti:Completed add_episode in 162786.20886802673 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [agent_nats-asyncio-service_pydantic-nats-schema-specialist]: nodes=4, edges=4, invalidated=0
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced agent 'pydantic-nats-schema-specialist'
INFO:graphiti_core.graphiti:Completed add_episode in 133414.5951271057 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [agent_nats-asyncio-service_pydantic-settings-config-specialist]: nodes=3, edges=2, invalidated=0
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced agent 'pydantic-settings-config-specialist'
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 240s: agent_nats-asyncio-service_faststream-nats-broker-specialist
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync agent 'faststream-nats-broker-specialist' (episode creation returned None)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 164499.96614456177 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [rule_nats-asyncio-service_code-style]: nodes=6, edges=9, invalidated=0
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'code-style'
INFO:graphiti_core.graphiti:Completed add_episode in 95594.79093551636 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [rule_nats-asyncio-service_testing]: nodes=2, edges=1, invalidated=0
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'testing'
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to parse agent frontmatter: while parsing a block mapping
  in "<unicode string>", line 1, column 1:
    paths: "**/app.py", "**/handlers ...
    ^
expected <block end>, but found ','
  in "<unicode string>", line 1, column 19:
    paths: "**/app.py", "**/handlers/*.py", "**/config.py"
                      ^
INFO:graphiti_core.graphiti:Completed add_episode in 171760.9179019928 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [rule_nats-asyncio-service_module-level-singleton-for-service-instances_chunk1]: nodes=6, edges=3, invalidated=0
INFO:graphiti_core.graphiti:Completed add_episode in 117389.04118537903 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [rule_nats-asyncio-service_module-level-singleton-for-service-instances_chunk2]: nodes=4, edges=2, invalidated=0
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'module-level-singleton-for-service-instances' (2 chunks)
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to parse agent frontmatter: while parsing a block mapping
  in "<unicode string>", line 1, column 1:
    paths: "**/handlers/*.py", "**/s ...
    ^
expected <block end>, but found ','
  in "<unicode string>", line 1, column 26:
    paths: "**/handlers/*.py", "**/services/*.py", "**/app.py"
                             ^
INFO:graphiti_core.graphiti:Completed add_episode in 96243.92199516296 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [rule_nats-asyncio-service_explicit-unidirectional-dependency-flow-(handler-->-service)_chunk1]: nodes=2, edges=1, invalidated=0
INFO:graphiti_core.graphiti:Completed add_episode in 103222.32723236084 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [rule_nats-asyncio-service_explicit-unidirectional-dependency-flow-(handler-->-service)_chunk2]: nodes=3, edges=2, invalidated=0
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'explicit-unidirectional-dependency-flow-(handler-->-service)' (2 chunks)
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to parse agent frontmatter: while parsing a block mapping
  in "<unicode string>", line 1, column 1:
    paths: "**/config.py", "**/.env* ...
    ^
expected <block end>, but found ','
  in "<unicode string>", line 1, column 22:
    paths: "**/config.py", "**/.env*", "**/docker-compose ...
                         ^
INFO:graphiti_core.graphiti:Completed add_episode in 93654.20699119568 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [rule_nats-asyncio-service_environment-variable-configuration-via-pydantic-settings_chunk1]: nodes=2, edges=1, invalidated=0
INFO:graphiti_core.graphiti:Completed add_episode in 95676.10883712769 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [rule_nats-asyncio-service_environment-variable-configuration-via-pydantic-settings_chunk2]: nodes=2, edges=1, invalidated=0
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'environment-variable-configuration-via-pydantic-settings' (2 chunks)
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to parse agent frontmatter: while parsing a block mapping
  in "<unicode string>", line 1, column 1:
    paths: "**/tests/conftest.py", " ...
    ^
expected <block end>, but found ','
  in "<unicode string>", line 1, column 30:
    paths: "**/tests/conftest.py", "**/tests/*.py"
                                 ^
