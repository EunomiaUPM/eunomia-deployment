# =====================================================================
# hack.ps1 — despliegue sencillo de EUNOMIA para el hackatón (Windows).
# Gemelo de hack.sh (Linux/macOS): mismos comandos, mismos ficheros.
# Funciona con Windows PowerShell 5.1 y con PowerShell 7 (pwsh).
# Ayuda: .\hack.ps1 help      (o .\hack.cmd help si la ExecutionPolicy lo bloquea)
# =====================================================================

$Root = $PSScriptRoot
$Versions = "versions.env"
$InstDir = Join-Path $Root "instances"
$Registry = Join-Path $InstDir "registry.csv"
$RegistryHeader = "name,kind,role,http_port,db_port,created"
$ToolsImage = "eunomia-hack-tools:local"

$HttpPortRange = if ($env:HACK_HTTP_PORTS) { $env:HACK_HTTP_PORTS } else { "1600-1999" }
$DbPortRange = if ($env:HACK_DB_PORTS) { $env:HACK_DB_PORTS } else { "15400-15999" }
$WaitSecs = if ($env:HACK_WAIT_SECS) { [int]$env:HACK_WAIT_SECS } else { 300 }

# Puertos publicados por el mini base: las instancias nunca los usan.
$BasePorts = @(1100, 1200, 1300, 1400, 1450, 1500, 6379, 6380)
$BaseComponents = @("heimdall", "provider", "consumer")
$ReservedNames = @("consumer", "provider", "authority", "heimdall", "base", "mini", "fafnir", "all")
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false

# ---------------------------------------------------------------------
# Salida
# ---------------------------------------------------------------------
function Step([string]$Msg) { Write-Host "==> $Msg" -ForegroundColor Cyan }
function Ok([string]$Msg) { Write-Host "OK  $Msg" -ForegroundColor Green }
function Warn([string]$Msg) { Write-Host "!!  $Msg" -ForegroundColor Yellow }
function Die([string]$Msg) { throw "HACK:$Msg" }

function Show-Usage {
    @"
Uso: .\hack.ps1 <comando> [opciones]      (o .\hack.cmd <comando> [opciones])

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
"@ | Write-Host
}

# ---------------------------------------------------------------------
# Requisitos
# ---------------------------------------------------------------------
function Test-Requirements {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Die "No encuentro 'docker'. Instala Docker Desktop (Windows/macOS) o Docker Engine (Linux)."
    }
    docker info *> $null
    if ($LASTEXITCODE -ne 0) { Die "Docker está instalado pero no responde. Arranca Docker Desktop y reintenta." }
    $v = docker compose version --short 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $v) { Die "No encuentro 'docker compose' (Compose v2). Actualiza Docker Desktop." }
    $v = "$v".Trim().TrimStart("v")
    $major = 0
    if (-not [int]::TryParse($v.Split(".")[0], [ref]$major)) { Die "No entiendo la versión de Docker Compose: '$v'" }
    if ($major -lt 2) { Die "Docker Compose $v es demasiado antiguo: hace falta v2 o superior ('docker compose', no 'docker-compose')." }
    if (-not (Test-Path (Join-Path $Root $Versions))) { Die "Falta $Versions en $Root" }
}

function Invoke-Check {
    Test-Requirements
    Ok "Docker $(docker version --format '{{.Server.Version}}' 2>$null) en marcha"
    Ok "Docker Compose $(docker compose version --short)"
    Step "Imágenes (versions.env):"
    Get-Content (Join-Path $Root $Versions) | Where-Object { $_ -match '^[A-Z_]+=' } | ForEach-Object { Write-Host "    $_" }
}

# ---------------------------------------------------------------------
# Esperas
# ---------------------------------------------------------------------
function Get-ContainerState([string]$Name) {
    $s = docker container inspect -f '{{.State.Status}}/{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' $Name 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $s) { return "missing/none" }
    return "$s".Trim()
}

# Espera a que el contenedor esté "healthy" (o "running" si no tiene healthcheck).
function Wait-Healthy([string]$Name, [int]$TimeoutSecs = $WaitSecs) {
    $deadline = (Get-Date).AddSeconds($TimeoutSecs)
    Write-Host "    esperando a $Name " -NoNewline
    while ($true) {
        $state = Get-ContainerState $Name
        if ($state -eq "running/healthy" -or $state -eq "running/none") {
            Write-Host " listo" -ForegroundColor Green
            return $true
        }
        if ($state -match '^(exited|dead|missing)/') {
            Write-Host " $state" -ForegroundColor Red
            Warn "$Name no está en marcha. Mira: .\hack.ps1 logs $Name"
            return $false
        }
        if ((Get-Date) -gt $deadline) {
            Write-Host " timeout ($state)" -ForegroundColor Red
            Warn "$Name no está sano tras ${TimeoutSecs}s. Mira: .\hack.ps1 logs $Name"
            return $false
        }
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 3
    }
}

