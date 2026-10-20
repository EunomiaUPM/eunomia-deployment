"""The instances eunomia manages: authorities and agents, local or remote.

Every agent is the same thing: a DS-Agent that can publish a catalog and
negotiate in both directions. "Provider" and "consumer" are only the roles
two agents take in one exchange.

A local instance runs on this machine, from the templates in
deployment/instances/: free ports (HTTP 1600-1999, Postgres 15400-15999 by
default), its own compose project (<prefix>-<name>), containers and volumes,
and its own configuration and identity under instances/<name>/.

A remote instance is somebody's server, known by its public URL (and, to
restart it, by SSH). The commands that talk to instances (onboard, connect,
catalog, e2e, demo) take either kind by name.

The registry is one instances/<name>/instance.env per instance.
"""

from __future__ import annotations

import json
import os
import random
import re
import shutil
import string
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Dict, List, Optional, Sequence, Tuple

from .. import compose, http, log, settings
from ..settings import CONFIG_DIR, INSTANCES_DIR, REPO_ROOT, TEMPLATES_DIR
from .onboard import Peer

NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,30}$")
RESERVED = {"all", "demo", "prod", "instances"}
READINESS = {"agent": "/api/v1/readiness", "authority": "/readiness"}
CONSOLE = {"agent": "/admin/login", "authority": "/admin/home"}


@dataclass(frozen=True)
class Instance:
    name: str
    kind: str  # agent | authority
    location: str  # local | remote
    role: str = ""  # authorities: eco | dataspace
    http_port: int = 0
    db_port: int = 0
    url: str = ""  # remote: public URL
    ssh_host: str = ""
    ssh_user: str = ""
    ssh_path: str = ""

    @property
    def local(self) -> bool:
        return self.location == "local"

    @property
    def dir(self) -> Path:
        return INSTANCES_DIR / self.name

    @property
    def container(self) -> str:
        return f"{settings.prefix()}-{self.name}"

    @property
    def project(self) -> str:
        return self.container

    @property
    def peer(self) -> Peer:
        if self.local:
            host = settings.local_host()
            return Peer(self.name, f"http://{host}:{self.http_port}", f"http://host.docker.internal:{self.http_port}")
        return Peer(self.name, self.url, self.url)

    @property
    def display_url(self) -> str:
        return settings.for_humans(self.peer.url)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def _read(name: str) -> Optional[Instance]:
    env_file = INSTANCES_DIR / name / "instance.env"
    if not env_file.is_file():
        return None
    v = settings.parse_dotenv(env_file.read_text())
    return Instance(
        name=v["INSTANCE"],
        kind=v["KIND"],
        location=v.get("LOCATION", "local"),
        role=v.get("ROLE", ""),
        http_port=int(v.get("HTTP_PORT") or 0),
        db_port=int(v.get("DB_PORT") or 0),
        url=v.get("URL", ""),
        ssh_host=v.get("SSH_HOST", ""),
        ssh_user=v.get("SSH_USER", ""),
        ssh_path=v.get("SSH_PATH", ""),
    )


def all_instances() -> List[Instance]:
    if not INSTANCES_DIR.is_dir():
        return []
    found = [_read(d.name) for d in sorted(INSTANCES_DIR.iterdir()) if d.is_dir()]
    return [i for i in found if i]


def get(name: str, kind: Optional[str] = None) -> Instance:
    inst = _read(name)
    if inst is None:
        known = ", ".join(i.name for i in all_instances()) or "none yet"
        raise log.fail(f"There is no instance called {name!r} (instances: {known}). List them with: eunomia ls")
    if kind and inst.kind != kind:
        raise log.fail(f"{name!r} is an {inst.kind}, not an {kind}")
    return inst


def authority_for(name: Optional[str]) -> Instance:
    """The named authority, or the only one there is."""
    if name:
        return get(name, "authority")
    authorities = [i for i in all_instances() if i.kind == "authority"]
    if len(authorities) == 1:
        return authorities[0]
    if not authorities:
        raise log.fail("There is no authority yet. Create one with: eunomia authority add <name>")
    names = ", ".join(i.name for i in authorities)
    raise log.fail(f"There are several authorities ({names}): say which with --authority <name>")


