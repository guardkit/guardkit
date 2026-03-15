richardwoollcott@Mac deepagents-tutor-exemplar % guardkit init --copy-graphiti
Initializing GuardKit in /Users/richardwoollcott/Projects/appmilla_github/deepagents-tutor-exemplar
  Project: deepagents-tutor-exemplar
  Template: default

Step 1: Applying template...
INFO:guardkit.cli.init:Skipping rule code-style.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/deepagents-tutor-exemplar/.claude/rules/code-style.md
INFO:guardkit.cli.init:Skipping rule quality-gates.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/deepagents-tutor-exemplar/.claude/rules/quality-gates.md
INFO:guardkit.cli.init:Skipping rule workflow.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/deepagents-tutor-exemplar/.claude/rules/workflow.md
INFO:guardkit.cli.init:Skipping .claude/CLAUDE.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/deepagents-tutor-exemplar/.claude/CLAUDE.md
INFO:guardkit.cli.init:No manifest.json in template, skipping
INFO:guardkit.cli.init:Applied template 'default' to /Users/richardwoollcott/Projects/appmilla_github/deepagents-tutor-exemplar
  Applied template: default
  Warning: No source graphiti.yaml found (--copy-graphiti), falling back to project_id only
INFO:guardkit.cli.init:Written project_id 'deepagents-tutor-exemplar' to /Users/richardwoollcott/Projects/appmilla_github/deepagents-tutor-exemplar/.guardkit/graphiti.yaml

Step 2: Seeding project knowledge to Graphiti...
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
WARNING:neo4j.session:Transaction failed and will be retried in 1.1945953057242944s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.0431827910095839s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8442595365476782s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8456175371869499s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9233768127358942s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9170181632366724s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1250319854097253s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.061962465779813s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.0641735984877214s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8159363190833134s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.04800069298066s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.0222639797092936s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.951349904960043s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9540200986761517s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8329641433146562s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.823518873080014s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8259548241634729s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8214298837482612s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1061181543899485s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8651272778749126s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1018890534488288s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9458855040841999s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.0973754061477772s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.0403897770384232s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9505058404337458s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9115464645029292s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9175293699703088s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.0136072429953764s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1445353340684234s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.0332222819736379s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1940559833244255s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9702355018031238s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8457386567657064s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1863872138288984s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9285489085353413s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8665174954971868s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9411096063299202s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.0197943397476752s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1117886184570278s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8539494503731562s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.384761950710899s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.038844256576806s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.2843897051411615s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.6297511436039318s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.0354615941935483s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.144106776010106s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.135846400957333s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.6166606511401675s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.016880509771526s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.9125128356539374s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.6418333297970242s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.6366842173546008s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.094442363606928s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.8650323783822054s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.9495232329208383s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.3837314145385826s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.6452664525500644s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.9002338204531433s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.8427588010755123s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.3843112013401497s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.7443188105636487s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.3099858882901474s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.8888698775250308s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.1013134075566686s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.8362629472569085s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.028423935747232s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.9109039140420576s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.2144176814405703s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.1492858706513482s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.134721043633566s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.1045467933568176s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.9237438722771167s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.245908708724933s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.0497560489496274s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.770765736390868s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.2122907043988347s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.6159440107672955s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.1795165276113986s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.149111930083006s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.3694188435139276s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.9157707413842457s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.792091488873707s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.8029043958700295s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.4848887281251546s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.711246821290426s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.937733388364138s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.595373363024122s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.263930593992002s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.3308547463954543s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.332131971633448s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.065462043475926s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.817608331879897s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.636882112533361s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.357666885426793s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.307163304696267s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.648196382810285s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.8459031642489423s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.57359898141259s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.7859309894244526s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.6803097784012384s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.4588983991843136s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.530235637193552s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.370398581004469s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.288376007324252s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.762241789447112s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.2342741609073107s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.511221937642821s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.607798506357992s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.605715835582344s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.4569048766585s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.4014692321995597s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.4545099188742934s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.279740272641233s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.574214639739758s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.33240957648844s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.307253129068601s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.502741993243647s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.236963507687834s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.7743296928808245s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.3969108081345367s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.544874995528451s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 9.458850948251346s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.27961460042707s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.856299952524706s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.073424079415084s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.629113483538632s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.288497455702935s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.823892799821978s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.670214053218267s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.882196728889651s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.465099889232317s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.340460022006276s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 6.978860897769135s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.491233845524057s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.459248939535274s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 9.35961057788128s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 9.09797803380144s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 6.590751902973099s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.877008429788962s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.985729727871812s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 6.496484836913292s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.233576227908499s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.770335702851093s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 9.218016701635644s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.2083928007241616s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.349689590581423s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.397154764173187s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.800099279083854s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.017182098996747s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 6.510013387051842s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.385277692215785s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.802002950004093s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.576554500023965s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.566053421407556s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.691150659271031s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 9.242715336000076s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.508501300702073s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.078087161408243s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.304761885018362s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.846423156227885s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.980962199471733s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 16.75952479974999s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 16.947606923678936s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 18.958054291741366s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.204795837233384s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.53024827377193s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 18.0098290427213s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 14.041104740959947s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.049100763624965s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.880368283012224s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 18.36383348923689s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 16.800042244486022s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.177677481017913s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 18.830649523456188s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 14.720250157330668s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.711487885256517s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 14.550901955164234s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 12.96003678528654s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.401241683134284s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 16.112403139008837s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 16.385775945216366s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.717906192048552s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 15.882691970916257s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 19.074824837785428s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.997893232233835s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 15.035309991334183s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.714679734198906s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.979981522865838s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 14.322641773809359s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 18.526907458337266s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.620510401910915s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.260278802961356s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.292861316008803s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.769401027175988s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 15.903669548354223s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 14.701561797602476s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.30581107215587s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 19.144768503174134s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 14.890159361321993s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 18.968369049230724s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 26.57209903431987s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 26.29026282513751s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 38.05332733323789s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 31.808384462024215s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 30.568728448138266s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 30.21773789492313s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 33.398993824072974s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 34.83755494577956s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 32.927458450907295s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 31.890973681469845s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:neo4j.session:Transaction failed and will be retried in 36.945150476781386s (Couldn't connect to localhost:7687 (resolved to ('127.0.0.1:7687', '[::1]:7687')):
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687))
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0)))
WARNING:guardkit.knowledge.graphiti_client:Graphiti connection timed out after 30.0s. Is the database running?
  Warning: Graphiti unavailable, skipping seeding

GuardKit initialized successfully!

  Seeded: project knowledge (project overview from CLAUDE.md/README.md)
  Not yet seeded: system knowledge (templates, rules, role constraints, implementation modes)

Next steps:
  1. Seed system knowledge: guardkit graphiti seed-system
  2. Create a task: /task-create "Your first task"
  3. Work on it: /task-work TASK-XXX
  4. Complete it: /task-complete TASK-XXX

  Tip: For multi-project FalkorDB setups, use --copy-graphiti to share config across projects.
/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py:2047: RuntimeWarning: coroutine 'Neo4jDriver._execute_index_query' was never awaited
  handle = None  # Needed to break cycles when an exception occurs.
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
<sys>:0: RuntimeWarning: coroutine 'Neo4jDriver._execute_index_query' was never awaited
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
richardwoollcott@Mac deepagents-tutor-exemplar %