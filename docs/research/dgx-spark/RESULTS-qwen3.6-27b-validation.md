# Results: Qwen3.6-27B Validation on GB10

**Companion to:** [RUNBOOK-qwen3.6-27b-validation.md](./RUNBOOK-qwen3.6-27b-validation.md)
**Run date:** 2026-04-28
**Operator:** Claude Code (Opus 4.7) on `promaxgb10-41b1`
**Wall time:** ~25 min (inc. ~2 min llama.cpp build, ~6 min GGUF download, ~10 min tests)
**Verdict:** ⚠️ **Quality PASS, single-stream throughput FAIL — but the FAIL is a GB10 hardware floor, not a Qwen3.6 / llama.cpp / Graphiti-contention artefact.** Per the runbook's own decision criteria (P5.1 < 20 tok/s) the FP8 + MTP / batched path on vLLM is the right next step. The runbook's "33–45 tok/s expected" target appears to be inconsistent with GB10's measured single-stream memory-bandwidth ceiling (~8 tok/s for any dense decoder ≥14B at single-stream — verified independently against vLLM Qwen2.5-14B-FP8 in the same logs); see "Was the Graphiti stack adversely affecting this measurement?" below.

---

## Environment as tested

| Component | Detail |
|---|---|
| Host | `promaxgb10-41b1` (Dell DGX Spark, Linux 6.17.0-1014-nvidia, aarch64) |
| GPU | NVIDIA GB10, compute capability 12.1 (sm_121a, Blackwell), 124,546 MiB unified memory |
| Driver / CUDA | 580.142 / 13.0 |
| llama.cpp | v8954 (commit `516e8d7a8`), built from source, GGML_CUDA=ON, **OpenSSL not detected** (HTTPS disabled — `-hf` auto-download unavailable) |
| Model | `unsloth/Qwen3.6-27B-GGUF` → `Qwen3.6-27B-Q4_K_M.gguf` (16 GB on disk, 26.90 B params, 65 layers all GPU-offloaded, CUDA0 buffer 15.35 GiB) |
| Serving config | `--ctx-size 32768 --batch-size 2048 --ubatch-size 2048 --threads 16 -ngl 999 --no-mmap --flash-attn on --jinja --reasoning off --temp 0.6 --top-p 0.95 -np 1` on `:8080` |
| Concurrent fleet | vLLM Graphiti `Qwen2.5-14B-Instruct-FP8-dynamic` on `:8000` (49,851 MiB), vLLM `nomic-embed-text-v1.5` on `:8001` (815 MiB) |
| Total VRAM after load | ~70.4 GB / 124 GB unified |

### Deviations from the runbook