# Comprobación extra desde el equipo (no bloqueante): ¿responde el puerto publicado?
function Test-Http([string]$Url) {
    try {
        Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 | Out-Null
    } catch {
        $resp = $_.Exception.Response
        if ($resp -and [int]$resp.StatusCode -lt 500) { return }
        Warn "El contenedor está sano pero $Url no responde desde este equipo (¿firewall/proxy?)."
    }
}

# ---------------------------------------------------------------------
# Mini base
# ---------------------------------------------------------------------
function Invoke-BaseCompose([string]$Comp, [string[]]$Rest) {
    # Sin valor de retorno (la salida de docker va a pantalla): mira $LASTEXITCODE después.
    $composeArgs = @("compose", "--env-file", $Versions, "-f", "deployment/mini/docker-compose.mini.$Comp.yaml") + $Rest
    & docker @composeArgs
}

function Show-BaseUrls {
    Write-Host ""
    Write-Host "Mini base:" -ForegroundColor Green
    Write-Host "  Autoridad (Heimdall)  http://localhost:1500/admin/home   DID did:web:host.docker.internal%3A1500"
    Write-Host "  Provider              http://localhost:1200/admin/login  DID did:web:host.docker.internal%3A1200"
    Write-Host "  Consumer              http://localhost:1100/admin/login  DID did:web:host.docker.internal%3A1100"
    Write-Host "  Login consolas provider/consumer: eunomia / eunomia"
    Write-Host "  Desde otros contenedores: http://host.docker.internal:<puerto>"
    Write-Host "  Postgres: consumer localhost:1300, provider localhost:1400, heimdall localhost:1450"
    Write-Host "            (usuario = contraseña = BD: mini_consumer / mini_provider / mini_heimdall)"
}

function Invoke-BaseUp {
    Test-Requirements
    # pwsh en Linux: los contenedores corren como uid 10001 y el setup escribe en vault/*/secrets.
    if ($IsLinux -or $IsMacOS) { chmod -R a+rwX vault/consumer vault/provider vault/heimdall }
    foreach ($comp in $BaseComponents) {
        Step "Levantando mini-$comp (descarga imágenes la primera vez)"
        Invoke-BaseCompose $comp @("up", "-d")
        if ($LASTEXITCODE -ne 0) {
            Die "Fallo al levantar mini-$comp. Mira: .\hack.ps1 base logs $comp-setup  (o .\hack.ps1 base status)"
        }
    }
    Step "Esperando a que todo esté sano"
    $failed = $false
    foreach ($c in @("fafnir-wallet", "heimdall", "provider-fafnir-wallet", "provider", "consumer-fafnir-wallet", "consumer")) {
        if (-not (Wait-Healthy $c)) { $failed = $true }
    }
    if ($failed) { Die "Algún servicio del mini base no está sano (ver arriba)." }
    Test-Http "http://localhost:1500/readiness"
    Test-Http "http://localhost:1200/.well-known/dspace-version"
    Test-Http "http://localhost:1100/.well-known/dspace-version"
    Ok "Mini base listo"
    Show-BaseUrls
    Write-Host ""
    Write-Host "Siguiente paso típico: .\hack.ps1 base onboard"
}

function Invoke-BaseStop {
    Test-Requirements
    foreach ($comp in @("consumer", "provider", "heimdall")) {
        Step "Parando mini-$comp"
        Invoke-BaseCompose $comp @("stop")
    }
    Ok "Mini base parado (datos conservados). Vuelve con: .\hack.ps1 base up"
}

function Invoke-BaseDown {
    Test-Requirements
    foreach ($comp in @("consumer", "provider", "heimdall")) {
        Step "Borrando mini-$comp (contenedores y volúmenes)"
        Invoke-BaseCompose $comp @("down", "-v", "--remove-orphans")
    }
    Ok "Mini base borrado"
}

function Confirm-Action([string]$Msg, [string]$Yes) {
    if ($Yes -eq "-y" -or $Yes -eq "--yes") { return }
    $ans = Read-Host "$Msg [s/N]"
    if ($ans -notmatch '^(s|si|sí|y|yes)$') { Die "Cancelado." }
}

function Invoke-BaseStatus {
    Test-Requirements
    foreach ($comp in $BaseComponents) {
        Write-Host "mini-$comp" -ForegroundColor Cyan
        Invoke-BaseCompose $comp @("ps", "-a", "--format", 'table {{.Name}}\t{{.Status}}\t{{.Ports}}')
    }
    Show-BaseUrls
}

