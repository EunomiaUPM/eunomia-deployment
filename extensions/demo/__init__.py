"""The demo: a factory with robots, shared through the data space.

It shows every extension point at work, and is the example to copy for an
extension of your own:

  commands    up, down, publish <agent>, robots, events, token
  services    the factory (service/docker-compose.yaml)
  test        `eunomia demo test --consumer A --provider B` (e2e.py)
  notebooks   `eunomia demo notebook <provider> <consumer>` (notebooks/)

  eunomia demo up
  eunomia demo publish alice
  eunomia demo test --consumer bob --provider alice
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

from eunomia.ext import ComposeService, Extension, NotebookSet, Peer, add_exchange_roles, agent

from . import consume, e2e, factory, publish

HERE = Path(__file__).resolve().parent


class Demo(Extension):
    name = "demo"
    help = "the demo factory: run it, publish it from an agent, test it and use it through the data space"

    def commands(self, parser: argparse.ArgumentParser, actions: "argparse._SubParsersAction") -> None:
        p = actions.add_parser("up", help="start the demo factory")
        p.add_argument("--build", action="store_true", help="rebuild its image")
        p.set_defaults(run=lambda a: factory.up(a.build))

        p = actions.add_parser("down", help="remove the demo factory and its data")
        p.set_defaults(run=lambda a: factory.down())

        p = actions.add_parser("publish", help="publish the factory in an agent's catalog: dataset, policies, connectors")
        p.add_argument("agent")
        p.add_argument("--force", action="store_true", help="publish it again even if it is there")
        p.set_defaults(run=lambda a: publish.publish(agent(a.agent), factory.urls(), a.force))

        p = actions.add_parser("robots", help="negotiate and pull the robots, printed as JSON")
        add_exchange_roles(p)
        p.add_argument("-v", "--verbose", action="store_true")
        p.set_defaults(run=lambda a: consume.robots(agent(a.consumer), agent(a.provider), a.verbose))

        p = actions.add_parser("events", help="negotiate and print the robot events as they are pushed")
        add_exchange_roles(p)
        p.add_argument("-n", "--count", type=int, help="stop after this many events (default: Ctrl+C)")
        p.add_argument("-v", "--verbose", action="store_true")
        p.set_defaults(run=lambda a: consume.events(agent(a.consumer), agent(a.provider), a.count, a.verbose))

        p = actions.add_parser("token", help="a Keycloak token to call the factory API directly")
        p.set_defaults(run=lambda a: factory.token())

    def services(self) -> List[ComposeService]:
        return [factory.service()]

    def test_arguments(self, parser: argparse.ArgumentParser) -> None:
        e2e.add_arguments(parser)

    def test(self, consumer: Peer, provider: Peer, args: argparse.Namespace) -> int:
        return e2e.run(consumer, provider, factory.urls(), args)

    def notebooks(self) -> NotebookSet:
        return NotebookSet(
            directory=HERE / "notebooks",
            flows={"pull": "03_pull_flow.ipynb", "push": "04_push_flow.ipynb"},
            env=notebook_env,
        )


def notebook_env() -> Dict[str, str]:
    factory.require_running()
    return notebook_vars(factory.urls())


def notebook_vars(f: factory.Factory) -> Dict[str, str]:
    """The factory, as the notebooks reach it and as the provider's connectors do."""
    return {
        "EUNOMIA_FACTORY_URL": f.static_api,
        "EUNOMIA_FACTORY_DOCKER_URL": f.docker_static_api,
        "EUNOMIA_FACTORY_EVENTS_DOCKER_URL": f.docker_dynamic_api,
        "EUNOMIA_FACTORY_TOKEN_DOCKER_URL": f.docker_token_url,
    }


extension = Demo()
