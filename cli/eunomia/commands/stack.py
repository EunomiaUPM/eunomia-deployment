"""The hypervisor: start, stop, remove and inspect every instance at once.

`up` starts the local instances that are registered (all of them, or the
named ones); it never creates any. `down` removes every local instance, its
identity included, and the demo factory. `prod` runs the node of this server
in a production deployment.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Sequence

from .. import compose, log, settings
from ..settings import REPO_ROOT
from . import demo, instances


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


def stop(names: Sequence[str], with_demo: bool) -> None:
    compose.require_docker()
    for inst in reversed([i for i in instances.select(names) if i.local]):
        instances.stop(inst)
    if with_demo or not names:
        if demo.is_running():
            compose.compose(settings.demo_stack(), "stop")
            log.ok("Demo factory stopped")


def remove(names: Sequence[str], yes: bool) -> None:
    targets = [instances.get(n) for n in names]
    listed = ", ".join(i.name for i in targets)
    instances.confirm(f"This removes {listed}: containers, volumes, configuration and identity.", yes)
    for inst in targets:
        instances.remove(inst)


def down(yes: bool, dry_run: bool) -> None:
    """Remove every local instance and the demo factory; remote ones stay registered."""
    compose.require_docker()
    local = [i for i in instances.all_instances() if i.local]
    prefix = settings.container_prefix()

    if dry_run:
        log.info("DRY RUN: nothing will be removed")
        for inst in local:
            log.info(f"  would remove {inst.kind} {inst.name}: containers, volumes, instances/{inst.name}/")
        log.info(f"  would remove the demo factory and any {prefix}* container left behind")
        return
    instances.confirm(
        f"This removes every local instance ({', '.join(i.name for i in local) or 'none'}), "
        "their data and identities, and the demo factory.",
        yes,
    )
    for inst in local:
        instances.remove(inst)
    compose.compose(settings.demo_stack(), "down", "--volumes", "--remove-orphans")
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
    print(f"\ndemo factory: {'running' if demo.is_running() else 'not running (eunomia demo up)'}")
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
    if target == "demo":
        return demo.logs(follow, tail, list(services))
    if (settings.INSTANCES_DIR / target).is_dir():
        return instances.logs(instances.get(target), follow, tail, services)
    # Any container: an instance's setup job, say.
    return subprocess.call(["docker", "logs", "--tail", tail] + (["-f"] if follow else []) + [target], stdout=sys.stdout)
