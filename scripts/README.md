# Scripts

Helper scripts, grouped by purpose. Every script resolves its paths from its own location, so it
can be launched from any directory.

| Folder | Scripts | What they do |
|---|---|---|
| `run/` | `run-mini.ps1` | Brings up the mini deployment (Heimdall, provider, consumer) and waits until each one answers. `-Target heimdall\|provider\|consumer\|all`, `-Auth static\|keycloak`, `-Down`. See [the mini guide](../deployment/mini/README.md). |
| `onboarding/` | `mini-onboarding.sh` | Full onboarding of the mini deployment: links the three wallets, registers the consumer and the provider with the authority, then authenticates them with each other. |
| | `register-with-authority.sh` | Registers one participant (`PARTICIPANT_URL`) with the authority and gets its credential. |
| | `authenticate-participants.sh` | Authenticates the consumer with the provider. |
| | `auto-onboarding.ps1` | The same full onboarding, in PowerShell. |
| | `gaia.sh`, `gaia.ps1` | Gaia-X flow: the consumer generates its Gaia-X credentials and gets the Label Credential from the authority. |
| `lib/` | `lib.sh` | Shared by the bash scripts: default URLs (overridable with `AUTHORITY_URL`, `CONSUMER_URL`, `PROVIDER_URL`…) and request/log helpers. |
| `data/` | `populate_mock_data.sh` | Fills the provider's catalog: data service, datasets, distributions, a connector template with instances, and ODRL policies. The other mock scripts (contracts, transfers, participants, peer catalogs) live in ds-agent (`scripts/data/`). |
| `lib/` | `auth.sh` | Shared by the `data/` scripts: where the agents are and the token of the calls. |

## Filling the catalog

Bring the deployment up first (`run/run-mini.ps1`). Then, from the repository root, with `bash` and
`jq`:

```bash
# static identity (default mode): straight to the provider on http://127.0.0.1:1200
bash scripts/data/populate_mock_data.sh

# Keycloak mode (-Auth keycloak): through nginx by name, with a service-account token
EUNOMIA_KEYCLOAK=1 bash scripts/data/populate_mock_data.sh
```

With `EUNOMIA_KEYCLOAK=1` the calls go to `http://provider.localhost` / `http://consumer.localhost`
and carry a token of the realm's service account, asked to Keycloak with client credentials (client
`cli`, secret `<realm>-cli-secret`, the example values of the mini; the realm is the first label of
the target's host name). What the scripts create belongs to that service account, which is root
(`/admin`): `john.doe` sees it, the users below only what is public. `AGENT_URL`, `KEYCLOAK_URL`,
`EUNOMIA_CLIENT_ID`, `EUNOMIA_CLIENT_SECRET`, `EUNOMIA_PROVIDER_URL` and `EUNOMIA_CONSUMER_URL` change
the defaults; `EUNOMIA_TOKEN` sends a given token instead.