function Invoke-BaseLogs([string[]]$Rest) {
    Test-Requirements
    if ($Rest.Count -gt 0) {
        docker logs -f --tail 200 $Rest[0]
        return
    }
    foreach ($c in @("heimdall-setup", "heimdall", "fafnir-wallet", "provider-setup", "provider", "provider-fafnir-wallet", "consumer-setup", "consumer", "consumer-fafnir-wallet")) {
        Write-Host "----- $c (últimas 15 líneas) -----" -ForegroundColor Cyan
        # "$_" convierte en texto plano lo que PowerShell 5.1 envolvería como error (stderr).
        docker logs --tail 15 $c 2>&1 | ForEach-Object { "$_" }
    }
    Write-Host ""
    Write-Host "Para seguir uno: .\hack.ps1 base logs <contenedor>"
}

# ---------------------------------------------------------------------
# Registro de instancias (instances/registry.csv)
# ---------------------------------------------------------------------
function Initialize-Registry {
    if (-not (Test-Path $InstDir)) { New-Item -ItemType Directory -Path $InstDir -ErrorAction Stop | Out-Null }
    if (-not (Test-Path $Registry)) { [IO.File]::WriteAllText($Registry, "$RegistryHeader`n", $Utf8NoBom) }
}

function Get-RegistryRows {
    if (-not (Test-Path $Registry)) { return @() }
    $rows = @()
    foreach ($line in (Get-Content $Registry | Select-Object -Skip 1)) {
        if (-not $line.Trim()) { continue }
        $f = $line.Trim().Split(",")
        $rows += [pscustomobject]@{ Name = $f[0]; Kind = $f[1]; Role = $f[2]; HttpPort = [int]$f[3]; DbPort = [int]$f[4]; Created = $f[5] }
    }
    return $rows
}

function Get-Instance([string]$Name) {
    return (Get-RegistryRows | Where-Object { $_.Name -eq $Name } | Select-Object -First 1)
}

function Remove-RegistryRow([string]$Name) {
    if (-not (Test-Path $Registry)) { return }
    $lines = @($RegistryHeader)
    foreach ($r in (Get-RegistryRows | Where-Object { $_.Name -ne $Name })) {
        $lines += "$($r.Name),$($r.Kind),$($r.Role),$($r.HttpPort),$($r.DbPort),$($r.Created)"
    }
    [IO.File]::WriteAllText($Registry, (($lines -join "`n") + "`n"), $Utf8NoBom)
}

function Read-InstanceEnv([string]$Name) {
    $f = Join-Path $InstDir "$Name/instance.env"
    if (-not (Test-Path $f)) { Die "No existe la instancia '$Name' (falta $f). Mira: .\hack.ps1 list" }
    $vars = [ordered]@{}
    foreach ($line in (Get-Content $f)) {
        if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
        $k, $v = $line.Split("=", 2)
        $vars[$k.Trim()] = $v.Trim()
    }
    return $vars
}

# Compose da prioridad al entorno: las variables de la instancia van como variables de entorno.
function Invoke-InstanceCompose([string]$Name, [string[]]$Rest) {
    $vars = Read-InstanceEnv $Name
    $saved = @{}
    foreach ($k in $vars.Keys) {
        $saved[$k] = [Environment]::GetEnvironmentVariable($k)
        [Environment]::SetEnvironmentVariable($k, $vars[$k])
    }
    try {
        # Sin valor de retorno (la salida de docker va a pantalla): mira $LASTEXITCODE después.
        $composeArgs = @("compose", "-p", "hack-$Name", "--env-file", $Versions, "-f", "deployment/hack/docker-compose.$($vars['KIND']).yaml") + $Rest
        & docker @composeArgs
    } finally {
        foreach ($k in $saved.Keys) { [Environment]::SetEnvironmentVariable($k, $saved[$k]) }
    }
}

# ---------------------------------------------------------------------
# Puertos libres
# ---------------------------------------------------------------------
function Get-UsedPorts {
    $used = @() + $BasePorts
    foreach ($r in Get-RegistryRows) { $used += $r.HttpPort; $used += $r.DbPort }
    foreach ($line in (docker ps --format '{{.Ports}}' 2>$null)) {
        foreach ($m in [regex]::Matches("$line", ':(\d+)->')) { $used += [int]$m.Groups[1].Value }
    }
    return $used
}

function Test-PortBusy([int]$Port) {
    # ¿Algo escucha ya? (conexión a 127.0.0.1)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        if ($client.ConnectAsync("127.0.0.1", $Port).Wait(300)) { return $true }
    } catch { } finally { $client.Close() }
    # ¿Se puede reservar? (también detecta los rangos excluidos de Hyper-V/WinNAT)
    $listener = $null
    try {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Any, $Port)
        $listener.Start()
        return $false
    } catch {
        return $true
    } finally {
        if ($listener) { $listener.Stop() }
    }
}

function Find-FreePort([string]$Range, [int[]]$Exclude = @()) {
    $lo, $hi = $Range.Split("-") | ForEach-Object { [int]$_ }
    $used = (Get-UsedPorts) + $Exclude
    for ($p = $lo; $p -le $hi; $p++) {
        if ($used -contains $p) { continue }
        if (Test-PortBusy $p) { continue }
        return $p
    }
    Die "No hay puertos libres en el rango $Range"
}

