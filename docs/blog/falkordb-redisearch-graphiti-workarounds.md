# FalkorDB + Graphiti: When Your Knowledge Graph Searches Silently Return Zero Results

> **TL;DR**: If you're using graphiti-core with FalkorDB and your searches return empty results despite data being present, you've likely hit a RediSearch tokenization bug. Underscores in group_ids break fulltext queries. The fix is a 10-line monkey-patch. Here's the full story.

---

I've been building [GuardKit](https://github.com/appmilla/guardkit), an AI-assisted development tool that uses [Graphiti](https://github.com/getzep/graphiti) (by Zep) as its knowledge graph layer, backed by [FalkorDB](https://www.falkordb.com/) — a Redis-based graph database with RediSearch integration.

After migrating from Neo4j to FalkorDB, everything appeared to work. Writes succeeded. The database contained 44 named graphs and 406 episodes. But every search returned zero results.

This post documents the three bugs I found, why they were deceptively hard to diagnose, and the workarounds that fixed them.

---

## The Setup

Graphiti is a temporal knowledge graph library that extracts entities and relationships from unstructured text. It supports both Neo4j and FalkorDB as backends. FalkorDB's appeal is clear: Redis-based, lighter operational footprint than Neo4j, and it became Graphiti's default backend in late 2025.

GuardKit uses Graphiti to maintain system-level context about projects — architecture decisions, command workflows, technology stacks, design patterns. Each knowledge domain gets its own `group_id`, and FalkorDB maps each group_id to a separate named graph database. This is a clean multi-tenant architecture.

The group_ids follow standard Python naming conventions: `product_knowledge`, `command_workflows`, `guardkit__project_overview`, and so on.

---

## Bug 1: The Off-By-One That Breaks Single-Tenant Searches

