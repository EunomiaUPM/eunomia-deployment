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