def issues_gaia(authority: Instance) -> bool:
    """Local authorities say their role; a remote one is assumed to be eco."""
    return not (authority.local and authority.role == "dataspace")


def _write(inst: Instance) -> None:
    fields = {
        "INSTANCE": inst.name,
        "KIND": inst.kind,
        "LOCATION": inst.location,
        "ROLE": inst.role,
        "HTTP_PORT": str(inst.http_port or ""),
        "DB_PORT": str(inst.db_port or ""),
        "URL": inst.url,
        "SSH_HOST": inst.ssh_host,
        "SSH_USER": inst.ssh_user,
        "SSH_PATH": inst.ssh_path,
    }
    if inst.kind == "agent" and inst.local:
        fields["REDIS_PASSWORD"] = "ds_core_agent_redis"
    lines = [f"{k}={v}" for k, v in fields.items() if v]
    (inst.dir / "instance.env").write_text("\n".join(lines) + "\n")


def _env(inst: Instance) -> Dict[str, str]:
    env = os.environ.copy()
    env.update(settings.parse_dotenv((inst.dir / "instance.env").read_text()))
    env["CONTAINER"] = inst.container
    return env


def _compose_cmd(inst: Instance, *args: str) -> List[str]:
    return compose.compose_files_cmd([TEMPLATES_DIR / f"docker-compose.{inst.kind}.yaml"], *args, project=inst.project)


def _compose(inst: Instance, *args: str, check: bool = True, capture: bool = False) -> str:
    return compose.run(_compose_cmd(inst, *args), check=check, env=_env(inst), capture=capture)


def _require_local(inst: Instance, action: str) -> None:
    if not inst.local:
        raise log.fail(f"{inst.name!r} is a remote instance ({inst.url}): {action} it on its server.")


# ---------------------------------------------------------------------------
# Creating instances
# ---------------------------------------------------------------------------


def _validate_new(name: str) -> None:
    if not NAME_RE.match(name):
        raise log.fail(f"{name!r} is not a valid name: lowercase letters, digits and dashes, starting with a letter (2-31 characters).")
    if name in RESERVED:
        raise log.fail(f"{name!r} is reserved: pick another name.")
    if (INSTANCES_DIR / name).exists():
        raise log.fail(f"There is already an instance called {name!r}. List them with: eunomia ls")


def _random_name(prefix: str) -> str:
    while True:
        name = f"{prefix}-{''.join(random.choices(string.ascii_lowercase + string.digits, k=4))}"
        if not (INSTANCES_DIR / name).exists():
            return name


def _taken_ports() -> List[int]:
    taken = list(settings.demo_ports())
    for inst in all_instances():
        taken += [p for p in (inst.http_port, inst.db_port) if p]
    return taken


def identity(name: str) -> Tuple[str, str]:
    """(legal name, VAT number) of a local instance, stable for a given name."""
    digits = "".join(str((ord(c) * 7 + i) % 10) for i, c in enumerate(name * 3))[:9]
    legal = "".join(part.capitalize() for part in name.split("-"))
    return legal, f"VATES-{digits.rjust(9, '0')}"


def render_agent_config(name: str, http_port: int) -> Tuple[str, str]:
    """(agent.yaml, fafnir.yaml) of a local agent, from the templates."""
    legal, vat = identity(name)
    base = CONFIG_DIR / "agent" / "standalone"
    values = {"NAME": name, "PORT": str(http_port), "LEGAL_NAME": legal, "VAT": vat}
    agent = Template((base / "agent.template.yaml").read_text()).substitute(values)
    fafnir = (base / "fafnir.template.yaml").read_text()
    return agent, fafnir


def render_authority_config(role: str, http_port: int) -> Tuple[str, str]:
    """(authority.yaml, fafnir.yaml) of a local authority, from the templates."""
    base = CONFIG_DIR / "heimdall" / "standalone"
    template = "eco_authority.template.yaml" if role == "eco" else "dataspace_authority.template.yaml"
    authority = Template((base / template).read_text()).substitute({"PORT": str(http_port)})
    return authority, (base / "fafnir.template.yaml").read_text()


