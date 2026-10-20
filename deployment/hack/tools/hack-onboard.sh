#!/bin/bash
# Registra un conector en una autoridad reutilizando scripts/register-with-authority.sh
# y comprueba que la credencial DataSpaceParticipant llega a emitirse.
# Se ejecuta dentro de la imagen eunomia-hack-tools (ver tools.Dockerfile).
#
# AUTHORITY_URL / DOCKER_AUTHORITY_URL — autoridad (requerido)
# PARTICIPANT_URL                      — conector a registrar (requerido)
# PARTICIPANT_SLUG                     — nombre para los logs
set -euo pipefail
source /scripts/lib.sh
source /scripts/hack-lib.sh

: "${PARTICIPANT_URL:?PARTICIPANT_URL is required}"

log_step "Linking wallets (only if not linked yet)"
link_wallet "$AUTHORITY_URL"
link_wallet "$PARTICIPANT_URL"

bash /scripts/register-with-authority.sh

wait_last_status "$PARTICIPANT_URL/api/v1/vc-request/all" Finalized "Credential request" \
    || log_error "La autoridad no emitió la credencial. Revisa los logs del conector y de la autoridad."
