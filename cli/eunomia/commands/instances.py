"""Extra connectors and authorities, next to the standalone deployment.

Each instance gets free ports (HTTP 1600-1999, Postgres 15400-15999 by
default), its own compose project (eunomia-<name>) with its own containers
and volumes, and its own configuration and identity under instances/<name>/.

Its configuration is generated from the standalone one: same agent settings,
its own port, and the service names of deployment/instances/*.yaml (db,
redis, wallet) as hostnames. So a change to the standalone configs reaches
new instances too.

The names consumer, provider and authority refer to the standalone
participants wherever a command takes a participant.
"""

from __future__ import annotations

import os
import random
import re
import shutil
import string
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .. import compose, log, settings
from ..settings import INSTANCES_DIR, REPO_ROOT
from . import onboard
from .onboard import Peer
from .stack import containers, print_containers

TEMPLATES = settings.DEPLOYMENT_DIR / "instances"
RESERVED = {"consumer", "provider", "authority", "heimdall", "demo", "standalone", "all", "instances"}
NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,30}$")
STANDALONE_DB_PORTS = {"authority": 1450, "provider": 1400, "consumer": 1300}


@dataclass(frozen=True)
class Instance:
    name: str
    kind: str  # connector | authority
    role: str  # consumer | provider | eco | dataspace
    http_port: int
    db_port: int

    @property
    def dir(self) -> Path:
        return INSTANCES_DIR / self.name

    @property
    def project(self) -> str:
        return f"{settings.prefix()}-{self.name}"

    @property
    def peer(self) -> Peer:
        host = settings.local_host()
        return Peer(self.name, f"http://{host}:{self.http_port}", f"http://host.docker.internal:{self.http_port}")


# ---------------------------------------------------------------------------
# Registry: one instances/<name>/instance.env per instance
# ---------------------------------------------------------------------------


def _read(name: str) -> Optional[Instance]:
    env_file = INSTANCES_DIR / name / "instance.env"
    if not env_file.is_file():
        return None
    v = settings.parse_dotenv(env_file.read_text())
    return Instance(v["INSTANCE"], v["KIND"], v["ROLE"], int(v["HTTP_PORT"]), int(v["DB_PORT"]))


def all_instances() -> List[Instance]:
    if not INSTANCES_DIR.is_dir():
        return []
    found = [_read(d.name) for d in sorted(INSTANCES_DIR.iterdir()) if d.is_dir()]
    return [i for i in found if i]


def get(name: str) -> Instance:
    inst = _read(name)
    if inst is None:
        known = ", ".join(i.name for i in all_instances()) or "none yet"
        raise log.fail(f"There is no instance called {name!r} (instances: {known}). List them with: eunomia instances")
    return inst


def _write(inst: Instance) -> None:
    lines = [
        f"INSTANCE={inst.name}",
        f"KIND={inst.kind}",
        f"ROLE={inst.role}",
        f"HTTP_PORT={inst.http_port}",
        f"DB_PORT={inst.db_port}",
    ]
    if inst.kind == "connector":
        lines.append(f"REDIS_PASSWORD=ds_core_{inst.role}_redis")
    (inst.dir / "instance.env").write_text("\n".join(lines) + "\n")


def resolve(name: str) -> Tuple[str, Peer]:
    """(kind, peer) of a standalone participant or an instance."""
    if name in ("authority", "heimdall"):
        ep = settings.endpoints("standalone")
        return "authority", Peer("authority", ep.authority, ep.docker_authority)
    if name in ("provider", "consumer"):
        ep = settings.endpoints("standalone")
        return "connector", Peer(name, ep.url(name), ep.docker_url(name))
    inst = get(name)
    return inst.kind, inst.peer


def _compose_cmd(inst: Instance, *args: str) -> List[str]:
    return compose.compose_files_cmd([TEMPLATES / f"docker-compose.{inst.kind}.yaml"], *args, project=inst.project)


def _compose(inst: Instance, *args: str, check: bool = True) -> None:
    env = os.environ.copy()
    env.update(settings.parse_dotenv((inst.dir / "instance.env").read_text()))
    compose.run(_compose_cmd(inst, *args), check=check, env=env)


# ---------------------------------------------------------------------------
# Creating an instance
# ---------------------------------------------------------------------------


