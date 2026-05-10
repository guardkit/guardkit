# DECISION-RAG-001 — Unified ChromaDB approach for fleet RAG

**Status:** Accepted
**Date:** 2026-05-07
**Author:** Rich (pair-programmed with Claude Opus 4.6 in Claude Desktop)
**Scope:** All fleet agents that use retrieval-augmented generation: specialist-agent (architect role) and study-tutor. Establishes the single ChromaDB pattern used across the fleet.

---

## Summary

**Both the specialist-agent and study-tutor use ChromaDB `PersistentClient` on the GB10, with `OpenAIEmbeddingFunction` pointing at llama-swap's `/v1/embeddings` endpoint (nomic-embed-text-v1.5, 768 dimensions). No Ollama. No Chroma server process. No cross-network hops. Ingestion and query are both localhost operations on the GB10.**

This resolves ASSUM-002 (specialist-agent topology decision) and aligns RAG infrastructure with DECISION-DF-001 (llama-swap as single inference front door).

---

## 1. Context

Both the specialist-agent and study-tutor have RAG modules built and unit-tested but neither has production-wired ChromaDB:

**Specialist-agent (architect role):**
- `architecture_knowledge.py` tool uses `chromadb.Client()` — ephemeral in-memory, dead on arrival in production
- Ingestion script (`scripts/ingest_architecture_knowledge.py`) written for Ollama's `/api/embeddings` endpoint, which contradicts DECISION-DF-001
- Pre-processed dataset exists: `data/rag_index/knowledge.jsonl` (1,102 records, 8 MB, covering 19 architecture books)
- Runbook at `docs/deployment/architect-rag-deployment.md` flagged ASSUM-002 (topology: where does ChromaDB live?) as open

**Study-tutor:**
- RAG pipeline modules complete (PRV-001 → PRV-007): corpus loader, retrieval with BGE reranker, quote verifier, coach handover seam
- CLI passes `coach_handover=None` — RAG never fires in production
- No `chromadb` or `sentence-transformers` in `pyproject.toml`
- No ingestion script written
- No corpus populated (`domains/gcse-english/sources/` contains only a README)

---

## 2. Decision

### 2.1 ChromaDB client mode: PersistentClient on GB10

Both projects use `chromadb.PersistentClient` with a per-project persistence directory on the GB10 filesystem. No Chroma server process, no port, no health check.

**Why not Chroma server mode (HttpClient)?**
Adds a service to manage (`chroma run` on GB10). Both agents already run on GB10 (Docker). PersistentClient is just a directory on disk — zero operational overhead. And with HttpClient, the Mac-side embedding function still needs to call GB10 for embeddings, so you're paying two network hops per query (embed + search) instead of zero (both localhost on GB10).

**Why not PersistentClient on Mac?**
The agents are moving to GB10 (Docker deployment, DECISION-DF-001 topology). PersistentClient must be co-located with the agent process. Running Chroma on the Mac would require cross-network queries from the GB10 container back to the Mac, which inverts the dependency direction.

### 2.2 Embedding function: llama-swap, not Ollama

Both projects use `chromadb.utils.embedding_functions.OpenAIEmbeddingFunction` pointing at llama-swap's OpenAI-compatible `/v1/embeddings` endpoint on localhost:9000. The embedding model is `nomic-embed-text` (v1.5, 768 dimensions), which is always-on in llama-swap (no swap needed).

**Why not Ollama?**
llama-swap is the single inference front door (DECISION-DF-001). Ollama is not running on the GB10. The specialist-agent's ingestion script was written for Ollama's `/api/embeddings` — this is a bug that needs patching. The fleet should not have two inference endpoints.

### 2.3 Ingestion runs on GB10

Both ingestion scripts run on the GB10 where llama-swap and the persistence directories are localhost. Zero network hops for embedding or storage. Ingestion is a one-time operation (re-run when the source corpus changes).

---

## 3. The unified code pattern

Both projects use identical connection code:

```python
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

# Embedding function — same for ingest and query
ef = OpenAIEmbeddingFunction(
    api_base="http://localhost:9000/v1",
    api_key="not-needed",              # llama-swap doesn't require auth
    model_name="nomic-embed-text",
)

# Client — PersistentClient, per-project directory
client = chromadb.PersistentClient(path="data/chroma")

# Collection — per-project name
collection = client.get_or_create_collection(
    name="<collection-name>",          # see §4 for project-specific names
    embedding_function=ef,
)

# Query
results = collection.query(
    query_texts=["How should I handle webhook retries?"],
    n_results=8,
)
```

### 3.1 Environment variables

For flexibility across deployment contexts, both projects should read from env with sensible defaults:

| Variable | Default | Purpose |
|---|---|---|
| `CHROMA_PERSIST_DIR` | `data/chroma` | PersistentClient path |
| `CHROMA_COLLECTION` | (project-specific) | Collection name |
| `LLM_EMBEDDINGS_BASE_URL` | `http://localhost:9000/v1` | llama-swap OpenAI-compatible endpoint |
| `LLM_EMBEDDINGS_MODEL` | `nomic-embed-text` | Embedding model name |

---

## 4. Per-project specifics

### 4.1 Specialist-agent (architect role)