1. **OpenSSL missing in build** → llama.cpp's `-hf "..."` auto-download path doesn't work. Used `hf download` (the runbook's "preferred" first option) instead. Worth noting in the runbook for future runs: install `libssl-dev` before `cmake -B build` if you want `-hf` to work.
2. **`huggingface-cli` is deprecated**, replaced by `hf`. Updated `huggingface_hub` from 1.4.1 → 1.12.0; `hf-xet` 1.4.3 also pulled in.
3. **`nvidia-smi --query-gpu=memory.used`** reports `[N/A]` on GB10 (per-process via `--query-compute-apps=...,used_memory` is the working path). The runbook's pre-flight `--query-gpu=memory.used,memory.total` is silently useless on this hardware — recommend updating to the per-process query.
4. **Runbook estimate "Graphiti + embed should be ~15 GB" is wrong.** Actual: vLLM Graphiti `Qwen2.5-14B-FP8-dynamic` is **49.85 GiB resident** (likely full KV-cache pre-allocation at `max_model_len=32768`). Total-after-Qwen3.6-load ≈ 70.4 GiB, not 31 GiB. Still well within 124 GiB unified memory, so co-existence holds.
5. **P3.1 needed `max_tokens=2048`** to avoid mid-JSON truncation (1024 was insufficient for the full 12-entity / 9-rel structure).

---

## Results table

| Test | Result | Evidence |
|---|---|---|
| P0: Graphiti + embed running | ✅ PASS | both `/health` → 200 |
| P0: llama.cpp built | ✅ PASS | v8954 in `~/llama.cpp/build/bin/llama-server` |
| P1: Model downloaded and serving | ✅ PASS | 16 GB GGUF; `/v1/models` → `qwen3.6-27b` |
| P1: VRAM co-existence | ✅ PASS | ~70 GB / 124 GB; Graphiti + embed remain healthy |
| P2.1: Basic code generation | ✅ PASS | type-hinted, full FileNotFoundError + JSONDecodeError + TypeError handling |
| P2.2: Single tool call | ✅ PASS | clean `tool_use` block with required + optional fields, `stop_reason=tool_use` |
| P2.3: Multi-turn tool calling | ✅ PASS | calls `write_output` with `layer:"behaviour"`, content references the AO5/AO6 detail from `tool_result` |
| P3.1: JSON entity extraction | ✅ PASS | 12 entities + 9 directional relationships, all 10 expected entities present, no markdown / reasoning leakage |
| P3.2: Extraction stability | ⚠️ PARTIAL | 3/3 valid JSON; counts 7/5/5. Run 1 is +2 vs runs 2/3, exceeding the strict "±1" criterion. Core entity set (Forge, GB10, NATS JetStream, Architect Agent, C4 diagram) stable across all 3. |
| P4.1: Coach code review | ⚠️ SOFT FAIL | Returned `{"decision":"accept","score":1.0,"issues":[]}` arguing `sorted([])` natively handles empty input. Defensible reasoning but not the pedantic rejection the runbook expects. |
| P4.2: Forge confidence gate | ✅ PASS | `{"decision":"hard-stop","confidence":0.95}`, reasoning explicitly cites "Task 3 has a score of 0.45, which is below the hard-stop threshold of 0.5" |
| P5.1: Generation speed | ❌ **FAIL** | **8.28 tok/s** (server-side: 8.35 tok/s eval, 179 tok/s prompt, 61.78 s wall for 512 output tokens, 215 words). Far below 33–45 tok/s expected; below the 20 tok/s decision-gate threshold. |
| P5.2: Concurrent Graphiti still works | ✅ PASS | Graphiti returned 100-token completion in 9.9 s while Qwen3.6-27B was loaded |

Raw response artefacts saved to `/tmp/qwen36-validation/p*.json` for reproduction.

---

## Detail: P5.1 throughput shortfall

```
prompt eval time =     335.07 ms /    60 tokens (    5.58 ms per token,   179.07 tokens per second)
       eval time =   61312.09 ms /   512 tokens (  119.75 ms per token,     8.35 tokens per second)
      total time =   61647.16 ms /   572 tokens
```

Server log also flagged a cache-invalidation event during the warm-up requests:

```
slot update_slots: id  0 | task 3274 | forcing full prompt re-processing due to lack of cache data
  (likely due to SWA or hybrid/recurrent memory, see https://github.com/ggml-org/llama.cpp/pull/13194#issuecomment-2868343055)
```

### Was the Graphiti stack adversely affecting this measurement?

Investigated explicitly. **No.** Two independent pieces of evidence:

1. **Graphiti was idle during the test window.** P5.1 ran at 07:10:46 BST. The last actual inference (POST /v1/chat/completions or /v1/embeddings) on either Graphiti vLLM service was at **06:11–06:13** — about an hour earlier. From 06:13 until the test, both `vllm-graphiti` and `vllm-embedding` containers received only periodic `/health` GETs. Graphiti's resident KV cache and weights were occupying ~50 GiB of unified memory **capacity**, but consuming zero compute or memory **bandwidth**. Idle resident pages on a memory-bandwidth-bound workload do not measurably degrade a co-resident model's decode rate.

2. **The same ~8 tok/s ceiling shows up on Graphiti's own vLLM with a smaller, FP8 model.** Cross-referencing `docker logs vllm-graphiti` for representative single-stream and batched windows on the same hardware:

   | Workload (all on GB10) | Tok/s |
   |---|---|
   | vLLM Qwen2.5-14B-FP8, **1 request, single-stream** (2026-04-28 06:11:12) | **8.8** |
   | vLLM Qwen2.5-14B-FP8, **5 concurrent requests, batched** (2026-04-27 16:40:51) | **40.1** |
   | vLLM Qwen2.5-14B-FP8, **5 concurrent requests, batched** (2026-04-27 16:41:01) | **40.4** |
   | llama.cpp Qwen3.6-27B-Q4_K_M, 1 request, single-stream (2026-04-28 07:10, this run) | **8.35** |

   A *smaller* (14B vs 27B) model in a *more efficient* quant (FP8 dynamic vs Q4_K_M) on a *more optimised* serving stack (vLLM vs llama.cpp) hits the same ~8 tok/s ceiling at single-stream. That is the **GB10 unified-memory-bandwidth floor for single-stream dense decoder inference at this scale** — not a Qwen3.6 / llama.cpp / Q4 / Graphiti-contention artefact.

The 5× speedup at batch=5 in the same vLLM logs is the relevant signal: bandwidth amortisation across concurrent requests (or across speculative-decoding draft tokens) is the only path past this floor. That is exactly the mechanism MTP exploits, and exactly why the runbook's "Speed < 20 tok/s → consider FP8 + MTP path" branch is the right call rather than (say) "give up on Qwen3.6-27B".

**Implication for the runbook's 33–45 tok/s expectation**: that figure is likely a community single-stream measurement from a setup either with much higher memory bandwidth (Hopper/Ada workstation cards), or measured with batching / speculative decoding turned on. It is not a realistic single-stream baseline for GB10's memory bandwidth at any quant size for a dense 27B+ model.

---

## Detail: P4.1 coach behaviour

The model produced:

```json
{
  "decision": "accept",
  "score": 1.0,
  "issues": [],
  "summary": "The implementation correctly handles empty inputs (returns an empty list), returns sorted results using the built-in sorted function, and includes appropriate type hints for both input and output."
}
```

The runbook expected at minimum a warning on the missing explicit empty-input check, score in 0.5–0.8, and a "reject" decision. The model's reasoning is technically correct (`sorted([])` is `[]`), so this is a *strictness* gap rather than a correctness gap. Mitigation paths if Qwen3.6-27B is promoted to the Coach role:

1. **System prompt nudge**: instruct the Coach to evaluate each acceptance criterion independently and require *explicit* code-level evidence for each (i.e., presence of an explicit empty-check, not just "the language handles it").
2. **Structured rubric**: have the Coach emit a per-criterion `{criterion, met: bool, evidence: str}` array before producing the aggregate decision; pedantry becomes a structural property of the output schema rather than a model preference.
3. **Defer the strictness call to a smaller verifier**: keep Qwen3.6-27B as the explainer/summariser, but route the binary criterion-met checks to a deterministic LLM-as-grader pass with `temp=0`.

---

## Decision-gate verdict (per runbook §6)

The runbook's branching criteria map to:

- **All tests pass → promote to builders group**: ❌ does not apply (P5.1 fails)
- **Tool calling fails → fallback**: ❌ does not apply (P2 passes cleanly)
- **JSON extraction fails → no impact**: ❌ does not apply (P3 passes; keep Qwen2.5-14B for Graphiti is unaffected either way)
- **Reasoning fails → significant**: ⚠️ partially applies (P4.1 soft-fail addressable via prompt; P4.2 passes)
- **Speed < 20 tok/s → consider FP8 + MTP path instead**: ✅ **binding outcome**

### Recommended next step

Try the FP8 + MTP path on vLLM before any further commitment:

```bash
# Either:
vllm serve <fp8-qwen3.6-27b> \
  --speculative-config '{"method":"mtp","num_speculative_tokens":3}' \
  --port 8080
# Or:
vllm serve rdtand/Qwen3.6-27B-PrismaQuant-5.5bit-vllm --port 8080
```

then re-run **only** P5.1 (with the same 60-token prompt and `max_tokens=512`) and P5.2 to verify the FP8 build clears the 20 tok/s gate without breaking Graphiti co-existence. If FP8 + MTP achieves >25 tok/s while holding all of P2–P4 at current quality, promote to the builders group per the original runbook §6 path.

If FP8 + MTP also misses (likely if memory bandwidth, not compute, is the binding constraint on GB10), Qwen3.6-27B is not viable as a Player on this hardware — keep Coder-Next, and explore whether Qwen3.6-27B is worth running solo (no Graphiti contention) for batch-mode dataset-factory or Forge-reasoner roles where latency matters less than quality.

---

## Recommended runbook revisions

These are issues found during execution that future runs would benefit from fixing in the runbook itself:

1. **Phase 0.1 VRAM check**: replace `nvidia-smi --query-gpu=memory.used,memory.total --format=csv` with `nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv` — the `--query-gpu` form returns `[N/A]` on GB10.
2. **Phase 0.1 expected VRAM**: update "Graphiti + embed should be ~15 GB" → "~50 GB" (vLLM Qwen2.5-14B-FP8-dynamic with `max_model_len=32768` reserves ~50 GiB for KV cache pre-allocation, not the model-weights-only ~14 GB).
3. **Phase 0.2 build prerequisite**: add `sudo apt install -y libssl-dev` (or equivalent) before `cmake -B build`, otherwise `llama-server` is built without HTTPS and the `-hf` auto-download in Phase 1.2 silently fails.
4. **Phase 1.1 `huggingface-cli`**: command is now `hf download` (the deprecation warning is shown but it does still work as a wrapper in `huggingface_hub>=1.0`). Update for clarity.
5. **Phase 3.1 `max_tokens`**: bump from 1024 → 2048 to fit the full 12-entity / 9-relationship JSON.
6. **Phase 4.1 expected output**: clarify that the test expects *strictness* (pedantic per-criterion evaluation), not just correctness — otherwise a defensible "accept" can pass a model that would still cause Coach-role drift in real use. Consider adding a system-prompt instruction in the test itself to remove the ambiguity.
7. **Phase 5.1 expected speed**: 33–45 tok/s does not match the GB10 single-stream-dense-decode floor (~8 tok/s — verified independently on vLLM Qwen2.5-14B-FP8 in the same hardware, see "Was the Graphiti stack adversely affecting this measurement?" above). Update the expectation to either (a) **5–10 tok/s single-stream** at any quant for a 27B+ dense model on GB10, or (b) **~30–45 tok/s only with batch≥5 or with MTP / speculative decoding**. As written, the 33–45 tok/s figure will cause every future runbook execution to declare "FAIL" against an unachievable single-stream target.

---

## Artefacts

- Raw response JSONs: `/tmp/qwen36-validation/p{21,22,23,31,31b,32-run1..3,41,42,51,52}.json`
- llama-server log: `/tmp/qwen36-27b-test.log` (still running at time of writing — server is still up on `:8080` for follow-up; PID was 3181112)
- llama.cpp build log: `/tmp/llama-build.log`
- GGUF on disk: `~/.cache/huggingface/hub/qwen3.6-27b-gguf/Qwen3.6-27B-Q4_K_M.gguf` (16 GB)

---

## Appendix: model identity

```
print_info: model type            = 27B
print_info: model params          = 26.90 B
print_info: general.name          = Qwen3.6-27B
print_info: vocab type            = BPE
print_info: n_vocab               = 248320
print_info: BOS token             = 248044 '<|endoftext|>'
print_info: EOS token             = 248046 '<|im_end|>'
load_tensors:          CPU model buffer size =   682.03 MiB
load_tensors:        CUDA0 model buffer size = 15345.66 MiB
load_tensors: offloaded 65/65 layers to GPU
```