def _port_range(var: str, default: str) -> Tuple[int, int]:
    value = os.environ.get(var) or default
    try:
        lo, hi = (int(x) for x in value.split("-", 1))
        return lo, hi
    except ValueError:
        raise log.fail(f"{var}={value!r}: expected a range like {default}")


def _taken_ports() -> List[int]:
    taken = [p for s in settings.stacks("standalone").values() for p in s.ports]
    for inst in all_instances():
        taken += [inst.http_port, inst.db_port]
    return taken


def _validate(name: str) -> None:
    if not NAME_RE.match(name):
        raise log.fail(f"{name!r} is not a valid name: lowercase letters, digits and dashes, starting with a letter (2-31 characters).")
    if name in RESERVED:
        raise log.fail(f"{name!r} is reserved for the standalone deployment.")
    if (INSTANCES_DIR / name).exists():
        raise log.fail(f"There is already an instance called {name!r}. List them with: eunomia instances")
    if compose.run(["docker", "ps", "-aq", "--filter", f"name=^/{name}$"], capture=True, check=False).strip():
        raise log.fail(f"There is already a Docker container called {name!r}.")


def _random_name(prefix: str) -> str:
    while True:
        name = f"{prefix}-{''.join(random.choices(string.ascii_lowercase + string.digits, k=4))}"
        if not (INSTANCES_DIR / name).exists():
            return name


def _identity(name: str) -> Tuple[str, str]:
    """(legal name, VAT number) of an instance, stable for a given name."""
    digits = "".join(str((ord(c) * 7 + i) % 10) for i, c in enumerate(name * 3))[:9]
    legal = "".join(part.capitalize() for part in name.split("-"))
    return legal, f"VATES-{digits.rjust(9, '0')}"


def _new_vault(role: str, name: str, dest: Path) -> None:
    """The instance's own identity: a fresh key pair and certificate.

    Copying the example keys would give the instance the same did:jwk as the
    standalone participant of its role, since the DID is derived from the key.
    The authority reads the VAT number of the Gaia-X legal VC from the
    certificate's organizationIdentifier, so every instance gets its own.
    openssl comes from the postgres image every stack already pulls.
    """
    src = settings.VAULT_DIR / role
    for sub in ("config", "secrets", "data"):
        (dest / sub).mkdir(parents=True, exist_ok=True)
    for f in (src / "config").glob("*.example"):
        shutil.copy(f, dest / "config" / f.name)
    shutil.copy(src / "secrets" / "db.json.example", dest / "secrets" / "db.json.example")

    legal, vat = _identity(name)
    subject = f"/CN={legal}.local/O={legal}/C=ES/organizationIdentifier={vat}"
    script = (
        "set -e; cd /out; "
        "openssl req -x509 -newkey rsa:2048 -nodes -days 365 "
        f"-keyout private_key.pem.example -out cert.pem.example -subj '{subject}' "
        "-addext basicConstraints=critical,CA:TRUE 2>/dev/null; "
        "openssl pkey -in private_key.pem.example -pubout -out public_key.pem.example; "
        "chmod 666 *.example"
    )
    compose.run(
        ["docker", "run", "--rm", "-v", f"{(dest / 'secrets').resolve()}:/out", "postgres:18", "sh", "-c", script],
        capture=True,
    )
    if os.name == "posix":
        # The setup jobs run unprivileged and write the generated keys here.
        for root, dirs, files in os.walk(dest):
            for n in dirs + files:
                p = os.path.join(root, n)
                try:
                    os.chmod(p, os.stat(p).st_mode | 0o666 | (0o111 if n in dirs else 0))
                except OSError:
                    pass


GAIA_NAMES = {"consumer": ("EunomiaConsumer", "VATES-123456789"), "provider": ("EunomiaProvider", "VATES-987654321")}


