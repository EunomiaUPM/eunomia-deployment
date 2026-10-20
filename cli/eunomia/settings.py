"""Where things live: repo paths, the demo backend, the prod stacks, settings.

eunomia is a hypervisor of instances: authorities and agents. Local ones run
on this machine from the templates in deployment/instances/; remote ones are
somebody's server, known by URL. The registry is instances/ (see
commands/instances.py). Nothing here assumes a fixed set of participants.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

from . import log

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOYMENT_DIR = REPO_ROOT / "deployment"
TEMPLATES_DIR = DEPLOYMENT_DIR / "instances"
VAULT_DIR = REPO_ROOT / "vault"
CONFIG_DIR = REPO_ROOT / "static" / "config"
CATALOG_DIR = REPO_ROOT / "static" / "catalog"
DEMO_DIR = REPO_ROOT / "services" / "demo-factory"
INSTANCES_DIR = REPO_ROOT / "instances"
VERSIONS_FILE = REPO_ROOT / "versions.env"
ENV_FILE = REPO_ROOT / ".env"

KINDS = ("agent", "authority")


def prefix() -> str:
    """Container and project name prefix (EUNOMIA_PREFIX, default eunomia)."""
    return os.environ.get("EUNOMIA_PREFIX") or "eunomia"


def container_prefix() -> str:
    # Every local container is named <prefix>-*, which is what `down` sweeps.
    return f"{prefix()}-"


def local_host() -> str:
    """How this process reaches what Docker publishes.

    127.0.0.1 on the host. Inside the tools container that address is the
    container itself, so the wrappers set EUNOMIA_HOST=host.docker.internal.
    """
    return os.environ.get("EUNOMIA_HOST") or "127.0.0.1"


def for_humans(url: str) -> str:
    """A URL as the person at this machine opens it: from the tools container
    the CLI reaches the host as host.docker.internal, a browser as 127.0.0.1."""
    host = local_host()
    return url.replace(f"//{host}:", "//127.0.0.1:") if host != "127.0.0.1" else url


def port(name: str, default: int) -> int:
    value = os.environ.get(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        raise log.fail(f"{name}={value!r} is not a port number")


def port_range(name: str, default: str) -> Tuple[int, int]:
    value = os.environ.get(name) or default
    try:
        lo, hi = (int(x) for x in value.split("-", 1))
        return lo, hi
    except ValueError:
        raise log.fail(f"{name}={value!r}: expected a range like {default}")


def http_ports() -> Tuple[int, int]:
    """Where local instances get their HTTP port."""
    return port_range("EUNOMIA_HTTP_PORTS", "1600-1999")


def db_ports() -> Tuple[int, int]:
    """Where local instances get their Postgres port."""
    return port_range("EUNOMIA_DB_PORTS", "15400-15999")


@dataclass(frozen=True)
class Stack:
    name: str
    compose: Path
    # Host ports the stack publishes; checked before starting it.
    ports: Tuple[int, ...]


def demo_ports() -> Tuple[int, int, int]:
    return (
        port("EUNOMIA_FACTORY_STATIC_PORT", 1210),
        port("EUNOMIA_FACTORY_DYNAMIC_PORT", 1220),
        port("EUNOMIA_FACTORY_KEYCLOAK_PORT", 1230),
    )


def demo_stack() -> Stack:
    return Stack("demo", DEMO_DIR / "docker-compose.yaml", demo_ports())


def prod_stacks() -> Dict[str, Stack]:
    """One node per server: `eunomia prod up agent|authority` on that server."""
    d = DEPLOYMENT_DIR / "prod"
    return {
        "agent": Stack("agent", d / "docker-compose.agent.yaml", (443, 8200)),
        "authority": Stack("authority", d / "docker-compose.heimdall.yaml", (443, 8443, 8200)),
    }


# ---------------------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------------------


def parse_dotenv(text: str) -> Dict[str, str]:
    """Parse KEY=VALUE lines.

    Quoted values are taken verbatim. In unquoted ones a ' #' starts an inline
    comment, but a bare '#' is kept so passwords containing it survive.
    """
    out: Dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export ") :].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        else:
            for marker in (" #", "\t#"):
                if marker in value:
                    value = value.split(marker, 1)[0].rstrip()
        out[key] = value
    return out


def load_env() -> None:
    """Load the repo-root .env into os.environ without overriding the shell."""
    if not ENV_FILE.is_file():
        return
    for key, value in parse_dotenv(ENV_FILE.read_text()).items():
        os.environ.setdefault(key, value)


def versions() -> Dict[str, str]:
    """The image pins in versions.env."""
    if not VERSIONS_FILE.is_file():
        raise log.fail(f"{VERSIONS_FILE.name} is missing from {REPO_ROOT}. It pins the EUNOMIA images.")
    return parse_dotenv(VERSIONS_FILE.read_text())


# ---------------------------------------------------------------------------
# Demo backend (the factory an agent can share)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Demo:
    """The factory's URLs, seen from this process and from the agents.

    The docker_* ones go into the connector instances: the agent that shares
    the factory is the one that calls it, from inside its container.
    """

    static_api: str
    dynamic_api: str
    keycloak: str
    docker_static_api: str
    docker_dynamic_api: str
    docker_keycloak: str

    # Demo credentials, the same ones imported with the Keycloak realm.
    realm: str = "factory"
    client_id: str = "factory-client"
    client_secret: str = "factory-secret"
    username: str = "testuser"
    password: str = "password"

    @property
    def token_url(self) -> str:
        return f"{self.keycloak}/realms/{self.realm}/protocol/openid-connect/token"


def demo() -> Demo:
    host = local_host()
    static, dynamic, keycloak = demo_ports()

    def url(name: str, default: str) -> str:
        return (os.environ.get(name) or default).rstrip("/")

    return Demo(
        url("FACTORY_STATIC_URL", f"http://{host}:{static}"),
        url("FACTORY_DYNAMIC_URL", f"http://{host}:{dynamic}"),
        url("FACTORY_KEYCLOAK_URL", f"http://{host}:{keycloak}"),
        url("DOCKER_FACTORY_STATIC_URL", f"http://host.docker.internal:{static}"),
        url("DOCKER_FACTORY_DYNAMIC_URL", f"http://host.docker.internal:{dynamic}"),
        url("DOCKER_FACTORY_KEYCLOAK_URL", f"http://host.docker.internal:{keycloak}"),
    )


def optional(name: str) -> Optional[str]:
    value = os.environ.get(name)
    return value or None