# ---------------------------------------------------------------------
# Instancias
# ---------------------------------------------------------------------
function Test-ContainerExists([string]$Name) {
    docker container inspect $Name *> $null
    return ($LASTEXITCODE -eq 0)
}

function Assert-NewName([string]$Name) {
    if ($Name -cnotmatch '^[a-z][a-z0-9-]{1,30}$') {
        Die "Nombre '$Name' no válido: minúsculas, números y guiones, empezando por letra (2-31 caracteres)."
    }
    if ($ReservedNames -contains $Name) { Die "'$Name' está reservado para el mini base." }
    if ((Get-Instance $Name) -or (Test-Path (Join-Path $InstDir $Name))) { Die "Ya existe una instancia '$Name'. Mira: .\hack.ps1 list" }
    if (Test-ContainerExists $Name) { Die "Ya hay un contenedor llamado '$Name' en Docker." }
}

function New-RandomName([string]$Prefix) {
    $chars = "abcdefghijklmnopqrstuvwxyz0123456789".ToCharArray()
    while ($true) {
        $n = "$Prefix-" + (-join (1..4 | ForEach-Object { $chars | Get-Random }))
        if (-not (Get-Instance $n) -and -not (Test-Path (Join-Path $InstDir $n))) { return $n }
    }
}

function Read-Text([string]$RelPath) { return [IO.File]::ReadAllText((Join-Path $Root $RelPath)) }
function Write-Text([string]$Path, [string]$Text) { [IO.File]::WriteAllText($Path, $Text, $Utf8NoBom) }

# Copia los secretos de ejemplo de un rol del mini (claves/cert PEM, db, wallet).
# El setup de cada servicio genera los *.json.example de claves a partir de los PEM.
function Copy-Vault([string]$FromRole, [string]$To) {
    $from = Join-Path $Root "vault/$FromRole"
    foreach ($d in @("config", "secrets", "data")) { New-Item -ItemType Directory -Force -Path (Join-Path $To $d) -ErrorAction Stop | Out-Null }
    Copy-Item (Join-Path $from "config/*.example") (Join-Path $To "config") -ErrorAction Stop
    foreach ($f in @("db.json", "wallet.json", "private_key.pem", "public_key.pem", "cert.pem")) {
        Copy-Item (Join-Path $from "secrets/$f.example") (Join-Path $To "secrets/$f.example") -ErrorAction Stop
    }
    # pwsh en Linux/macOS: los contenedores corren como uid 10001 y escriben en secrets/.
    if ($IsLinux -or $IsMacOS) { chmod -R a+rwX $To }
}

function Write-Instance([string]$Name, [string]$Kind, [string]$Role, [int]$Http, [int]$Db, [string]$RedisPassword = "") {
    $lines = @("INSTANCE=$Name", "KIND=$Kind", "ROLE=$Role", "HTTP_PORT=$Http", "DB_PORT=$Db")
    if ($RedisPassword) { $lines += "REDIS_PASSWORD=$RedisPassword" }
    Write-Text (Join-Path $InstDir "$Name/instance.env") (($lines -join "`n") + "`n")
    Initialize-Registry
    $created = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    [IO.File]::AppendAllText($Registry, "$Name,$Kind,$Role,$Http,$Db,$created`n", $Utf8NoBom)
}

function Show-Instance([string]$Name) {
    $i = Get-Instance $Name
    Write-Host ""
    if ($i.Kind -eq "connector") {
        Write-Host "Conector '$Name' ($($i.Role)):" -ForegroundColor Green
        Write-Host "  Consola     http://localhost:$($i.HttpPort)/admin/login   (eunomia / eunomia)"
    } else {
        Write-Host "Autoridad '$Name' ($($i.Role)):" -ForegroundColor Green
        Write-Host "  Consola     http://localhost:$($i.HttpPort)/admin/home"
    }
    Write-Host "  API         http://localhost:$($i.HttpPort)/api/v1"
    Write-Host "  DID         did:web:host.docker.internal%3A$($i.HttpPort)"
    Write-Host "  Contenedores: http://host.docker.internal:$($i.HttpPort)"
    Write-Host "  Postgres    localhost:$($i.DbPort)"
    Write-Host "  Logs        .\hack.ps1 logs $Name"
}

function Wait-Instance([string]$Name) {
    $i = Get-Instance $Name
    Step "Esperando a que '$Name' esté sano"
    $okWallet = Wait-Healthy "$Name-wallet"
    $okMain = Wait-Healthy $Name
    if (-not ($okWallet -and $okMain)) { Die "'$Name' no está sano. Mira: .\hack.ps1 logs $Name" }
    if ($i.Kind -eq "connector") { Test-Http "http://localhost:$($i.HttpPort)/.well-known/dspace-version" } else { Test-Http "http://localhost:$($i.HttpPort)/readiness" }
    Ok "'$Name' listo"
}

