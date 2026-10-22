# shellcheck shell=bash
# shellcheck disable=SC2034 # mode, project, port, label_* are read by the scripts that source this
# shellcheck disable=SC2154 # root is set by the script that sources this
#
# GuardKit deployment kit: the one place that implements the software
# factory's deployment contract for a Docker Compose project. Sourced by
# deploy/deploy.sh, deploy/healthcheck.sh and deploy/live-gate.sh after
# deploy/settings.sh. Copied verbatim by `guardkit deploy init`; a project
# does not need to edit it.
#
# What the factory (Forge) sends each step, read from Forge's own source
# (src/forge/deploy/stage.py, runbook_builder.py, executor/shell_steps.py,
# pipeline/merge_executor.py, pipeline/deployment_identity.py):
#
#   candidate check  CANDIDATE=1 + candidate.env + DEPLOY_IDENTITY
#   candidate down   CANDIDATE_DOWN=1 + candidate.env + DEPLOY_IDENTITY
#   promote          PROMOTE=1 + DEPLOY_IDENTITY + DEPLOY_ARTIFACT (no port)
#   revert           REVERT=1 (+ ROLLBACK_IMAGE_REF); this kit keeps none
#   what is running  RUNNING_IDENTITY=1, nothing else
#   health checks    candidate.env after the candidate; nothing after promote
#   live gate        candidate.env on the candidate leg; live_gate.env after
#                    promote; argv gets --feature <id> --target <env id>
#
# Every program gets an environment built from nothing (PATH, a private HOME
# and TMPDIR, the locale, proxies, and the values above), so the scripts take
# nothing else from the environment except the optional waits in settings.sh.
#
# What the scripts print for the factory (one line each, last one wins):
#   CHECKED_ARTIFACT=<service>=sha256:<id>[,...]   after a candidate check
#   DEPLOYED_IDENTITY=<identity>                   after a candidate or promote
#   RUNNING_IDENTITY=<identity> | none             answer to RUNNING_IDENTITY=1
#   RUNNING_IDENTITY_UNKNOWN=<reason>              when that cannot be told
# Everything else goes to stderr.
#
# The health check and the live gate are NOT sent the deploy step's identity
# (Forge sends them candidate.env, or nothing after a promote). So each deploy
# step that brings a project up records what it deployed in a per-project
# file, <state dir>/<compose project>.env (IDENTITY, PORT), and the checks
# compare the running containers with that record. The state dir is
# DEPLOY_STATE_DIR or $HOME/.local/state/guardkit-deploy; Forge gives every
# project program of one checkout the same private HOME, so the deploy step
# and the checks that follow it read the same file. Candidate down deletes
# the candidate's record.

# The label every container of a deployment carries, holding the identity the
# factory handed the deploy step. RUNNING_IDENTITY, the health check and the
# live gate read it back.
IDENTITY_LABEL="guardkit.deploy.identity"

# The label every container of a deployment also carries: the sorted,
# comma-separated list of ALL the deployment's services, from the compose file
# of the tree that was deployed. The running-state test needs nothing else,
# so it gives the same answer from any commit's tree.
SERVICES_LABEL="guardkit.deploy.services"

die() {
  echo "deploy: $*" >&2
  exit 1
}

truthy() { [[ "${1:-}" =~ ^(1|true|yes)$ ]]; }

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "$1 is required and was not found on PATH"
}

# Checks the values deploy/settings.sh carries and sets the project names.
kit_settings() {
  [[ "${DEPLOY_ENV_ID:-}" =~ ^[a-z][a-z0-9-]{0,39}$ && "$DEPLOY_ENV_ID" != *- ]] ||
    die "deploy/settings.sh: DEPLOY_ENV_ID must be lower-case letters, digits and '-', starting with a letter"
  local name
  for name in DEPLOY_LIVE_PORT DEPLOY_CANDIDATE_PORT; do
    valid_port "${!name:-}" || die "deploy/settings.sh: $name must be a port number"
  done
  [[ "${DEPLOY_HEALTH_PATH:-}" =~ ^/[A-Za-z0-9._~/-]*$ ]] ||
    die "deploy/settings.sh: DEPLOY_HEALTH_PATH must be a path starting with '/'"
  for name in DEPLOY_WAIT_SECONDS DEPLOY_HEALTH_WAIT_SECONDS DEPLOY_GATE_WAIT_SECONDS; do
    [[ "${!name:-}" =~ ^(0|[1-9][0-9]{0,4})$ ]] || die "$name must be a whole number of seconds"
  done
  live_project="$DEPLOY_ENV_ID-live"
  candidate_project="$DEPLOY_ENV_ID-cand"
}

