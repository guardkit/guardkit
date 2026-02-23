Here's a complete testing guide based on the investigation work in TASK-REV-55C3 and the FEAT-GLI feature.

Testing AutoBuild via vLLM on Dell ProMax GB10
Prerequisites
Dell ProMax GB10 reachable via Tailscale (hostname: promaxgb10-41b1)
Docker installed on the GB10
HuggingFace token set if using gated models (HF_TOKEN)
Step 1: Start the vLLM Server on GB10
SSH into the GB10 and run the serve script (or use Docker directly):


# Option A: Use the provided script (copy it to GB10 first)
scp scripts/vllm-serve.sh promaxgb10-41b1:~/
ssh promaxgb10-41b1
./vllm-serve.sh              # Default: Qwen3-Coder-Next FP8 (best quality)
# OR
./vllm-serve.sh 30b          # Faster but lower quality

# Option B: Direct Docker command on GB10
docker run -d \
  --name vllm-qwen3-coder \
  --gpus all -p 8000:8000 --ipc=host \
  --ulimit memlock=-1 --ulimit stack=67108864 \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  nvcr.io/nvidia/vllm:26.01-py3 \
  vllm serve Qwen/Qwen3-Coder-Next-FP8 \
    --host 0.0.0.0 --port 8000 \
    --served-model-name claude-sonnet-4-5-20250929 \
    --enable-auto-tool-choice --tool-call-parser qwen3_coder \
    --gpu-memory-utilization 0.8 --max-model-len 65536 \
    --attention-backend flashinfer --enable-prefix-caching \
    --load-format fastsafetensors
Wait 3-5 minutes for the 80B model to load.

Step 2: Verify the Server is Ready (from your Mac)
Run these from your MacBook:


# 1. Health check (should return OK)
curl http://promaxgb10-41b1:8000/health

# 2. Check model is loaded (should list claude-sonnet-4-5-20250929)
curl http://promaxgb10-41b1:8000/v1/models

# 3. Test the Anthropic Messages API endpoint directly
curl http://promaxgb10-41b1:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: dummy-key" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "Hello, are you working? Reply in one sentence."}]
  }'
All three should succeed before proceeding.

Step 3: Test AutoBuild with the Wrapper
The simplest approach (Approach A from the review) - inline env vars:


# Quick test with a simple existing task
ANTHROPIC_BASE_URL=http://promaxgb10-41b1:8000 \
ANTHROPIC_API_KEY=vllm-local-key \
guardkit autobuild task TASK-GLI-004 --verbose
TASK-GLI-004 (update graphiti.yaml schema) is complexity 2, making it a good first test.

Step 4: Create the Permanent Wrapper Script (Optional)
For repeated use, set up the wrapper:


# Create the wrapper
mkdir -p ~/.local/bin

cat > ~/.local/bin/autobuild-vllm << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

VLLM_HOST="${VLLM_HOST:-promaxgb10-41b1}"
VLLM_PORT="${VLLM_PORT:-8000}"
VLLM_URL="http://${VLLM_HOST}:${VLLM_PORT}"

# Pre-flight: check VLLM server is reachable
if ! curl -sf "${VLLM_URL}/health" > /dev/null 2>&1; then
    echo "ERROR: VLLM server at ${VLLM_URL} is not reachable"
    echo "Start it with: ssh ${VLLM_HOST} './vllm-serve.sh'"
    exit 1
fi

export ANTHROPIC_BASE_URL="${VLLM_URL}"
export ANTHROPIC_API_KEY="vllm-local-key"

echo "AutoBuild → VLLM/Qwen3 @ ${VLLM_URL}"
echo "---"
exec guardkit autobuild "$@"
EOF

chmod +x ~/.local/bin/autobuild-vllm

# Then use it:
autobuild-vllm task TASK-GLI-004 --verbose
Step 5: Graduated Testing Sequence
Test progressively to build confidence:

Test	Command	What It Validates
Smoke test	Step 3 curl to /v1/messages	vLLM serves Anthropic API format
Simple task	autobuild-vllm task TASK-GLI-004 --verbose	Tool calling + Player-Coach basic flow
Medium task	autobuild-vllm task TASK-GLI-002 --verbose	Multi-file edits, config changes
Full workflow	autobuild-vllm task TASK-GLI-003 --verbose	Complex code injection, mocking
What to Watch For
Tool calling failures: If the model doesn't use tools correctly, try --tool-call-parser qwen3_xml instead of qwen3_coder in the vllm-serve command
Model name mismatch: The --served-model-name must be claude-sonnet-4-5-20250929 (AutoBuild's default)
Slow first request: Normal - prefix cache is cold. Subsequent turns should be faster
Context overflow: If tasks have very large prompts, reduce --max-model-len or use the 30B model
Key Verification
Your interactive Claude Code sessions (VS Code extension, claude CLI) remain on the Anthropic API and are completely unaffected - only the specific guardkit autobuild invocations with the env vars use vLLM.