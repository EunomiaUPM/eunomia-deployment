---
title: API reference
description: Where the OpenAPI specs of the agent, the authority and the demo factory are, and the calls you need most.
---

## Specs

| Component | Spec | Covers |
| --- | --- | --- |
| DS-Agent (provider, consumer) | [`static/specs/agent/openapi/merged_openapi.yaml`](../../static/specs/agent/openapi/merged_openapi.yaml) | everything below, in one file |
| | `static/specs/agent/openapi/auth/` | wallets, credentials, peer connections, mates |
| | `static/specs/agent/openapi/catalog/` | catalog management (`catalog_agent`) and DSP catalog (`catalog_dsp`) |
| | `static/specs/agent/openapi/contracts/` | negotiations, management and DSP |
| | `static/specs/agent/openapi/transfer/` | transfers, management, DSP and data plane |
| | `static/specs/agent/openapi/keystore/` | keys |
| | `static/specs/agent/openapi/fe-gateway.yaml` | the gateway the consoles use |
| Heimdall (authority) | [`static/specs/heimdall/openapi/openapi.json`](../../static/specs/heimdall/openapi/openapi.json) | the authority |
| Demo factory | [`services/demo-factory/specs/openapi/robots.yaml`](../../services/demo-factory/specs/openapi/robots.yaml) | robots, measures, subscriptions; also at <http://127.0.0.1:1210/docs> |

The demo factory also has Postman collections in `services/demo-factory/specs/postman/`.

To browse an agent spec with Swagger UI, with Docker only:

```bash
docker run --rm -p 1280:8080 -e SWAGGER_JSON=/spec/merged_openapi.yaml \
  -v "$PWD/static/specs/agent/openapi:/spec:ro" swaggerapi/swagger-ui:v5.17.14
# then open http://127.0.0.1:1280
```

## Base URLs

| | From your machine | From a container |
| --- | --- | --- |
| Authority | `http://127.0.0.1:1500` | `http://host.docker.internal:1500` |
| Provider | `http://127.0.0.1:1200` | `http://host.docker.internal:1200` |
| Consumer | `http://127.0.0.1:1100` | `http://host.docker.internal:1100` |

Management routes are under `/api/v1`, Dataspace Protocol routes under `/dsp/current`. The addresses the agents put in DSP and GNAP messages must be the container ones.

## Calls you need most

| What | Call | Where |
| --- | --- | --- |
| Is it up | `GET /api/v1/readiness` (`/readiness` on the authority) | any |
| Own DID | `GET /.well-known/did.json` or `GET /api/v1/mates/myself` | any |
| Known participants and tokens | `GET /api/v1/mates/all` | agent |
| Link the wallet | `POST /api/v1/wallet/link` | any |
| Ask for a credential | `POST /api/v1/vc-request/beg` | agent |
| Credential requests | `GET /api/v1/vc-request/all` | agent |
| Gaia-X self-attested VCs | `POST /api/v1/gaia/generate` | consumer |
| Connect to a provider | `POST /api/v1/peer-connection/connect` | consumer |
| Connection requests | `GET /api/v1/peer-connection/request/all` | agent |
| Catalog of a provider | `POST /dsp/current/catalog/rpc/setup-catalog-request` | consumer |
| Negotiation steps | `POST /dsp/current/negotiations/rpc/<step>` | both |
| Transfer steps | `POST /dsp/current/transfers/rpc/<step>` | both |
| Datasets, distributions, policies | `/api/v1/catalog-agent/...` | provider |
| Connector templates and instances | `/api/v1/connector/...` | provider |

[Onboarding](../concepts/onboarding.md) shows the bodies of the onboarding calls and [Exchanging data](../guides/data-exchange.md) those of the catalog, negotiation and transfer calls. The CLI sends exactly those: `./eunomia e2e -v` prints every request and response.
