"""Restart remote instances on their servers over SSH.

A remote instance knows how to reach its server when it was registered with
`eunomia remote add <name> ... --ssh user@host --path <deployment/prod dir>`.
A password, if the server needs one, comes from the environment:
<NAME>_SSH_PASS (the instance name upper-cased, dashes as underscores); leave
it unset to use SSH keys.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from typing import List, Sequence

from .. import compose, log, settings
from . import instances

# The service and wallet each kind runs in deployment/prod.
SERVICES = {"agent": ("agent", "agent-fafnir-wallet"), "authority": ("heimdall", "heimdall-fafnir-wallet")}


def _remote_script(path: str, compose_file: str, service: str, wallet: str) -> str:
    q = shlex.quote
    # The compose files read the image pins from versions.env at the repo root.
    dc = f"docker compose --env-file ../../versions.env -f {q(compose_file)}"
    # Only the service and its wallet are recreated. The databases have no
    # volume, so recreating them would wipe the instance's state.
    body = (
        f"{dc} pull {q(wallet)} {q(service)}\n"
        f"{dc} up -d --wait --force-recreate --no-deps {q(wallet)} {q(service)}"
    )
    return f"set -e\ncd {q(path)}\n{body}\necho '--- running containers ---'\n{dc} ps\n"


def _password_var(name: str) -> str:
    return name.upper().replace("-", "_") + "_SSH_PASS"


def _ssh_cmd(inst: "instances.Instance") -> List[str]:
    if not (inst.ssh_host and inst.ssh_user and inst.ssh_path):
        raise log.fail(
            f"{inst.name!r} has no SSH access registered. Register it again with\n"
            f"  eunomia remote add {inst.name} --kind {inst.kind} --url {inst.url} --ssh <user>@<host> --path <dir>"
        )
    # accept-new pins the host key on first contact and refuses a changed one,
    # instead of trusting whatever answers like StrictHostKeyChecking=no did.
    ssh = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=10", f"{inst.ssh_user}@{inst.ssh_host}", "bash", "-s"]
    if os.environ.get(_password_var(inst.name)):
        compose.require("sshpass", "Install it (brew install hudochenkov/sshpass/sshpass) or switch to SSH keys.")
        # -e reads SSHPASS from the environment, so the password never shows in ps.
        return ["sshpass", "-e", *ssh]
    return ssh


def restart(names: Sequence[str], dry_run: bool) -> int:
    targets = [instances.get(n) for n in names]
    failed = []
    for inst in targets:
        if inst.local:
            log.info(f"{inst.name} is local: restarting it here")
            if not dry_run:
                instances.stop(inst)
                instances.start(inst)
            continue
        service, wallet = SERVICES[inst.kind]
        compose_file = settings.prod_stacks()[inst.kind].compose.name
        script = _remote_script(inst.ssh_path, compose_file, service, wallet)
        cmd = _ssh_cmd(inst)

        log.step(f"Restarting {inst.name} on {inst.ssh_host}")
        if dry_run:
            log.info("  " + " ".join(cmd))
            print(script, file=sys.stderr)
            continue
        env = {**os.environ, "SSHPASS": os.environ.get(_password_var(inst.name), "")}
        if subprocess.run(cmd, input=script, text=True, env=env).returncode != 0:
            log.warn(f"{inst.name}: remote execution failed")
            failed.append(inst.name)
            continue
        log.ok(f"{inst.name} restarted")

    if failed:
        raise log.fail(f"\nFailed: {', '.join(failed)}")
    return 0
