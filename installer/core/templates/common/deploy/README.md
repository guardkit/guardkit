# Deployment kit

These files make the project deployable by the software factory. They were
written by `guardkit deploy init`. The factory's deployment rules are already
implemented in them; the project only supplies its own service.

## What the project provides

1. **A root `compose.yaml`** that starts the service. Its public service must
   publish the port the kit gives it in `APP_PORT`, on loopback only:

   ```yaml
   services:
     web:
       build: .
       environment:
         PORT: "8080"
       ports:
         - "127.0.0.1:${APP_PORT:?APP_PORT is required}:8080"
   ```

   The port inside the container is the project's choice. Do not set
   `container_name`, fixed host ports, or `external` volumes: the live app and
   the candidate run side by side as two compose projects.
2. **A health path** that answers HTTP 200 when the service is up (for
   example `GET /health`). It was given to `guardkit deploy init` and is kept
   in `deploy/settings.sh`.

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
| What is running (`RUNNING_IDENTITY=1`) | Prints the live project's identity, `none`, or why it cannot tell. Changes nothing. |
| Revert (`REVERT=1`) | Refused: the kit keeps no rollback image. |

The identity is stored as the container label `guardkit.deploy.identity`.
The factory does not send the health check and live gate the identity, so each
successful candidate or promote also records it, with the port, in
`$HOME/.local/state/guardkit-deploy/<compose project>.env` (the factory gives
every step of one checkout the same private home); the checks compare the
running containers with that record.
Checked images are kept as `<env id>-deploy-<service>:<identity>`; old ones can
be removed by hand once they are no longer live.

## Files

- `profile.yaml`: the deployment profile the factory reads.
- `settings.sh`: this project's values (environment id, ports, health path,
  waits).
- `lib.sh`, `deploy.sh`, `healthcheck.sh`, `live-gate.sh`: the kit. Commit the
  three scripts as executable files.

Check the profile with `guardkit qa validate deploy-profile deploy/profile.yaml`.