# Parser mínimo de opciones estilo "--role x --onboard nombre".
function Read-Options([string[]]$ArgList, [string[]]$ValueOpts, [string[]]$FlagOpts) {
    $opts = @{ _pos = @() }
    for ($k = 0; $k -lt $ArgList.Count; $k++) {
        $a = $ArgList[$k]
        if ($ValueOpts -contains $a) {
            if ($k + 1 -ge $ArgList.Count) { Die "$a necesita valor" }
            $opts[$a] = $ArgList[$k + 1]; $k++
        } elseif ($FlagOpts -contains $a) {
            $opts[$a] = $true
        } elseif ($a.StartsWith("-")) {
            Die "Opción desconocida: $a"
        } else {
            $opts._pos += $a
        }
    }
    return $opts
}

function Add-Connector([string[]]$ArgList) {
    $o = Read-Options $ArgList @("--role", "--authority") @("--onboard")
    if ($o._pos.Count -gt 1) { Die "Sobra el argumento '$($o._pos[1])'" }
    $role = if ($o["--role"]) { $o["--role"] } else { "consumer" }
    if (@("consumer", "provider") -notcontains $role) { Die "--role debe ser consumer o provider" }
    $authority = if ($o["--authority"]) { $o["--authority"] } else { "authority" }
    $onboard = [bool]($o["--onboard"] -or $o["--authority"])
    Test-Requirements
    Initialize-Registry
    $name = if ($o._pos.Count -eq 1) { $o._pos[0] } else { New-RandomName "conn" }
    Assert-NewName $name
    if ($onboard) { Resolve-Port $authority | Out-Null }

    $http = Find-FreePort $HttpPortRange
    $db = Find-FreePort $DbPortRange @($http)
    $dir = Join-Path $InstDir $name
    Step "Creando conector '$name' ($role) en instances/$name — HTTP $http, Postgres $db"
    New-Item -ItemType Directory -Force -Path (Join-Path $dir "config") -ErrorAction Stop | Out-Null

    # Configuración generada desde las plantillas de main (static/config).
    $basePort = if ($role -eq "consumer") { 1100 } else { 1200 }
    $cfg = Read-Text "static/config/$role/mini/mini.$role.yaml"
    $cfg = $cfg.Replace("'$basePort'", "'$http'").Replace("$role-fafnir-wallet", "$name-wallet")
    $cfg = $cfg.Replace("$role-redis", "$name-redis").Replace("$role-db", "$name-db")
    Write-Text (Join-Path $dir "config/agent.yaml") $cfg
    Write-Text (Join-Path $dir "config/fafnir.yaml") ((Read-Text "static/config/fafnir/$role.yaml").Replace("$role-db", "$name-db"))
    Copy-Vault $role (Join-Path $dir "vault")
    Write-Instance $name "connector" $role $http $db "ds_core_${role}_redis"

    Step "Levantando (proyecto hack-$name)"
    Invoke-InstanceCompose $name @("up", "-d")
    if ($LASTEXITCODE -ne 0) { Die "Fallo al levantar '$name'. Mira: .\hack.ps1 logs $name  (o .\hack.ps1 rm $name)" }
    Wait-Instance $name
    Show-Instance $name
    if ($onboard) {
        Invoke-OnboardConnector $name $authority
    } else {
        Write-Host ""
        Write-Host "Para registrarlo en la autoridad del mini base: .\hack.ps1 onboard $name"
    }
}

function Add-Authority([string[]]$ArgList) {
    $o = Read-Options $ArgList @("--role") @()
    if ($o._pos.Count -gt 1) { Die "Sobra el argumento '$($o._pos[1])'" }
    $role = if ($o["--role"]) { $o["--role"] } else { "eco" }
    switch ($role) {
        "eco" { $tmpl = "static/config/heimdall/mini/mini_eco_authority.yaml" }
        "dataspace" { $tmpl = "static/config/heimdall/mini/mini_dataspace_authority.yaml" }
        default { Die "--role debe ser eco o dataspace" }
    }
    Test-Requirements
    Initialize-Registry
    $name = if ($o._pos.Count -eq 1) { $o._pos[0] } else { New-RandomName "auth" }
    Assert-NewName $name

    $http = Find-FreePort $HttpPortRange
    $db = Find-FreePort $DbPortRange @($http)
    $dir = Join-Path $InstDir $name
    Step "Creando autoridad '$name' ($role) en instances/$name — HTTP $http, Postgres $db"
    New-Item -ItemType Directory -Force -Path (Join-Path $dir "config") -ErrorAction Stop | Out-Null
    $cfg = Read-Text $tmpl
    $cfg = $cfg.Replace("'1500'", "'$http'").Replace("'heimdall-db'", "'$name-db'").Replace("'fafnir-wallet'", "'$name-wallet'")
    Write-Text (Join-Path $dir "config/authority.yaml") $cfg
    Write-Text (Join-Path $dir "config/fafnir.yaml") ((Read-Text "static/config/fafnir/heimdall.yaml").Replace("heimdall-db", "$name-db"))
    Copy-Vault "heimdall" (Join-Path $dir "vault")
    Write-Instance $name "authority" $role $http $db

    Step "Levantando (proyecto hack-$name)"
    Invoke-InstanceCompose $name @("up", "-d")
    if ($LASTEXITCODE -ne 0) { Die "Fallo al levantar '$name'. Mira: .\hack.ps1 logs $name  (o .\hack.ps1 rm $name)" }
    Wait-Instance $name
    Show-Instance $name
    Write-Host ""
    Write-Host "Registra un conector en ella: .\hack.ps1 onboard <conector> --authority $name"
}

