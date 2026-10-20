---
title: Troubleshooting
description: Frequent problems, what causes them and how to fix them.
---

Start with `./eunomia doctor`, then `./eunomia status`, and look at the logs of whatever is not ready: `./eunomia logs <authority|provider|consumer|demo>`, or `./eunomia logs <container>` for a single container. The one-shot `*-setup` containers end in `exited`; if one fails, its log says why.

## Starting

| Symptom | Cause and fix |
| --- | --- |
| `Docker is installed but not answering` | Start Docker Desktop (or `sudo systemctl start docker`) and wait until it is running. |
| `Ports … are already in use by another program` | Something else holds a deployment port. Stop it, or move the database and demo ports in `.env` (see [Configuration](./guides/configuration.md)). The agent ports 1100, 1200 and 1500 cannot move. |
| `These ports are held by processes outside Docker` | A native process (an agent built locally, a dev server) on a deployment port. It would answer on `127.0.0.1` while the container looks healthy. Stop it. |
| A service never becomes healthy | `./eunomia logs <node>`. On Apple Silicon the amd64 images are emulated and the first start is slow; run `./eunomia up` again. |
| Image pull fails | Check your connection and the tags in `versions.env`; `./eunomia doctor --images` checks them all. |
| Setup job fails with a permission error on `vault/` (Linux) | The setup jobs write into `vault/*/secrets`. `./eunomia up` makes it writable; if you started compose by hand, `chmod -R a+rwX vault`. |

## Onboarding

| Symptom | Cause and fix |
| --- | --- |
| Onboarding times out on Linux | The firewall (ufw, firewalld) blocks containers from reaching the host at `host.docker.internal`. Allow the `docker0` interface. |
| A credential stays `Approved` or `Pending`, never `Finalized` | `./eunomia logs authority`. For `gx:VatId`: the participant certificate needs an `organizationIdentifier` with a VAT number, and the authority needs the eco role. |
| The connection stays `Pending` | The provider asks for `gx:LabelCredential` and the consumer lacks it: `./eunomia gaia --consumer <name>`. |
| `502` from the consumer on any DSP call | The consumer holds no token for the provider: the connection never completed. `./eunomia onboard connect`. |
| `Mate not found` on the catalog request | The agents use `did:web` on `host.docker.internal`: the port in the DID breaks the lookup. Use `did:jwk` in standalone (`did_config.type: Jwk`). |
| Everything breaks after June 2027 | The example certificates in `vault/*/secrets/cert.pem.example` expire then. Regenerate them, keeping the `organizationIdentifier`. |

## Exchanging data

| Symptom | Cause and fix |
| --- | --- |
| `The provider catalog is empty` | `./eunomia catalog populate`. |
| The data plane proxy answers an error | The provider could not reach the factory: `./eunomia status` (is `demo` up?) and `./eunomia logs provider`. |
| `No event reached :1290` | `./eunomia logs demo`, `provider` and `consumer`. Port 1290 must be free (`EUNOMIA_SINK_PORT` to move it), and on Linux the firewall must let containers reach the host. |
| `Cannot listen on port 1290` | Another `e2e` or `demo events` is running, or something else uses the port: set `EUNOMIA_SINK_PORT`. |
| Every event type arrives, not just the one subscribed to | That is how the demo factory behaves: it sends every event to every subscriber. |

## Starting over

```bash
./eunomia down --yes    # containers, volumes and generated identities
./eunomia up
```

For an extra participant: `./eunomia rm <name> --yes` and create it again.
