"""Stack lifecycle: up, down, stop, status, logs."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from typing import Dict, List, Sequence

from .. import compose, http, log, settings
from ..settings import DATASPACE_NODES, REPO_ROOT, Stack
from . import catalog, onboard

URL_SUFFIX = {"authority": "/admin/home", "provider": "/admin/login", "consumer": "/admin/login"}


def resolve_nodes(requested: Sequence[str]) -> List[str]:
    """No args or `all` means everything: the dataspace and the demo backend."""
    if not requested or "all" in requested:
        return list(settings.ALL_NODES)
    # Keep the dependency order whatever order they were typed in.
    return [n for n in settings.ALL_NODES if n in requested]


def _check_ports(chosen: Sequence[Stack]) -> None:
    """Fail early on ports held by something other than this deployment."""
    ours = _running_containers()
    squatters = compose.foreign_listeners(p for s in chosen for p in s.ports)
    if squatters:
        raise log.fail(
            "These ports are held by processes outside Docker. Stop them first, or the\n"
            "deployment will look healthy while 127.0.0.1 reaches the other process:\n" + "\n".join(squatters)
        )
    # Without lsof (Windows, the tools container) a busy port is only an
    # error when none of our containers is running: then it is someone else.
    if ours:
        return
    busy = compose.busy_ports(p for s in chosen for p in s.ports)
    if busy:
        raise log.fail(
            f"Ports {', '.join(map(str, busy))} are already in use by another program or container.\n"
            "Free them, or change the database and demo ports in .env (see .env.example)."
        )


def _running_containers() -> List[str]:
    out = compose.run(
        ["docker", "ps", "-q", "--filter", f"name=^/{settings.container_prefix()}"], capture=True, check=False
    )
    return out.split()


def _prepare_vault() -> None:
    # On Linux the setup jobs run as an unprivileged user and write the
    # generated keys into vault/*/secrets, a bind mount owned by the host user.
    if os.name == "posix":
        for node in ("consumer", "provider", "heimdall"):
            for root, dirs, files in os.walk(settings.VAULT_DIR / node):
                for name in dirs + files:
                    try:
                        path = os.path.join(root, name)
                        os.chmod(path, os.stat(path).st_mode | 0o666 | (0o111 if name in dirs else 0))
                    except OSError:
                        pass


# ---------------------------------------------------------------------------
# up
# ---------------------------------------------------------------------------


def up(env: str, nodes: Sequence[str], onboarding: bool, populate: bool, pull: bool, build: bool = False) -> None:
    compose.require_docker()
    settings.versions()
    targets = resolve_nodes(nodes)
    all_stacks = settings.stacks(env)
    chosen = [all_stacks[n] for n in targets]

    if env == "standalone":
        _check_ports(chosen)
        _prepare_vault()

    for stack in chosen:
        log.step(f"Starting {stack.node}" + (" (the first time this downloads the images)" if stack.node == "authority" else ""))
        if pull:
            compose.compose(stack, "pull", "--ignore-buildable")
        args = ["up", "-d", "--wait", "--remove-orphans"]
        if stack.node == "demo" and build:
            args.append("--build")
        try:
            compose.compose(stack, *args)
        except log.Abort:
            raise log.fail(f"{stack.node} did not start. See why with: eunomia logs {stack.node}")

    urls = {s.node: settings.node_url(env, s.node) for s in chosen if s.node in DATASPACE_NODES}
    log.step("Checking readiness from this host")
    for stack in chosen:
        if stack.readiness:
            compose.wait_http(stack.node.capitalize(), f"{urls[stack.node]}{stack.readiness}")

    whole_dataspace = all(n in targets for n in DATASPACE_NODES)
    if env == "prod":
        # In prod each participant lives on its own server, so cross-node
        # steps are run once all of them are up, from anywhere.
        log.info("\nProd: run `eunomia onboard --env prod` and `eunomia catalog populate --env prod` once every node is up.")
    else:
        ep = settings.endpoints(env)
        if onboarding and whole_dataspace:
            onboard.run_all(ep)
        elif onboarding:
            log.info("Onboarding skipped: it needs authority, provider and consumer up together")
        if populate and "provider" in targets:
            catalog.populate(ep.provider, settings.demo())

    print_urls(env, targets)
    if env == "standalone" and whole_dataspace and "demo" in targets:
        log.info("Next: eunomia e2e   (a negotiation, a pull and a push transfer, end to end)")


def print_urls(env: str, targets: Sequence[str]) -> None:
    lines = []
    for node in targets:
        if node in DATASPACE_NODES:
            lines.append(f"  {node:<10} {settings.for_humans(settings.node_url(env, node))}{URL_SUFFIX[node]}")
    if "provider" in targets or "consumer" in targets:
        lines.append("             (provider and consumer consoles: eunomia / eunomia)")
    if "demo" in targets:
        d = settings.demo()
        h = settings.for_humans
        lines.append(f"  demo       {h(d.static_api)}/docs  (robots, pull)")
        lines.append(f"             {h(d.dynamic_api)}/docs  (robot events, push)")
        lines.append(f"             {h(d.keycloak)}  (Keycloak: admin / admin)")
    log.ok(f"\n{env.capitalize()} deployment ready:\n" + "\n".join(lines))


# ---------------------------------------------------------------------------
# stop / down
# ---------------------------------------------------------------------------


def stop(env: str, nodes: Sequence[str]) -> None:
    compose.require_docker()
    stacks = settings.stacks(env)
    for node in reversed(resolve_nodes(nodes)):
        log.info(f"stop: {node}")
        compose.compose(stacks[node], "stop")
    log.ok("Stopped. Data and identities are kept: start again with eunomia up")


def _wipe_vault(dry_run: bool) -> None:
    """Remove the identity material the setup jobs generate under vault/.

    The DIDs, keys and wallet state live in vault/ through a bind mount, not
    in a Docker volume, so `down -v` leaves them behind and a redeploy would
    silently reuse the old identities. Only generated files go: vault/ also
    holds committed .example files the deployment needs to boot.
    """
    if shutil.which("git") and (REPO_ROOT / ".git").exists():
        # git knows which files are committed, so it draws the line. -x
        # includes ignored files, which is where the generated keys live.
        # LC_ALL=C because the "Would remove" prefix is translated otherwise.
        res = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "clean", "-ndx", "--", "vault/"],
            capture_output=True,
            text=True,
            env={**os.environ, "LC_ALL": "C"},
        )
        if res.returncode == 0:
            pending = [line.replace("Would remove ", "  ") for line in res.stdout.splitlines()]
            if not pending:
                log.ok("vault/ is already clean")
                return
            print("\n".join(pending), file=sys.stderr)
            compose.run(["git", "-C", str(REPO_ROOT), "clean", "-fdx", "--", "vault/"], dry_run=dry_run, capture=True)
            log.ok("Generated identity material " + ("would be removed" if dry_run else "removed"))
            return

    # Not a git checkout (a downloaded zip, say, or git refusing a directory
    # owned by another user inside the tools container): fall back to the
    # names the setup jobs are known to generate.
    log.info("Removing the known generated files")
    for node in ("consumer", "provider", "heimdall"):
        secrets = settings.VAULT_DIR / node / "secrets"
        for name in ("cert.json.example", "private_key.json.example", "public_key.json.example"):
            target = secrets / name
            if target.is_file():
                if dry_run:
                    log.info(f"  would remove {target.relative_to(REPO_ROOT)}")
                else:
                    target.unlink()
    log.ok("Generated identity material " + ("would be removed" if dry_run else "removed"))


def down(yes: bool, dry_run: bool, images: bool, keep_identities: bool) -> None:
    compose.require_docker()
    stacks = settings.stacks("standalone")
    order = ["demo", "consumer", "provider", "authority"]
    prefix = settings.container_prefix()

    if not dry_run and not yes:
        log.info("This removes the whole standalone deployment:")
        log.info(f"  · every {prefix}* container, network and volume")
        log.info("  · the catalog and every negotiated agreement (they live in the databases)")
        log.info("  · the demo factory data")
        if not keep_identities:
            log.info("  · the generated identities in vault/: the agents get new DIDs")
        if images:
            log.info("  · the locally built images")
        if not sys.stdin.isatty():
            raise log.fail("Not running interactively. Re-run with --yes to confirm, or --dry-run to preview.")
        if input("Type 'yes' to continue: ").strip() != "yes":
            raise log.fail("Aborted, nothing was removed.")
    if dry_run:
        log.info("DRY RUN: nothing will actually be removed")

    log.step("Step 1 · Removing the stacks")
    for node in order:
        stack = stacks[node]
        args = ["down", "--volumes", "--remove-orphans"] + (["--rmi", "local"] if images else [])
        log.info(f"down: {node}")
        compose.compose(stack, *args, dry_run=dry_run)

    log.step("Step 2 · Sweeping stray containers and networks")
    # Anything started outside compose, or left by an interrupted run, is
    # invisible to `down` but still holds its name and port.
    if dry_run:
        # Nothing was brought down, so every container would look stray here.
        log.info(f"would remove any {prefix}* container or network still left after step 1")
    else:
        _sweep()

    log.step("Step 3 · Generated state in vault/")
    if keep_identities:
        log.info("Keeping vault/ (--keep-identities): the agents will reuse their DIDs")
    else:
        _wipe_vault(dry_run)

    log.step("Step 4 · Checking the ports are free")
    if dry_run:
        log.info("Skipped in dry-run mode")
    else:
        ports = [p for n in order for p in stacks[n].ports]
        busy = compose.busy_ports(ports)
        if busy:
            detail = "\n".join(f"  :{p}  {line}" for p in busy for line in compose.listeners(p))
            raise log.fail(
                f"Ports {', '.join(map(str, busy))} are still in use. Stop whatever holds them before redeploying."
                + (f"\n{detail}" if detail else "")
            )
        log.ok(f"All {len(ports)} ports are free")

    log.ok("\nDry run complete: nothing was removed." if dry_run else "\nTeardown complete. Redeploy with: eunomia up")


def _sweep() -> None:
    prefix = settings.container_prefix()
    stray = compose.run(["docker", "ps", "-aq", "--filter", f"name=^/{prefix}"], capture=True).split()
    if stray:
        compose.run(["docker", "rm", "-f", *stray], capture=True)
        log.ok(f"Removed {len(stray)} leftover container(s)")
    else:
        log.ok("No stray containers")
    nets = compose.run(["docker", "network", "ls", "-q", "--filter", f"name=^{prefix}"], capture=True).split()
    if nets:
        compose.run(["docker", "network", "rm", *nets], capture=True, check=False)
        log.ok(f"Removed {len(nets)} leftover network(s)")
    else:
        log.ok("No stray networks")


# ---------------------------------------------------------------------------
# status / logs
# ---------------------------------------------------------------------------


def containers(compose_cmd: List[str]) -> List[Dict[str, str]]:
    out = compose.run(compose_cmd + ["ps", "-a", "--format", "json"], capture=True, check=False).strip()
    if not out:
        return []
    # Compose prints a JSON array in older releases and JSON lines in newer ones.
    if out.startswith("["):
        return json.loads(out)
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def print_containers(rows: List[Dict[str, str]]) -> None:
    if not rows:
        print("    (no containers)")
    for c in rows:
        state = c.get("State", "")
        health = c.get("Health") or ""
        print(f"    {c.get('Name', ''):<40} {state:<9} {health}")


def status(env: str) -> int:
    compose.require_docker()
    healthy = True
    for node, stack in settings.stacks(env).items():
        rows = containers(compose.compose_cmd(stack))
        # A prod server runs one node; the demo is optional anywhere.
        if not rows and (node == "demo" or env == "prod"):
            continue
        ready = ""
        if stack.readiness:
            if env == "prod" and not os.environ.get(f"{node.upper()}_URL"):
                ready = f"readiness unknown: {node.upper()}_URL not set"
            else:
                code = http.probe(f"{settings.node_url(env, node)}{stack.readiness}")
                ready = "ready" if code == 200 else f"not ready ({code or 'no answer'})"
                healthy &= code == 200
        print(f"\n{node}  {ready}")
        print_containers(rows)
    return 0 if healthy else 1


def logs(env: str, node: str, follow: bool, tail: str, services: Sequence[str]) -> int:
    stack = settings.stacks(env)[node]
    args = ["logs", "--tail", tail] + (["-f"] if follow else []) + list(services)
    return subprocess.call(compose.compose_cmd(stack, *args), cwd=REPO_ROOT)
