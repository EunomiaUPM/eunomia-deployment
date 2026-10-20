# EUNOMIA Deployment

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![DSP](https://img.shields.io/badge/Protocol-DSP-orange)](https://docs.internationaldataspaces.org/ids-knowledgebase/v/dataspace-protocol)
[![GAIA-X](https://img.shields.io/badge/GAIA--X-Compliant-00A86B)](https://gaia-x.eu/)
[![Open in GitHub Codespaces](https://img.shields.io/badge/Open_in-Codespaces-181717?logo=github)](https://codespaces.new/EunomiaUPM/eunomia-deployment)

Run [EUNOMIA](https://github.com/EunomiaUPM) data spaces: authorities that admit participants with verifiable credentials, and as many agents as you need, each one able to publish a catalog and to negotiate and exchange data with any other. `eunomia` works as a hypervisor of these instances: on one machine for development and demos, or one per server in production.

## Quick start

All you need is Docker.

```bash
git clone https://github.com/EunomiaUPM/eunomia-deployment.git
cd eunomia-deployment
./eunomia doctor                                     # check Docker, ports and versions
./eunomia authority add authority                    # an authority
./eunomia agent add alice                            # two agents, onboarded with it
./eunomia agent add bob
./eunomia demo up                                    # a demo backend: a factory with robots
./eunomia demo publish alice                         # alice publishes it
./eunomia demo test --consumer bob --provider alice  # bob negotiates, pulls the robots, streams their events
```

On Windows, use `.\eunomia.cmd` instead of `./eunomia`. No Docker at hand? Open the repository in GitHub Codespaces.

`./eunomia ls` lists the instances, their URLs and their consoles (agents: `eunomia` / `eunomia`). `./eunomia demo notebook alice bob` runs the same exchange one call per cell, in Jupyter. Any agent can play either role: `./eunomia demo publish bob` and `./eunomia demo test --consumer alice --provider bob` run it the other way round.

The demo is an extension (`extensions/demo/`): what agents share, and how you test it, comes from extensions. Your own project is another one, kept in its own repository and loaded with `EUNOMIA_EXTENSIONS`; see [Extensions](https://eunomiaupm.github.io/eunomia-deployment/docs/cli/extensions).

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

- **[DS-Agent](https://github.com/EunomiaUPM/ds-agent)**: the agent every participant runs.
- **[Heimdall](https://github.com/EunomiaUPM/heimdall)**: the dataspace authority.
- **[Fafnir](https://github.com/EunomiaUPM/fafnir-wallet)**: the wallet next to each of them.
- **[Ymir](https://github.com/EunomiaUPM/ymir)**: the core library they share.

Their versions are pinned in [`versions.env`](versions.env).

## License

[GPL v3](LICENSE.md)
