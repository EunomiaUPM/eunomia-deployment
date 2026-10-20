# EUNOMIA Deployment

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![DSP](https://img.shields.io/badge/Protocol-DSP-orange)](https://docs.internationaldataspaces.org/ids-knowledgebase/v/dataspace-protocol)
[![GAIA-X](https://img.shields.io/badge/GAIA--X-Compliant-00A86B)](https://gaia-x.eu/)

Deploy a complete [EUNOMIA](https://github.com/EunomiaUPM) dataspace: an authority, a provider and a consumer, onboarded with verifiable credentials, and a demo factory whose robots the provider shares under negotiated contracts. On one machine for development and demos, or one participant per server in production.

## Quick start

All you need is Docker ([requirements](docs-internal/getting-started/requirements.md)).

```bash
git clone https://github.com/EunomiaUPM/eunomia-deployment.git
cd eunomia-deployment
./eunomia doctor   # check Docker, ports and versions
./eunomia up       # start, onboard, populate the catalog
./eunomia e2e      # negotiate a contract, pull the robots, receive their events
```

On Windows, use `.\eunomia.cmd` instead of `./eunomia`.

Then open the consumer console at <http://127.0.0.1:1100/admin/login> (`eunomia` / `eunomia`), or try `./eunomia demo events` to watch the robot events arrive through the dataspace.

## Documentation

The documentation lives in [`docs-internal/`](docs-internal/index.md):

- [Quickstart](docs-internal/getting-started/quickstart.md) and [requirements](docs-internal/getting-started/requirements.md)
- [Concepts](docs-internal/concepts/overview.md), [onboarding](docs-internal/concepts/onboarding.md) and [the demo factory](docs-internal/concepts/demo-factory.md)
- Guides: [standalone](docs-internal/guides/standalone.md), [exchanging data](docs-internal/guides/data-exchange.md), [extra participants](docs-internal/guides/instances.md), [configuration](docs-internal/guides/configuration.md), [extending](docs-internal/guides/extending.md), [production](docs-internal/guides/prod/index.md)
- Reference: [CLI](docs-internal/reference/cli.md) and [APIs](docs-internal/reference/api.md)
- [Troubleshooting](docs-internal/troubleshooting.md)

## Components

- **[DS-Agent](https://github.com/EunomiaUPM/ds-agent)**: the dataspace agent of each participant.
- **[Heimdall](https://github.com/EunomiaUPM/heimdall)**: the dataspace authority and clearing house.
- **[Fafnir](https://github.com/EunomiaUPM/fafnir-wallet)**: the wallet next to each of them.

Their versions are pinned in [`versions.env`](versions.env).

## License

[GPL v3](LICENSE.md)
