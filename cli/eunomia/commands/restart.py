"""Restart prod participants on their servers over SSH.

Connection settings come from the repo-root .env, one block per node:

  <PREFIX>_SSH_HOST   server to reach                       (required)
  <PREFIX>_SSH_USER   login user                            (required)
  <PREFIX>_SSH_PASS   password; leave empty to use SSH keys (needs sshpass if set)
  <PREFIX>_PATH       directory on the server holding the compose file (required)
  <PREFIX>_COMPOSE    compose file name   (default: the one in deployment/prod)
  <PREFIX>_SERVICE    agent service name  (default: heimdall / provider / consumer)

PREFIX is AUTHORITY, PROVIDER or CONSUMER.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from typing import List, Sequence

from .. import compose, log, settings

PREFIXES = {
    "authority": "AUTHORITY",
    "provider": "PROVIDER",
    "consumer": "CONSUMER",
}


def _var(prefix: str, name: str, default: str = "") -> str:
    value = os.environ.get(f"{prefix}_{name}", default)
    if not value:
        raise log.fail(f"{prefix}_{name} is not set. Add it to .env (see .env.example).")
    return value


def _remote_script(path: str, compose_file: str, service: str, wallet: str) -> str:
    q = shlex.quote
    # The compose files read the image pins from versions.env at the repo root.
    dc = f"docker compose --env-file ../../versions.env -f {q(compose_file)}"
    # Only the agent and its wallet are recreated. The databases have no
    # volume, so recreating them would wipe the participant's state.
    body = (
        f"{dc} pull {q(wallet)} {q(service)}\n"
        f"{dc} up -d --wait --force-recreate --no-deps {q(wallet)} {q(service)}"
    )
    return f"set -e\ncd {q(path)}\n{body}\necho '--- running containers ---'\n{dc} ps\n"


def _ssh_cmd(prefix: str) -> List[str]:
    host = _var(prefix, "SSH_HOST")
    user = _var(prefix, "SSH_USER")
    # accept-new pins the host key on first contact and refuses a changed one,
    # instead of trusting whatever answers like StrictHostKeyChecking=no did.
    ssh = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=10", f"{user}@{host}", "bash", "-s"]
    if os.environ.get(f"{prefix}_SSH_PASS"):
        compose.require("sshpass", "Install it (brew install hudochenkov/sshpass/sshpass) or switch to SSH keys.")
        # -e reads SSHPASS from the environment, so the password never shows in ps.
        return ["sshpass", "-e", *ssh]
    return ssh


def restart(nodes: Sequence[str], dry_run: bool) -> int:
    nodes_all = settings.DATASPACE_NODES
    targets = [n for n in nodes_all if n in nodes] if "all" not in nodes else list(nodes_all)
    prod = settings.stacks("prod")

    failed = []
    for node in targets:
        prefix = PREFIXES[node]
        stack = prod[node]
        path = _var(prefix, "PATH")
        compose_file = os.environ.get(f"{prefix}_COMPOSE") or stack.compose.name
        service = os.environ.get(f"{prefix}_SERVICE") or (stack.service or "")
        script = _remote_script(path, compose_file, service, f"{service}-fafnir-wallet")
        cmd = _ssh_cmd(prefix)

        log.step(f"Restarting {node} on {os.environ.get(prefix + '_SSH_HOST')}")
        if dry_run:
            log.info("  " + " ".join(cmd))
            print(script, file=sys.stderr)
            continue
        env = {**os.environ, "SSHPASS": os.environ.get(f"{prefix}_SSH_PASS", "")}
        if subprocess.run(cmd, input=script, text=True, env=env).returncode != 0:
            log.warn(f"{node}: remote execution failed")
            failed.append(node)
            continue
        log.ok(f"{node} restarted")

    if failed:
        raise log.fail(f"\nFailed: {', '.join(failed)}")
    return 0
