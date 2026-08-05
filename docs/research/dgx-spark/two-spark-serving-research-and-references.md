# Two-Spark Serving — Research & References

**Purpose:** Annotated reference for running inference across a stacked pair of NVIDIA DGX Spark (GB10) units — multi-node tensor parallelism for large models, the single-node multi-model swap stack, and the layered front door that combines them. Companion to `../../decisions/DECISION-DF-004-two-spark-serving-topology-unified-front-door.md` and the single-node baseline in `dark-factory-economics-and-model-serving.md`.
**Compiled:** 2026-06-18 (Claude Desktop research session). The DGX Spark space moves weekly — treat all throughput numbers as point-in-time, captured at this date.

---

## Key findings at a glance

**Stacking = capacity, not speed.**
- Two nodes do not fuse into one 256 GB GPU. Tensor parallelism splits each layer's matrices across the boxes; activations cross the QSFP link every forward pass. What you gain is the ability to load a model whose weights + KV exceed one node. (corti)
- The ConnectX-7 on GB10 is wired as two PCIe Gen5 x4 links, not one x8; full 200 Gb needs both x4 paths aggregated. Each physical port shows two Linux interface names (four total for two ports) — use the `enp1...` names. (corti; NVIDIA Sync docs)
- A ~120B model that fits on one node: ~35–50 tok/s single-stream on one box, ~55–75 stacked, gains mostly under concurrency. (corti)
- **Leaderboard caveat:** Spark Arena is concurrency-first (tests at c=5/c=10) — its near-2× two-node gpt-oss-120b rows are aggregate throughput, not batch-1 decode (a dendro-logic recipe beat it +46%/+54% at exactly c=5/c=10 just by adding those CUDA-graph capture sizes). Batch-1 all-reduces are KB-scale, so the fitting-model single-stream gain is capped ~1.3–1.5× by per-layer sync *latency* + the unsharded remainder — not by the link's ~25 GB/s, which binds at prefill/concurrency. (added 2026-08-05)
- DeepSeek-V4-Flash (official FP8, ~149 GB, TP=2): ~40 tok/s decode warm single-stream; ~6 min cold start; long-context cold prefill weak (~53s TTFT @32K, ~250s @128K); decode collapses under concurrency + depth. (forum recipe thread)

**The two field patterns are separate.**
- Single-node multi-model fleet (LiteLLM + llama-swap + vLLM/llama.cpp/Ollama, 10+ models, swap-to-fit) — well documented, but essentially one lineage (martinB78 -> Dre Dyson -> dasroot).
- Two-node single-model TP (one big model across the boxes) — NVIDIA playbooks + forum recipes + build logs.
- The union (swap pool + TP model coexisting across two nodes behind one front door) did not surface — that is the gap DECISION-DF-004 occupies. (Not proof of non-existence; just absent from a focused search.)

**Bring-up gotchas the community already paid for.**
- Update CX-7 / mlx5 firmware + `dgx-spark-mlnx-hotplug` first; OTA April 2026+.
- Same physical port on both ends or the link won't come up; verify with `ibdev2netdev`.
- Pin NCCL / UCX / GLOO / TP socket interfaces to the QSFP link or traffic falls back to the slow NIC; verify with `all_gather_perf` before model load.
- Pin the exact vLLM commit (GB10 validation is commit-specific, not a branch); `--no-ray` / `mp` backend fits full context and is marginally faster than Ray.
- Firmware can hard-power-off the box under heavy GPU load; mitigate by lowering GPU clock (`nvidia-smi -lgc 200,2150`).
- These recipes take GB (not %) for `--gpu-memory-utilization`; the unified-memory allocator may not free promptly between model swaps.

---

## Diagrams

Rendered SVGs live in `diagrams/` (clean-line renderings of the architecture; an editable `.excalidraw` source sits beside each one).

**Two-Spark fleet serving architecture** — the layered topology: clients hit one LiteLLM front door, which fans out to the llama-swap pool (plus always-on nomic) on Node A and a vLLM TP=2 DeepSeek spanning both nodes; Postgres + pgvector lives on the NAS.

![Two-Spark fleet serving architecture](diagrams/two-spark-fleet-serving-architecture.svg)

**Request routing — two paths, one front door** — Path A swaps a fleet model in on a single node; Path B brings up the cross-node two-box DeepSeek. Same proxy instance, different backend.

