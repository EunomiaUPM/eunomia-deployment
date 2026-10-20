#!/usr/bin/env bash
# =====================================================================
# hack.sh — despliegue sencillo de EUNOMIA para el hackatón (Linux / macOS).
# Gemelo de hack.ps1 (Windows): mismos comandos, mismos ficheros.
# Ayuda: ./hack.sh help
# =====================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"   # todas las rutas que se pasan a docker son relativas a la raíz
# Git Bash (Windows): que no reescriba rutas como /scripts/x.sh al llamar a docker.
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"

VERSIONS="versions.env"
INST_DIR="instances"
REGISTRY="$INST_DIR/registry.csv"
REGISTRY_HEADER="name,kind,role,http_port,db_port,created"
TOOLS_IMAGE="eunomia-hack-tools:local"

HTTP_PORT_RANGE="${HACK_HTTP_PORTS:-1600-1999}"
DB_PORT_RANGE="${HACK_DB_PORTS:-15400-15999}"
WAIT_SECS="${HACK_WAIT_SECS:-300}"

# Puertos publicados por el mini base: las instancias nunca los usan.
BASE_PORTS="1100 1200 1300 1400 1450 1500 6379 6380"
BASE_COMPONENTS="heimdall provider consumer"
RESERVED_NAMES="consumer provider authority heimdall base mini fafnir all"

# ---------------------------------------------------------------------
# Salida
# ---------------------------------------------------------------------
if [ -t 1 ]; then
    C_STEP=$'\033[36m'; C_OK=$'\033[32m'; C_WARN=$'\033[33m'; C_ERR=$'\033[31m'; C_DIM=$'\033[2m'; C_OFF=$'\033[0m'
else
    C_STEP=""; C_OK=""; C_WARN=""; C_ERR=""; C_DIM=""; C_OFF=""
fi
step() { echo "${C_STEP}==> $*${C_OFF}"; }
ok()   { echo "${C_OK}OK  $*${C_OFF}"; }
warn() { echo "${C_WARN}!!  $*${C_OFF}" >&2; }
die()  { echo "${C_ERR}ERROR: $*${C_OFF}" >&2; exit 1; }

usage() {
    cat <<'EOF'
Uso: ./hack.sh <comando> [opciones]

Mini base (autoridad + provider + consumer, puertos fijos 1500/1200/1100):
  base up                 Levanta el mini base y espera a que esté sano
  base stop               Lo para (conserva datos)
  base down               Lo borra entero, volúmenes incluidos
  base reset              base down + base up (empezar de cero)
  base status             Estado y URLs
  base logs [contenedor]  Logs (sin argumento: últimas líneas de cada servicio)
  base onboard            Onboarding completo de main (scripts/mini-onboarding.sh)

Entidades independientes (puertos libres automáticos):
  connector add [nombre] [--role consumer|provider] [--onboard] [--authority <aut>]
  authority add [nombre] [--role eco|dataspace]
  onboard <conector> [--authority <aut>]   Registra el conector en una autoridad
                                           (por defecto la del mini base)
  connect <consumer> <provider>            El consumer se autentica en el provider
  gaia [--consumer c] [--provider p] [--authority a]   Flujo Gaia-X (scripts/gaia.sh)

  list                    Instancias registradas, puertos y estado
  status [nombre]         Estado de una instancia (sin nombre: todo)
  logs <nombre|contenedor> [servicio]   Sigue los logs (Ctrl+C para salir)
  stop <nombre>           Para una instancia (conserva datos)
  start <nombre>          La vuelve a arrancar
  rm <nombre> [-y]        La borra (contenedores, volúmenes y configuración)

Otros:
  check                   Comprueba Docker y Docker Compose v2
  help                    Esta ayuda

Nombres reservados para el mini base: consumer, provider, authority (= heimdall).
Variables opcionales: HACK_HTTP_PORTS (1600-1999), HACK_DB_PORTS (15400-15999),
HACK_WAIT_SECS (300).
EOF
}

