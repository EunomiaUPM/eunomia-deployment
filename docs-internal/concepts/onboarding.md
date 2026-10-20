---
title: Onboarding
description: What `eunomia onboard` does, step by step, and the API calls behind each step.
---

`./eunomia up` runs the onboarding after starting the stacks; `./eunomia onboard` runs it again on its own. Each step checks first and skips what is already done, so it is safe to repeat. To run one step: `./eunomia onboard wallets|register|gaia|connect`.

## 1. Wallets

Every participant links its Fafnir wallet:

```http
POST /api/v1/wallet/link
```

on the authority, the provider and the consumer. The wallet creates the participant's keys and DID.

## 2. Register

The provider and the consumer each ask the authority for a `DataSpaceParticipant` credential, proving who they are with their certificate:

```http
POST /api/v1/vc-request/beg
{
  "url": "http://host.docker.internal:1500/api/v1/gate/access",
  "id": "<authority DID>",
  "nick": "authority",
  "vc_type": "DataSpaceParticipant_jwt_vc_json",
  "method": "cert",
  "auto": true
}
```

`GET /api/v1/vc-request/all` lists the requests; the step waits until this one is `Finalized`.

## 3. Gaia-X credentials

The provider asks for `gx:labelcredential` (`verify_req_config.vcs_requested` in its configuration), so the consumer needs it before it can connect:

1. **Legal VC**: `vc-request/beg` with `vc_type: gx_VatId_jwt_vc_json` and `method: cert`. The authority reads the VAT number from the `organizationIdentifier` of the consumer's certificate, so it must hold one (`VATES-…`).
2. **Self-attested VCs**: `POST /api/v1/gaia/generate`, from the `gaia_config.legal_person` block of the consumer's configuration.
3. **Label VC**: `vc-request/beg` with `vc_type: gx_LabelCredential_jwt_vc_json` and `method: oidc4vp`: the consumer presents the previous credentials and the authority's clearing house issues the label.

Only an authority with the **eco** role issues Gaia-X credentials; the standalone one has it. `./eunomia gaia --consumer <name>` runs this step for any consumer.

## 4. Connect

The consumer opens a GNAP grant with the provider:

```http
POST /api/v1/peer-connection/connect
{
  "id": "<provider DID>",
  "nick": "provider",
  "url": "http://host.docker.internal:1200/api/v1/gate/access",
  "actions": ["talk"],
  "auto": true
}
```

The provider verifies the consumer's credentials and, when it holds what the provider asks for, approves the connection: `GET /api/v1/peer-connection/request/all` shows it `Approved`, and `GET /api/v1/mates/all` on the consumer shows the provider with a token. Without the label credential it stays `Pending`.

## Addresses

The URLs in these calls are the ones the **agents** use to reach each other, from inside their containers: `http://host.docker.internal:<port>`. The CLI itself talks to the agents at `http://127.0.0.1:<port>`.
