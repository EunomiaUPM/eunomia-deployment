---
title: Concepts
description: The participants of an EUNOMIA dataspace, how they prove who they are, and how data moves between them.
---

## The participants

```text
                        ┌──────────────────────┐
                        │      Authority       │  issues credentials,
                        │      (Heimdall)      │  governs who takes part
                        └──────────┬───────────┘
                   credentials     │     credentials
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
   ┌─────────────────────┐   catalog, contract,  ┌─────────────────────┐
   │    Provider agent   │ ◄──── transfer ─────► │    Consumer agent   │
   │     (DS-Agent)      │      (DSP + GNAP)     │     (DS-Agent)      │
   └──────────┬──────────┘                       └──────────┬──────────┘
              │ calls it, with its                          │ receives the data,
              │ own credentials                             │ or forwards pushes
   ┌──────────▼──────────┐                       ┌──────────▼──────────┐
   │   Data backend      │                       │ Consumer application│
   │ (the demo factory)  │                       │ (e2e, demo events)  │
   └─────────────────────┘                       └─────────────────────┘
```

- **Authority** ([Heimdall](https://github.com/EunomiaUPM/heimdall)): the dataspace's registry and clearing house. It issues the credential that makes an organisation a participant, and, in its eco role, the Gaia-X credentials.
- **Provider** ([DS-Agent](https://github.com/EunomiaUPM/ds-agent)): publishes a **catalog** of datasets, each with **policies** that say on what terms it can be used, and **connectors** that say how to reach the data behind it.
- **Consumer** (DS-Agent too): browses catalogs, **negotiates contracts** and starts **transfers**.
- **Wallet** ([Fafnir](https://github.com/EunomiaUPM/fafnir-wallet)): every participant runs one next to it. It keeps the participant's keys, DID and credentials in the participant's own database.
- **Data backend**: the system that actually holds the data. The provider agent sits in front of it and the consumer never talks to it directly. In this repository it is the [demo factory](./demo-factory.md).

An agent can be provider and consumer at once; the standalone deployment runs one of each to keep the roles clear.

## Identities

Every participant has a **DID** (decentralised identifier) and proves it holds the key behind it.

- **Standalone** uses `did:jwk`: the DID is derived from the public key itself, so nothing has to be resolved over the network. A `did:web` on `host.docker.internal` would carry the port as `%3A` in the DID, and the agents then fail to find their peers by DID.
- **Prod** uses `did:web` on each participant's domain, which is what Gaia-X supports.

The keys and certificates of the standalone participants are committed examples under `vault/<participant>/secrets/` (`*.pem.example`). The setup jobs derive the rest from them on first start; `./eunomia down` removes what they generated, so the next `up` starts with fresh state. [Extra participants](../guides/instances.md) get their own keys.

## Credentials

Credentials are W3C verifiable credentials the authority issues and the wallet keeps:

| Credential | Who gets it | What for |
| --- | --- | --- |
| `DataSpaceParticipant` | provider and consumer | being a member of the dataspace |
| `gx:VatId` | consumer | the Gaia-X legal registration number, read from its certificate |
| `gx:LabelCredential` | consumer | the Gaia-X label; the provider only accepts consumers holding it |

The consumer also generates its own self-signed Gaia-X credentials (legal person, terms and conditions) from the `gaia_config` block of its configuration. [Onboarding](./onboarding.md) has each step.

## Talking to each other

- **GNAP** (Grant Negotiation and Authorization Protocol): before anything else, the consumer connects to the provider, presents its credentials and gets a token. `eunomia connect` and the last onboarding step do this.
- **DSP** ([Dataspace Protocol](https://docs.internationaldataspaces.org/ids-knowledgebase/v/dataspace-protocol)): with that token, the consumer requests the **catalog**, runs a **contract negotiation** that ends in an **agreement**, and starts **transfer processes** under it.
- **Data plane**: a transfer hands the consumer an address on the provider. For a **pull**, the consumer GETs it and the provider fetches the data from the backend, with the backend's own credentials. For a **push**, the provider subscribes to the backend and forwards every event to an endpoint the consumer chose.

The consumer never sees the backend's credentials: the provider adds them. `eunomia e2e` proves it by checking that the same backend URL refuses an anonymous call.

[Exchanging data](../guides/data-exchange.md) goes through the whole sequence.

## The repository

| Path | What |
| --- | --- |
| `eunomia`, `eunomia.cmd`, `cli/` | The CLI |
| `versions.env` | The EUNOMIA image versions, in one place |
| `deployment/standalone/` | Compose files for one machine |
| `deployment/prod/` | Compose files for real servers |
| `deployment/instances/` | Templates for extra connectors and authorities |
| `services/demo-factory/` | The demo data backend |
| `static/config/` | Agent, authority and wallet configuration |
| `static/catalog/` | The catalog the provider is populated with |
| `static/specs/` | OpenAPI specs of the agent and the authority |
| `vault/` | Example keys, certificates and secrets |
