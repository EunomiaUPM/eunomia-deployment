#!/bin/bash
# Ejecuta un script de onboarding de main (mini-onboarding.sh o gaia.sh) y comprueba al final
# que la conexión consumer -> provider quedó aprobada (esos scripts no lo verifican).
# Uso: hack-verify-connection.sh <script.sh>      Variables: ver lib.sh
set -euo pipefail
source /scripts/lib.sh
source /scripts/hack-lib.sh

bash "/scripts/${1:?script required}"

wait_last_status "$CONSUMER_URL/api/v1/peer-connection/request/all" Approved "Consumer -> provider connection" 20 \
    || log_error "El flujo terminó pero el provider no aprobó la conexión. Revisa los logs del consumer y del provider."
