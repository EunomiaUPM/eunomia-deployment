"""Check this machine can run the deployment, and say what to fix when not."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys

from .. import compose, log, settings
from . import images as images_cmd


class Report:
    def __init__(self) -> None:
        self.problems = 0

    def ok(self, msg: str) -> None:
        log.ok(f"  ok    {msg}")

    def bad(self, msg: str, fix: str) -> None:
        self.problems += 1
        log.fail(f"  FAIL  {msg}\n        {fix}")

    def warn(self, msg: str) -> None:
        log.info(f"  warn  {msg}")


def _docker(r: Report) -> bool:
    if shutil.which("docker") is None:
        r.bad("docker not found", "Install Docker Desktop (Windows, macOS) or Docker Engine (Linux).")
        return False
    info = subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"], capture_output=True, text=True)
    if info.returncode != 0:
        r.bad("Docker is installed but not answering", "Start Docker Desktop (or the docker service) and wait until it is running.")
        return False
    r.ok(f"Docker {info.stdout.strip()} is running")

    res = subprocess.run(["docker", "compose", "version", "--short"], capture_output=True, text=True)
    version = res.stdout.strip().lstrip("v")
    major = re.match(r"(\d+)", version)
    if res.returncode != 0 or not major:
        r.bad("Docker Compose v2 not found", "Update Docker, or install the docker-compose-plugin package ('docker compose', not 'docker-compose').")
        return False
    if int(major.group(1)) < 2:
        r.bad(f"Docker Compose {version} is too old", "Version 2 or later is needed.")
        return False
    r.ok(f"Docker Compose {version}")
    return True


def _python(r: Report) -> None:
    v = sys.version_info
    if v < (3, 8):
        r.bad(f"Python {v.major}.{v.minor}", "Python 3.8 or later is needed, or let ./eunomia run the CLI in its container: see the Requirements page of the docs")
    else:
        r.ok(f"Python {v.major}.{v.minor}.{v.micro}")


def _versions(r: Report) -> None:
    try:
        pins = settings.versions()
    except log.Abort:
        r.problems += 1
        return
    missing = [k for k in ("EUNOMIA_IMAGE", "EUNOMIA_TAG", "HEIMDALL_IMAGE", "HEIMDALL_TAG", "FAFNIR_IMAGE", "FAFNIR_TAG") if not pins.get(k)]
    if missing:
        r.bad(f"versions.env lacks {', '.join(missing)}", "Restore it from git: git checkout versions.env")
    else:
        r.ok(
            f"versions.env: ds-agent {pins['EUNOMIA_TAG']}, heimdall {pins['HEIMDALL_TAG']}, fafnir {pins['FAFNIR_TAG']}"
        )


def _ports(r: Report) -> None:
    demo_ports = list(settings.demo_ports())
    busy = compose.busy_ports(demo_ports)
    demo_up = compose.run(["docker", "ps", "-q", "--filter", f"name=^/{settings.container_prefix()}factory-"], capture=True, check=False).strip()
    if not busy:
        r.ok(f"Demo factory ports free: {', '.join(map(str, demo_ports))}")
    elif demo_up:
        r.ok("Demo factory ports in use by the demo factory itself")
    else:
        r.bad(
            f"Demo factory ports {', '.join(map(str, busy))} are in use by another program",
            "Free them, or move them in .env (EUNOMIA_FACTORY_*_PORT, see .env.example).",
        )
    for label, (lo, hi) in (("HTTP", settings.http_ports()), ("Postgres", settings.db_ports())):
        sample = list(range(lo, min(hi, lo + 40) + 1))
        free = [p for p in sample if not compose.port_in_use(p)]
        if free:
            r.ok(f"{label} ports for instances: {lo}-{hi}, free ones available")
        else:
            r.bad(f"No free {label} port at the start of {lo}-{hi}", f"Set EUNOMIA_{label.upper() if label == 'HTTP' else 'DB'}_PORTS to another range in .env.")


def _images(r: Report) -> None:
    for ref in sorted(images_cmd.pinned()):
        res = subprocess.run(["docker", "manifest", "inspect", ref], capture_output=True, text=True)
        if res.returncode == 0:
            r.ok(f"image {ref}")
        else:
            r.bad(f"image {ref} cannot be pulled", (res.stderr.strip().splitlines() or ["check your connection"])[-1])


def run(check_images: bool) -> int:
    r = Report()
    log.step("Checking this machine")
    if _docker(r):
        _ports(r)
        if check_images:
            _images(r)
        else:
            log.info("  ...   registries not queried (add --images to check every image can be pulled)")
    _python(r)
    _versions(r)
    if r.problems:
        log.fail(f"\n{r.problems} problem(s) found. Fix them and run eunomia doctor again.")
        return 1
    log.ok("\nAll good. Start with: eunomia authority add <name>")
    return 0