# ---------------------------------------------------------------------
# Requisitos
# ---------------------------------------------------------------------
check_requirements() {
    command -v docker >/dev/null 2>&1 || die "No encuentro 'docker'. Instala Docker Desktop (Windows/macOS) o Docker Engine (Linux)."
    docker info >/dev/null 2>&1 || die "Docker está instalado pero no responde. Arranca Docker Desktop / el servicio docker y reintenta."
    local v
    v=$(docker compose version --short 2>/dev/null) || die "No encuentro 'docker compose' (Compose v2). Actualiza Docker o instala el plugin docker-compose-plugin."
    v=${v#v}
    case "${v%%.*}" in
        ''|*[!0-9]*) die "No entiendo la versión de Docker Compose: '$v'" ;;
    esac
    [ "${v%%.*}" -ge 2 ] || die "Docker Compose $v es demasiado antiguo: hace falta v2 o superior ('docker compose', no 'docker-compose')."
    [ -f "$VERSIONS" ] || die "Falta $VERSIONS en $ROOT"
}

cmd_check() {
    check_requirements
    ok "Docker $(docker version --format '{{.Server.Version}}' 2>/dev/null) en marcha"
    ok "Docker Compose $(docker compose version --short)"
    step "Imágenes (versions.env):"
    grep -E '^[A-Z_]+=' "$VERSIONS" | tr -d '\r' | sed 's/^/    /'
}

# ---------------------------------------------------------------------
# Esperas
# ---------------------------------------------------------------------
# Espera a que el contenedor esté "healthy" (o "running" si no tiene healthcheck).
wait_healthy() {
    local c=$1 timeout=${2:-$WAIT_SECS} start state
    start=$(date +%s)
    printf '    esperando a %s ' "$c"
    while :; do
        state=$(docker container inspect -f '{{.State.Status}}/{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$c" 2>/dev/null || echo "missing/none")
        case "$state" in
            running/healthy|running/none) echo " ${C_OK}listo${C_OFF}"; return 0 ;;
            exited/*|dead/*|missing/*)
                echo " ${C_ERR}$state${C_OFF}"
                warn "$c no está en marcha. Mira: ./hack.sh logs $c"
                return 1 ;;
        esac
        if [ $(( $(date +%s) - start )) -ge "$timeout" ]; then
            echo " ${C_ERR}timeout ($state)${C_OFF}"
            warn "$c no está sano tras ${timeout}s. Mira: ./hack.sh logs $c"
            return 1
        fi
        printf '.'
        sleep 3
    done
}

# Comprobación extra desde el equipo (no bloqueante): ¿responde el puerto publicado?
probe_http() {
    local url=$1 code
    command -v curl >/dev/null 2>&1 || return 0
    code=$(curl -s -o /dev/null -m 5 -w '%{http_code}' "$url" || true)
    case "$code" in
        2*|3*|401|403) ;;
        *) warn "El contenedor está sano pero $url devuelve '$code' desde este equipo (¿firewall/proxy?)." ;;
    esac
}

# ---------------------------------------------------------------------
# Mini base
# ---------------------------------------------------------------------
base_compose() {
    local comp=$1; shift
    docker compose --env-file "$VERSIONS" -f "deployment/mini/docker-compose.mini.$comp.yaml" "$@"
}

base_main_container() {
    case "$1" in heimdall) echo heimdall ;; provider) echo provider ;; consumer) echo consumer ;; esac
}

base_print_urls() {
    cat <<EOF

${C_OK}Mini base:${C_OFF}
  Autoridad (Heimdall)  http://localhost:1500/admin/home   DID did:web:host.docker.internal%3A1500
  Provider              http://localhost:1200/admin/login  DID did:web:host.docker.internal%3A1200
  Consumer              http://localhost:1100/admin/login  DID did:web:host.docker.internal%3A1100
  Login consolas provider/consumer: eunomia / eunomia
  Desde otros contenedores: http://host.docker.internal:<puerto>
  Postgres: consumer localhost:1300, provider localhost:1400, heimdall localhost:1450
            (usuario = contraseña = BD: mini_consumer / mini_provider / mini_heimdall)
EOF
}

base_up() {
    check_requirements
    # En Linux los contenedores corren como uid 10001 y el setup escribe en vault/*/secrets.
    chmod -R a+rwX vault/consumer vault/provider vault/heimdall 2>/dev/null || true
    local comp
    for comp in $BASE_COMPONENTS; do
        step "Levantando mini-$comp (descarga imágenes la primera vez)"
        base_compose "$comp" up -d || die "Fallo al levantar mini-$comp. Mira: ./hack.sh base logs $comp-setup  (o ./hack.sh base status)"
    done
    step "Esperando a que todo esté sano"
    local failed=0
    for c in fafnir-wallet heimdall provider-fafnir-wallet provider consumer-fafnir-wallet consumer; do
        wait_healthy "$c" || failed=1
    done
    [ "$failed" = 0 ] || die "Algún servicio del mini base no está sano (ver arriba)."
    probe_http "http://localhost:1500/readiness"
    probe_http "http://localhost:1200/.well-known/dspace-version"
    probe_http "http://localhost:1100/.well-known/dspace-version"
    ok "Mini base listo"
    base_print_urls
    echo
    echo "Siguiente paso típico: ./hack.sh base onboard"
}