| Item | Value |
|---|---|
| Collection name | `architect-knowledge-v1` |
| Persist directory | `specialist-agent/data/chroma/` (on GB10) |
| Source data | `specialist-agent/data/rag_index/knowledge.jsonl` (1,102 records, 8 MB) |
| Ingestion script | `specialist-agent/scripts/ingest_architecture_knowledge.py` — **needs patching**: change Ollama endpoint to `OpenAIEmbeddingFunction` via llama-swap |
| Consumer tool | `specialist-agent/src/specialist_agent/tools/architecture_knowledge.py` — **needs patching**: swap `chromadb.Client()` to `chromadb.PersistentClient(path=os.environ.get("CHROMA_PERSIST_DIR", "data/chroma"))` and wire `OpenAIEmbeddingFunction` |
| Docker volume | Mount `data/chroma/` into the specialist-agent container |

**Work required (1–2 hours, Claude Code):**
1. Patch `architecture_knowledge.py`: `Client()` → `PersistentClient` + `OpenAIEmbeddingFunction`
2. Patch ingestion script: Ollama endpoint → llama-swap endpoint
3. Run ingestion on GB10: `python scripts/ingest_architecture_knowledge.py`
4. Smoke test: architect session with `architecture_knowledge_query` tool returning results

### 4.2 Study-tutor

| Item | Value |
|---|---|
| Collection name | `gcse-english-v1` |
| Persist directory | `study-tutor/data/chroma/` (on GB10) |
| Source data | Standard Ebooks Shakespeare (Macbeth, Romeo & Juliet, etc.) + secondary study guides — **needs populating** in `domains/gcse-english/sources/primary_text/` |
| Ingestion script | **Needs writing** — follows the pattern: `load_corpus(root)` → embed each `CorpusChunk` → upsert into collection with `CHUNK_PAYLOAD_KEY` metadata |
| Consumer | CLI `coach_handover` closure — **needs wiring**: `set_collection_provider()`, `decide_retrieval()`, `retrieve()`, `apply_quote_verification()` |

**Work required (4–6 hours, Claude Code):**
1. Add `chromadb` to `pyproject.toml`
2. Write `scripts/ingest_corpus.py`: takes domain root, calls `load_corpus()`, opens PersistentClient, upserts chunks with `OpenAIEmbeddingFunction`
3. Populate `domains/gcse-english/sources/primary_text/` with Standard Ebooks Shakespeare
4. Wire providers + `coach_handover` in `cli/main.py` at serve startup (see study-tutor RAG review for the four-step wiring sequence)
5. Run ingestion on GB10
6. Smoke test: Macbeth session with `mode="rerank"` visible in turn metadata and `VerifierMetadata.primary_matches` populated

---

## 5. What this enables

### For the DDD demo (16 May)

If wired, the audience sees `reason=retrieve:primary_present` vs `reason=ao3_only:training_first` in the log pane during Demo 1 (architect) and Demo 3 (tutor). This makes the "selective retrieval" thesis from ADR-FLEET-002 visible — the model's behaviour is fine-tuned, the factual knowledge comes from RAG, and the decision to retrieve is itself a learned behaviour.

The Coach's `quote_fidelity` rubric criterion fires when the Player quotes Shakespeare — currently dormant because `coach_handover=None`.

### For the hackathon (18 May)

The two-layer architecture (fine-tuning for behaviour, RAG for knowledge) is central to the technical write-up. Having RAG working in the video strengthens the "this isn't just a chatbot" story.

### Priority

RAG is a nice-to-have for both events, not a must-have. The fine-tuned models produce quality results without RAG. The specialist-agent wiring (1–2 hours) is the faster win since the ingestion script and source data already exist.

---

## 6. Relationship to other decisions

| Decision | Relationship |
|---|---|
| DECISION-DF-001 (local-first inference) | RAG embeddings go through llama-swap, the single inference front door. No Ollama, no cloud embedding APIs. |
| ADR-FLEET-002 (selective retrieval) | This decision implements the infrastructure for selective retrieval. The retrieval decision logic is in the study-tutor's `decide_retrieval()` function. |
| ADR-ARCH-013 (specialist-agent, nomic-embed-text baseline) | Commits to nomic-embed-text-v1.5 at 768 dimensions. This decision uses the same model via llama-swap. |
| ASSUM-002 (ChromaDB topology) | Resolved by this decision: PersistentClient on GB10, co-located with agents and llama-swap. |

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| `OpenAIEmbeddingFunction` requires `openai` Python package | ChromaDB bundles this dependency. Both projects already have it transitively via LangChain. |
| Embedding dimension mismatch between ingest and query | Both use the same `OpenAIEmbeddingFunction` with the same model (`nomic-embed-text`). Dimension is determined by the model, not the code. |
| llama-swap model swap during embedding calls | `nomic-embed-text` is always-on in llama-swap (not in a swap group). No swap latency. |
| Ingestion script re-run overwrites existing data | Use `get_or_create_collection()` + upsert pattern. Idempotent by design. |
| Docker container can't access `data/chroma/` | Mount as a Docker volume. The specialist-agent's `docker-compose.dual-role.yml` already mounts data directories. |

---

*Accepted: 7 May 2026*
*Seed to Graphiti: `guardkit__decisions` group*