![Request routing - two paths, one front door](diagrams/two-spark-request-routing.svg)

**fleet-memory write path** — zero-LLM structured ingest: structured payloads go straight to the deterministic writer (no model in the loop), and only markdown/text touches nomic for embedding before landing in Postgres.

*(The fleet-memory write-path diagram is a fleet-memory subsystem asset — kept with fleet-memory in the [guardkit repo](https://github.com/guardkit/guardkit/blob/main/docs/research/dgx-spark/diagrams/fleet-memory-write-path.svg), not duplicated in this public Spark repo.)*

## NVIDIA official

- DGX Spark / GB10 forum (category index) — https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/dgx-spark-gb10/721
- Connect Two Sparks (build.nvidia.com playbook) — https://build.nvidia.com/spark/connect-two-sparks/stacked-sparks
- vLLM on stacked Sparks (build.nvidia.com) — https://build.nvidia.com/spark/vllm/stacked-sparks · instructions: https://build.nvidia.com/spark/vllm/instructions
- Spark clustering guide — https://docs.nvidia.com/dgx/dgx-spark/spark-clustering.html · User Guide PDF: https://docs.nvidia.com/dgx/dgx-spark/dgx-spark.pdf
- NVIDIA Sync "Cluster Assistant" (GUI for the CX-7 mesh + passwordless SSH) — https://docs.nvidia.com/sync/latest/cluster-assistant.html
- dgx-spark-playbooks (DeepWiki): Multi-Node Setups — https://deepwiki.com/NVIDIA/dgx-spark-playbooks/7-multi-node-setups · Connecting Two Sparks — https://deepwiki.com/NVIDIA/dgx-spark-playbooks/7.1-connecting-two-sparks · vLLM Ray Cluster — https://deepwiki.com/NVIDIA/dgx-spark-playbooks/7.3-vllm-ray-cluster
- vLLM project blog — vLLM on DGX Spark (architecture, NVFP4 MoE, unified-memory behaviour) — https://vllm-project.github.io/2026/06/01/vllm-dgx-spark.html

## Two-node TP recipes & benchmarks (forum)

- **DeepSeek-V4-Flash official FP8 across 2x Spark, TP=2, MTP, 200K ctx — recipe + numbers (canonical thread)** — https://forums.developer.nvidia.com/t/deepseek-v4-flash-official-fp8-running-across-2x-dgx-spark-tp-2-mtp-200k-ctx-recipe-numbers/370309
- **DSpark speculative decoding (DeepSeek; MIT; released 2026-06-27) — the evolution of the `deepseek_mtp` above.** Reuses V4's MTP heads and adds a semi-autoregressive draft head (fixes "suffix decay") + confidence-scheduled verification. Framework/algos (DSpark · DFlash · Eagle3 + training): https://github.com/deepseek-ai/DeepSpec · checkpoints `deepseek-ai/DeepSeek-V4-Flash-DSpark` / `-V4-Pro-DSpark` (V4 base + draft module, not new base models). **GB10 status (researched 2026-06-29): no runnable aarch64 path yet** — vLLM support is open issue [#46910](https://github.com/vllm-project/vllm/issues/46910) (assigned, *no* PR/branch), the pinned `jasl/vllm` carries MTP not DSpark, and DeepSpec training assumes x86 multi-GPU. The "57–85% faster" headline is measured vs **MTP-1**; we already run **MTP-2**, so the realistic *incremental* gain is ~10–25% `[inferred]`, and cross-node it may be all-gather-bound over the CX-7 (see [`qwen3.6-27b-gb10-community-research.md`](./qwen3.6-27b-gb10-community-research.md): TP=2+MTP can go *worse*). Shipped draft heads are Qwen3-4B/8B/14B + Gemma-4-12B-it — **not** our Qwen3.6-35B-A3B / Gemma-4-26B-A4B (custom heads = x86-only training). **Verdict: watch #46910 + `jasl/vllm` rebases; when a branch lands, A/B DSpark vs MTP-2 on ONE box at small ctx over code/reasoning prompts (its high-acceptance regime = the distillation factory), and confirm byte-identical output. Don't deploy / don't train custom heads yet.**
- Deepseek v4 Flash on 2 Nodes — https://forums.developer.nvidia.com/t/deepseek-v4-flash-on-2-nodes/368916
- DeepSeek V4 Flash 1M ctx on 2x Spark — custom Sparkrun recipe — https://forums.developer.nvidia.com/t/deepseek-v4-flash-1-048-576-context-on-2x-dgx-spark-custom-sparkrun-recipe/373206
- MiMo-V2.5-NVFP4 on 2x Spark cluster — https://forums.developer.nvidia.com/t/mimo-v2-5-nvfp4-on-2x-spark-cluster-recipe-findings-fixes-benchmarks/370459
- MiniMax M3 NVFP4 for quad Spark — https://forums.developer.nvidia.com/t/minimax-m3-nvfp4-for-quad-dgx-spark/372123
- **Multi-node inference crash on GB10 (NCCL timeouts, 0x51 mem alloc; Qwen 122B & Nemotron 120B) — failure-mode reference** — https://forums.developer.nvidia.com/t/multi-node-inference-crash-on-blackwell-gb10-memory-allocation-0x51-nccl-timeouts-tested-on-qwen-122b-nemotron-120b/363989
- Multi-node vLLM with Docker Compose — https://forums.developer.nvidia.com/t/multi-node-vllm-on-dgx-spark-with-docker-compose/364969
- DGX Spark hard power-off under GPU load (firmware) — https://forums.developer.nvidia.com/t/dgx-spark-gb10-reproducibly-hard-powers-off-under-gpu-load-fully-updated-zero-crash-capture/373251
- Best speed for Qwen 3.6 27B without quantizing (one-model workhorse thread) — https://forums.developer.nvidia.com/t/whats-the-best-speed-we-can-get-with-qwen-3-6-27b-without-quantizing/367561

## Single-node multi-model fleet (LiteLLM + llama-swap) — the "real-world fleet" lineage

- NVIDIA forum: Running a Full LLM Stack (App -> LiteLLM -> llama-swap -> vLLM/llama.cpp/Ollama) — the origin thread — https://forums.developer.nvidia.com/t/running-a-full-llm-stack-on-dgx-spark-gb10-your-application-litellm-llama-swap-vllm-llama-cpp-ollama/367580
- **martinB78 reference repo (our original source)** — https://github.com/mARTin-B78/dgx-spark_lite-llm_llama-swap_vllm_llama-cpp_ollama
- Dre Dyson series (the tutorial layer built over the martinB78 repo):
  - Production-ready multi-model stack — https://dredyson.com/how-i-built-a-production-ready-multi-model-llm-stack-on-a-single-nvidia-dgx-spark-gb10-a-saas-founders-complete-step-by-step-guide-to-running-litellm-llama-swap-vllm-llama-cpp-and-ollam/
  - 10+ models / advanced config (memory math; the MoE allocator-not-freeing bug; `--network container:llama-swap`) — https://dredyson.com/how-i-mastered-running-a-full-multi-model-llm-stack-on-dgx-spark-gb10-advanced-litellm-llama-swap-vllm-llama-cpp-ollama-configuration-guide-with-dynamic-vram-orchestration-for-10-models/
  - FinOps / cut cloud bill ~90% — https://dredyson.com/how-i-cut-our-cloud-llm-bill-by-90-using-a-full-multi-model-stack-on-nvidia-dgx-spark-gb10-litellm-llama-swap-vllm-llama-cpp-ollama-a-finops-complete-step-by-step-configuration-and-cos/
  - 5 critical mistakes (CPU-pinning LiteLLM vs llama-swap; Docker networking) — https://dredyson.com/5-critical-mistakes-everyone-makes-with-running-a-full-llm-stack-on-dgx-spark-gb10-your-application-litellm-llama-swap-vllm-llama-cpp-ollama-and-how-to-fix-them-before-you-lose-your-mind/
  - Beginner setup guide — https://dredyson.com/how-to-run-a-full-llm-stack-on-dgx-spark-gb10-a-complete-beginners-step-by-step-setup-guide-with-litellm-llama-swap-vllm-llama-cpp-and-ollama/
  - 5-minute fix guide — https://dredyson.com/fix-running-a-full-llm-stack-on-dgx-spark-gb10-your-application-litellm-llama-swap-vllm-llama-cpp-ollama-in-under-5-minutes-actually-works/
- dasroot: Mastering Multi-Model Stacks with Llama-Swap (matrix groups; DSL swap logic) — https://dasroot.net/posts/2026/05/mastering-multi-model-stacks-llama-swap/
- calico88x/DGX-Model-Manager (web UI orchestrating LiteLLM + SGLang/vLLM/llama.cpp/Ollama; control panel, never in the request path) — https://github.com/calico88x/DGX-Model-Manager

## Build logs / explainers

- corti: Two Sparks, One Cluster (capacity mental model; PCIe x4 x2 quirk; stacked numbers; 405B-class claim) — https://corti.com/two-sparks-one-cluster-why-stacking-nvidia-dgx-spark-units-unlocks-local-frontier-scale-inference/
- Michael Peres (Medium): Two DGX Sparks -> LLM cluster with vLLM, Ray, Qwen3.6 (ships an architecture diagram) — https://medium.com/@michaelperes1/turning-two-dgx-sparks-into-a-local-llm-cluster-with-vllm-ray-and-qwen3-6-7eb2a6e04ade
- Doran Gao (Medium): Connecting two Sparks via 200Gb/s RoCE (network setup; NCCL; automation scripts) — https://medium.com/@dorangao/connecting-two-dgx-spark-systems-via-200gb-s-roce-network-for-multi-node-gpu-training-50d67d3630a5
- NADDOD: How to deploy DGX Spark (cabling; direct vs switch topologies) — https://www.naddod.com/blog/how-to-deploy-nvidia-dgx-spark · https://naddod.medium.com/how-to-deploy-nvidia-dgx-spark-7aa4d8151346
- Kubesimplify: Anatomy of an LLM inference request on DGX Spark (prefill/decode/KV; memory-bandwidth as the lever) — https://blog.kubesimplify.com/day-2-anatomy-of-an-llm-inference-request-from-prompt-to-answer-step-by-step
- Thomas P. Braun / Avarok: DGX Spark, Nemotron3, NVFP4 — 65+ tps (local PDF in this folder)

## Repos / engines

- mostlygeek/llama-swap (the swap-to-fit front door) — https://github.com/mostlygeek/llama-swap
- eugr/spark-vllm-docker (dual-Spark vLLM; recipes incl. DeepSeek-V4-Flash; `--no-ray`, fastsafetensors, GB-based gpu-mem-util; the `nvidia-smi -lgc` power-off mitigation) — https://github.com/eugr/spark-vllm-docker · DeepSeek recipe PR #219 — https://github.com/eugr/spark-vllm-docker/pull/219 · configurable repo URLs PR #244 — https://github.com/eugr/spark-vllm-docker/pull/244
- mark-ramsey-ri/vllm-dgx-spark (1-to-N Sparks; 41 model presets; auto IB/interface detection; same code path single/2/3+ nodes) — https://github.com/mark-ramsey-ri/vllm-dgx-spark
- tonyd2wild/deepseek-v4-flash-dual-spark-recipe (the reproducible 2x recipe from the canonical thread) — https://github.com/tonyd2wild/deepseek-v4-flash-dual-spark-recipe
- jasl/vllm fork (DeepSeek-V4-Flash GB10 enablement) — https://github.com/jasl/vllm
- llama.cpp PR #17570 (native Anthropic `/v1/messages` — the change that made llama.cpp a drop-in for Claude-protocol clients) — https://github.com/ggml-org/llama.cpp/pull/17570

## Serving-layer tooling

- LiteLLM docs — https://docs.litellm.ai/ · docker quick start — https://docs.litellm.ai/docs/proxy/docker_quick_start · routing / load-balancing / fallbacks — https://docs.litellm.ai/docs/routing-load-balancing · config.yaml spec — https://docs.litellm.ai/docs/proxy/configs
- Sparkrun — https://sparkrun.dev · CLI overview — https://sparkrun.dev/cli/overview/ · proxy gateway — https://sparkrun.dev/tutorials/proxy-gateway/ · multi-node TP — https://sparkrun.dev/tutorials/multi-node/ · repo — https://github.com/spark-arena/sparkrun · web UI — https://github.com/mcampa/sparkrun-ui (see "Considered and deferred: sparkrun" below)
- spark-arena.com — community GB10 benchmarks / leaderboard — https://spark-arena.com · https://spark-arena.com/leaderboard

## Considered and deferred: sparkrun (2026-07-01)

Evaluated as a candidate to absorb parts of the hand-rolled two-Spark bring-up (`RUNBOOK-two-spark-bring-up.md`) and/or the LiteLLM front-door overlay. **Verdict: not adopted** — the division of labour turned out narrower than it first looked.

**Genuinely replaces (mechanical boilerplate):**
- SSH mesh setup; CX-7 IP/netplan config (`sparkrun setup cx7` — static IPs, MTU 9000, jumbo frames — **IP addressing only, not firmware**)
- NCCL env-var computation + multi-node launch syntax (`--tp N` → head/worker container launch, automatic node-count trimming)
- Model + container distribution to remote hosts over the CX-7 link

**Does NOT replace (the load-bearing gates — still ours regardless):**
- **CX-7 firmware currency** (28.45.4028+, the all_gather-halving fix). `setup cx7` never touches firmware — that's a separate `mlxconfig`/`mlnx-fw-updater`/DOCA-OFED path. Our Phase 2 gate + the NIC-brick guard (`apt-mark hold mlnx-fw-updater`) stay necessary either way.
- **The two-signal transport gate** (busbw ≥ 20GB/s AND `NET/IB` not `NET/Socket`). Sparkrun's own docs treat a slow multi-node launch as reactive troubleshooting ("make sure CX-7 is configured") rather than a pre-launch assertion — exactly the "blog says watch out" pattern the gate exists to replace. A healthy busbw number can still mask a silent TCP fallback; this needs verifying no matter what launched the job.
- **The power-off mitigation** (`nvidia-smi -lgc 200,2150` before any TP launch). Not documented on sparkrun's native `vllm-distributed` runtime; may be inherited only via the `eugr`-delegating runtime.
- **vLLM commit/torch pinning** for the actual DeepSeek-V4-Flash launch (`jasl/vllm @ dda4668b` + torch 2.9.1, the cudagraph mode avoiding vLLM #40969). Writing a sparkrun recipe with these exact pins is the same pinning work as the runbook — just serialised as YAML instead of bash + gates.
- **DF-001 no-cloud-fallback enforcement.** Sparkrun's `proxy` command is a LiteLLM-powered auto-discovery gateway (convenience-oriented); no documented equivalent to our `fallbacks: []` + no-cloud-target assertion.

**Dependency-cost note:** sparkrun bundles LiteLLM, a fast-release CLI (uv-installed, 40+ releases), and git-based community recipe registries by default — more third-party surface, in exchange for automating the lower-risk half of the bring-up while the higher-risk half (the gates above) still has to be hand-written on top. Same supply-chain caution already applied to LiteLLM itself applies here; net complexity doesn't obviously drop if the gates still have to run regardless of what did the launching.

**Where it's a genuinely good idea, not yet built:** sparkrun's `runtime` layer is a Python-entry-point plugin system — `vllm-distributed`, `vllm`/Ray, `sglang`, `llama-cpp`, `trt-llm`/MPI, and an `eugr`-delegating runtime all coexist as plugins today. A **`llama-swap` runtime** — rendering a recipe into a `matrix.sets` entry in a shared `config.yaml` and triggering `-watch-config`, instead of launching a standalone container — is architecturally native to that system, not a fork. It would combine sparkrun's recipe registry / VRAM pre-flight / CX-7 distribution with llama-swap's actual differentiator: memory-aware coexistence across a fixed always-on fleet. Scope note: only helps the single-node fleet host (Node A) — doesn't touch the cross-node two-box DeepSeek story, which stays sparkrun's (or our Phase 8's) territory either way. **Not scheduled** — logged here as a backlog idea, and a plausible future video hook in its own right ("the gap in the DGX Spark tooling ecosystem").

## Related local docs

- `../../decisions/DECISION-DF-004-two-spark-serving-topology-unified-front-door.md` — the decision this research backs
- `../../decisions/DECISION-DF-001-local-first-inference-on-dark-factory-critical-path.md` — the single-node front-door decision DF-004 evolves
- `dark-factory-economics-and-model-serving.md` — single-node baseline + the April cost analysis
- `llama-swap-config.yaml`, `llama-swap-setup.md` — single-node config + setup guide
- `gb10-memory-budget-and-macbook-offload.md`, `gb10-model-requirements-matrix.md` — memory budgeting + model footprints
- `AUTOBUILD-ON-LLAMA-SWAP-findings.md` — the §9.5–9.8 consolidation findings referenced by fleet-memory

---

*Compiled 2026-06-18. Paraphrased summaries only — follow the links for the originals; numbers are point-in-time.*