# Sets `mode` to one of: running candidate candidate_down promote revert
# preview none. Two or more signals are refused: the step never guesses.
kit_mode() {
  local found=()
  truthy "${RUNNING_IDENTITY:-}" && found+=(running)
  truthy "${CANDIDATE:-}" && found+=(candidate)
  truthy "${CANDIDATE_DOWN:-}" && found+=(candidate_down)
  truthy "${PROMOTE:-}" && found+=(promote)
  truthy "${REVERT:-}" && found+=(revert)
  if truthy "${PREVIEW:-}" || [[ -n "${FACTORY_PREVIEW_PORT:-}" ]]; then
    found+=(preview)
  fi
  ((${#found[@]} <= 1)) || die "more than one deploy mode is set (${found[*]}); refusing to guess"
  mode="${found[0]:-none}"
}

valid_project_name() { [[ "$1" =~ ^[a-z0-9][a-z0-9_-]{0,62}$ ]]; }

valid_port() { [[ "$1" =~ ^[1-9][0-9]{1,4}$ ]] && (($1 >= 1 && $1 <= 65535)); }

# Forge's identity text is "<name>@<fingerprint>" (deployment_identity.py).
valid_identity() { [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,100}(@[A-Za-z0-9]{1,64})?$ ]]; }

# An image tag cannot carry '@'; the tag form turns it into '-'.
identity_tag() { printf '%s' "${1//@/-}"; }

# The image name the kit keeps a checked service image under.
kit_image() { printf '%s-deploy-%s:%s' "$DEPLOY_ENV_ID" "${1,,}" "$(identity_tag "$2")"; }

# docker compose for `project`, with the project's compose.yaml and, when
# `override` is set, the kit's generated override file.
kit_compose() {
  local files=(-f "$root/compose.yaml")
  [[ -n "${override:-}" ]] && files+=(-f "$override")
  docker compose --project-name "$project" --project-directory "$root" "${files[@]}" "$@"
}

# The compose file's services, sorted, one per line.
# Each name must also make a valid image name once lower-cased (the kit keeps
# images as <env id>-deploy-<service>), and no two names may differ only by
# case, or they would share one image name.
kit_services() {
  local out name lower
  local -A seen=()
  out="$(override='' kit_compose config --services)" || die "docker compose could not read compose.yaml"
  out="$(printf '%s\n' "$out" | LC_ALL=C sort -u)"
  [[ -n "$out" ]] || die "compose.yaml declares no services"
  while IFS= read -r name; do
    [[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || die "unexpected service name in compose.yaml: $name"
    lower="${name,,}"
    [[ "$lower" =~ ^[a-z0-9]+(([._]|__|-+)[a-z0-9]+)*$ ]] ||
      die "the service name $name in compose.yaml cannot be used in an image name; use letters, digits and single '.', '_' or '-' between them"
    [[ -z "${seen[$lower]:-}" ]] ||
      die "the services ${seen[$lower]} and $name in compose.yaml differ only by case; rename one of them"
    seen[$lower]="$name"
  done <<<"$out"
  printf '%s\n' "$out"
}

# Writes the override file: the identity label on every service and, for a
# promote, the exact checked image for every service.
kit_write_override() {
  local file="$1" identity="$2" with_images="$3" services svc all
  services="$(kit_services)"
  all="$(paste -sd, - <<<"$services")"
  {
    echo "# Generated by deploy/lib.sh for one deploy step; not committed."
    echo "services:"
    while IFS= read -r svc; do
      echo "  $svc:"
      echo "    labels:"
      echo "      $IDENTITY_LABEL: \"$identity\""
      echo "      $SERVICES_LABEL: \"$all\""
      if [[ "$with_images" == images ]]; then
        echo "    image: \"$(kit_image "$svc" "$identity")\""
      fi
    done <<<"$services"
  } >"$file"
}

# Reads the identity labels of every container (running or not) in `project`:
# who owns them, for a teardown. Whether they are running is kit_run_state.
# Sets label_state to none (no containers), one (all carry label_value) or
# mixed (label_reason says why). Returns 2 when docker could not be asked.
kit_label_state() {
  local out values
  label_state="" label_value="" label_reason=""
  out="$(docker ps -a --filter "label=com.docker.compose.project=$project" \
    --format "c:{{.Label \"$IDENTITY_LABEL\"}}" 2>/dev/null)" || {
    label_reason="docker could not list the containers of $project"
    return 2
  }
  if [[ -z "$out" ]]; then
    label_state=none
    return 0
  fi
  if grep -qx 'c:' <<<"$out"; then
    label_state=mixed
    label_reason="a container in $project carries no $IDENTITY_LABEL label"
    return 0
  fi
  # shellcheck disable=SC2001 # the prefix is removed per line, not anywhere
  values="$(sed 's/^c://' <<<"$out" | LC_ALL=C sort -u)"
  if [[ "$values" == *$'\n'* ]]; then
    label_state=mixed
    label_reason="the containers in $project carry different identities: ${values//$'\n'/, }"
    return 0
  fi
  label_state=one
  label_value="$values"
}

# Whether `project` is RUNNING a deployment, and whose (the read-only question,
# the health check, the live gate and the checks after a deploy). Unlike
# kit_label_state, which answers "whose containers are these" for a teardown,
# this uses only the containers' own labels, never the current compose file.
# Sets run_state:
#   none     no container of the project exists at all
#   running  every container is running, all carry one identity and one
#            services list ($SERVICES_LABEL), and every service in that list
#            has exactly one container and no container is outside it
#   unknown  anything else, with run_reason
# Returns 2 when docker could not be asked (run_reason says so).
kit_run_state() {
  local out line state service identity listed total=0 svc
  local -A count=()
  local identities="" lists="" problems=""
  run_state="" run_identity="" run_reason=""
  out="$(docker ps -a --filter "label=com.docker.compose.project=$project" \
    --format "c|{{.State}}|{{.Label \"com.docker.compose.service\"}}|{{.Label \"$IDENTITY_LABEL\"}}|{{.Label \"$SERVICES_LABEL\"}}" \
    2>/dev/null)" || {
    run_reason="docker could not list the containers of $project"
    return 2
  }
  if [[ -z "$out" ]]; then
    run_state=none
    return 0
  fi
  run_state=unknown
  while IFS='|' read -r line state service identity listed; do
    [[ "$line" == c ]] || continue
    total=$((total + 1))
    [[ "$state" == running ]] || problems+="${problems:+; }${service:-a container} is $state"
    [[ -n "$identity" ]] || problems+="${problems:+; }${service:-a container} carries no $IDENTITY_LABEL label"
    [[ -n "$listed" ]] || problems+="${problems:+; }${service:-a container} carries no $SERVICES_LABEL label"
    service="${service:-(none)}"
    count[$service]=$((${count[$service]:-0} + 1))
    identities+="$identity"$'\n'
    lists+="$listed"$'\n'
  done <<<"$out"
  identities="$(printf '%s' "$identities" | LC_ALL=C sort -u)"
  lists="$(printf '%s' "$lists" | LC_ALL=C sort -u)"
  if [[ "$identities" == *$'\n'* ]]; then
    problems+="${problems:+; }the containers carry different identities: ${identities//$'\n'/, }"
  fi
  if [[ "$lists" == *$'\n'* ]]; then
    problems+="${problems:+; }the containers name different service lists: ${lists//$'\n'/ and }"
  fi
  if [[ -z "$problems" ]]; then
    local -A named=()
    IFS=',' read -r -a wanted <<<"$lists"
    for svc in "${wanted[@]}"; do
      named[$svc]=1
      case "${count[$svc]:-0}" in
      1) ;;
      0) problems+="${problems:+; }service $svc has no container" ;;
      *) problems+="${problems:+; }service $svc has ${count[$svc]} containers" ;;
      esac
    done
    for svc in "${!count[@]}"; do
      [[ -n "${named[$svc]:-}" ]] || problems+="${problems:+; }a container of service $svc is not part of the deployment"
    done
  fi
  if [[ -n "$problems" ]]; then
    run_reason="$project is not a complete running deployment ($total containers): $problems"
    return 0
  fi
  run_state=running
  run_identity="$identities"
}

