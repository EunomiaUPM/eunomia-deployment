"""The hypervisor: start, stop, remove and inspect every instance at once.

`up` starts the local instances that are registered (all of them, or the
named ones); it never creates any. `down` removes every local instance, its
identity included, and the extensions' services (the demo factory, say).
`prod` runs the node of this server in a production deployment.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Sequence

from .. import compose, extensions, log, settings
from ..settings import REPO_ROOT
from . import instances


def up(names: Sequence[str]) -> None:
    compose.require_docker()
    settings.versions()
    targets = [i for i in instances.select(names) if i.local]
    if not targets:
        instances.list_instances()
        return
    for inst in targets:
        instances.start(inst)
    log.ok(f"\n{len(targets)} instance(s) up. See them all with: eunomia ls")


def stop(names: Sequence[str], with_services: bool) -> None:
    compose.require_docker()
    for inst in reversed([i for i in instances.select(names) if i.local]):
        instances.stop(inst)
    if with_services:
        for _, svc in extensions.services():
            if svc.is_running():
                svc.stop()
                log.ok(f"{svc.label or svc.name} stopped")


def remove(names: Sequence[str], yes: bool) -> None:
    targets = [instances.get(n) for n in names]
    listed = ", ".join(i.name for i in targets)
    instances.confirm(f"This removes {listed}: containers, volumes, configuration and identity.", yes)
    for inst in targets:
        instances.remove(inst)


def down(yes: bool, dry_run: bool) -> None:
    """Remove every local instance and the extensions' services; remote ones stay registered."""
    compose.require_docker()
    local = [i for i in instances.all_instances() if i.local]
    prefix = settings.container_prefix()

    if dry_run:
        log.info("DRY RUN: nothing will be removed")
        for inst in local:
            log.info(f"  would remove {inst.kind} {inst.name}: containers, volumes, instances/{inst.name}/")
        for _, svc in extensions.services():
            log.info(f"  would remove the {svc.label or svc.name} and its data")
        log.info(f"  would remove any {prefix}* container left behind")
        return
    instances.confirm(
        f"This removes every local instance ({', '.join(i.name for i in local) or 'none'}), "
        "their data and identities, and the extensions' services.",
        yes,
    )
    for inst in local:
        instances.remove(inst)
    for _, svc in extensions.services():
        svc.down()
    _sweep()
    log.ok("\nEverything local is gone. Start again with: eunomia authority add <name>")


def _sweep() -> None:
    """Containers and networks left behind by an interrupted run."""
    prefix = settings.container_prefix()
    stray = compose.run(["docker", "ps", "-aq", "--filter", f"name=^/{prefix}"], capture=True).split()
    if stray:
        compose.run(["docker", "rm", "-f", *stray], capture=True)
        log.ok(f"Removed {len(stray)} leftover container(s)")
    nets = compose.run(["docker", "network", "ls", "-q", "--filter", f"name=^{prefix}"], capture=True).split()
    if nets:
        compose.run(["docker", "network", "rm", *nets], capture=True, check=False)


def status() -> int:
    compose.require_docker()
    instances.list_instances()
    svcs = extensions.services()
    if svcs:
        print()
    for ext_name, svc in svcs:
        state = "running" if svc.is_running() else "not running" + (f" ({svc.start_hint})" if svc.start_hint else "")
        print(f"{svc.label or svc.name} ({ext_name} extension): {state}")
    unhealthy = [i for i in instances.all_instances() if not instances.state(i).startswith(("running (healthy)", "ready"))]
    return 1 if unhealthy else 0


# ---------------------------------------------------------------------------
# Production: the node of this server
# ---------------------------------------------------------------------------


def prod_up(kind: str, pull: bool) -> None:
    compose.require_docker()
    stack = settings.prod_stacks()[kind]
    log.step(f"Starting the {kind} of this server")
    if pull:
        compose.compose(stack, "pull")
    compose.compose(stack, "up", "-d", "--wait", "--remove-orphans")
    log.ok(
        f"\nThe {kind} is up. From any machine that reaches it, register it by its public URL:\n"
        f"  eunomia remote add <name> --kind {kind} --url https://<its domain>"
    )


def prod_status(kind: str) -> int:
    stack = settings.prod_stacks()[kind]
    return subprocess.call(compose.compose_cmd(stack, "ps", "-a"), cwd=REPO_ROOT)


def prod_logs(kind: str, follow: bool, tail: str, services: Sequence[str]) -> int:
    stack = settings.prod_stacks()[kind]
    args = ["logs", "--tail", tail] + (["-f"] if follow else []) + list(services)
    return subprocess.call(compose.compose_cmd(stack, *args), cwd=REPO_ROOT)


def logs(target: str, follow: bool, tail: str, services: Sequence[str]) -> int:
    for _, svc in extensions.services():
        if target == svc.name:
            return svc.logs(follow, tail, services)
    if (settings.INSTANCES_DIR / target).is_dir():
        return instances.logs(instances.get(target), follow, tail, services)
    # Any container: an instance's setup job, say.
    return subprocess.call(["docker", "logs", "--tail", tail] + (["-f"] if follow else []) + [target], stdout=sys.stdout)
