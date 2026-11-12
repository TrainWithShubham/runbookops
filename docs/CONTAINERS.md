# Container operations

The Compose configuration publishes only `127.0.0.1:8006`. It starts offline with hash embeddings and no model key. Local state lives in the named `runbookops_state` volume. The image uses UID 1000, drops Linux capabilities, disables privilege escalation, and runs with a read-only root filesystem; `/tmp` and the state volume remain writable.

```bash
docker compose up --build -d --wait
docker compose logs -f app
docker compose exec app runbookops demo
python3 scripts/container_smoke.py
docker compose down
```

The smoke test creates a synthetic incident, checks viewer approval denial, restarts the actual container, approves with the persisted signing key, verifies HTTP 200, rejects replay, and discovers the MCP tools. It writes a sanitized report under ignored `artifacts`.

## Browser authentication

Use the uv setup for the local persona picker. The container's network gateway is intentionally not treated as a loopback client. With Docker, generate a short-lived application token and paste it into the browser's connection dialog:

```bash
docker compose exec app runbookops --as bagha token
docker compose exec app runbookops --as jethalal token
```

Each token expires after ten minutes. Treat it as a credential. Do not enable a remote token issuer or publish the container to a shared network as a shortcut.

## Preserve or reset state

`docker compose down` preserves the volume. To back up stopped state, stop the app and use Docker's volume backup procedure or copy `/app/.state` through `docker cp`. The signing key is private: protect the backup and never commit it.

`docker compose down --volumes` removes the local demo database, retrieval index, and signing key. It does not clean AWS resources. [AWS cleanup](AWS.md) is separate.

## Build targets

- `local`: offline/local application, port 8000 inside the container.
- `agentcore`: includes the semantic embedding model and serves `/ping` and `/invocations` on port 8080. Build for `linux/arm64`.

Provider keys are runtime configuration, never build arguments. `.dockerignore` excludes local environments, credentials, state, artifacts, and Terraform working files. Builds use `uv.lock` and omit development dependencies. The Python base-image tag and dependency lock should be updated through reviewed dependency changes and rescanned.