# The image of every service's containers in `project`, as
# "<service>=sha256:<id>,..." sorted by service.
kit_running_images() {
  local services svc cids cid image first out=""
  services="$(kit_services)"
  while IFS= read -r svc; do
    cids="$(kit_compose ps -a -q "$svc")" || die "docker compose could not list $svc in $project"
    [[ -n "$cids" ]] || die "service $svc has no container in $project"
    first=""
    while IFS= read -r cid; do
      image="$(docker inspect --format '{{.Image}}' "$cid")" || die "docker could not inspect $cid"
      [[ "$image" =~ ^sha256:[0-9a-f]{64}$ ]] || die "service $svc runs an image with no sha256 id ($image)"
      [[ -z "$first" || "$first" == "$image" ]] || die "the containers of $svc in $project run different images"
      first="$image"
    done <<<"$cids"
    out+="${out:+,}$svc=$first"
  done <<<"$services"
  printf '%s' "$out"
}

# The artifact text with its parts sorted, for comparison.
sorted_artifact() { tr ',' '\n' <<<"$1" | LC_ALL=C sort | paste -sd, -; }

# One health probe of `project` on `port`: the health path answers HTTP 200
# and every container is running and carries one identity (and `expected`,
# when given).
# Sets probe_detail; returns 0 healthy, 1 not healthy, 2 docker unavailable.
kit_probe() {
  local port="$1" expected="${2:-}" code url
  url="http://127.0.0.1:$port$DEPLOY_HEALTH_PATH"
  probe_http="" probe_identity=""
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 "$url" 2>/dev/null)" || code="000"
  probe_http="$code"
  if [[ "$code" != 200 ]]; then
    probe_detail="$url answered HTTP $code, not 200"
    return 1
  fi
  local rc=0
  kit_run_state || rc=$?
  if ((rc != 0)); then
    probe_detail="$run_reason"
    return 2
  fi
  case "$run_state" in
  none)
    probe_detail="$url answers, but no container of $project is running"
    return 1
    ;;
  unknown)
    probe_detail="$run_reason"
    return 1
    ;;
  esac
  probe_identity="$run_identity"
  if [[ -n "$expected" && "$run_identity" != "$expected" ]]; then
    probe_detail="$project runs $run_identity, not $expected"
    return 1
  fi
  probe_detail="$project answers on $url as $run_identity"
  return 0
}

