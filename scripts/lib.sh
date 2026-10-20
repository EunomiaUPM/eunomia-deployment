AUTHORITY_URL="${AUTHORITY_URL:-http://127.0.0.1:1500}"
CONSUMER_URL="${CONSUMER_URL:-http://127.0.0.1:1100}"
PROVIDER_URL="${PROVIDER_URL:-http://127.0.0.1:1200}"

DOCKER_AUTHORITY_URL="${DOCKER_AUTHORITY_URL:-http://host.docker.internal:1500}"
DOCKER_CONSUMER_URL="${DOCKER_CONSUMER_URL:-http://host.docker.internal:1100}"
DOCKER_PROVIDER_URL="${DOCKER_PROVIDER_URL:-http://host.docker.internal:1200}"

log_step()    { echo -e "\n\033[36m$1\033[0m" >&2; }
log_success() { echo -e "\033[32m$1\033[0m" >&2; }
log_error()   { echo -e "\033[31m$1\033[0m" >&2; exit 1; }
log_info()    { echo -e "\033[33m$1\033[0m" >&2; }

# Imprime el cuerpo de la respuesta; si el HTTP es >= 400 (o no hay conexión) aborta con el error.
curl_raw() {
    local method=${1:-GET}
    local url=$2
    local body=${3:-}
    local response code
    if [ -n "$body" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" -H "Content-Type: application/json" -d "$body") || true
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" -H "Content-Type: application/json") || true
    fi
    code=$(echo "$response" | tail -n1)
    response=$(echo "$response" | sed '$d')
    if [ -z "$code" ] || [ "$code" = "000" ] || [ "$code" -ge 400 ]; then
        log_error "ERROR: $method $url -> HTTP ${code:-000}
$response"
    fi
    echo "$response"
}

# Enlaza el wallet solo si aún no lo está (GET /wallet/is-linked: 200 = enlazado).
link_wallet() {
    local url=$1
    if [ "$(curl -s -o /dev/null -w '%{http_code}' "$url/api/v1/wallet/is-linked")" = "200" ]; then
        log_info "Wallet already linked: $url"
    else
        curl_raw POST "$url/api/v1/wallet/link" >/dev/null
    fi
}