def render_connector_config(role: str, http_port: int, name: str = "") -> Tuple[str, str]:
    """(agent.yaml, fafnir.yaml) for a connector, from the standalone ones."""
    base = settings.REPO_ROOT / "static" / "config" / role / "standalone"
    standalone_port = settings.STANDALONE_PORTS[role]
    agent = (base / f"standalone.{role}.yaml").read_text()
    agent = agent.replace(f'"{role}-fafnir-wallet"', '"wallet"').replace(f'"{role}-redis"', '"redis"')
    agent = agent.replace(f'"{role}-db"', '"db"').replace(f'"{standalone_port}"', f'"{http_port}"')
    if name:
        # The Gaia-X legal person the instance declares, matching its certificate.
        legal, vat = _identity(name)
        old_legal, old_vat = GAIA_NAMES[role]
        agent = agent.replace(f'"{old_legal}"', f'"{legal}"').replace(f'"{old_vat}"', f'"{vat}"')
    fafnir = (base / f"fafnir.{role}.yaml").read_text().replace(f'"{role}-db"', '"db"')
    return agent, fafnir


def render_authority_config(role: str, http_port: int) -> Tuple[str, str]:
    """(authority.yaml, fafnir.yaml) for an authority, from the standalone ones."""
    base = settings.REPO_ROOT / "static" / "config" / "heimdall" / "standalone"
    source = "standalone.eco_authority.yaml" if role == "eco" else "standalone.authority.yaml"
    authority = (base / source).read_text()
    authority = authority.replace("'heimdall-fafnir-wallet'", "'wallet'").replace("'heimdall-db'", "'db'")
    authority = authority.replace("'1500'", f"'{http_port}'")
    fafnir = (base / "fafnir.heimdall.yaml").read_text().replace('"heimdall-db"', '"db"').replace("'heimdall-db'", "'db'")
    return authority, fafnir


def _create(name: Optional[str], kind: str, role: str) -> Instance:
    compose.require_docker()
    settings.versions()
    name = name or _random_name("conn" if kind == "connector" else "auth")
    _validate(name)
    taken = _taken_ports()
    http_port = compose.free_port(*_port_range("EUNOMIA_HTTP_PORTS", "1600-1999"), exclude=taken)
    db_port = compose.free_port(*_port_range("EUNOMIA_DB_PORTS", "15400-15999"), exclude=taken + [http_port])
    inst = Instance(name, kind, role, http_port, db_port)

    log.step(f"Creating {kind} {name!r} ({role}) in instances/{name}: HTTP {http_port}, Postgres {db_port}")
    (inst.dir / "config").mkdir(parents=True)
    if kind == "connector":
        agent, fafnir = render_connector_config(role, http_port, name)
        (inst.dir / "config" / "agent.yaml").write_text(agent)
        _new_vault(role, name, inst.dir / "vault")
    else:
        agent, fafnir = render_authority_config(role, http_port)
        (inst.dir / "config" / "authority.yaml").write_text(agent)
        _new_vault("heimdall", name, inst.dir / "vault")
    (inst.dir / "config" / "fafnir.yaml").write_text(fafnir)
    _write(inst)

    _start(inst)
    return inst


def _start(inst: Instance) -> None:
    log.step(f"Starting {inst.name} (project {inst.project})")
    try:
        _compose(inst, "up", "-d", "--wait")
    except log.Abort:
        raise log.fail(f"{inst.name} did not start. See why with: eunomia logs {inst.name}   (remove it with: eunomia rm {inst.name})")
    readiness = "/readiness" if inst.kind == "authority" else "/api/v1/readiness"
    compose.wait_http(inst.name, f"{inst.peer.url}{readiness}")
    _print(inst)


def _print(inst: Instance) -> None:
    console = "/admin/home" if inst.kind == "authority" else "/admin/login"
    login = "" if inst.kind == "authority" else "   (eunomia / eunomia)"
    url = settings.for_humans(inst.peer.url)
    log.ok(
        f"\n{inst.kind.capitalize()} {inst.name!r} ({inst.role}):\n"
        f"  Console          {url}{console}{login}\n"
        f"  API              {url}/api/v1\n"
        f"  From containers  {inst.peer.docker_url}\n"
        f"  Postgres         127.0.0.1:{inst.db_port}\n"
        f"  Logs             eunomia logs {inst.name}"
    )


def add_connector(name: Optional[str], role: str, onboard_it: bool, authority: str) -> None:
    if onboard_it:
        kind, _ = resolve(authority)
        if kind != "authority":
            raise log.fail(f"{authority!r} is not an authority")
    inst = _create(name, "connector", role)
    if onboard_it:
        register(inst.name, authority)
    else:
        log.info(f"\nRegister it with the standalone authority: eunomia register {inst.name}")