# Which deployment a health check or live gate looks at, from what the factory
# sent it: the candidate after a candidate check, the live app otherwise.
# Sets project and port.
kit_check_target() {
  if [[ -n "${FACTORY_PREVIEW_PORT:-}" ]] || truthy "${PREVIEW:-}"; then
    die "this deployment kit has no review preview; remove the preview section from deploy/profile.yaml"
  fi
  if [[ -n "${CANDIDATE_PORT:-}" ]] || truthy "${CANDIDATE:-}"; then
    port="${CANDIDATE_PORT:-$DEPLOY_CANDIDATE_PORT}"
    project="${COMPOSE_PROJECT_NAME:-$candidate_project}"
    [[ "$project" != "$live_project" ]] || die "the candidate check names the live project $live_project"
  else
    port="$DEPLOY_LIVE_PORT"
    project="$live_project"
  fi
  valid_port "$port" || die "invalid port: $port"
  valid_project_name "$project" || die "invalid compose project name: $project"
}

# The deploy record file for `project`.
kit_record_file() {
  local dir="${DEPLOY_STATE_DIR:-${HOME:?HOME is not set}/.local/state/guardkit-deploy}"
  valid_project_name "$1" || die "invalid compose project name: $1"
  printf '%s/%s.env' "$dir" "$1"
}

# Records that `project` now runs `identity` on `port` (private, atomic).
kit_write_record() {
  local file dir tmp
  file="$(kit_record_file "$1")"
  dir="$(dirname "$file")"
  (umask 077 && mkdir -p "$dir")
  tmp="$(umask 077 && mktemp "$dir/.record.XXXXXX")"
  printf 'IDENTITY=%s\nPORT=%s\n' "$2" "$3" >"$tmp"
  mv -f "$tmp" "$file"
}