def _new_vault(seed: str, name: str, dest: Path) -> None:
    """The instance's own identity: a fresh key pair and certificate.

    The DID is did:jwk, derived from the key, so every instance needs its own
    key. The authority reads the VAT number of the Gaia-X legal VC from the
    certificate's organizationIdentifier, so every instance gets its own.
    openssl comes from the postgres image every instance already pulls.
    """
    src = settings.VAULT_DIR / seed
    for sub in ("config", "secrets", "data"):
        (dest / sub).mkdir(parents=True, exist_ok=True)
    for f in (src / "config").glob("*.example"):
        shutil.copy(f, dest / "config" / f.name)
    shutil.copy(src / "secrets" / "db.json.example", dest / "secrets" / "db.json.example")

    legal, vat = identity(name)
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
    _make_writable(dest)


def _make_writable(path: Path) -> None:
    # On Linux the setup jobs run unprivileged and write derived keys here.
    if os.name != "posix":
        return
    for root, dirs, files in os.walk(path):
        for n in dirs + files:
            p = os.path.join(root, n)
            try:
                os.chmod(p, os.stat(p).st_mode | 0o666 | (0o111 if n in dirs else 0))
            except OSError:
                pass


def _create(name: Optional[str], kind: str, role: str = "") -> Instance:
    compose.require_docker()
    settings.versions()
    name = name or _random_name(kind)
    _validate_new(name)
    taken = _taken_ports()
    http_port = compose.free_port(*settings.http_ports(), exclude=taken)
    db_port = compose.free_port(*settings.db_ports(), exclude=taken + [http_port])
    inst = Instance(name, kind, "local", role=role, http_port=http_port, db_port=db_port)

    log.step(f"Creating {kind} {name!r}{f' ({role})' if role else ''}: HTTP {http_port}, Postgres {db_port}")
    (inst.dir / "config").mkdir(parents=True)
    if kind == "agent":
        config, fafnir = render_agent_config(name, http_port)
        (inst.dir / "config" / "agent.yaml").write_text(config)
        _new_vault("agent", name, inst.dir / "vault")
    else:
        config, fafnir = render_authority_config(role, http_port)
        (inst.dir / "config" / "authority.yaml").write_text(config)
        _new_vault("heimdall", name, inst.dir / "vault")
    (inst.dir / "config" / "fafnir.yaml").write_text(fafnir)
    _write(inst)
    start(inst)
    return inst


def add_agent(name: Optional[str], authority: Optional[str], onboard_it: bool) -> Instance:
    auth = authority_for(authority) if onboard_it else None
    inst = _create(name, "agent")
    if auth:
        from . import onboard

        onboard.onboard_agent(inst.peer, auth.peer, with_gaia=issues_gaia(auth))
    else:
        log.info(f"\nOnboard it with: eunomia onboard {inst.name}")
    return inst


def add_authority(name: Optional[str], role: str) -> Instance:
    inst = _create(name, "authority", role)
    log.info(f"\nCreate agents and onboard them with it: eunomia agent add <name> --authority {inst.name}")
    return inst


def add_remote(name: str, kind: str, url: str, ssh: Optional[str], path: Optional[str]) -> Instance:
    _validate_new(name)
    if not re.match(r"^https?://", url):
        raise log.fail(f"{url!r} is not a URL: give the instance's public address, e.g. https://agent.example.org")
    user, _, host = (ssh or "").rpartition("@")
    inst = Instance(name, kind, "remote", url=url.rstrip("/"), ssh_host=host, ssh_user=user, ssh_path=path or "")
    inst.dir.mkdir(parents=True)
    _write(inst)
    code = http.probe(f"{inst.url}{READINESS[kind]}")
    if code == 200:
        log.ok(f"{kind} {name!r} registered: {inst.url} is ready")
    else:
        log.warn(f"{kind} {name!r} registered, but {inst.url}{READINESS[kind]} answers {code or 'nothing'}")
    return inst


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def start(inst: Instance) -> None:
    _require_local(inst, "start")
    log.step(f"Starting {inst.kind} {inst.name} (project {inst.project})")
    _make_writable(inst.dir / "vault")
    try:
        _compose(inst, "up", "-d", "--wait")
    except log.Abort:
        raise log.fail(f"{inst.name} did not start. See why with: eunomia logs {inst.name}")
    compose.wait_http(inst.name, f"{inst.peer.url}{READINESS[inst.kind]}")
    _print(inst)


