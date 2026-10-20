#!/bin/bash
# Autentica un consumer contra un provider reutilizando scripts/authenticate-participants.sh
# y comprueba que el provider aprueba la conexión.
# Se ejecuta dentro de la imagen eunomia-hack-tools (ver tools.Dockerfile).
#
# CONSUMER_URL, PROVIDER_URL, DOCKER_PROVIDER_URL, PROVIDER_SLUG — ver lib.sh
set -euo pipefail
source /scripts/lib.sh
source /scripts/hack-lib.sh

log_step "Linking wallets (only if not linked yet)"
link_wallet "$CONSUMER_URL"
link_wallet "$PROVIDER_URL"

bash /scripts/authenticate-participants.sh

wait_last_status "$CONSUMER_URL/api/v1/peer-connection/request/all" Approved "Connection" 20 \
    || log_error "El provider no aprobó la conexión. Los providers de main exigen gx:LabelCredential:
el consumer la obtiene con el flujo Gaia (ver HACKATHON.md, comando 'gaia')."
