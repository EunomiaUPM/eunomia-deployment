# Helpers comunes de los scripts hack-*.sh (se cargan después de scripts/lib.sh).

# Espera a que la petición más reciente de una lista (vc-request/all, peer-connection/request/all)
# llegue al estado esperado. wait_last_status <url-lista> <estado> <descripción> [segundos]
wait_last_status() {
    local list_url=$1 expected=$2 what=$3 timeout=${4:-30} status="" i
    for (( i = 0; i < timeout; i += 2 )); do
        status=$(curl -s "$list_url" | jq -r 'sort_by(.created_at // "") | last | .status // "none"' 2>/dev/null || true)
        [ "$status" = "$expected" ] && { log_success "$what: $status"; return 0; }
        sleep 2
    done
    echo -e "\033[31m$what: estado '$status' (se esperaba '$expected')\033[0m" >&2
    return 1
}