def stop(inst: Instance) -> None:
    _require_local(inst, "stop")
    _compose(inst, "stop")
    log.ok(f"{inst.name} stopped (data kept). Start it again with: eunomia up {inst.name}")


def remove(inst: Instance) -> None:
    if inst.local:
        try:
            _compose(inst, "down", "--volumes", "--remove-orphans")
        except log.Abort:
            log.warn("docker compose down failed; removing the configuration anyway")
    shutil.rmtree(inst.dir)
    log.ok(f"{inst.name} removed" + ("" if inst.local else " from the registry (the server itself is untouched)"))


def _print(inst: Instance) -> None:
    login = "   (eunomia / eunomia)" if inst.kind == "agent" else ""
    lines = [
        f"\n{inst.kind.capitalize()} {inst.name!r}:",
        f"  Console          {inst.display_url}{CONSOLE[inst.kind]}{login}",
        f"  API              {inst.display_url}/api/v1",
        f"  From containers  {inst.peer.docker_url}",
    ]
    if inst.local:
        lines.append(f"  Postgres         127.0.0.1:{inst.db_port}")
        lines.append(f"  Logs             eunomia logs {inst.name}")
    log.ok("\n".join(lines))


def state(inst: Instance) -> str:
    if not inst.local:
        code = http.probe(f"{inst.url}{READINESS[inst.kind]}")
        return "ready" if code == 200 else f"not ready ({code or 'no answer'})"
    out = compose.run(
        ["docker", "container", "inspect", "-f", "{{.State.Status}}{{if .State.Health}} ({{.State.Health.Status}}){{end}}", inst.container],
        capture=True,
        check=False,
    ).strip()
    return out or "not created"


def list_instances() -> None:
    rows = all_instances()
    if not rows:
        log.info(
            "No instances yet. Create an authority and some agents:\n"
            "  eunomia authority add authority\n"
            "  eunomia agent add alice --authority authority\n"
            "  eunomia agent add bob --authority authority"
        )
        return
    print(f"{'NAME':<18} {'KIND':<16} {'WHERE':<7} {'URL':<34} STATE")
    for i in rows:
        kind = i.kind + (f" ({i.role})" if i.role else "")
        print(f"{i.name:<18} {kind:<16} {i.location:<7} {i.display_url:<34} {state(i)}")


def containers(inst: Instance) -> List[Dict[str, str]]:
    out = _compose(inst, "ps", "-a", "--format", "json", check=False, capture=True).strip()
    if not out:
        return []
    # Compose prints a JSON array in older releases and JSON lines in newer ones.
    if out.startswith("["):
        return json.loads(out)
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def status(inst: Instance) -> None:
    if inst.local:
        rows = containers(inst)
        if not rows:
            print("    (no containers)")
        for c in rows:
            print(f"    {c.get('Name', ''):<40} {c.get('State', ''):<9} {c.get('Health') or ''}")
    _print(inst)


def logs(inst: Instance, follow: bool, tail: str, services: Sequence[str]) -> int:
    _require_local(inst, "read the logs of")
    args = ["logs", "--tail", tail] + (["-f"] if follow else []) + list(services)
    return subprocess.call(_compose_cmd(inst, *args), cwd=REPO_ROOT, env=_env(inst))


def select(names: Sequence[str]) -> List[Instance]:
    """The named instances, or every one when no name is given."""
    if names:
        return [get(n) for n in names]
    return all_instances()


def confirm(message: str, yes: bool) -> None:
    if yes:
        return
    if not sys.stdin.isatty():
        raise log.fail("Not running interactively. Re-run with --yes to confirm.")
    if input(f"{message} Type 'yes' to continue: ").strip() != "yes":
        raise log.fail("Aborted, nothing was removed.")
