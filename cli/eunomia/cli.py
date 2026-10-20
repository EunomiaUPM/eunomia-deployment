"""Command-line entry point."""

from __future__ import annotations

import argparse
import dataclasses
import subprocess
import sys
from typing import List, Optional

from . import __version__, log, settings
from .commands import catalog, demo, doctor, e2e, images, instances, onboard, restart, stack

NODES_HELP = "authority, provider, consumer, demo, or all (default: all of them)"


def _node(value: str) -> str:
    # A type check rather than choices=: with nargs="*", argparse also checks
    # the empty default against choices and rejects a bare `eunomia up`.
    allowed = settings.ALL_NODES + ("all",)
    if value not in allowed:
        raise argparse.ArgumentTypeError(f"invalid node {value!r} (choose from {', '.join(allowed)})")
    return value


def _add_env(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--env",
        choices=settings.ENVIRONMENTS,
        default="standalone",
        help="standalone (default): every participant on this host. prod: real servers.",
    )


def _add_peers(p: argparse.ArgumentParser, consumer: bool = True) -> None:
    if consumer:
        p.add_argument("--consumer", help="consumer to use: an instance name (default: the standalone consumer)")
    p.add_argument("--provider", help="provider to use: an instance name (default: the standalone provider)")


def _endpoints(args: argparse.Namespace) -> settings.Endpoints:
    """The standalone endpoints, with the consumer or provider swapped for an instance."""
    ep = settings.endpoints(args.env)
    swaps = {}
    for role in ("consumer", "provider"):
        name = getattr(args, role, None)
        if name and name != role:
            kind, peer = instances.resolve(name)
            if kind != "connector":
                raise log.fail(f"{name!r} is not a connector")
            swaps[role], swaps[f"docker_{role}"] = peer.url, peer.docker_url
    return dataclasses.replace(ep, **swaps) if swaps else ep


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eunomia",
        description="Deploy, onboard and try an EUNOMIA dataspace.",
        epilog=(
            "Start with: eunomia doctor, then eunomia up, then eunomia e2e.\n"
            "Settings come from the shell and from .env at the repo root (see .env.example)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"eunomia {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # -- the standalone deployment ---------------------------------------------
    p = sub.add_parser("doctor", help="check Docker, Compose, ports and versions.env")
    p.add_argument("--images", action="store_true", help="also check every pinned image can be pulled")

    p = sub.add_parser("up", help="start the deployment, onboard the participants and populate the catalog")
    p.add_argument("nodes", nargs="*", type=_node, metavar="node", help=NODES_HELP)
    _add_env(p)
    p.add_argument("--no-onboarding", action="store_true", help="only start the stacks")
    p.add_argument("--no-catalog", action="store_true", help="do not populate the provider catalog")
    p.add_argument("--pull", action="store_true", help="pull the pinned images before starting")
    p.add_argument("--build", action="store_true", help="rebuild the demo factory image")

    p = sub.add_parser("stop", help="stop nodes or instances, keeping their data")
    p.add_argument("targets", nargs="*", metavar="target", help=f"{NODES_HELP}, or an instance name")
    _add_env(p)

    p = sub.add_parser("down", help="remove the standalone deployment, identities included")
    p.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")
    p.add_argument("-n", "--dry-run", action="store_true", help="show what would be removed")
    p.add_argument("--images", action="store_true", help="also remove locally built images")
    p.add_argument("--keep-identities", action="store_true", help="keep vault/, so the agents keep their DIDs")

    p = sub.add_parser("status", help="containers and readiness of every node, or of one instance")
    p.add_argument("name", nargs="?", help="an instance name (default: the standalone deployment)")
    _add_env(p)

    p = sub.add_parser("logs", help="logs of a node, an instance or any container")
    p.add_argument("target", help="authority, provider, consumer, demo, an instance or a container name")
    p.add_argument("services", nargs="*", help="limit to these compose services")
    _add_env(p)
    p.add_argument("-f", "--follow", action="store_true")
    p.add_argument("--tail", default="200", help="lines per container (default: 200, or 'all')")

    p = sub.add_parser("onboard", help="link wallets, register, get the Gaia-X credentials, connect")
    p.add_argument(
        "step",
        nargs="?",
        choices=("wallets", "register", "gaia", "connect"),
        help="run a single step (default: all of them, in order)",
    )
    p.add_argument("node", nargs="?", choices=("provider", "consumer"), help="for register: who registers")
    _add_env(p)

    p = sub.add_parser("catalog", help="provider catalog")
    csub = p.add_subparsers(dest="action", metavar="<action>")
    csub.required = True
    cp = csub.add_parser("populate", help="create the demo factory dataset, policies and connectors")
    cp.add_argument("--force", action="store_true", help="create them again even if they exist")
    _add_env(cp)
    _add_peers(cp, consumer=False)
    cs = csub.add_parser("show", help="list datasets, distributions and connector instances")
    _add_env(cs)
    _add_peers(cs, consumer=False)

    p = sub.add_parser("e2e", help="negotiate, then pull and push data end to end")
    _add_env(p)
    p.add_argument("--dataset", help="substring of the dataset title (default: the demo factory dataset)")
    p.add_argument("--list-datasets", action="store_true", help="list the catalog and exit")
    p.add_argument("--keep-open", action="store_true", help="leave the pull transfer STARTED")
    p.add_argument("--no-suspend", action="store_true", help="skip the suspend/resume leg")
    p.add_argument("--no-data-pull", action="store_true", help="skip the data pull through the proxy")
    p.add_argument("--no-push", action="store_true", help="skip the push transfer")
    p.add_argument("-v", "--verbose", action="store_true", help="dump every request and response")
    _add_peers(p)

    p = sub.add_parser("demo", help="use the demo factory through the dataspace")
    dsub = p.add_subparsers(dest="action", metavar="<action>")
    dsub.required = True
    dp = dsub.add_parser("robots", help="negotiate and pull the robots, printed as JSON")
    _add_env(dp)
    _add_peers(dp)
    dp.add_argument("-v", "--verbose", action="store_true")
    dp = dsub.add_parser("events", help="negotiate and print the robot events as they are pushed")
    _add_env(dp)
    _add_peers(dp)
    dp.add_argument("-n", "--count", type=int, help="stop after this many events (default: Ctrl+C)")
    dp.add_argument("-v", "--verbose", action="store_true")
    dsub.add_parser("token", help="a Keycloak token to call the factory API directly")

    # -- more participants -------------------------------------------------------
    p = sub.add_parser("connector", help="extra connectors next to the standalone deployment")
    nsub = p.add_subparsers(dest="action", metavar="<action>")
    nsub.required = True
    np_ = nsub.add_parser("add", help="create and start a connector on free ports")
    np_.add_argument("name", nargs="?", help="default: conn-<random>")
    np_.add_argument("--role", choices=("consumer", "provider"), default="consumer")
    np_.add_argument("--onboard", action="store_true", help="register it with the authority once it is up")
    np_.add_argument("--authority", default="authority", help="authority to register with (implies --onboard)")

    p = sub.add_parser("authority", help="extra authorities next to the standalone deployment")
    asub = p.add_subparsers(dest="action", metavar="<action>")
    asub.required = True
    ap = asub.add_parser("add", help="create and start an authority on free ports")
    ap.add_argument("name", nargs="?", help="default: auth-<random>")
    ap.add_argument("--role", choices=("eco", "dataspace"), default="eco", help="eco (default) also issues Gaia-X credentials")

    sub.add_parser("instances", help="list the extra connectors and authorities")

    p = sub.add_parser("start", help="start an instance again")
    p.add_argument("name")

    p = sub.add_parser("rm", help="remove an instance: containers, volumes and configuration")
    p.add_argument("name")
    p.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")

    p = sub.add_parser("register", help="register a connector with an authority")
    p.add_argument("connector", help="provider, consumer or an instance")
    p.add_argument("--authority", default="authority", help="default: the standalone authority")

    p = sub.add_parser("connect", help="connect a consumer to a provider (GNAP handshake)")
    p.add_argument("consumer")
    p.add_argument("provider")

    p = sub.add_parser("gaia", help="Gaia-X credentials for a consumer, then connect it to a provider")
    p.add_argument("--consumer", default="consumer")
    p.add_argument("--provider", default="provider", help="connect to it afterwards (default: provider; '' to skip)")
    p.add_argument("--authority", default="authority", help="must have the eco role (default: authority)")

    # -- prod and maintenance ----------------------------------------------------
    p = sub.add_parser("restart", help="restart prod nodes on their servers over SSH")
    p.add_argument("nodes", nargs="+", choices=settings.DATASPACE_NODES + ("all",), metavar="node", help="authority, provider, consumer or all")
    p.add_argument("-n", "--dry-run", action="store_true", help="print the SSH commands instead")

    p = sub.add_parser("images", help="pinned images; --check looks for newer tags")
    _add_env(p)
    p.add_argument("--check", action="store_true", help="query the registries")

    return parser


def _split_targets(targets: List[str]) -> "tuple[List[str], List[str]]":
    nodes, names = [], []
    for t in targets:
        (nodes if t in settings.ALL_NODES + ("all",) else names).append(t)
    return nodes, names


def dispatch(args: argparse.Namespace) -> int:
    cmd = args.command
    if cmd == "doctor":
        return doctor.run(args.images)
    if cmd == "up":
        stack.up(args.env, args.nodes, not args.no_onboarding, not args.no_catalog, args.pull, args.build)
    elif cmd == "stop":
        nodes, names = _split_targets(args.targets)
        for name in names:
            instances.stop(name)
        if nodes or not names:
            stack.stop(args.env, nodes)
    elif cmd == "down":
        stack.down(args.yes, args.dry_run, args.images, args.keep_identities)
    elif cmd == "status":
        if args.name:
            instances.status(args.name)
            return 0
        code = stack.status(args.env)
        if args.env == "standalone" and instances.all_instances():
            print()
            instances.list_instances()
        return code
    elif cmd == "logs":
        if args.target in settings.ALL_NODES:
            return stack.logs(args.env, args.target, args.follow, args.tail, args.services)
        if instances.is_instance(args.target):
            return instances.logs(args.target, args.follow, args.tail, args.services)
        # Any container: the *-setup jobs, say.
        return subprocess.call(["docker", "logs", "--tail", args.tail] + (["-f"] if args.follow else []) + [args.target])
    elif cmd == "onboard":
        ep = settings.endpoints(args.env)
        authority, provider, consumer = onboard.peers(ep)
        if args.step is None:
            onboard.run_all(ep)
        elif args.step == "wallets":
            onboard.link_wallets([authority, provider, consumer])
        elif args.step == "register":
            for p in [provider, consumer] if not args.node else [provider if args.node == "provider" else consumer]:
                onboard.register(p, authority)
        elif args.step == "gaia":
            onboard.gaia(consumer, authority)
        else:
            onboard.connect(consumer, provider)
    elif cmd == "catalog":
        ep = _endpoints(args)
        if args.action == "populate":
            catalog.populate(ep.provider, settings.demo(), force=args.force)
        else:
            catalog.show(ep.provider)
    elif cmd == "e2e":
        return e2e.run(
            _endpoints(args),
            settings.demo(),
            dataset=args.dataset,
            list_datasets=args.list_datasets,
            suspend=not args.no_suspend,
            data_pull=not args.no_data_pull,
            push=not args.no_push,
            keep_open=args.keep_open,
            verbose=args.verbose,
        )
    elif cmd == "demo":
        if args.action == "robots":
            return demo.robots(_endpoints(args), args.verbose)
        if args.action == "events":
            return demo.events(_endpoints(args), args.count, args.verbose)
        return demo.token(settings.demo())
    elif cmd == "connector":
        instances.add_connector(args.name, args.role, args.onboard or args.authority != "authority", args.authority)
    elif cmd == "authority":
        instances.add_authority(args.name, args.role)
    elif cmd == "instances":
        instances.list_instances()
    elif cmd == "start":
        instances.start(args.name)
    elif cmd == "rm":
        instances.remove(args.name, args.yes)
    elif cmd == "register":
        instances.register(args.connector, args.authority)
    elif cmd == "connect":
        instances.connect(args.consumer, args.provider)
    elif cmd == "gaia":
        instances.gaia(args.consumer, args.provider or None, args.authority)
    elif cmd == "restart":
        return restart.restart(args.nodes, args.dry_run)
    elif cmd == "images":
        return images.show(args.env, args.check)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if not settings.DEPLOYMENT_DIR.is_dir():
        # The CLI drives the compose files and payloads of its own checkout.
        log.fail(f"No deployment/ next to {settings.REPO_ROOT}. Run ./eunomia from the repo, or pip install -e .")
        return 1
    settings.load_env()
    try:
        return dispatch(args)
    except log.Abort:
        return 1
    except KeyboardInterrupt:
        print(file=sys.stderr)
        return 130
