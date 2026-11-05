"""docker compose and host-level helpers."""

from __future__ import annotations

import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from . import http, log, settings
from .settings import REPO_ROOT, Stack


def require(binary: str, hint: str = "") -> None:
    if shutil.which(binary) is None:
        raise log.fail(f"{binary} not found in PATH. {hint}".rstrip())


def require_docker() -> None:
    require("docker", "Install Docker Desktop (Windows, macOS) or Docker Engine (Linux).")
    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        raise log.fail("Docker is installed but not answering. Start Docker Desktop (or the docker service) and retry.")


def run(
    cmd: Sequence[str],
    dry_run: bool = False,
    capture: bool = False,
    check: bool = True,
    env: Optional[Dict[str, str]] = None,
) -> str:
    """Run a command from the repo root. With dry_run, only print it."""
    if dry_run:
        log.info("  would run: " + " ".join(cmd))
        return ""
    res = subprocess.run(
        list(cmd),
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        env=env,
    )
    if check and res.returncode != 0:
        detail = f"\n{res.stderr.strip()}" if capture and res.stderr else ""
        raise log.fail(f"command failed ({res.returncode}): {' '.join(cmd)}{detail}")
    return res.stdout or ""


def compose_files_cmd(files: Sequence[Path], *args: str, project: Optional[str] = None) -> List[str]:
    # versions.env goes to every compose file: the images are pinned there.
    cmd = ["docker", "compose", "--env-file", str(settings.VERSIONS_FILE)]
    if project:
        cmd += ["-p", project]
    for f in files:
        cmd += ["-f", str(f)]
    return cmd + list(args)


def compose_cmd(stack: Stack, *args: str) -> List[str]:
    return compose_files_cmd([stack.compose], *args)


def compose(stack: Stack, *args: str, dry_run: bool = False, capture: bool = False, check: bool = True) -> str:
    return run(compose_cmd(stack, *args), dry_run=dry_run, capture=capture, check=check)


# ---------------------------------------------------------------------------
# Ports
# ---------------------------------------------------------------------------


def port_in_use(port: int, host: Optional[str] = None) -> bool:
    """Whether something accepts TCP connections on the port.

    A connect attempt rather than lsof: it works the same on Windows and from
    inside the tools container (where the host is host.docker.internal).
    """
    hosts = [host] if host else [settings.local_host()]
    if not host and hosts[0] == "127.0.0.1":
        hosts.append("::1")
    for h in hosts:
        try:
            with socket.create_connection((h, port), timeout=0.5):
                return True
        except OSError:
            continue
    return False


def busy_ports(ports: Iterable[int]) -> List[int]:
    return [p for p in ports if port_in_use(p)]


def listeners(port: int) -> List[str]:
    """`lsof` lines for whatever listens on a TCP port, header excluded.

    Empty without a real lsof, and inside the tools container, which cannot
    see the host's processes anyway. busybox lsof (Alpine) ignores its
    arguments and lists every open file: no COMMAND header tells it apart.
    """
    if shutil.which("lsof") is None or settings.local_host() != "127.0.0.1":
        return []
    res = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"], text=True, capture_output=True)
    lines = res.stdout.splitlines()
    if not lines or not lines[0].startswith("COMMAND"):
        return []
    return [line for line in lines[1:] if line.strip()]


def foreign_listeners(ports: Iterable[int]) -> List[str]:
    """Listeners that are not Docker.

    A native process on the same port silently wins over the container:
    Docker publishes on IPv6 too, a process bound to 127.0.0.1 takes the IPv4
    side, so 127.0.0.1:<port> reaches the stray process while the container
    looks perfectly healthy. Needs lsof; without it nothing is reported.
    """
    found = []
    for port in ports:
        for line in listeners(port):
            command = line.split()[0]
            if not command.startswith("com.docke") and command not in ("docker-pr", "vpnkit", "dockerd"):
                found.append(f"  :{port}  {line}")
    return found


def free_port(lo: int, hi: int, exclude: Iterable[int] = ()) -> int:
    taken = set(exclude)
    for p in range(lo, hi + 1):
        if p not in taken and not port_in_use(p):
            return p
    raise log.fail(f"No free port between {lo} and {hi}")


# ---------------------------------------------------------------------------
# Readiness
# ---------------------------------------------------------------------------


def wait_http(name: str, url: str, timeout: float = 180.0) -> None:
    """Poll a URL until it answers 200, or abort after `timeout` seconds."""
    deadline = time.monotonic() + timeout
    status: Optional[int] = None
    while time.monotonic() < deadline:
        status = http.probe(url)
        if status == 200:
            log.ok(f"{name} is ready")
            return
        time.sleep(2)
    got = f"HTTP {status}" if status else "no answer"
    raise log.fail(f"{name} did not become ready at {url} ({got})")