function Assert-Instance([string]$Name) {
    if (-not (Get-Instance $Name)) { Die "No existe la instancia '$Name'. Mira: .\hack.ps1 list" }
}

# Puerto HTTP de una entidad: nombres del mini base o instancia registrada.
function Resolve-Port([string]$Name) {
    switch ($Name) {
        "consumer" { return 1100 }
        "provider" { return 1200 }
        "authority" { return 1500 }
        "heimdall" { return 1500 }
    }
    Assert-Instance $Name
    return (Get-Instance $Name).HttpPort
}

function Resolve-Kind([string]$Name) {
    if (@("consumer", "provider") -contains $Name) { return "connector" }
    if (@("authority", "heimdall") -contains $Name) { return "authority" }
    $i = Get-Instance $Name
    if ($i) { return $i.Kind }
    return ""
}

# Ejecuta un script de scripts/ (o deployment/hack/tools/) en el contenedor de herramientas.
function Invoke-Tool([string[]]$EnvPairs, [string]$Script, [string]$ScriptArg = "") {
    Step "Preparando contenedor de herramientas (bash + curl + jq)"
    docker build -q -f deployment/hack/tools.Dockerfile -t $ToolsImage . | Out-Null
    if ($LASTEXITCODE -ne 0) { Die "No pude construir $ToolsImage" }
    $runArgs = @("run", "--rm", "--add-host", "host.docker.internal:host-gateway")
    foreach ($e in $EnvPairs) { $runArgs += @("-e", $e) }
    $runArgs += @($ToolsImage, "bash", "/scripts/$Script")
    if ($ScriptArg) { $runArgs += $ScriptArg }
    # Sin valor de retorno (la salida va a pantalla): mira $LASTEXITCODE después.
    & docker @runArgs
}

function Invoke-OnboardConnector([string]$Name, [string]$Authority = "authority") {
    if ((Resolve-Kind $Name) -ne "connector") { Die "'$Name' no es un conector" }
    if ((Resolve-Kind $Authority) -ne "authority") { Die "'$Authority' no es una autoridad" }
    $cport = Resolve-Port $Name
    $aport = Resolve-Port $Authority
    Step "Onboarding de '$Name' (puerto $cport) en la autoridad '$Authority' (puerto $aport)"
    Invoke-Tool @(
        "AUTHORITY_URL=http://host.docker.internal:$aport",
        "DOCKER_AUTHORITY_URL=http://host.docker.internal:$aport",
        "PARTICIPANT_URL=http://host.docker.internal:$cport",
        "PARTICIPANT_SLUG=$Name"
    ) "hack-onboard.sh"
    if ($LASTEXITCODE -ne 0) { Die "Onboarding fallido. Mira: .\hack.ps1 logs $Name  y  .\hack.ps1 logs $Authority" }
    Ok "'$Name' registrado en '$Authority'"
}

function Invoke-Onboard([string[]]$ArgList) {
    $o = Read-Options $ArgList @("--authority") @()
    if ($o._pos.Count -ne 1) { Die "Uso: .\hack.ps1 onboard <conector> [--authority <aut>]" }
    $authority = if ($o["--authority"]) { $o["--authority"] } else { "authority" }
    Test-Requirements
    Invoke-OnboardConnector $o._pos[0] $authority
}

function Invoke-Connect([string[]]$ArgList) {
    if ($ArgList.Count -ne 2) { Die "Uso: .\hack.ps1 connect <consumer> <provider>" }
    Test-Requirements
    $consumer, $provider = $ArgList
    if ((Resolve-Kind $consumer) -ne "connector") { Die "'$consumer' no es un conector" }
    if ((Resolve-Kind $provider) -ne "connector") { Die "'$provider' no es un conector" }
    $cport = Resolve-Port $consumer
    $pport = Resolve-Port $provider
    Step "'$consumer' (puerto $cport) se autentica en '$provider' (puerto $pport)"
    Invoke-Tool @(
        "CONSUMER_URL=http://host.docker.internal:$cport",
        "PROVIDER_URL=http://host.docker.internal:$pport",
        "DOCKER_PROVIDER_URL=http://host.docker.internal:$pport",
        "PROVIDER_SLUG=$provider"
    ) "hack-connect.sh"
    if ($LASTEXITCODE -ne 0) { Die "Autenticación fallida. Mira: .\hack.ps1 logs $consumer  y  .\hack.ps1 logs $provider" }
    Ok "'$consumer' autenticado en '$provider'"
}

