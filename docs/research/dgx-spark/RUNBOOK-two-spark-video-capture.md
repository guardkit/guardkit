# Two-Spark Bring-Up — Video Capture Runbook

**Spine:** *A second node buys capacity, not speed — share the boxes by time, not at once.* (DECISION-DF-004)

**How to use this:** a capture *spine*, not a script. Record the real bring-up with OBS and narrate as you go. Don't re-shoot for polish, don't write lines, don't hide failures — the gotchas are the content. Don't let the camera slow the build; if a phase doesn't land, pick it up in a second session.
Audience: AI engineers. Target: ~12–18 min build-log + architecture explainer.

## The one idea (three beats — open on beat 1, close on beat 3)

1. **The intuition** — "Two boxes, twice the tokens, right?" Everyone assumes stacking = speed.
2. **The reality** — the 200G ConnectX-7 link (~25 GB/s, wired as 2× PCIe Gen5 x4, not one x8) is the ceiling. Cross-node tensor-parallelism only helps a model too big for one 128 GB node; anything that fits is *faster* single-node.
3. **The consequence** — so you don't stack for speed. You stack for **capacity** (run the model that won't fit 128 GB) and **parallel throughput**, then **time-share** the boxes: swap the fleet on one node, reserve TP for the one oversized proposer.

## Pre-read (open in tabs before recording)

- `diagrams/two-spark-fleet-serving-architecture.svg` and `diagrams/two-spark-request-routing.svg`
- `DECISION-DF-004-two-spark-serving-topology-unified-front-door.md` (§2.1 topology, §2.2 memory rule)
- `two-spark-serving-research-and-references.md` (the gotchas + the expected numbers)

## Pre-flight — recording setup &nbsp; · &nbsp; **Gate:** scenes ready, diagrams loaded, terminal legible

- OBS scenes: (a) desk/hardware cam, (b) full-screen terminal, (c) diagram/browser. Terminal font ≥ 18pt.
- Both Sparks powered; CX-7 cable in hand for the cold open; single clean shell, history cleared.

## Capture phases

| # | On screen | Say (prompts, not lines) | Gate (pass/fail) |
|---|-----------|--------------------------|------------------|
| **P1 Hook** | The two Sparks + the cable | Beat 1 then beat 3 in ~30s: "I stacked two of these — and the lesson wasn't what I expected." | Thesis stated on camera |
| **P2 Bring-up** *(the war story)* | firmware / `dgx-spark-mlnx-hotplug` update → cable in the **same physical port** both ends → `ip link` showing the **`enp1…`** names (CX-7 shows 4 names for 2 ports) → pin `NCCL/UCX/GLOO/TP_SOCKET_IFNAME` to the QSFP iface → `all_gather_perf` | Narrate each gotcha as you hit it. Call out the firmware **hard power-off under load** and the `sudo nvidia-smi -lgc 200,2150` clamp that prevents it. | Link up + `all_gather_perf` passes on camera |
| **P3 Proof** *(the number)* | Launch vLLM `--tp 2` (pinned commit, `--no-ray`/mp backend), then the *same* model single-node; read decode tok/s off both; show the ~6 min cold start | "Here's the number that settles it." Compare TP=2 vs single-node tok/s; note the expectation (≈40 tok/s warm, weak long-context prefill, decode collapses under concurrency). | Both tok/s + cold-start time captured |
| **P4 Payoff** *(architecture)* | The two SVG diagrams | Walk the layered stack: one **LiteLLM :4000** front door → **llama-swap** pool (fleet + always-on nomic) on Node A → **vLLM TP=2** proposer across both nodes → Postgres+pgvector on the NAS. State the **memory rule** (the big proposer and a full swap pool can't co-reside — choose per session) and the **no auto cloud fallback** guard (DF-001). | Topology + "share by time" rule explained |
| **P5 Close** | Back to hardware / diagram | Restate beat 3; one-line tease of fleet-memory and the dark factory. | Lesson restated |

## Evidence / RESULTS — prompt pack (for the edit + publish)

- **Title options:** "I Stacked Two DGX Sparks — It Wasn't Faster (Here's Why)" · "200GbE Between Two Sparks: Capacity, Not Speed" · "Two-Node Local LLM Serving — The Honest Bring-Up"
- **Thumbnail text:** `2× THE BOX ≠ 2× THE SPEED`
- **Chapters** = the phases: `00:00` Hook · Bring-up · The benchmark · The architecture · Close.
- **Lower-third captions** (drop your real numbers): TP=2 decode tok/s · single-node tok/s · cold-start time · link bandwidth.
- **Say-these truths** (the spine, safe to repeat): the interconnect is the ceiling · TP only for models that don't fit one node · stack for capacity + parallelism · share the boxes by time, not at once.
- **Do NOT:** re-shoot for polish · script lines · cut the failures · let the camera slow the build.
- **Must-haves to make the video** (any gate that failed → a second session is fine): (1) thesis on camera, (2) ≥2 bring-up gotchas captured live, (3) the benchmark numbers, (4) the architecture explainer, (5) the close.

---
*Source material: DECISION-DF-004, `two-spark-serving-research-and-references.md`, and the `diagrams/` SVGs. Numbers in P3 are captured live, not pre-stated.*