base_stop() {
    check_requirements
    local comp
    for comp in consumer provider heimdall; do
        step "Parando mini-$comp"
        base_compose "$comp" stop
    done
    ok "Mini base parado (datos conservados). Vuelve con: ./hack.sh base up"
}

base_down() {
    check_requirements
    local comp
    for comp in consumer provider heimdall; do
        step "Borrando mini-$comp (contenedores y volúmenes)"
        base_compose "$comp" down -v --remove-orphans
    done
    ok "Mini base borrado"
}

confirm() {
    local msg=$1 yes=${2:-}
    [ "$yes" = "-y" ] || [ "$yes" = "--yes" ] && return 0
    printf '%s [s/N] ' "$msg"
    local ans; read -r ans || true
    case "$ans" in s|S|si|SI|sí|y|Y|yes) return 0 ;; *) die "Cancelado." ;; esac
}

base_status() {
    check_requirements
    local comp
    for comp in $BASE_COMPONENTS; do
        echo "${C_STEP}mini-$comp${C_OFF}"
        base_compose "$comp" ps -a --format 'table {{.Name}}\t{{.Status}}\t{{.Ports}}'
    done
    base_print_urls
}

base_logs() {
    check_requirements
    if [ $# -gt 0 ]; then
        docker logs -f --tail 200 "$1"
        return
    fi
    local c
    for c in heimdall-setup heimdall fafnir-wallet provider-setup provider provider-fafnir-wallet consumer-setup consumer consumer-fafnir-wallet; do
        echo "${C_STEP}----- $c (últimas 15 líneas) -----${C_OFF}"
        docker logs --tail 15 "$c" 2>&1 || true
    done
    echo
    echo "Para seguir uno: ./hack.sh base logs <contenedor>"
}

# ---------------------------------------------------------------------
# Registro de instancias (instances/registry.csv)
# ---------------------------------------------------------------------
registry_init() {
    mkdir -p "$INST_DIR"
    [ -f "$REGISTRY" ] || echo "$REGISTRY_HEADER" > "$REGISTRY"
}

registry_rows() { [ -f "$REGISTRY" ] && tail -n +2 "$REGISTRY" | tr -d '\r' | grep -v '^$' || true; }

registry_get() {   # registry_get <nombre> <columna 1..6>
    registry_rows | awk -F, -v n="$1" -v col="$2" '$1==n {print $col}'
}

registry_has() { [ -n "$(registry_get "$1" 1)" ]; }

registry_remove() {
    [ -f "$REGISTRY" ] || return 0
    local tmp="$REGISTRY.tmp"
    { echo "$REGISTRY_HEADER"; registry_rows | awk -F, -v n="$1" '$1!=n'; } > "$tmp"
    mv "$tmp" "$REGISTRY"
}

# Carga instances/<nombre>/instance.env en el entorno (Compose da prioridad al entorno).
load_instance_env() {
    local f="$INST_DIR/$1/instance.env" k v
    [ -f "$f" ] || die "No existe la instancia '$1' (falta $f). Mira: ./hack.sh list"
    while IFS='=' read -r k v || [ -n "$k" ]; do
        v=${v%$'\r'}
        case "$k" in ''|\#*) continue ;; esac
        export "$k=$v"
    done < "$f"
}

inst_compose() {
    local name=$1; shift
    (
        load_instance_env "$name"
        docker compose -p "hack-$name" --env-file "$VERSIONS" -f "deployment/hack/docker-compose.$KIND.yaml" "$@"
    )
}

# ---------------------------------------------------------------------
# Puertos libres
# ---------------------------------------------------------------------
used_ports() {
    echo "$BASE_PORTS"
    registry_rows | awk -F, '{print $4; print $5}'
    docker ps --format '{{.Ports}}' 2>/dev/null | grep -oE ':[0-9]+->' | grep -oE '[0-9]+' || true
}

host_port_busy() {   # algo escucha ya en el puerto
    (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
}

find_free_port() {   # find_free_port <lo-hi> <puertos a excluir...>
    local range=$1; shift
    local lo=${range%-*} hi=${range#*-} used p
    used=" $(used_ports | tr '\n' ' ') $* "
    for (( p = lo; p <= hi; p++ )); do
        case "$used" in *" $p "*) continue ;; esac
        host_port_busy "$p" && continue
        echo "$p"
        return 0
    done
    die "No hay puertos libres en el rango $range"
}

# ---------------------------------------------------------------------
# Instancias
# ---------------------------------------------------------------------
validate_name() {
    local name=$1 r
    echo "$name" | grep -Eq '^[a-z][a-z0-9-]{1,30}$' \
        || die "Nombre '$name' no válido: minúsculas, números y guiones, empezando por letra (2-31 caracteres)."
    for r in $RESERVED_NAMES; do
        [ "$name" != "$r" ] || die "'$name' está reservado para el mini base."
    done
    if registry_has "$name" || [ -d "$INST_DIR/$name" ]; then
        die "Ya existe una instancia '$name'. Mira: ./hack.sh list"
    fi
    if docker container inspect "$name" >/dev/null 2>&1; then
        die "Ya hay un contenedor llamado '$name' en Docker."
    fi
}

random_name() {
    local prefix=$1 n
    while :; do
        n="$prefix-$(LC_ALL=C tr -dc 'a-z0-9' </dev/urandom 2>/dev/null | head -c 4 || true)"
        [ ${#n} -gt $(( ${#prefix} + 1 )) ] || n="$prefix-$RANDOM"
        registry_has "$n" || [ -d "$INST_DIR/$n" ] || { echo "$n"; return; }
    done
}

# Copia los secretos de ejemplo de un rol del mini (claves/cert PEM, db, wallet).
# El setup de cada servicio genera los *.json.example de claves a partir de los PEM.
copy_vault() {
    local from="vault/$1" to=$2 f
    mkdir -p "$to/config" "$to/secrets" "$to/data"
    cp "$from"/config/*.example "$to/config/"
    for f in db.json wallet.json private_key.pem public_key.pem cert.pem; do
        cp "$from/secrets/$f.example" "$to/secrets/$f.example"
    done
    chmod -R a+rwX "$to" 2>/dev/null || true
}

write_instance() {   # write_instance <nombre> <kind> <role> <http> <db> [redis_password]
    local dir="$INST_DIR/$1"
    {
        echo "INSTANCE=$1"
        echo "KIND=$2"
        echo "ROLE=$3"
        echo "HTTP_PORT=$4"
        echo "DB_PORT=$5"
        [ -z "${6:-}" ] || echo "REDIS_PASSWORD=$6"
    } > "$dir/instance.env"
    registry_init
    echo "$1,$2,$3,$4,$5,$(date '+%Y-%m-%dT%H:%M:%S')" >> "$REGISTRY"
}

print_instance() {
    local name=$1 kind role http db
    kind=$(registry_get "$name" 2); role=$(registry_get "$name" 3)
    http=$(registry_get "$name" 4); db=$(registry_get "$name" 5)
    echo
    if [ "$kind" = connector ]; then
        echo "${C_OK}Conector '$name' ($role):${C_OFF}"
        echo "  Consola     http://localhost:$http/admin/login   (eunomia / eunomia)"
    else
        echo "${C_OK}Autoridad '$name' ($role):${C_OFF}"
        echo "  Consola     http://localhost:$http/admin/home"
    fi
    echo "  API         http://localhost:$http/api/v1"
    echo "  DID         did:web:host.docker.internal%3A$http"
    echo "  Contenedores: http://host.docker.internal:$http"
    echo "  Postgres    localhost:$db"
    echo "  Logs        ./hack.sh logs $name"
}

instance_wait() {
    local name=$1 kind failed=0
    kind=$(registry_get "$name" 2)
    step "Esperando a que '$name' esté sano"
    wait_healthy "$name-wallet" || failed=1
    wait_healthy "$name" || failed=1
    [ "$failed" = 0 ] || die "'$name' no está sano. Mira: ./hack.sh logs $name"
    if [ "$kind" = connector ]; then
        probe_http "http://localhost:$(registry_get "$name" 4)/.well-known/dspace-version"
    else
        probe_http "http://localhost:$(registry_get "$name" 4)/readiness"
    fi
    ok "'$name' listo"
}

connector_add() {
    local name="" role=consumer onboard=0 authority=authority
    while [ $# -gt 0 ]; do
        case "$1" in
            --role) role=${2:?--role necesita valor}; shift 2 ;;
            --onboard) onboard=1; shift ;;
            --authority) authority=${2:?--authority necesita valor}; onboard=1; shift 2 ;;
            -*) die "Opción desconocida: $1" ;;
            *) [ -z "$name" ] || die "Sobra el argumento '$1'"; name=$1; shift ;;
        esac
    done
    case "$role" in consumer|provider) ;; *) die "--role debe ser consumer o provider" ;; esac
    check_requirements
    registry_init
    [ -n "$name" ] || name=$(random_name conn)
    validate_name "$name"
    [ "$onboard" = 0 ] || resolve_port "$authority" >/dev/null

    local http db base_port dir
    http=$(find_free_port "$HTTP_PORT_RANGE")
    db=$(find_free_port "$DB_PORT_RANGE" "$http")
    dir="$INST_DIR/$name"
    step "Creando conector '$name' ($role) en $dir — HTTP $http, Postgres $db"
    mkdir -p "$dir/config"

    # Configuración generada desde las plantillas de main (static/config).
    [ "$role" = consumer ] && base_port=1100 || base_port=1200
    sed -e "s/'$base_port'/'$http'/g" \
        -e "s/$role-fafnir-wallet/$name-wallet/g" \
        -e "s/$role-redis/$name-redis/g" \
        -e "s/$role-db/$name-db/g" \
        "static/config/$role/mini/mini.$role.yaml" > "$dir/config/agent.yaml"
    sed -e "s/$role-db/$name-db/g" "static/config/fafnir/$role.yaml" > "$dir/config/fafnir.yaml"
    copy_vault "$role" "$dir/vault"
    write_instance "$name" connector "$role" "$http" "$db" "ds_core_${role}_redis"

    step "Levantando (proyecto hack-$name)"
    inst_compose "$name" up -d || die "Fallo al levantar '$name'. Mira: ./hack.sh logs $name  (o ./hack.sh rm $name)"
    instance_wait "$name"
    print_instance "$name"
    if [ "$onboard" = 1 ]; then
        onboard_connector "$name" "$authority"
    else
        echo
        echo "Para registrarlo en la autoridad del mini base: ./hack.sh onboard $name"
    fi
}

authority_add() {
    local name="" role=eco tmpl
    while [ $# -gt 0 ]; do
        case "$1" in
            --role) role=${2:?--role necesita valor}; shift 2 ;;
            -*) die "Opción desconocida: $1" ;;
            *) [ -z "$name" ] || die "Sobra el argumento '$1'"; name=$1; shift ;;
        esac
    done
    case "$role" in
        eco) tmpl=static/config/heimdall/mini/mini_eco_authority.yaml ;;
        dataspace) tmpl=static/config/heimdall/mini/mini_dataspace_authority.yaml ;;
        *) die "--role debe ser eco o dataspace" ;;
    esac
    check_requirements
    registry_init
    [ -n "$name" ] || name=$(random_name auth)
    validate_name "$name"

    local http db dir
    http=$(find_free_port "$HTTP_PORT_RANGE")
    db=$(find_free_port "$DB_PORT_RANGE" "$http")
    dir="$INST_DIR/$name"
    step "Creando autoridad '$name' ($role) en $dir — HTTP $http, Postgres $db"
    mkdir -p "$dir/config"
    sed -e "s/'1500'/'$http'/g" \
        -e "s/'heimdall-db'/'$name-db'/g" \
        -e "s/'fafnir-wallet'/'$name-wallet'/g" \
        "$tmpl" > "$dir/config/authority.yaml"
    sed -e "s/heimdall-db/$name-db/g" static/config/fafnir/heimdall.yaml > "$dir/config/fafnir.yaml"
    copy_vault heimdall "$dir/vault"
    write_instance "$name" authority "$role" "$http" "$db"

    step "Levantando (proyecto hack-$name)"
    inst_compose "$name" up -d || die "Fallo al levantar '$name'. Mira: ./hack.sh logs $name  (o ./hack.sh rm $name)"
    instance_wait "$name"
    print_instance "$name"
    echo
    echo "Registra un conector en ella: ./hack.sh onboard <conector> --authority $name"
}

require_instance() { registry_has "$1" || die "No existe la instancia '$1'. Mira: ./hack.sh list"; }

# Puerto HTTP de una entidad: nombres del mini base o instancia registrada.
resolve_port() {
    case "$1" in
        consumer) echo 1100 ;;
        provider) echo 1200 ;;
        authority|heimdall) echo 1500 ;;
        *) require_instance "$1"; registry_get "$1" 4 ;;
    esac
}

resolve_kind() {
    case "$1" in
        consumer|provider) echo connector ;;
        authority|heimdall) echo authority ;;
        *) registry_get "$1" 2 ;;
    esac
}

# Ejecuta un script de scripts/ (o deployment/hack/tools/) en el contenedor de herramientas.
run_tool() {
    step "Preparando contenedor de herramientas (bash + curl + jq)"
    docker build -q -f deployment/hack/tools.Dockerfile -t "$TOOLS_IMAGE" . >/dev/null \
        || die "No pude construir $TOOLS_IMAGE"
    docker run --rm --add-host host.docker.internal:host-gateway "$@"
}

onboard_connector() {
    local name=$1 authority=${2:-authority} cport aport
    [ "$(resolve_kind "$name")" = connector ] || die "'$name' no es un conector"
    [ "$(resolve_kind "$authority")" = authority ] || die "'$authority' no es una autoridad"
    cport=$(resolve_port "$name"); aport=$(resolve_port "$authority")
    step "Onboarding de '$name' (puerto $cport) en la autoridad '$authority' (puerto $aport)"
    run_tool \
        -e AUTHORITY_URL="http://host.docker.internal:$aport" \
        -e DOCKER_AUTHORITY_URL="http://host.docker.internal:$aport" \
        -e PARTICIPANT_URL="http://host.docker.internal:$cport" \
        -e PARTICIPANT_SLUG="$name" \
        "$TOOLS_IMAGE" bash /scripts/hack-onboard.sh \
        || die "Onboarding fallido. Mira: ./hack.sh logs $name  y  ./hack.sh logs $authority"
    ok "'$name' registrado en '$authority'"
}

cmd_onboard() {
    local name="" authority=authority
    while [ $# -gt 0 ]; do
        case "$1" in
            --authority) authority=${2:?--authority necesita valor}; shift 2 ;;
            -*) die "Opción desconocida: $1" ;;
            *) [ -z "$name" ] || die "Sobra el argumento '$1'"; name=$1; shift ;;
        esac
    done
    [ -n "$name" ] || die "Uso: ./hack.sh onboard <conector> [--authority <aut>]"
    check_requirements
    onboard_connector "$name" "$authority"
}

cmd_connect() {
    [ $# -eq 2 ] || die "Uso: ./hack.sh connect <consumer> <provider>"
    check_requirements
    local cport pport
    [ "$(resolve_kind "$1")" = connector ] || die "'$1' no es un conector"
    [ "$(resolve_kind "$2")" = connector ] || die "'$2' no es un conector"
    cport=$(resolve_port "$1"); pport=$(resolve_port "$2")
    step "'$1' (puerto $cport) se autentica en '$2' (puerto $pport)"
    run_tool \
        -e CONSUMER_URL="http://host.docker.internal:$cport" \
        -e PROVIDER_URL="http://host.docker.internal:$pport" \
        -e DOCKER_PROVIDER_URL="http://host.docker.internal:$pport" \
        -e PROVIDER_SLUG="$2" \
        "$TOOLS_IMAGE" bash /scripts/hack-connect.sh \
        || die "Autenticación fallida. Mira: ./hack.sh logs $1  y  ./hack.sh logs $2"
    ok "'$1' autenticado en '$2'"
}

cmd_gaia() {
    local consumer=consumer provider=provider authority=authority
    while [ $# -gt 0 ]; do
        case "$1" in
            --consumer) consumer=${2:?}; shift 2 ;;
            --provider) provider=${2:?}; shift 2 ;;
            --authority) authority=${2:?}; shift 2 ;;
            *) die "Opción desconocida: $1" ;;
        esac
    done
    check_requirements
    local c p a
    c=$(resolve_port "$consumer"); p=$(resolve_port "$provider"); a=$(resolve_port "$authority")
    run_tool \
        -e CONSUMER_URL="http://host.docker.internal:$c" -e DOCKER_CONSUMER_URL="http://host.docker.internal:$c" \
        -e PROVIDER_URL="http://host.docker.internal:$p" -e DOCKER_PROVIDER_URL="http://host.docker.internal:$p" \
        -e AUTHORITY_URL="http://host.docker.internal:$a" -e DOCKER_AUTHORITY_URL="http://host.docker.internal:$a" \
        "$TOOLS_IMAGE" bash /scripts/hack-verify-connection.sh gaia.sh
}

base_onboard() {
    check_requirements
    run_tool \
        -e CONSUMER_URL="http://host.docker.internal:1100" -e DOCKER_CONSUMER_URL="http://host.docker.internal:1100" \
        -e PROVIDER_URL="http://host.docker.internal:1200" -e DOCKER_PROVIDER_URL="http://host.docker.internal:1200" \
        -e AUTHORITY_URL="http://host.docker.internal:1500" -e DOCKER_AUTHORITY_URL="http://host.docker.internal:1500" \
        "$TOOLS_IMAGE" bash /scripts/hack-verify-connection.sh mini-onboarding.sh
}

container_state() {
    docker container inspect -f '{{.State.Status}}{{if .State.Health}} ({{.State.Health.Status}}){{end}}' "$1" 2>/dev/null || echo "no creado"
}

cmd_list() {
    check_requirements
    registry_init
    printf '%-20s %-10s %-10s %-6s %-6s %s\n' NOMBRE TIPO ROL HTTP PG ESTADO
    local name kind role http db _ any=0
    while IFS=, read -r name kind role http db _; do
        [ -n "$name" ] || continue
        any=1
        printf '%-20s %-10s %-10s %-6s %-6s %s\n' "$name" "$kind" "$role" "$http" "$db" "$(container_state "$name")"
    done <<EOF
$(registry_rows)
EOF
    [ "$any" = 1 ] || echo "(sin instancias; crea una con ./hack.sh connector add o ./hack.sh authority add)"
    echo
    echo "Mini base: heimdall $(container_state heimdall), provider $(container_state provider), consumer $(container_state consumer)"
}

cmd_status() {
    if [ $# -eq 0 ]; then
        base_status
        echo
        cmd_list
        return
    fi
    check_requirements
    require_instance "$1"
    inst_compose "$1" ps -a --format 'table {{.Name}}\t{{.Status}}\t{{.Ports}}'
    print_instance "$1"
}

cmd_logs() {
    [ $# -ge 1 ] || die "Uso: ./hack.sh logs <instancia|contenedor> [servicio]"
    check_requirements
    if registry_has "$1"; then
        local name=$1; shift
        inst_compose "$name" logs -f --tail 200 "$@"
    elif docker container inspect "$1" >/dev/null 2>&1; then
        docker logs -f --tail 200 "$1"
    else
        die "No conozco '$1' (ni instancia ni contenedor). Mira: ./hack.sh list"
    fi
}

cmd_stop() {
    [ $# -eq 1 ] || die "Uso: ./hack.sh stop <nombre>"
    [ "$1" != base ] || { base_stop; return; }
    check_requirements
    require_instance "$1"
    inst_compose "$1" stop
    ok "'$1' parado (datos conservados). Vuelve con: ./hack.sh start $1"
}

cmd_start() {
    [ $# -eq 1 ] || die "Uso: ./hack.sh start <nombre>"
    [ "$1" != base ] || { base_up; return; }
    check_requirements
    require_instance "$1"
    inst_compose "$1" up -d || die "Fallo al arrancar '$1'. Mira: ./hack.sh logs $1"
    instance_wait "$1"
    print_instance "$1"
}

cmd_rm() {
    local name="" yes=""
    while [ $# -gt 0 ]; do
        case "$1" in
            -y|--yes) yes=-y; shift ;;
            *) [ -z "$name" ] || die "Sobra el argumento '$1'"; name=$1; shift ;;
        esac
    done
    [ -n "$name" ] || die "Uso: ./hack.sh rm <nombre> [-y]"
    check_requirements
    if ! registry_has "$name" && [ ! -d "$INST_DIR/$name" ]; then
        die "No existe la instancia '$name'. Mira: ./hack.sh list"
    fi
    confirm "Se borrarán los contenedores, volúmenes y la configuración de '$name'. ¿Seguro?" "$yes"
    if [ -f "$INST_DIR/$name/instance.env" ]; then
        inst_compose "$name" down -v --remove-orphans || warn "docker compose down falló; sigo limpiando"
    fi
    rm -rf "${INST_DIR:?}/$name"
    registry_remove "$name"
    ok "'$name' borrado"
}

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
main() {
    local cmd=${1:-help}
    [ $# -eq 0 ] || shift
    case "$cmd" in
        base)
            local sub=${1:-}
            [ $# -eq 0 ] || shift
            case "$sub" in
                up) base_up ;;
                stop) base_stop ;;
                down) confirm "Se borrará el mini base con sus volúmenes. ¿Seguro?" "${1:-}"; base_down ;;
                reset) confirm "Se borrará el mini base con sus volúmenes y se levantará de cero. ¿Seguro?" "${1:-}"; base_down; base_up ;;
                status) base_status ;;
                logs) base_logs "$@" ;;
                onboard) base_onboard ;;
                *) die "Uso: ./hack.sh base up|stop|down|reset|status|logs|onboard" ;;
            esac ;;
        connector)
            [ "${1:-}" = add ] || die "Uso: ./hack.sh connector add [nombre] [--role consumer|provider] [--onboard] [--authority <aut>]"
            shift; connector_add "$@" ;;
        authority)
            [ "${1:-}" = add ] || die "Uso: ./hack.sh authority add [nombre] [--role eco|dataspace]"
            shift; authority_add "$@" ;;
        onboard) cmd_onboard "$@" ;;
        connect) cmd_connect "$@" ;;
        gaia) cmd_gaia "$@" ;;
        list|ls) cmd_list ;;
        status) cmd_status "$@" ;;
        logs) cmd_logs "$@" ;;
        stop) cmd_stop "$@" ;;
        start) cmd_start "$@" ;;
        rm|remove|delete) cmd_rm "$@" ;;
        check) cmd_check ;;
        help|-h|--help) usage ;;
        *) usage; exit 1 ;;
    esac
}

main "$@"
