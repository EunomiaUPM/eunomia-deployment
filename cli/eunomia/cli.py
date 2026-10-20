"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__, log, settings
from .commands import catalog, demo, doctor, e2e, images, instances, onboard, restart, stack

EPILOG = """\
eunomia is a hypervisor of instances: authorities and agents. Every agent can
publish a catalog and negotiate both ways; "consumer" and "provider" are the
roles two agents take in one exchange.

  eunomia authority add authority
  eunomia agent add alice
  eunomia agent add bob
  eunomia login alice bob
  eunomia demo up
  eunomia catalog populate alice
  eunomia e2e --consumer bob --provider alice

Settings come from the shell and from .env at the repo root (see .env.example)."""


def _add_exchange(p: argparse.ArgumentParser) -> None:
    p.add_argument("--consumer", required=True, metavar="AGENT", help="the agent that negotiates and receives")
    p.add_argument("--provider", required=True, metavar="AGENT", help="the agent whose catalog is used")


def _add_logs(p: argparse.ArgumentParser) -> None:
    p.add_argument("services", nargs="*", help="limit to these compose services")
    p.add_argument("-f", "--follow", action="store_true")
    p.add_argument("--tail", default="200", help="lines per container (default: 200, or 'all')")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eunomia",
        description="Run and connect EUNOMIA authorities and agents, on this machine or on servers.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"eunomia {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # -- check -------------------------------------------------------------------
    p = sub.add_parser("doctor", help="check Docker, Compose, ports and versions.env")
    p.add_argument("--images", action="store_true", help="also check every pinned image can be pulled")

    # -- instances ---------------------------------------------------------------
    p = sub.add_parser("authority", help="authorities: issue credentials and admit agents")
    asub = p.add_subparsers(dest="action", metavar="<action>")
    asub.required = True
    ap = asub.add_parser("add", help="create and start an authority on free ports")
    ap.add_argument("name", nargs="?", help="default: authority-<random>")
    ap.add_argument("--role", choices=("eco", "dataspace"), default="eco", help="eco (default) also issues Gaia-X credentials")

    p = sub.add_parser("agent", help="agents: publish catalogs, negotiate, exchange data")
    gsub = p.add_subparsers(dest="action", metavar="<action>")
    gsub.required = True
    gp = gsub.add_parser("add", help="create and start an agent on free ports, and onboard it")
    gp.add_argument("name", nargs="?", help="default: agent-<random>")
    gp.add_argument("--authority", help="onboard it with this authority (default: the only one there is)")
    gp.add_argument("--no-onboard", action="store_true", help="only create and start it")

    p = sub.add_parser("remote", help="instances running on other servers, known by URL")
    rsub = p.add_subparsers(dest="action", metavar="<action>")
    rsub.required = True
    rp = rsub.add_parser("add", help="register a remote authority or agent")
    rp.add_argument("name")
    rp.add_argument("--kind", choices=settings.KINDS, required=True)
    rp.add_argument("--url", required=True, help="its public URL, e.g. https://agent.example.org")
    rp.add_argument("--ssh", metavar="USER@HOST", help="SSH access, for eunomia restart")
    rp.add_argument("--path", help="its deployment/prod directory on the server, for eunomia restart")

    sub.add_parser("ls", help="every instance, where it runs and its state")

    p = sub.add_parser("up", help="start registered local instances (default: all of them)")
    p.add_argument("names", nargs="*", metavar="name")

    p = sub.add_parser("stop", help="stop local instances, keeping their data (default: all, and the demo)")
    p.add_argument("names", nargs="*", metavar="name")

    p = sub.add_parser("rm", help="remove instances: containers, volumes, configuration and identity")
    p.add_argument("names", nargs="+", metavar="name")
    p.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")

    p = sub.add_parser("down", help="remove every local instance and the demo factory")
    p.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")
    p.add_argument("-n", "--dry-run", action="store_true", help="show what would be removed")

    p = sub.add_parser("status", help="every instance and the demo factory, or one instance in detail")
    p.add_argument("name", nargs="?")

    p = sub.add_parser("logs", help="logs of an instance, of the demo factory or of any container")
    p.add_argument("target", help="an instance name, 'demo', or a container name")
    _add_logs(p)

    # -- relationships -----------------------------------------------------------
    p = sub.add_parser("onboard", help="wallets, membership and Gaia-X credentials for agents")
    p.add_argument("agents", nargs="+", metavar="agent")
    p.add_argument("--authority", help="default: the only authority there is")

    p = sub.add_parser("login", help="GNAP login between two agents: once approved, each holds a token for the other")
    p.add_argument("a", metavar="agent", help="the agent that asks for the grant")
    p.add_argument("b", metavar="other", help="the agent that verifies its credentials and approves it")

    p = sub.add_parser("catalog", help="an agent's catalog")
    csub = p.add_subparsers(dest="action", metavar="<action>")
    csub.required = True
    cp = csub.add_parser("populate", help="load the demo factory dataset, policies and connectors into an agent")
    cp.add_argument("agent")
    cp.add_argument("--force", action="store_true", help="create them again even if they exist")
    cs = csub.add_parser("show", help="list an agent's datasets, distributions and connector instances")
    cs.add_argument("agent")

    # -- data ---------------------------------------------------------------------
    p = sub.add_parser("e2e", help="two agents: negotiate, then pull and push data end to end")
    _add_exchange(p)
    p.add_argument("--dataset", help="substring of the dataset title (default: the demo factory dataset)")
    p.add_argument("--list-datasets", action="store_true", help="list the provider's catalog and exit")
    p.add_argument("--keep-open", action="store_true", help="leave the pull transfer STARTED")
    p.add_argument("--no-suspend", action="store_true", help="skip the suspend/resume leg")
    p.add_argument("--no-data-pull", action="store_true", help="skip the data pull through the proxy")
    p.add_argument("--no-push", action="store_true", help="skip the push transfer")
    p.add_argument("-v", "--verbose", action="store_true", help="dump every request and response")

    p = sub.add_parser("demo", help="the demo factory: run it, and use it through the data space")
    dsub = p.add_subparsers(dest="action", metavar="<action>")
    dsub.required = True
    dp = dsub.add_parser("up", help="start the demo factory")
    dp.add_argument("--build", action="store_true", help="rebuild its image")
    dsub.add_parser("down", help="remove the demo factory and its data")
    dp = dsub.add_parser("robots", help="negotiate and pull the robots, printed as JSON")
    _add_exchange(dp)
    dp.add_argument("-v", "--verbose", action="store_true")
    dp = dsub.add_parser("events", help="negotiate and print the robot events as they are pushed")
    _add_exchange(dp)
    dp.add_argument("-n", "--count", type=int, help="stop after this many events (default: Ctrl+C)")
    dp.add_argument("-v", "--verbose", action="store_true")
    dsub.add_parser("token", help="a Keycloak token to call the factory API directly")

    # -- production and maintenance ----------------------------------------------
    p = sub.add_parser("prod", help="the production node of this server")
    psub = p.add_subparsers(dest="action", metavar="<action>")
    psub.required = True
    pp = psub.add_parser("up", help="start this server's agent or authority (deployment/prod)")
    pp.add_argument("kind", choices=settings.KINDS)
    pp.add_argument("--pull", action="store_true", help="pull the pinned images first")
    pp = psub.add_parser("status", help="its containers")
    pp.add_argument("kind", choices=settings.KINDS)
    pp = psub.add_parser("logs", help="its logs")
    pp.add_argument("kind", choices=settings.KINDS)
    _add_logs(pp)

    p = sub.add_parser("restart", help="restart instances: remote ones over SSH, local ones here")
    p.add_argument("names", nargs="+", metavar="name")
    p.add_argument("-n", "--dry-run", action="store_true", help="print the SSH commands instead")

    p = sub.add_parser("images", help="pinned images; --check looks for newer tags")
    p.add_argument("--check", action="store_true", help="query the registries")

    return parser


def _agent(name: str) -> onboard.Peer:
    return instances.get(name, "agent").peer


def dispatch(args: argparse.Namespace) -> int:
    cmd = args.command
    if cmd == "doctor":
        return doctor.run(args.images)
    if cmd == "authority":
        instances.add_authority(args.name, args.role)
    elif cmd == "agent":
        has_authority = args.authority or any(i.kind == "authority" for i in instances.all_instances())
        instances.add_agent(args.name, args.authority, onboard_it=not args.no_onboard and bool(has_authority))
    elif cmd == "remote":
        instances.add_remote(args.name, args.kind, args.url, args.ssh, args.path)
    elif cmd == "ls":
        instances.list_instances()
    elif cmd == "up":
        stack.up(args.names)
    elif cmd == "stop":
        stack.stop(args.names, with_demo=not args.names)
    elif cmd == "rm":
        stack.remove(args.names, args.yes)
    elif cmd == "down":
        stack.down(args.yes, args.dry_run)
    elif cmd == "status":
        if args.name:
            instances.status(instances.get(args.name))
            return 0
        return stack.status()
    elif cmd == "logs":
        return stack.logs(args.target, args.follow, args.tail, args.services)
    elif cmd == "onboard":
        authority = instances.authority_for(args.authority)
        for name in args.agents:
            onboard.onboard_agent(_agent(name), authority.peer, with_gaia=instances.issues_gaia(authority))
    elif cmd == "login":
        if args.a == args.b:
            raise log.fail("An agent cannot log in with itself: name two agents.")
        onboard.login(_agent(args.a), _agent(args.b))
    elif cmd == "catalog":
        peer = _agent(args.agent)
        if args.action == "populate":
            catalog.populate(peer.name, peer.url, settings.demo(), force=args.force)
        else:
            catalog.show(peer.name, peer.url)
    elif cmd == "e2e":
        return e2e.run(
            _agent(args.consumer),
            _agent(args.provider),
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
        if args.action == "up":
            demo.up(args.build)
        elif args.action == "down":
            demo.down()
        elif args.action == "robots":
            return demo.robots(_agent(args.consumer), _agent(args.provider), args.verbose)
        elif args.action == "events":
            return demo.events(_agent(args.consumer), _agent(args.provider), args.count, args.verbose)
        else:
            return demo.token(settings.demo())
    elif cmd == "prod":
        if args.action == "up":
            stack.prod_up(args.kind, args.pull)
        elif args.action == "status":
            return stack.prod_status(args.kind)
        else:
            return stack.prod_logs(args.kind, args.follow, args.tail, args.services)
    elif cmd == "restart":
        return restart.restart(args.names, args.dry_run)
    elif cmd == "images":
        return images.show(args.check)
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
