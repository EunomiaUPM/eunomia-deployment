# Mini Deployment

This folder contains the "mini" deployment of the Eunomia framework (Heimdall, a provider and a consumer) using Docker Compose files. Each component brings its own database and its own **Fafnir** wallet, so nothing else has to be started first.

## Requirements
- Docker
- Docker Compose 2.24 or newer (the Keycloak mode uses `!reset`)
- PowerShell, to use `scripts/run/run-mini.ps1`

## Deploying

The easiest way is the `scripts/run/run-mini.ps1` script (it works from any directory). It creates the shared `ds-mini` Docker network if it is missing, then brings up Heimdall, the provider and the consumer (in that order) and waits until each one answers:

```powershell
./scripts/run/run-mini.ps1                      # everything, static identity (default)
./scripts/run/run-mini.ps1 -Target provider     # heimdall | provider | consumer | all
./scripts/run/run-mini.ps1 -Auth keycloak       # everything behind Keycloak (see below)
./scripts/run/run-mini.ps1 -Down                # bring everything down
```

To do it by hand, create the network once and run `docker compose up -d` against each file:

```bash
docker network create ds-mini
docker compose -f docker-compose.mini.heimdall.yaml up -d
docker compose -f docker-compose.mini.provider.yaml up -d
docker compose -f docker-compose.mini.consumer.yaml up -d
```

## Entity URLs (default mode)

In the default mode the components talk to each other through `host.docker.internal` and publish their own ports:

- **Heimdall**: [http://localhost:1500/admin/](http://localhost:1500/admin/)
- **Provider**: [http://localhost:1200/admin/](http://localhost:1200/admin/)
- **Consumer**: [http://localhost:1100/admin/](http://localhost:1100/admin/)

`/` redirects to the console in all of them.

## Credentials

In the default mode there is no sign-in: every request acts as a fixed system user with the root role (`static` identity, used when the config has no `oauth` block). It is meant for local work only; the components refuse to start with it when `is_prod` is set. For the users of the Keycloak mode, see [Keycloak mode](#keycloak-mode).

The wallets are internal (no published port). Their example secrets live in `/vault/[role]/secrets/`.

## Keycloak mode

With `-Auth keycloak` every component sits behind its own oauth2-proxy and a shared Keycloak handles the sign-in (one realm per component). The components no longer publish their own port: the proxy is the only way in. Protocol routes (DSP, GNAP, OID4VCI/OID4VP, well-known) pass without a session; everything else needs one.

Every service gets a `*.localhost` name, valid both from the browser (browsers resolve `*.localhost` to 127.0.0.1) and from the containers (aliases on the `ds-mini` network):

| Component | URL |
|---|---|
| Heimdall | [http://authority.localhost:8083/admin/](http://authority.localhost:8083/admin/) |
| Provider | [http://provider.localhost:8081/admin/](http://provider.localhost:8081/admin/) |
| Consumer | [http://consumer.localhost:8082/admin/](http://consumer.localhost:8082/admin/) |
| Keycloak | [http://keycloak.localhost:8080](http://keycloak.localhost:8080) (admin console: `admin` / `admin`) |

Users (same in the three realms; the password is the user name):

| User | Role |
|---|---|
| `john.doe` | `/admin` (root) |
| `jane.doe` | `/admin/org` |
| `richard.roe` | `/admin/org/team` |

Switching between `static` and `keycloak` needs a `-Down` first: each component stores its own URL and DID, which differ between modes. Keycloak keeps no data, so every time its container is recreated it imports the default realms again (`static/config/keycloak/mini/`).

The Keycloak mode needs agent and Heimdall images with `oauth: keycloak` support and with `did:web` resolved over http for `*.localhost`.
