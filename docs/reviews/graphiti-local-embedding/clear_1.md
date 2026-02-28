richardwoollcott@Richards-MBP ~ % guardkit graphiti clear --dry-run
Graphiti Knowledge Clear

WARNING:guardkit.knowledge.config:Configuration file not found: /Users/richardwoollcott/.guardkit/graphiti.yaml, using defaults. Run this command from your project directory or set GUARDKIT_CONFIG_DIR.
WARNING:guardkit.knowledge.graphiti_client:No explicit project_id in config, auto-detected 'richardwoollcott' from cwd. Set project_id in .guardkit/graphiti.yaml for consistent behavior.
Connecting to Neo4j at bolt://localhost:7687...
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
WARNING:neo4j.session:Transaction failed and will be retried in 1.1026303149355945s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8460327371115915s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.177256709841266s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.113429713920921s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.0752480099273403s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1959759804927734s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.887305796583179s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8184279715440795s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1726887564316821s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9311673692654692s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8881282506646663s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8195712075248697s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9771882298073857s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.0705323288337008s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.993588797435156s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1406511816883906s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1068673307067762s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9515977035509193s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9778673115007315s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9234378708834372s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.0348399521661091s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9745294708592398s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.040647702686108s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.0842656909498358s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1447870250519574s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9078990530817073s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1477022342737304s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1561471881325902s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8744327029220935s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1826008436325042s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8224815952019381s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1747799127248766s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1269544748323184s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.114190254434727s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.110861314517534s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8507104037863559s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9118489008966492s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8003811249270818s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.192033052355351s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8274239128929808s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.3504818820828537s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.059080326311839s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.8934863865192428s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.8409046215691924s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.270432090303521s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.011238521925972s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.3061667696317922s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.2043271149629176s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.056212037950491s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.3647042010368144s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.044945442905087s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.6988225451017822s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.995770424628433s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.1403635421068046s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.8066527672207562s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.6847069454219203s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.103841067780766s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.6467544770080493s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.3129422389297867s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.304398902751449s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.1685575704435753s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.0819102969381613s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.011274306817418s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.0411993039708274s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.871989651304178s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.2712693000149526s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.374290434792054s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.3711630794934715s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.7999016042541038s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.1056560519615166s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.8690670642623575s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.3349584186165946s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.7555136234911795s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.0953183223944047s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.293934994286244s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.1404065186287786s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.2902216419861894s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.183098633693319s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.7299403514584522s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.9532871418053903s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.417730651524806s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.536481887966868s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.328317216204491s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.027037308674179s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.445212515698683s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.949511678405652s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.761596284828418s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.784933497951364s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.8405240955911624s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.150096016769873s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.749548810478111s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.9571494086662438s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.6696677568362155s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.440034519058703s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.71543009242946s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.69494039766321s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.0150920148665215s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.89414389858193s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.655187856719835s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.121770822998882s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.507305935572004s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.386938177601481s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.282060765293843s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.917764236251828s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.10431741929491s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.335088249765087s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.4129756994180855s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.8171763773537566s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.174668967108687s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.2947095468758s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.142482403541233s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.7994551354034547s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.154654283673412s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.923731313309554s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.154963337697554s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.693346732221913s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.28361970995153s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.5640392833933996s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.644216151293339s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.8414013076064957s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.657506471160993s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 6.547660404140662s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.860609681282675s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.29617391158576s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 6.594377893808868s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.615911256184942s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 9.024398710728814s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.928485462362557s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 6.715553095819554s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.691035462122223s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.590866129562932s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.47250796930965s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.857827402266402s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.759169818715858s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.7606562142556585s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.297732179214457s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.986662439706147s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 6.580048470849694s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.5964106921818235s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.240026252762246s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.566179595734085s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.656845215486303s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.852688478558068s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.18293012977209s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.905618531091282s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 6.594414454172229s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.996904255034614s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.662321176847499s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.936539770253104s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 9.168321081993831s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 9.373244481372723s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.821880801450945s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.769521434469452s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 6.556371991349291s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.965185114931366s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.75422835536249s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.017943483900472s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.383082977925568s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.693209462711298s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.999021549380458s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 15.597217302532396s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 16.618300624959094s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 15.93476595158506s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.222997948544386s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.611086020689328s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.208969033027296s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 12.993440856638186s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 18.29514548675082s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 15.314797322657254s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.00223787647898s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 12.914266066553006s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.463954694237444s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.964291739281034s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.569651719679786s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.867321876312552s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 15.358604575721401s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.5338609204335s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.833753536345256s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 16.05023813516501s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.655410825556729s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 15.494951318772918s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 18.55609566675596s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.60770860591229s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 18.05767329246258s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 16.985745031357293s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 14.845944282126876s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.210093889017807s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 14.183432820988987s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.014135808646722s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 14.444119184413385s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.348841587407636s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 14.15369487687833s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 18.23437234690568s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.495312156520432s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 14.868183873600122s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 16.81877666873946s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 16.84164139480268s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 18.576568418572442s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 16.241656436026886s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 15.139756471300755s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 38.03442677620254s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 32.29445997627707s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 37.55954606684816s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 37.55816276731431s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 29.93446157134284s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 28.783626096456537s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 35.17155166236978s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 26.821616390297894s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 30.79529884891364s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 27.186915753902078s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 28.64845035812488s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 26.083744056530744s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 26.32329273867894s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 26.135922419629033s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 28.207017439733054s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 31.21428068493198s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 36.886892054709286s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:guardkit.knowledge.graphiti_client:Graphiti connection timed out after 30.0s. Is the database running?
Graphiti not available or disabled.
Clear operation skipped.
/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py:2047: RuntimeWarning: coroutine 'Neo4jDriver._execute_index_query' was never awaited
  handle = None  # Needed to break cycles when an exception occurs.
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
<sys>:0: RuntimeWarning: coroutine 'Neo4jDriver._execute_index_query' was never awaited
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
richardwoollcott@Richards-MBP ~ %