def add_authority(name: Optional[str], role: str) -> None:
    inst = _create(name, "authority", role)
    log.info(f"\nRegister a connector with it: eunomia register <connector> --authority {inst.name}")


# ---------------------------------------------------------------------------
# Onboarding between any participants
# ---------------------------------------------------------------------------


def _expect(name: str, kind: str) -> Peer:
    actual, peer = resolve(name)
    if actual != kind:
        raise log.fail(f"{name!r} is not a {kind}")
    return peer


def register(connector: str, authority: str = "authority") -> None:
    participant = _expect(connector, "connector")
    auth = _expect(authority, "authority")
    onboard.link_wallets([auth, participant])
    onboard.register(participant, auth)


def connect(consumer: str, provider: str) -> None:
    c, p = _expect(consumer, "connector"), _expect(provider, "connector")
    onboard.link_wallets([c, p])
    onboard.connect(c, p)


def gaia(consumer: str, provider: Optional[str], authority: str) -> None:
    c = _expect(consumer, "connector")
    a = _expect(authority, "authority")
    onboard.link_wallets([a, c])
    onboard.gaia(c, a)
    if provider:
        onboard.connect(c, _expect(provider, "connector"))


# ---------------------------------------------------------------------------
# list, status, logs, start, stop, rm
# ---------------------------------------------------------------------------


def _state(name: str) -> str:
    out = compose.run(
        ["docker", "container", "inspect", "-f", "{{.State.Status}}{{if .State.Health}} ({{.State.Health.Status}}){{end}}", name],
        capture=True,
        check=False,
    ).strip()
    return out or "not created"


def list_instances() -> None:
    compose.require_docker()
    rows = all_instances()
    print(f"{'NAME':<20} {'KIND':<10} {'ROLE':<10} {'HTTP':<6} {'PG':<6} STATE")
    for i in rows:
        print(f"{i.name:<20} {i.kind:<10} {i.role:<10} {i.http_port:<6} {i.db_port:<6} {_state(i.name)}")
    if not rows:
        print("(no instances: create one with eunomia connector add, or eunomia authority add)")
    p = settings.prefix()
    print(
        f"\nStandalone: authority {_state(p + '-authority-heimdall')}, "
        f"provider {_state(p + '-provider')}, consumer {_state(p + '-consumer')}"
    )


def status(name: str) -> None:
    inst = get(name)
    env = os.environ.copy()
    env.update(settings.parse_dotenv((inst.dir / "instance.env").read_text()))
    os.environ.update(env)
    print_containers(containers(_compose_cmd(inst)))
    _print(inst)


def logs(name: str, follow: bool, tail: str, services: List[str]) -> int:
    inst = get(name)
    env = os.environ.copy()
    env.update(settings.parse_dotenv((inst.dir / "instance.env").read_text()))
    args = ["logs", "--tail", tail] + (["-f"] if follow else []) + services
    return subprocess.call(_compose_cmd(inst, *args), cwd=REPO_ROOT, env=env)


def start(name: str) -> None:
    compose.require_docker()
    _start(get(name))


def stop(name: str) -> None:
    compose.require_docker()
    inst = get(name)
    _compose(inst, "stop")
    log.ok(f"{name} stopped (data kept). Start it again with: eunomia start {name}")


def remove(name: str, yes: bool) -> None:
    compose.require_docker()
    if not (INSTANCES_DIR / name).exists():
        raise log.fail(f"There is no instance called {name!r}. List them with: eunomia instances")
    if not yes:
        if not sys.stdin.isatty():
            raise log.fail("Not running interactively. Re-run with --yes to confirm.")
        if input(f"This removes the containers, volumes and configuration of {name!r}. Type 'yes': ").strip() != "yes":
            raise log.fail("Aborted, nothing was removed.")
    inst = _read(name)
    if inst:
        try:
            _compose(inst, "down", "--volumes", "--remove-orphans")
        except log.Abort:
            log.warn("docker compose down failed; removing the configuration anyway")
    shutil.rmtree(INSTANCES_DIR / name)
    log.ok(f"{name} removed")


def is_instance(name: str) -> bool:
    return _read(name) is not None


def instance_names() -> Dict[str, Instance]:
    return {i.name: i for i in all_instances()}
