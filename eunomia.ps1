# Run the eunomia CLI from this checkout on Windows: .\eunomia.cmd <command>
# (eunomia.cmd calls this script without depending on the ExecutionPolicy).
#
# With Python 3.8+ on the machine it runs directly. Without it, or with
# EUNOMIA_CONTAINER=1, it runs inside a small container (deployment/tools)
# that only needs Docker Desktop.
# Not "Stop": Windows PowerShell 5.1 turns any stderr line of a native command
# into an error then. Failures are checked through $LASTEXITCODE instead.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Find-Python {
    foreach ($candidate in @(@("py", "-3"), @("python3"), @("python"))) {
        $exe = $candidate[0]
        if (Get-Command $exe -ErrorAction SilentlyContinue) {
            $checkArgs = @($candidate | Select-Object -Skip 1) + @("-c", "import sys; sys.exit(sys.version_info < (3, 8))")
            & $exe @checkArgs 2>$null
            if ($LASTEXITCODE -eq 0) { return ,$candidate }
        }
    }
    return $null
}

if (-not $env:EUNOMIA_CONTAINER) {
    $python = Find-Python
    if ($python) {
        $env:PYTHONPATH = Join-Path $Root "cli"
        $exe = $python[0]
        $pyArgs = @($python | Select-Object -Skip 1) + @("-m", "eunomia") + $args
        & $exe @pyArgs
        exit $LASTEXITCODE
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "eunomia needs Python 3.8+ or Docker Desktop. Install Docker Desktop and retry." -ForegroundColor Red
    exit 1
}
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker is installed but not answering. Start Docker Desktop, wait until it is running, and retry." -ForegroundColor Red
    exit 1
}

$Image = "eunomia-tools:1"
docker image inspect $Image *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Building $Image, the container that runs the CLI (first time only)..."
    docker build -q -t $Image (Join-Path $Root "deployment\tools") | Out-Null
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

# The compose files bind-mount paths under the checkout, and Docker Desktop
# resolves bind mounts in its own VM, where C:\Users\me\repo is
# /run/desktop/mnt/host/c/Users/me/repo. The checkout is mounted at that path
# inside the container too, so the paths the CLI passes on are valid there.
$drive = $Root.Substring(0, 1).ToLower()
$hostPath = "/run/desktop/mnt/host/$drive" + ($Root.Substring(2) -replace "\\", "/")

$dockerArgs = @("run", "--rm", "-i")
if (-not [Console]::IsInputRedirected -and -not [Console]::IsOutputRedirected) { $dockerArgs += "-t" }
if ($args.Count -gt 0 -and @("e2e", "demo") -contains $args[0]) {
    $sink = if ($env:EUNOMIA_SINK_PORT) { $env:EUNOMIA_SINK_PORT } else { "1290" }
    $dockerArgs += @("-p", "${sink}:${sink}", "-e", "EUNOMIA_SINK_PORT=$sink")
}
$dockerArgs += @(
    "-v", "//var/run/docker.sock:/var/run/docker.sock",
    "-v", "${Root}:${hostPath}", "-w", $hostPath,
    "--add-host", "host.docker.internal:host-gateway",
    "-e", "EUNOMIA_HOST=host.docker.internal",
    "-e", "PYTHONPATH=$hostPath/cli",
    $Image, "python3", "-m", "eunomia"
) + $args

& docker @dockerArgs
exit $LASTEXITCODE