function Get-EntityEnv([int]$Consumer, [int]$Provider, [int]$Authority) {
    return @(
        "CONSUMER_URL=http://host.docker.internal:$Consumer", "DOCKER_CONSUMER_URL=http://host.docker.internal:$Consumer",
        "PROVIDER_URL=http://host.docker.internal:$Provider", "DOCKER_PROVIDER_URL=http://host.docker.internal:$Provider",
        "AUTHORITY_URL=http://host.docker.internal:$Authority", "DOCKER_AUTHORITY_URL=http://host.docker.internal:$Authority"
    )
}

function Invoke-Gaia([string[]]$ArgList) {
    $o = Read-Options $ArgList @("--consumer", "--provider", "--authority") @()
    if ($o._pos.Count -gt 0) { Die "Opción desconocida: $($o._pos[0])" }
    Test-Requirements
    $c = Resolve-Port $(if ($o["--consumer"]) { $o["--consumer"] } else { "consumer" })
    $p = Resolve-Port $(if ($o["--provider"]) { $o["--provider"] } else { "provider" })
    $a = Resolve-Port $(if ($o["--authority"]) { $o["--authority"] } else { "authority" })
    Invoke-Tool (Get-EntityEnv $c $p $a) "hack-verify-connection.sh" "gaia.sh"
    if ($LASTEXITCODE -ne 0) { Die "Flujo Gaia fallido (ver arriba)." }
}

function Invoke-BaseOnboard {
    Test-Requirements
    Invoke-Tool (Get-EntityEnv 1100 1200 1500) "hack-verify-connection.sh" "mini-onboarding.sh"
    if ($LASTEXITCODE -ne 0) { Die "Onboarding fallido (ver arriba)." }
}

function Get-StateText([string]$Name) {
    $s = docker container inspect -f '{{.State.Status}}{{if .State.Health}} ({{.State.Health.Status}}){{end}}' $Name 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $s) { return "no creado" }
    return "$s".Trim()
}

function Invoke-List {
    Test-Requirements
    Initialize-Registry
    $fmt = "{0,-20} {1,-10} {2,-10} {3,-6} {4,-6} {5}"
    Write-Host ($fmt -f "NOMBRE", "TIPO", "ROL", "HTTP", "PG", "ESTADO")
    $rows = @(Get-RegistryRows)
    foreach ($r in $rows) {
        Write-Host ($fmt -f $r.Name, $r.Kind, $r.Role, $r.HttpPort, $r.DbPort, (Get-StateText $r.Name))
    }
    if ($rows.Count -eq 0) { Write-Host "(sin instancias; crea una con .\hack.ps1 connector add o .\hack.ps1 authority add)" }
    Write-Host ""
    Write-Host "Mini base: heimdall $(Get-StateText heimdall), provider $(Get-StateText provider), consumer $(Get-StateText consumer)"
}

function Invoke-Status([string[]]$ArgList) {
    if ($ArgList.Count -eq 0) {
        Invoke-BaseStatus
        Write-Host ""
        Invoke-List
        return
    }
    Test-Requirements
    Assert-Instance $ArgList[0]
    Invoke-InstanceCompose $ArgList[0] @("ps", "-a", "--format", 'table {{.Name}}\t{{.Status}}\t{{.Ports}}')
    Show-Instance $ArgList[0]
}

function Invoke-Logs([string[]]$ArgList) {
    if ($ArgList.Count -lt 1) { Die "Uso: .\hack.ps1 logs <instancia|contenedor> [servicio]" }
    Test-Requirements
    $name = $ArgList[0]
    $rest = @($ArgList | Select-Object -Skip 1)
    if (Get-Instance $name) {
        Invoke-InstanceCompose $name (@("logs", "-f", "--tail", "200") + $rest)
    } elseif (Test-ContainerExists $name) {
        docker logs -f --tail 200 $name
    } else {
        Die "No conozco '$name' (ni instancia ni contenedor). Mira: .\hack.ps1 list"
    }
}

function Invoke-Stop([string[]]$ArgList) {
    if ($ArgList.Count -ne 1) { Die "Uso: .\hack.ps1 stop <nombre>" }
    if ($ArgList[0] -eq "base") { Invoke-BaseStop; return }
    Test-Requirements
    Assert-Instance $ArgList[0]
    Invoke-InstanceCompose $ArgList[0] @("stop")
    Ok "'$($ArgList[0])' parado (datos conservados). Vuelve con: .\hack.ps1 start $($ArgList[0])"
}

