---
title: Production
description: One participant per server, with a domain, TLS, HashiCorp Vault and did:web.
---

Unlike the [standalone deployment](../standalone.md), prod puts each participant on its own server, with a domain name, TLS certificates and HashiCorp Vault for the secrets. The compose files live in [`deployment/prod/`](../../../deployment/prod/).

| Component | Role | Guide |
| --- | --- | --- |
| **Heimdall** | Dataspace authority: registers participants, issues credentials, enforces governance | [Authority in production](./heimdall.md) |
| **Agent** | Participant: provider, consumer or both | [Agent in production](./agent.md) |

Each one has its own compose file and its own Vault. They can share a server or not.

> [!IMPORTANT]
> **Deploy the authority first.** Agents register with a running Heimdall to get their credentials before they can take part in the dataspace.

> [!WARNING]
> The prod configs have not been run against a real Vault since the move to the Fafnir wallet. Treat this guide as the way to get there, not as a tested recipe, until it has been done on real servers.

## Requirements

- Docker and Docker Compose on each server
- A domain name pointing to each server
- TLS certificates for each domain, in PEM format

## Steps

1. Deploy the authority: [Authority in production](./heimdall.md).
2. Deploy one or more agents: [Agent in production](./agent.md).
3. On each server, or with the [deploy workflow](./automated-deployment.md):

   ```bash
   ./eunomia up authority --env prod     # on the authority server, first
   ./eunomia up provider  --env prod     # on the provider server
   ./eunomia up consumer  --env prod     # on the consumer server
   ```

4. Onboarding and the catalog span servers: run them once every node is up, from any machine that reaches the three public URLs (`AUTHORITY_URL`, `PROVIDER_URL`, `CONSUMER_URL` in `.env`):

   ```bash
   ./eunomia onboard --env prod
   ./eunomia catalog populate --env prod
   ./eunomia e2e --env prod
   ```

   The catalog points at the demo factory. To share your own data, see [Extending the deployment](../extending.md).

## Restarting a node

`./eunomia restart <node…>` restarts nodes on their servers over SSH, with the `<NODE>_SSH_*` settings in `.env` (see [`.env.example`](../../../.env.example)). It recreates only the agent and its wallet: the databases have no volume, so recreating them would wipe the participant's state. `--dry-run` prints the SSH commands instead.

## Wallet and images

Each component runs its own [Fafnir](https://github.com/EunomiaUPM/fafnir-wallet) wallet inside its compose file: there is no external wallet service or account. The wallet stores its keys and DID in the component's own database and is reachable only on the compose network.

The images are pinned in [`versions.env`](../../../versions.env), the same file standalone uses. They are amd64 only. `./eunomia images --env prod --check` lists newer tags.

## DID method

Prod uses **`did:web`** on each participant's domain, the method Gaia-X supports. Standalone uses `did:jwk` instead; [Concepts](../../concepts/overview.md#identities) explains why.
