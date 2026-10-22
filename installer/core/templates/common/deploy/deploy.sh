#!/usr/bin/env bash
# The project's deploy step (deploy/profile.yaml compose.script), from
# GuardKit's deployment kit. The factory runs it with no arguments; every
# input arrives in the environment (deploy/lib.sh lists what each step sends).
#
# Modes (exactly one signal; none, or two, is refused):
#   CANDIDATE=1        build and start the candidate compose project
#                      (COMPOSE_PROJECT_NAME, CANDIDATE_PORT from candidate.env)
#                      labelled with DEPLOY_IDENTITY; print
#                      CHECKED_ARTIFACT=<service>=sha256:<image id>,... and
#                      DEPLOYED_IDENTITY=<identity>
#   CANDIDATE_DOWN=1   remove the named candidate project, its volumes and its
#                      deploy record, only when what runs there is
#                      DEPLOY_IDENTITY's (or nothing)
#   PROMOTE=1          start the live project "<env id>-live" on the live port
#                      from exactly the images in DEPLOY_ARTIFACT (never a
#                      rebuild) labelled with DEPLOY_IDENTITY; print
#                      DEPLOYED_IDENTITY=<identity>
#   RUNNING_IDENTITY=1 read-only: print RUNNING_IDENTITY=<identity>, =none, or
#                      RUNNING_IDENTITY_UNKNOWN=<reason>; always exits 0
#   REVERT=1           refused: this kit keeps no rollback image
#
# Long command output (image builds) goes to a log file and only its end is
# shown, and the marker lines are printed on stdout and again as the last
# lines of stderr, so the factory's output limits never cut them off.
#
# After a promote, this project's older kept images (<env id>-deploy-*) are
# removed by exact name; nothing is pruned.
#
# The compose file is the project's own root compose.yaml. The kit exports
# APP_PORT (the loopback port the public service must publish) and adds a
# generated override that labels every container with the identity and, for
# a promote, pins every service to its checked image. A successful candidate
# or promote records the identity and port for the health check and live gate
# (deploy/lib.sh, kit_write_record). The live project is
# never touched by a candidate step, and a candidate step never names it.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
# shellcheck source=deploy/settings.sh
source "$root/deploy/settings.sh"
# shellcheck source=deploy/lib.sh
source "$root/deploy/lib.sh"
kit_settings
kit_mode

case "$mode" in
none) die "no deploy mode is set: expected CANDIDATE, CANDIDATE_DOWN, PROMOTE or RUNNING_IDENTITY" ;;
revert) die "REVERT: this deployment kit keeps no rollback image (the profile has no rollback_image_ref)" ;;
preview) die "this deployment kit has no review preview; remove the preview section from deploy/profile.yaml" ;;
esac

require_command docker

# --- Read-only: what is the live project running? --------------------------------
if [[ "$mode" == running ]]; then
  project="$live_project"
  rc=0
  kit_label_state || rc=$?
  if ((rc != 0)); then
    echo "RUNNING_IDENTITY_UNKNOWN=$label_reason"
  elif [[ "$label_state" == none ]]; then
    echo "RUNNING_IDENTITY=none"
  elif [[ "$label_state" == mixed ]]; then
    echo "RUNNING_IDENTITY_UNKNOWN=$label_reason"
  else
    echo "RUNNING_IDENTITY=$label_value"
  fi
  exit 0
fi

docker compose version >/dev/null 2>&1 || die "docker compose is required and is not available"
identity="${DEPLOY_IDENTITY:-}"
[[ -n "$identity" ]] || die "$mode needs DEPLOY_IDENTITY, the identity the factory handed this step"
valid_identity "$identity" || die "DEPLOY_IDENTITY must be <name> or <name>@<fingerprint> (letters, digits, '.', '_', '-')"

# --- Which project ----------------------------------------------------------------
case "$mode" in
candidate | candidate_down)
  project="${COMPOSE_PROJECT_NAME:-$candidate_project}"
  [[ "$project" != "$live_project" ]] || die "$mode refuses to act on the live project $live_project"
  ;;
promote)
  [[ -z "${COMPOSE_PROJECT_NAME:-}" || "$COMPOSE_PROJECT_NAME" == "$live_project" ]] ||
    die "PROMOTE deploys the live project $live_project, not $COMPOSE_PROJECT_NAME"
  project="$live_project"
  ;;
esac
valid_project_name "$project" || die "invalid compose project name: $project"
# Compose must not pick up a project name of its own from the environment.
unset COMPOSE_PROJECT_NAME COMPOSE_FILE

