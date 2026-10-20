"""Check this machine can run the deployment, and say what to fix when not."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from typing import List

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
        r.bad(f"Python {v.major}.{v.minor}", "Python 3.8 or later is needed, or use the container: see docs-internal/getting-started/requirements.md")
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
    ours = compose.run(["docker", "ps", "-q", "--filter", f"name=^/{settings.container_prefix()}"], capture=True, check=False).split()
    ports: List[int] = [p for s in settings.stacks("standalone").values() for p in s.ports]
    busy = compose.busy_ports(ports)
    if not busy:
        r.ok(f"Ports free: {', '.join(map(str, ports))}")
    elif ours:
        r.ok(f"Ports {', '.join(map(str, busy))} in use, the standalone deployment is running")
    else:
        r.bad(
            f"Ports {', '.join(map(str, busy))} are in use by another program",
            "Free them, or move the database and demo ports in .env (see .env.example).",
        )
    foreign = compose.foreign_listeners(ports)
    if foreign:
        r.bad("Processes outside Docker hold deployment ports:\n" + "\n".join(foreign), "Stop them: 127.0.0.1 would reach them instead of the containers.")


def _images(r: Report) -> None:
    for ref in sorted(images_cmd.pinned("standalone")):
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
    log.ok("\nAll good. Start with: eunomia up")
    return 0
