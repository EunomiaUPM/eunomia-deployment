# EUNOMIA Deployment

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![DSP](https://img.shields.io/badge/Protocol-DSP-orange)](https://docs.internationaldataspaces.org/ids-knowledgebase/v/dataspace-protocol)
[![GAIA-X](https://img.shields.io/badge/GAIA--X-Compliant-00A86B)](https://gaia-x.eu/)
[![Open in GitHub Codespaces](https://img.shields.io/badge/Open_in-Codespaces-181717?logo=github)](https://codespaces.new/EunomiaUPM/eunomia-deployment)

Deploy a complete [EUNOMIA](https://github.com/EunomiaUPM) data space: an authority, a provider and a consumer, onboarded with verifiable credentials, and a demo factory whose robots the provider shares under negotiated contracts. On one machine for development and demos, or one participant per server in production.

## Quick start

All you need is Docker.

```bash
git clone https://github.com/EunomiaUPM/eunomia-deployment.git
cd eunomia-deployment
./eunomia doctor   # check Docker, ports and versions
./eunomia up       # start, onboard, populate the catalog
./eunomia e2e      # negotiate a contract, pull the robots, receive their events
```

On Windows, use `.\eunomia.cmd` instead of `./eunomia`. No Docker at hand? Open the repository in GitHub Codespaces.

Then open the consumer console at <http://127.0.0.1:1100/admin/login> (`eunomia` / `eunomia`), or run `./eunomia demo events` to watch the robot events arrive through the data space.

## Documentation

**<https://eunomiaupm.github.io/eunomia-deployment>**: quickstart, architecture, the components (DS-Agent, Heimdall, Fafnir, Ymir), standalone and production deployment, the `eunomia` CLI and the API reference.

The site is built from [`docs/`](docs/) with [Fumadocs](https://fumadocs.dev); the pages are MDX files under [`docs/content/docs/`](docs/content/docs/). To run it locally:

```bash
cd docs
npm ci
npm run dev            # http://localhost:3000
npm run generate:api   # after changing an OpenAPI spec
```

## Components

- **[DS-Agent](https://github.com/EunomiaUPM/ds-agent)**: the dataspace agent of each participant.
- **[Heimdall](https://github.com/EunomiaUPM/heimdall)**: the dataspace authority.
- **[Fafnir](https://github.com/EunomiaUPM/fafnir-wallet)**: the wallet next to each of them.
- **[Ymir](https://github.com/EunomiaUPM/ymir)**: the core library they share.

Their versions are pinned in [`versions.env`](versions.env).

## License

[GPL v3](LICENSE.md)