This one was already documented upstream ([#1161](https://github.com/getzep/graphiti/issues/1161), [PR #1170](https://github.com/getzep/graphiti/pull/1170)).

Graphiti's `@handle_multiple_group_ids` decorator clones the FalkorDB driver to point at the correct named graph for each group_id. But the length check uses `> 1`:

```python
if group_ids and len(group_ids) > 1:
    # Clone driver per group_id
```

If you search with a single group_id — the common case — cloning is skipped entirely. The search runs against whatever graph the driver happens to be pointing at, which after an `add_episode()` call, is the graph that was last written to. Your search targets the wrong database.

**Fix**: Change `> 1` to `>= 1`. The PR has been open for over five weeks.

---

## Bug 2: The Underscore That Breaks Everything

This was the subtle one. After fixing Bug 1, searches with real query terms started working — our test script returned results from all six groups we tested. But the `guardkit graphiti status` command still showed zero across the board.

The error logs told the story:

```
ERROR: RediSearch: Syntax error at offset 31 near product_knowledge
query: '(@group_id:product_knowledge) ()'
```

Graphiti's `build_fulltext_query()` constructs RediSearch queries with a `@group_id` field filter. The problem: RediSearch treats underscores as **token separators**.

When FalkorDB indexes an edge with `group_id = "product_knowledge"`, RediSearch stores two tokens: `product` and `knowledge`. When you then query `@group_id:product_knowledge`, RediSearch tries to match the literal `product_knowledge` — which doesn't exist in the index. Syntax error.

RediSearch's full list of separator characters:

```
, . < > { } [ ] " ' : ; ! @ # $ % ^ & * ( ) - + = ~ _
```

That trailing underscore is easy to miss.

### The Wrong Fix

My first instinct was to escape underscores: `product\_knowledge`. This doesn't work because tokenization happens at **index time** too. The stored tokens are `product` and `knowledge` — no amount of query-side escaping can match `product_knowledge` when the index doesn't contain it.

Even groups without underscores like `patterns` and `agents` failed, because the search text portion was empty (producing invalid `()` syntax — more on that below).

### The Right Fix

On FalkorDB, the `@group_id` fulltext filter is completely redundant. Group isolation is already handled by:

1. The driver clone from Bug 1's fix — each search runs against the correct named graph
2. A Cypher `WHERE e.group_id IN $group_ids` clause that performs exact string comparison

So the fix is simple: remove the `@group_id` filter from fulltext queries when using FalkorDB.

```python
def build_fulltext_query_fixed(self, query, group_ids=None, max_query_length=128):
    # Skip the broken @group_id filter entirely.
    # Group isolation is handled by driver clone + Cypher WHERE clause.
    return original_build_fulltext_query(self, query, None, max_query_length)
```

The upstream fix should either skip `@group_id` on FalkorDB, or use RediSearch TAG fields (which support exact matching without tokenization) instead of fulltext fields for group_id filtering.

---

## Bug 3: The Empty Query That Crashes RediSearch

With the `@group_id` filter removed, a third bug emerged. The status command probes each group with a generic query that gets fully stripped by RediSearch's stopword removal. The result:

```
query: ' ()'
```

Empty parentheses. Invalid RediSearch syntax.

**Fix**: If the query result is `()` or empty after stripping, return `*` (RediSearch wildcard for "match all"). The Cypher WHERE clause still filters correctly.

One caveat: the `*` wildcard can timeout on large graphs. This only affects "count everything" operations; real searches with actual query terms produce proper tokens and work fine.

---

## Why These Bugs Were Hard to Find

Three factors made diagnosis difficult:

**Writes always succeed.** `add_episode()` uses Cypher directly, not RediSearch fulltext. So you can seed your knowledge graph, verify episodes exist, and still have zero search results.

**Vector searches have fallback paths.** Graphiti's search combines fulltext and vector similarity. When fulltext fails, the vector path might still return results depending on the code path. Some searches worked, some didn't, with no obvious pattern.

**Diagnostics gave misleading results.** Raw Cypher queries against FalkorDB from Python returned garbled data due to binary graph protocol parsing differences. It looked like the database was empty when it wasn't. It took three iterations of diagnostic scripts to prove the data was intact and that the search layer was the problem.

---

## The Workaround Module

All three fixes live in a single module (`falkordb_workaround.py`) that's called once at startup:

```python
from guardkit.knowledge.falkordb_workaround import apply_falkordb_workaround

# Apply all three patches before creating any Graphiti clients
apply_falkordb_workaround()
```

The module auto-detects if upstream fixes are applied and skips unnecessary patches. It logs which workarounds were activated:

```
[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched 
  for single group_id support (upstream PR #1170)
[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched 
  to remove group_id filter (redundant on FalkorDB)
```

---

## Results

Before workarounds: every group reported 0 facts.

After workarounds:

| Group | Facts |
|-------|-------|
| product_knowledge | 27 |
| command_workflows | 100 |
| patterns | 100 |
| agents | 16 |
| project_overview | 39 |
| project_architecture | 35 |
| architecture_decisions | 65 |
| failure_patterns | 24 |
| **Total** | **406 episodes** |

---

## Lessons for Anyone Using Graphiti + FalkorDB

1. **Avoid underscores in group_ids if you can.** Use hyphens or camelCase instead. RediSearch won't tokenize `productKnowledge` or `product-knowledge` the same way (though hyphens are also separators — camelCase is safest).

2. **Test the fulltext search path explicitly.** Vector-only searches may work even when fulltext is broken. Call `search()` with actual query terms and verify results, don't just confirm writes succeed.

3. **FalkorDB's multi-graph model makes some graphiti-core filtering redundant.** The `@group_id` fulltext filter was designed for Neo4j where all groups share one database. On FalkorDB, each group is already an isolated graph — the filter is unnecessary and actively harmful.

4. **Check RediSearch's separator characters.** If you're storing identifiers in fulltext-indexed fields, any of these characters will cause tokenization: `, . < > { } [ ] " ' : ; ! @ # $ % ^ & * ( ) - + = ~ _`

5. **Monkey-patching is acceptable for open-source bugs.** The decorator fix PR has been unreviewed for five weeks. Waiting isn't an option when you're building on top of the library. Document the workaround, auto-detect the upstream fix, and move on.

---

## Upstream Status

| Issue | Status | Action Needed |
|-------|--------|--------------|
| Decorator off-by-one ([PR #1170](https://github.com/getzep/graphiti/pull/1170)) | Open, unreviewed | Needs maintainer attention |
| RediSearch group_id tokenization | Not yet filed | Needs upstream issue |
| Empty query fallback | Not yet filed | Needs upstream issue |

If you've hit these same issues, the workaround module is in GuardKit's source. The approach generalises to any graphiti-core + FalkorDB deployment that uses underscored group_ids.

---

*Rich Woollcott is the creator of [GuardKit](https://github.com/appmilla/guardkit), an AI-assisted development tool that brings guardrails and quality gates to Claude Code workflows. He writes about practical AI integration challenges at [Appmilla](https://www.appmilla.com).*