function Invoke-Start([string[]]$ArgList) {
    if ($ArgList.Count -ne 1) { Die "Uso: .\hack.ps1 start <nombre>" }
    if ($ArgList[0] -eq "base") { Invoke-BaseUp; return }
    Test-Requirements
    Assert-Instance $ArgList[0]
    Invoke-InstanceCompose $ArgList[0] @("up", "-d")
    if ($LASTEXITCODE -ne 0) { Die "Fallo al arrancar '$($ArgList[0])'. Mira: .\hack.ps1 logs $($ArgList[0])" }
    Wait-Instance $ArgList[0]
    Show-Instance $ArgList[0]
}

function Invoke-Rm([string[]]$ArgList) {
    $o = Read-Options $ArgList @() @("-y", "--yes")
    if ($o._pos.Count -ne 1) { Die "Uso: .\hack.ps1 rm <nombre> [-y]" }
    $name = $o._pos[0]
    $yes = if ($o["-y"] -or $o["--yes"]) { "-y" } else { "" }
    Test-Requirements
    $dir = Join-Path $InstDir $name
    if (-not (Get-Instance $name) -and -not (Test-Path $dir)) { Die "No existe la instancia '$name'. Mira: .\hack.ps1 list" }
    Confirm-Action "Se borrarán los contenedores, volúmenes y la configuración de '$name'. ¿Seguro?" $yes
    if (Test-Path (Join-Path $dir "instance.env")) {
        Invoke-InstanceCompose $name @("down", "-v", "--remove-orphans")
        if ($LASTEXITCODE -ne 0) { Warn "docker compose down falló; sigo limpiando" }
    }
    if (Test-Path $dir) { Remove-Item -Recurse -Force $dir -ErrorAction Stop }
    Remove-RegistryRow $name
    Ok "'$name' borrado"
}

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
function Invoke-Main([string[]]$ArgList) {
    if ($ArgList.Count -eq 0) { Show-Usage; return }
    $cmd = $ArgList[0]
    $rest = @($ArgList | Select-Object -Skip 1)
    switch ($cmd) {
        "base" {
            $sub = if ($rest.Count -gt 0) { $rest[0] } else { "" }
            $subRest = @($rest | Select-Object -Skip 1)
            $yes = if ($subRest.Count -gt 0) { $subRest[0] } else { "" }
            switch ($sub) {
                "up" { Invoke-BaseUp }
                "stop" { Invoke-BaseStop }
                "down" { Confirm-Action "Se borrará el mini base con sus volúmenes. ¿Seguro?" $yes; Invoke-BaseDown }
                "reset" { Confirm-Action "Se borrará el mini base con sus volúmenes y se levantará de cero. ¿Seguro?" $yes; Invoke-BaseDown; Invoke-BaseUp }
                "status" { Invoke-BaseStatus }
                "logs" { Invoke-BaseLogs $subRest }
                "onboard" { Invoke-BaseOnboard }
                default { Die "Uso: .\hack.ps1 base up|stop|down|reset|status|logs|onboard" }
            }
        }
        "connector" {
            if ($rest.Count -lt 1 -or $rest[0] -ne "add") { Die "Uso: .\hack.ps1 connector add [nombre] [--role consumer|provider] [--onboard] [--authority <aut>]" }
            Add-Connector @($rest | Select-Object -Skip 1)
        }
        "authority" {
            if ($rest.Count -lt 1 -or $rest[0] -ne "add") { Die "Uso: .\hack.ps1 authority add [nombre] [--role eco|dataspace]" }
            Add-Authority @($rest | Select-Object -Skip 1)
        }
        "onboard" { Invoke-Onboard $rest }
        "connect" { Invoke-Connect $rest }
        "gaia" { Invoke-Gaia $rest }
        { $_ -in @("list", "ls") } { Invoke-List }
        "status" { Invoke-Status $rest }
        "logs" { Invoke-Logs $rest }
        "stop" { Invoke-Stop $rest }
        "start" { Invoke-Start $rest }
        { $_ -in @("rm", "remove", "delete") } { Invoke-Rm $rest }
        "check" { Invoke-Check }
        { $_ -in @("help", "-h", "--help") } { Show-Usage }
        default { Show-Usage; Die "Comando desconocido: $cmd" }
    }
}

# Las rutas que se pasan a docker son relativas a la raíz del repo.
$exitCode = 0
Push-Location $Root
try {
    Invoke-Main @($args)
} catch {
    $msg = "$($_.Exception.Message)"
    if ($msg.StartsWith("HACK:")) {
        Write-Host "ERROR: $($msg.Substring(5))" -ForegroundColor Red
    } else {
        Write-Host "ERROR inesperado: $msg" -ForegroundColor Red
        Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray
    }
    $exitCode = 1
} finally {
    Pop-Location
}
exit $exitCode
