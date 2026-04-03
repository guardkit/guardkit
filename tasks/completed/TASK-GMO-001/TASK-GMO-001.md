---
id: TASK-GMO-001
title: "Install and configure Ollama with Qwen2.5-14B on MacBook Pro M2 Max"
status: completed
updated: 2026-04-03T13:55:00Z
created: 2026-04-03T00:00:00Z
priority: high
tags: [graphiti, macbook, ollama, setup]
task_type: implementation
parent_review: TASK-REV-GMAC
feature_id: FEAT-GMO
implementation_mode: direct
wave: 1
complexity: 2
---

# Task: Install and configure Ollama with Qwen2.5-14B on MacBook Pro M2 Max

## Description

Install Ollama on the MacBook Pro M2 Max, pull Qwen2.5-14B-Instruct Q4_K_M, and verify
it serves on port 8000 with network access enabled.

## Steps

1. Install Ollama: `brew install ollama`
2. Pull model: `ollama pull qwen2.5:14b-instruct-q4_K_M`
3. Start with network binding: `OLLAMA_HOST=0.0.0.0:8000 ollama serve`
4. Verify health: `curl http://localhost:8000/v1/models`
5. Verify from GB10: `curl http://<macbook-tailscale-ip>:8000/v1/models`
6. Check macOS firewall allows incoming connections on port 8000

## Acceptance Criteria

- [x] Ollama installed and running on MacBook (v0.18.0, via brew)
- [x] Qwen2.5-14B Q4_K_M model pulled and loaded (9.0 GB)
- [x] Server accessible on port 8000 from local network / Tailscale (100.111.236.109:8000)
- [x] `curl /v1/models` returns model list from both localhost and Tailscale IP

## Notes

- Ollama reconfigured from default port 11434 → 0.0.0.0:8000 via `OLLAMA_HOST`
- `launchctl setenv OLLAMA_HOST "0.0.0.0:8000"` set for GUI app persistence
- Currently running as CLI process (`ollama serve`); for persistence, relaunch the Ollama.app
  which will pick up the `launchctl setenv` variable
- macOS firewall allowed connections (no prompt blocked)
- Tailscale IP: 100.111.236.109
