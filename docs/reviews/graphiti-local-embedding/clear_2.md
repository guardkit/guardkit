richardwoollcott@Richards-MBP ~ % guardkit graphiti clear --dry-run
Graphiti Knowledge Clear

WARNING:guardkit.knowledge.config:Configuration file not found: /Users/richardwoollcott/.guardkit/graphiti.yaml, using defaults. Run this command from your project directory or set GUARDKIT_CONFIG_DIR.
WARNING:guardkit.knowledge.graphiti_client:No explicit project_id in config, auto-detected 'richardwoollcott' from cwd. Set project_id in .guardkit/graphiti.yaml for consistent behavior.
Connecting to Neo4j at bolt://localhost:7687...
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
WARNING:neo4j.session:Transaction failed and will be retried in 0.8584517851002981s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9891410915631423s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1424770579577874s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1943752931772773s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1884097562385714s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.0031598149313128s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.01269307244024s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8854942379982365s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8998047705327465s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9746602285409631s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8643499084322237s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9594957781843525s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9690247688203284s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.066791294637568s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8170393903941715s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9606786022326406s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.0754328254533088s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1426098670319957s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8829453690546047s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1324545848100342s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.891788717181314s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9363798628850137s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8081537059768797s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9886338853898166s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.0903443045296943s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8257353826643186s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.0696796198864962s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8412058613962514s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.0718456978883952s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.019939626177063s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1709633465351499s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9835087460881305s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1445762392349275s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9720120814653943s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.1369215173883411s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.8981716100050984s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9074028184366909s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.02448832684889s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9578249571272526s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 0.9881086722080952s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.176776430822595s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.367480937070228s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.7543040546505624s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.3374669185147967s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.044727400113541s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.0079900821975665s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.7434888136980689s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.8384520065159653s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.6737123819443653s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.68799864483044s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.3721638157923057s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.3665188582086123s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.712089304017439s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.164006171999683s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.238590844890189s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.0464933217346966s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.7762014149311804s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.252918652652741s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.1994087030090275s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.952327348725726s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.6169346568676481s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.335738842255683s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.117503247221661s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.9905070713962587s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.6537559295787507s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.9228319325501784s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.7505777701961822s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.9563893760991955s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.3355492693350812s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.188433743978079s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.3593988664372834s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.6590360288752566s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.9988292555630678s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 2.3300009178921113s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.6899585578632361s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.6601599348598017s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.8121572488628204s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.8706400946086719s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.9087475334014807s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 1.7487779409536404s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.408903821189279s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.757974818754184s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.246495595860673s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.518018406614069s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.6037473119451304s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.548401343273912s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.226529645406782s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.525421150543012s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.114815747154859s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.798784251216562s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.315476062238761s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.389337405279978s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.76398493779377s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.711132489629009s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.5316855348945984s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.362509902057166s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.239901281941298s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.487048187341383s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.6733174817171332s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.566071980346018s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.3909334761203342s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.444697816342226s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.013895179919815s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.981811537587301s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.648311426534644s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.628766780430416s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.4683423944102305s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.733001356263305s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.549162917746665s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.4223096926378216s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.483482313776073s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.231279870337668s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.398746227692776s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.7198242518771543s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.561611870048542s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.981217435853409s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.3907371718830204s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.191416106040129s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 4.78339628781605s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 3.6099182102658234s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.118198027516982s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 9.34964993379044s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 9.270204908998327s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.427804749170896s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 9.422587590512123s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.114744992087595s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 9.365895343106509s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.870047213979866s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.878230433461081s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.973848056984813s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 6.665156193323327s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.9926932592183135s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.897675355215107s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.711376367723918s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 9.30162871597879s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.480594001602495s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 6.657809474291642s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 6.979051269463093s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.061648304695749s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.442054186374818s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.995249140447754s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.968531117242687s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 6.580274592662355s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.688580000332387s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.78932111784717s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 6.997193324089414s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 6.7201148619106235s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 9.23371636435106s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 9.169164308978154s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.682199360261625s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.878797972487694s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 6.6291414725640365s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 9.125533075865013s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 6.461682160839391s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.308746105708972s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.828558029116266s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 9.504229753340418s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.639604081402254s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 8.904036572447282s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 7.452457407568034s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 14.39551384038791s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 14.807147645173652s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 14.871591651944247s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 12.898882701524128s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 18.166742778191068s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.176014327071552s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 12.935242734924417s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.16336966687982s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 15.344313894606621s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.169009199518996s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.39461490266714s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 19.009318177911815s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 12.963312129615227s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 18.86607878150411s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 12.840254614807264s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 19.169633185898967s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 15.590890908539267s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.913748212042588s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 16.9023499556536s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.99687346854765s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 16.84171296995916s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 18.691161509723877s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.21121111545831s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.606124208085813s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 18.41915332586278s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 16.929885054541835s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 14.746379007967677s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 16.93320101006834s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 14.151071387951061s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 18.536581329713307s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 15.538501083021032s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 15.787019688224696s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 14.733737769873061s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 14.456024773079713s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.40212289554791s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 15.749506924943397s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.598759544860243s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 16.33722479429764s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 13.528853724544842s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 17.14187925417029s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 37.51117779139078s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 28.110088520089278s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 32.721904933809334s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 35.792711876948644s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 29.353525753144325s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 29.484601821539528s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 36.8138545729981s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 26.303911773049556s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 29.482862795619987s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 28.361230723191646s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:neo4j.session:Transaction failed and will be retried in 29.308753146001717s (Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):
Failed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 61] Connect call failed ('::1', 7687, 0, 0))
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed ('127.0.0.1', 7687)))
WARNING:guardkit.knowledge.graphiti_client:Graphiti connection timed out after 30.0s. Is the database running?
Graphiti not available or disabled.
Clear operation skipped.
<sys>:0: RuntimeWarning: coroutine 'Neo4jDriver._execute_index_query' was never awaited
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
richardwoollcott@Richards-MBP ~ %