#!/usr/bin/env bash
# The project's live-gate driver (deploy/profile.yaml live_gate.driver), from
# GuardKit's deployment kit. The factory accepts a project's first deployment
# profile only when it names a live-gate driver (Forge
# pipeline/merge_executor.py first_deployment_profile_is_usable), and runs it
# after the candidate's health check (with candidate.env) and after a promote
# (with live_gate.env only), always appending
#   --feature <feature id> --target <env id> [--gates <ids>]
# which this smoke gate accepts and does not need.
#
# The gate: the deployment answers its health path with HTTP 200 and every
# container carries the identity the deploy step recorded for it. It prints one results envelope (JSON)
# on stdout and exits by the factory's driver map: 0 pass, 1 fail,
# 3 instrument_fail, 4 environment_fail (deploy/live_gate.py in Forge).
#
# A project that grows real end-to-end checks replaces this driver in
# deploy/profile.yaml with its own; until then this proves the running service
# is the one that was deployed and that it answers.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

feature="unknown"
while (($# > 0)); do
  case "$1" in
  --feature) feature="${2:-unknown}"; shift 2 || shift ;;
  --target | --gates) shift 2 || shift ;;
  *) shift ;;
  esac
done
[[ "$feature" =~ ^[A-Za-z0-9._-]{1,80}$ ]] || feature="unknown"

gate_id="deploy-kit-health"
run_id="$feature-$(date -u +%Y%m%dT%H%M%SZ)"

# Text safe to put inside a JSON string: no quotes, backslashes or controls.
# shellcheck disable=SC1003 # '"\\' is a quote and a backslash for tr
plain() { printf '%s' "$1" | tr -d '"\\' | tr -c '[:print:]' ' '; }

envelope() {
  local verdict="$1" status="$2" detail="$3" exit_code="$4"
  printf '{"run_id":"%s","verdict":"%s","gates":[{"gate_id":"%s","exit_code":%s,"assertions":[{"id":"%s::health","status":"%s","observed":"%s"}]}]}\n' \
    "$(plain "$run_id")" "$verdict" "$gate_id" "$exit_code" "$gate_id" "$status" "$(plain "$detail")"
}

# shellcheck source=deploy/settings.sh
source "$root/deploy/settings.sh"
# shellcheck source=deploy/lib.sh
source "$root/deploy/lib.sh"
# Anything that stops the gate before it can look is an instrument problem,
# never a verdict on the app.
die() {
  echo "live gate: $*" >&2
  envelope instrument_fail fail "the gate could not run: $*" 3
  exit 3
}
kit_settings
require_command curl
require_command docker
kit_check_target
kit_expected_identity

deadline=$(($(date +%s) + DEPLOY_GATE_WAIT_SECONDS))
while :; do
  rc=0
  kit_probe "$port" "$expected" || rc=$?
  ((rc == 0)) && break
  (($(date +%s) < deadline)) || break
  sleep 2
done

case "$rc" in
0)
  echo "live gate: $probe_detail" >&2
  envelope pass pass "$probe_detail" 0
  exit 0
  ;;
2)
  envelope environment_fail fail "$probe_detail" 4
  exit 4
  ;;
*)
  envelope fail fail "$probe_detail" 1
  exit 1
  ;;
esac
