"""The extension API: what an extension implements, and what it may use.

An extension is a directory with an __init__.py that defines `extension`, an
instance of a subclass of Extension. eunomia loads the ones under extensions/
in this repository and the ones EUNOMIA_EXTENSIONS names (paths separated
like PATH: an extension directory, or a directory of them), and gives each a
command group: `eunomia <name> ...`. The demo in extensions/demo is one.

Extension points, each optional:

  commands(parser)   its own actions: `eunomia <name> <action>`. Each action
                     sets `run` (args -> exit code) with set_defaults.
  services()         the compose stacks it runs. stop, down, status, logs,
                     images and doctor take them into account.
  test(...)          its end-to-end test between two agents:
                     `eunomia <name> test --consumer A --provider B`.
  notebooks()        its notebooks, opened per provider/consumer pair:
                     `eunomia <name> notebook <provider> <consumer>`.

What an extension may use is what this module exports; the rest of the CLI
can change without notice.
"""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import catalog, compose, exchange, http, log, settings
from .commands.onboard import Peer
from .settings import REPO_ROOT, Stack

__all__ = [
    "Extension", "ComposeService", "NotebookSet", "Peer",
    "agent", "add_exchange_roles", "catalog", "exchange", "http", "log", "settings", "REPO_ROOT",
]


def agent(name: str) -> Peer:
    """A registered agent, local or remote: its name, its URL from here and from the containers."""
    from .commands import instances

    return instances.get(name, "agent").peer


def add_exchange_roles(parser: argparse.ArgumentParser) -> None:
    """--consumer and --provider, the two roles of an exchange, as every command names them."""
    parser.add_argument("--consumer", required=True, metavar="AGENT", help="the agent that negotiates and receives")
    parser.add_argument("--provider", required=True, metavar="AGENT", help="the agent whose catalog is used")


@dataclass
class ComposeService:
    """A compose stack an extension runs next to the instances.

    `name` is how eunomia status and logs call it; `ports` are the host
    ports it publishes, checked by doctor and before it starts.
    """

    name: str
    compose_file: Path
    ports: Tuple[int, ...] = ()
    label: str = ""
    # How to start it, shown by eunomia status while it is down.
    start_hint: str = ""

    @property
    def stack(self) -> Stack:
        return Stack(self.name, self.compose_file, self.ports)

    def is_running(self) -> bool:
        out = compose.compose(self.stack, "ps", "-q", "--status", "running", capture=True, check=False)
        return bool(out.strip())

    def up(self, build: bool = False) -> None:
        compose.require_docker()
        busy = compose.busy_ports(self.ports)
        if busy and not self.is_running():
            raise log.fail(f"Ports {', '.join(map(str, busy))} are in use. Free them, or move them in .env (see .env.example).")
        compose.compose(self.stack, "up", "-d", "--wait", "--remove-orphans", *(["--build"] if build else []))

    def stop(self) -> None:
        compose.compose(self.stack, "stop")

    def down(self) -> None:
        compose.compose(self.stack, "down", "--volumes", "--remove-orphans")

    def logs(self, follow: bool, tail: str, services: Sequence[str]) -> int:
        args = ["logs", "--tail", tail] + (["-f"] if follow else []) + list(services)
        return subprocess.call(compose.compose_cmd(self.stack, *args), cwd=REPO_ROOT)


@dataclass
class NotebookSet:
    """An extension's notebooks and what they read from the environment.

    The session copies these next to the core ones (01_auth.ipynb, and
    helpers.py on the path), so a notebook can `%run ./01_auth.ipynb`.
    `env` returns the extension's own variables; it may raise log.fail when
    something they need is not running. `flows` names the notebooks
    --execute runs: {"pull": "03_pull_flow.ipynb", ...}.
    """

    directory: Path
    flows: Dict[str, str]
    env: Callable[[], Dict[str, str]] = dict
    # What the notebooks need first, e.g. "eunomia demo publish <provider>".
    describe: str = ""


class Extension:
    """Subclass it, set `name` and `help`, and override what the extension provides."""

    name: str = ""
    help: str = ""

    def commands(self, parser: argparse.ArgumentParser, actions: "argparse._SubParsersAction") -> None:
        """Add actions with actions.add_parser(...) and set_defaults(run=...)."""

    def services(self) -> List[ComposeService]:
        return []

    # The test: when an extension overrides `test`, eunomia adds
    # `eunomia <name> test --consumer A --provider B` with test_arguments' options.
    def test_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Options of the test beyond --consumer and --provider."""

    def test(self, consumer: Peer, provider: Peer, args: argparse.Namespace) -> int:
        raise NotImplementedError

    def notebooks(self) -> Optional[NotebookSet]:
        return None

    # -- for the core ----------------------------------------------------------

    def has_test(self) -> bool:
        return type(self).test is not Extension.test

    def __repr__(self) -> str:
        return f"<extension {self.name}>"


@dataclass
class Loaded:
    """An extension and where it came from, for messages and docs."""

    extension: Extension
    path: Path
    builtin: bool
    services: List[ComposeService] = field(default_factory=list)