# Reads `project`'s record into record_identity and record_port; dies when
# there is none or it is not well formed.
kit_read_record() {
  local file name value
  file="$(kit_record_file "$1")"
  [[ -r "$file" ]] || die "no deploy record for $1 ($file): it was not deployed from this checkout"
  record_identity="" record_port=""
  while IFS='=' read -r name value; do
    case "$name" in
    IDENTITY) record_identity="$value" ;;
    PORT) record_port="$value" ;;
    *) die "unexpected line in $file" ;;
    esac
  done <"$file"
  valid_identity "$record_identity" || die "the deploy record $file has no valid IDENTITY"
  valid_port "$record_port" || die "the deploy record $file has no valid PORT"
}

kit_remove_record() { rm -f "$(kit_record_file "$1")"; }

# What a health check or live gate expects: the identity the last deploy step
# recorded for `project` on `port` (and DEPLOY_IDENTITY, when a person sets it
# by hand, must agree). Sets expected.
kit_expected_identity() {
  kit_read_record "$project"
  [[ "$record_port" == "$port" ]] ||
    die "$project was deployed on port $record_port, but this check addresses port $port"
  expected="$record_identity"
  if [[ -n "${DEPLOY_IDENTITY:-}" && "$DEPLOY_IDENTITY" != "$expected" ]]; then
    die "DEPLOY_IDENTITY is $DEPLOY_IDENTITY, but $project was deployed as $expected"
  fi
}

# --- Output the factory can read --------------------------------------------------
#
# Forge joins a step's stdout and then its stderr, keeps the first 1 MiB
# (executor/shell_steps.py) and, through the sandbox helper, only the last
# 64 KiB of that (deploy_sidecar/service.py, OUTPUT_TAIL_CHARS). A long image
# build would push the marker lines out, and a deploy whose markers are lost
# is not deployed. So long command output goes to a log file and only its end
# is shown, and each marker is printed on stdout and again as the last lines
# of stderr.

kit_log_open() {
  kit_log="$(mktemp "${TMPDIR:-/tmp}/deploy-log.XXXXXX")"
}

# Shows the end of the log on stderr (at most 150 lines and 16 KiB).
kit_log_tail() {
  [[ -n "${kit_log:-}" && -s "$kit_log" ]] || return 0
  echo "--- the end of the deploy log ---" >&2
  tail -n 150 "$kit_log" | tail -c 16384 >&2
  echo "--- end of the deploy log ---" >&2
}

# kit_logged <what it is doing> <command...>: runs the command with its output
# in the log; on failure shows the end of the log and stops.
kit_logged() {
  local what="$1" rc=0
  shift
  "$@" >>"$kit_log" 2>&1 || rc=$?
  if ((rc != 0)); then
    kit_log_tail
    die "$what failed (exit $rc); the end of its output is above"
  fi
}

# A marker line for the factory, on stdout and as the last lines of stderr.
kit_say() {
  echo "$1"
  echo "$1" >&2
}

# After a promote: removes this project's older kept images by exact name,
# <env id>-deploy-<service>:<tag> for the services in compose.yaml, keeping
# `keep_tag`. Docker refuses to remove an image a container still uses (a
# standing candidate's, say), and that image is simply kept. Never prunes.
kit_remove_old_images() {
  local keep_tag="$1" services svc repo tags tag
  services="$(kit_services)"
  while IFS= read -r svc; do
    repo="$DEPLOY_ENV_ID-deploy-${svc,,}"
    tags="$(docker images --format '{{.Tag}}' "$repo" 2>/dev/null)" || continue
    while IFS= read -r tag; do
      [[ -n "$tag" && "$tag" != "$keep_tag" && "$tag" =~ ^[A-Za-z0-9._-]+$ ]] || continue
      if docker image rm "$repo:$tag" >>"$kit_log" 2>&1; then
        echo "deploy: removed the older image $repo:$tag" >&2
      else
        echo "deploy: kept $repo:$tag (in use, or it could not be removed)" >&2
      fi
    done <<<"$tags"
  done <<<"$services"
}