# --- Taking a candidate down --------------------------------------------------------
if [[ "$mode" == candidate_down ]]; then
  rc=0
  kit_label_state || rc=$?
  ((rc == 0)) || die "$label_reason; the candidate is left as it is"
  if [[ "$label_state" == mixed ]]; then
    die "$label_reason; leaving $project for a person to remove"
  fi
  if [[ "$label_state" == one && "$label_value" != "$identity" ]]; then
    die "the candidate in $project is $label_value, not $identity; leaving it for its own build"
  fi
  # Interpolation needs APP_PORT; its value does not matter to `down`.
  export APP_PORT="${CANDIDATE_PORT:-$DEPLOY_CANDIDATE_PORT}"
  override=""
  kit_log_open
  trap 'rm -f "$kit_log"' EXIT
  kit_logged "removing $project" kit_compose down --volumes --remove-orphans --timeout 10
  kit_remove_record "$project"
  echo "deploy: removed $project" >&2
  exit 0
fi

override="$(mktemp "${TMPDIR:-/tmp}/deploy-override.XXXXXX")"
kit_log_open
trap 'rm -f "$override" "$kit_log"' EXIT

# --- Candidate: build, start, and report what was checked ---------------------------
if [[ "$mode" == candidate ]]; then
  [[ -n "${CANDIDATE_PORT:-}" ]] || die "CANDIDATE needs CANDIDATE_PORT (deploy/profile.yaml candidate.env)"
  valid_port "$CANDIDATE_PORT" || die "invalid CANDIDATE_PORT: $CANDIDATE_PORT"
  [[ "$CANDIDATE_PORT" != "$DEPLOY_LIVE_PORT" ]] || die "the candidate port is the live port $DEPLOY_LIVE_PORT"
  export APP_PORT="$CANDIDATE_PORT"
  kit_write_override "$override" "$identity" labels
  kit_logged "building the candidate" kit_compose build
  kit_logged "starting the candidate" kit_compose up --detach --wait --wait-timeout "$DEPLOY_WAIT_SECONDS" --remove-orphans
  artifact="$(kit_running_images)"
  # Each checked image is kept under a name made from the identity, so the
  # promote can find it and nothing treats it as unused.
  IFS=',' read -r -a parts <<<"$artifact"
  for part in "${parts[@]}"; do
    docker tag "${part#*=}" "$(kit_image "${part%%=*}" "$identity")" >&2
  done
  rc=0
  kit_label_state || rc=$?
  ((rc == 0)) || die "$label_reason"
  [[ "$label_state" == one && "$label_value" == "$identity" ]] ||
    die "the containers in $project do not all carry $identity (${label_reason:-$label_state})"
  kit_write_record "$project" "$identity" "$APP_PORT"
  kit_log_tail
  echo "deploy: $project (candidate) up on 127.0.0.1:$APP_PORT as $identity" >&2
  kit_say "CHECKED_ARTIFACT=$artifact"
  kit_say "DEPLOYED_IDENTITY=$identity"
  exit 0
fi

# --- Promote: run exactly the checked images as the live project --------------------
artifact="${DEPLOY_ARTIFACT:-}"
part_re='[A-Za-z0-9][A-Za-z0-9._-]*=sha256:[0-9a-f]{64}'
[[ "$artifact" =~ ^$part_re(,$part_re)*$ ]] ||
  die "PROMOTE needs DEPLOY_ARTIFACT, the images the candidate check printed as CHECKED_ARTIFACT; refusing to rebuild"
export APP_PORT="$DEPLOY_LIVE_PORT"
services="$(kit_services)"
checked_services="$(tr ',' '\n' <<<"$artifact" | sed 's/=.*//' | LC_ALL=C sort)"
[[ "$checked_services" == "$services" ]] ||
  die "the checked images are for services (${checked_services//$'\n'/ }) but compose.yaml has (${services//$'\n'/ })"
IFS=',' read -r -a parts <<<"$artifact"
for part in "${parts[@]}"; do
  docker image inspect "${part#*=}" >/dev/null 2>&1 || die "the checked image ${part#*=} (${part%%=*}) is not on this machine"
  docker tag "${part#*=}" "$(kit_image "${part%%=*}" "$identity")" >&2
done
kit_write_override "$override" "$identity" images
kit_logged "starting the live project" kit_compose up --detach --no-build --pull never --wait --wait-timeout "$DEPLOY_WAIT_SECONDS" --remove-orphans
running="$(kit_running_images)"
[[ "$(sorted_artifact "$running")" == "$(sorted_artifact "$artifact")" ]] ||
  die "the live project runs $running, not the checked images $artifact"
rc=0
kit_label_state || rc=$?
((rc == 0)) || die "$label_reason"
[[ "$label_state" == one && "$label_value" == "$identity" ]] ||
  die "the containers in $project do not all carry $identity (${label_reason:-$label_state})"
kit_write_record "$project" "$identity" "$APP_PORT"
kit_remove_old_images "$(identity_tag "$identity")" || true
kit_log_tail
echo "deploy: $project (live) up on 127.0.0.1:$APP_PORT as $identity" >&2
kit_say "DEPLOYED_IDENTITY=$identity"
