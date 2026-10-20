---
title: EUNOMIA documentation
description: Deploy an EUNOMIA dataspace, onboard its participants and exchange data, on one machine or on real servers.
---

EUNOMIA is a framework for **dataspaces**: networks where organisations share data under agreed rules, keep control over who uses it and for what, and prove who they are with verifiable credentials. This repository deploys a complete one.

On one machine, three commands give you an authority, a provider and a consumer, onboarded and connected, and a demo factory whose robots the provider shares:

```bash
./eunomia doctor   # check Docker, ports and versions
./eunomia up       # start, onboard, populate the catalog
./eunomia e2e      # negotiate a contract, pull the robots, receive their events
```

## Where to start

| If you want to | Read |
| --- | --- |
| Run it and see it work | [Quickstart](./getting-started/quickstart.md) |
| Check what your machine needs | [Requirements](./getting-started/requirements.md) |
| Understand the pieces and how they talk | [Concepts](./concepts/overview.md) |
| Know what the demo shares | [The demo factory](./concepts/demo-factory.md) |
| Negotiate and move data step by step | [Exchanging data](./guides/data-exchange.md) |
| Add more connectors or authorities | [Extra participants](./guides/instances.md) |
| Share your own data instead of the demo | [Extending the deployment](./guides/extending.md) |
| Deploy on real servers | [Production](./guides/prod/index.md) |
| Look up a command | [CLI reference](./reference/cli.md) |
| Call the APIs directly | [API reference](./reference/api.md) |
| Fix something | [Troubleshooting](./troubleshooting.md) |

## The components

- **[DS-Agent](https://github.com/EunomiaUPM/ds-agent)**: the dataspace agent each participant runs, as a provider, a consumer or both.
- **[Heimdall](https://github.com/EunomiaUPM/heimdall)**: the dataspace authority and clearing house, which onboards participants and issues their credentials.
- **[Fafnir](https://github.com/EunomiaUPM/fafnir-wallet)**: the wallet next to each of them, which keeps its keys, DID and credentials.
