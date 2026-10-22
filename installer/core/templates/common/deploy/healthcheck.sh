#!/usr/bin/env bash
# Post-deploy health (deploy/profile.yaml health_checks), from GuardKit's
# deployment kit. The factory runs it with candidate.env after the candidate
# check and with nothing after a promote, so the target is chosen from those
# settings: the candidate project on CANDIDATE_PORT, else the live project on
# the live port (deploy/settings.sh).
#
# Healthy means: http://127.0.0.1:<port><health path> answers HTTP 200, and
# every container of the project carries one and the same identity label (the
# one the deploy step was handed; when DEPLOY_IDENTITY is set, exactly that).
# It waits up to DEPLOY_HEALTH_WAIT_SECONDS. The exit code is the verdict.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
# shellcheck source=deploy/settings.sh
source "$root/deploy/settings.sh"
# shellcheck source=deploy/lib.sh
source "$root/deploy/lib.sh"
kit_settings
require_command curl
require_command docker
kit_check_target
expected="${DEPLOY_IDENTITY:-}"
if [[ -n "$expected" ]]; then
  valid_identity "$expected" || die "DEPLOY_IDENTITY is not an identity"
fi

deadline=$(($(date +%s) + DEPLOY_HEALTH_WAIT_SECONDS))
while :; do
  rc=0
  kit_probe "$port" "$expected" || rc=$?
  if ((rc == 0)); then
    echo "healthy: $probe_detail"
    exit 0
  fi
  (($(date +%s) < deadline)) || break
  sleep 2
done
die "unhealthy: $probe_detail (waited ${DEPLOY_HEALTH_WAIT_SECONDS}s)"
