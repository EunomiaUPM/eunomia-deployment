# **Eunomia Deployment**

This repository contains artifacts and scripts to deploy and test the Eunomia framework. It includes example certificates for authority, provider, and consumer, a central docker-compose file, and automation scripts in Bash or Powershell.

## **Eunomia Components**

This deployment orchestrates several core components of the Eunomia ecosystem:

- **[Eunomia Agents](https://github.com/EunomiaUPM/ds-agent)**: The Dataspace Agents that handle the core logic for participants (Provider and Consumer).
- **[Heimdall](https://github.com/EunomiaUPM/heimdall)**: The Dataspace Authority and Clearing House that governs onboarding and compliance.


## **Deployment Methods**

There are two main ways to deploy this environment:

1. **[Mini Deployment](./deployment/mini/README.md)**: A lightweight deployment using Docker Compose. Click the link to see the specific guide.
2. **[Prod Deployment](./deployment/prod/README.md)**: Production deployment with TLS, Vault, and Keycloak. Click the link to see the specific guide.

## **Requirements**

- Docker and docker-compose (or Docker Desktop)
- Permissions to execute scripts (chmod +x)

## **DID Configuration**

Depending on the environment, the Decentralized Identifier (DID) method changes. While **GAIA-X officially only supports `did:web`**, Eunomia allows flexibility for local testing:

- **Mini Deployment (Local)**: Uses **`did:web`** over plain http. The `did.json` is resolved over http only for local hosts (`localhost`, `127.0.0.1`, `host.docker.internal` and any `*.localhost` name); any other domain is resolved over https. In the default mode the DIDs live on `host.docker.internal`; in the Keycloak mode, on each component's `*.localhost` name.
- **Prod Deployment**: Uses **`did:web`** on a real domain over https, as GAIA-X requires.

> [!TIP]
> `did:jwk` is still supported (`type: Jwk` in the `did_config` block) for setups where no `did.json` can be served.

## **External Dependencies**

Each component needs a wallet for its credentials. Mini deployments run a local **Fafnir** wallet per component (Heimdall, provider and consumer), started by the same compose files; production deployments point to the **public walt.id wallet API**. See the specific deployment guides for details.

## **GAIA-X Compliance**

By default, Eunomia operates in a generic dataspace mode. To make the deployment **GAIA-X compliant**, the following three changes are required:

### 1 — Verification configuration

In the Agent config YAML, update the `verify_req_config` block to require a GAIA-X Label Credential:

```yaml
verify_req_config:
  is_cert_allowed: false
  vcs_requested: [gx:LabelCredential]
```

### 2 — GAIA-X connectivity

Add (or update) the `gaia_config` block pointing to the Heimdall instance. The values differ between Mini and Prod:

```yaml
gaia_config:
  api:
    protocol: 'http'            # mini: http | prod: https
    url: 'url'                  # mini: host.docker.internal | prod: your.domain.com
    port: null                  # mini: 1500 (Heimdall port) | prod: null
```

### 3 — Heimdall startup command

In the Docker Compose file, change the `command` for **both** the `heimdall` and `heimdall-setup` services to use the GAIA-X ecosystem config:

```yaml
command:
  - setup
  - --env-file
  - /app/static/config/eco_authority.yaml
```
---

> [!NOTE]
> The `eco_authority.yaml` config activates **all** Heimdall roles simultaneously:
> - **GAIA-X Clearing House** — essentially a **Dataspace Authority specifically for the GAIA-X ecosystem**; it validates and signs compliance credentials on behalf of the ecosystem.
> - **Clearing House Proxy** — proxies requests to the Clearing House.
> - **Legal Authority** — issues legal-level credentials within the dataspace.
> - **Dataspace Authority** — governs participant onboarding and policy enforcement.
>
> In a **real-world ecosystem**, a single entity cannot (and should not) assume all these roles simultaneously as it would **centralize the system**, defeating the purpose of a decentralized architecture. This multi-role configuration is strictly intended for **development and testing** purposes.
