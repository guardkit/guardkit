# Deployment kit

These files make the project deployable by the software factory. They were
written by `guardkit deploy init`. The factory's deployment rules are already
implemented in them; the project only supplies its own service.

## What the project provides

1. **A root `compose.yaml`** that starts the service. The public service
   publishes `${APP_PORT}` to whatever port the app listens on inside its
   container (for example `"${APP_PORT}:8080"`, with no address in front).
   The kit sets `APP_PORT` (the live port or the candidate port); only one
   service publishes it. Do not write `127.0.0.1:${APP_PORT}`: the factory's
   sandbox forwards the port to the host machine's own loopback address only,
   and a port bound to the sandbox's 127.0.0.1 cannot be reached from the
   host at all:

   ```yaml
   services:
     web:
       build: .
       environment:
         PORT: "8080"
         DATABASE_URL: "postgres://app@db:5432/app"
       ports:
         - "${APP_PORT:?APP_PORT is required}:8080"
       depends_on:
         - db
     db:
       image: postgres:16-alpine
       environment:
         POSTGRES_USER: app
         POSTGRES_HOST_AUTH_METHOD: trust
       volumes:
         - dbdata:/var/lib/postgresql/data
   volumes:
     dbdata: {}
   ```

   (The database settings above are only an illustration; real secrets do not
   belong in compose.yaml.)

   Keep data in **named volumes** (like `dbdata` above). Never bind-mount a
   project folder (`./data:/data`): the factory builds and runs each
   candidate from a temporary copy of the project that is deleted after the
   check, so anything written into a mounted project folder is lost. Do not
   set `container_name`, fixed host ports, or `external` volumes: the live app
   and the candidate run side by side as two compose projects, each with its
   own volumes.
2. **A health path** that answers HTTP 200 when the service is up (for
   example `GET /health`). It was given to `guardkit deploy init` and is kept
   in `deploy/settings.sh`.

Every service in `compose.yaml` must keep running. One-off jobs (database
migrations, seeding) belong in the app's own start-up, not in separate
services that run and exit: a stopped service makes the deployment read as
unknown, and the factory then deploys nothing over it.

Nothing else. The service can be anything that runs in containers; the kit
does not care what language or framework is inside.

## What the kit does

| Step (signal from the factory) | What happens |
|---|---|
| Candidate check (`CANDIDATE=1`) | Builds and starts compose project `<env id>-cand` on the candidate port, labels every container with the identity the factory handed over, and prints the image of every service as `CHECKED_ARTIFACT` and the identity as `DEPLOYED_IDENTITY`. |
| Health check | `deploy/healthcheck.sh`: the health path answers 200 and every container carries the identity the deploy step recorded for that project. |
| Live gate | `deploy/live-gate.sh`: the same check, reported as a results envelope. |
| Promote (`PROMOTE=1`) | Starts compose project `<env id>-live` on the live port from exactly the checked images (never a rebuild), labelled with the identity. |
| Candidate down (`CANDIDATE_DOWN=1`) | Removes the candidate project and its volumes, only when it is the named identity's. Never touches the live project. |
| What is running (`RUNNING_IDENTITY=1`) | Prints the live project's identity when every service the deployment named (label `guardkit.deploy.services`) has exactly one container, running as it, `none` when the live project has no container at all, and otherwise (stopped, partial or mixed) why it cannot tell. Changes nothing. |
| Revert (`REVERT=1`) | Refused: the kit keeps no rollback image. |

The identity is stored as the container label `guardkit.deploy.identity`, and
the full list of the deployment's services as `guardkit.deploy.services`, so a
removed container is noticed without reading any compose file.
The factory does not send the health check and live gate the identity, so each
successful candidate or promote also records it, with the port, in
`$HOME/.local/state/guardkit-deploy/<compose project>.env` (the factory gives
every step of one checkout the same private home); the checks compare the
running containers with that record.
Checked images are kept as `<env id>-deploy-<service>:<identity>`. After a
successful promote the kit removes this project's older ones by exact name
(an image a container still uses is kept); it never prunes anything else.

Build and start output goes to a log file and only its last lines are shown,
and the lines the factory reads (`CHECKED_ARTIFACT=`, `DEPLOYED_IDENTITY=`)
are printed last, so a long build never pushes them out of the factory's
output limit.

## Files

- `profile.yaml`: the deployment profile the factory reads.
- `settings.sh`: this project's values (environment id, ports, health path,
  waits).
- `lib.sh`, `deploy.sh`, `healthcheck.sh`, `live-gate.sh`: the kit. Commit the
  three scripts as executable files.

Check the profile with `guardkit qa validate deploy-profile deploy/profile.yaml`.
