#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(dirname "$0")"
source "$SCRIPT_DIR/lib.sh"

echo -e "\n======================================"
echo "         FULL ONBOARDING"
echo "======================================"

log_step "Linking wallets"
link_wallet "$AUTHORITY_URL"
link_wallet "$CONSUMER_URL"
link_wallet "$PROVIDER_URL"
log_success "Wallets linked"

PARTICIPANT_URL="$CONSUMER_URL" PARTICIPANT_SLUG="consumer" \
    bash "$SCRIPT_DIR/register-with-authority.sh"

PARTICIPANT_URL="$PROVIDER_URL" PARTICIPANT_SLUG="provider" \
    bash "$SCRIPT_DIR/register-with-authority.sh"

# El provider del mini pide gx:LabelCredential: gaia.sh consigue las VCs Gaia-X del consumer
# y termina autenticándolo en el provider.
bash "$SCRIPT_DIR/gaia.sh"

echo -e "\n======================================"
echo "   ONBOARDING FINISHED SUCCESSFULLY"
echo "======================================"
