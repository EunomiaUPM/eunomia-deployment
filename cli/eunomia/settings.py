"""Where things live: repo paths, stacks per environment, and participant URLs.

Two environments exist:

  standalone  all three participants and the demo backend on this host,
              fake vault, did:web on host.docker.internal.
  prod        one participant per server, real Vault, did:web on a domain.
              `up` runs on the target server itself; the URLs of the other
              participants come from the repo-root .env.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

from . import log

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOYMENT_DIR = REPO_ROOT / "deployment"
VAULT_DIR = REPO_ROOT / "vault"
CATALOG_DIR = REPO_ROOT / "static" / "catalog"
DEMO_DIR = REPO_ROOT / "services" / "demo-factory"
INSTANCES_DIR = REPO_ROOT / "instances"
VERSIONS_FILE = REPO_ROOT / "versions.env"
ENV_FILE = REPO_ROOT / ".env"

ENVIRONMENTS = ("standalone", "prod")
DATASPACE_NODES = ("authority", "provider", "consumer")
# The demo backend is not a participant: it is what the provider shares.
ALL_NODES = DATASPACE_NODES + ("demo",)


def prefix() -> str:
    """Container and project name prefix (EUNOMIA_PREFIX, default eunomia)."""
    return os.environ.get("EUNOMIA_PREFIX") or "eunomia"


def container_prefix() -> str:
    # Every standalone container is named <prefix>-*, which is what teardown sweeps.
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


@dataclass(frozen=True)
class Stack:
    node: str
    compose: Path
    # Host ports the stack publishes; checked before `up` and after `down`.
    ports: Tuple[int, ...]
    # Path appended to the node URL that answers 200 once the node is ready.
    readiness: Optional[str]
    # Agent service in the compose file, and its wallet. Used by `restart`.
    service: Optional[str] = None
    wallet: Optional[str] = None


def demo_ports() -> Tuple[int, int, int]:
    return (
        port("EUNOMIA_FACTORY_STATIC_PORT", 1210),
        port("EUNOMIA_FACTORY_DYNAMIC_PORT", 1220),
        port("EUNOMIA_FACTORY_KEYCLOAK_PORT", 1230),
    )


def stacks(env: str) -> Dict[str, Stack]:
    demo = Stack("demo", DEMO_DIR / "docker-compose.yaml", demo_ports(), None)
    if env == "standalone":
        d = DEPLOYMENT_DIR / "standalone"
        return {
            "authority": Stack(
                "authority",
                d / "docker-compose.standalone.heimdall.yaml",
                (1500, port("EUNOMIA_AUTHORITY_DB_PORT", 1450)),
                "/readiness",
                "heimdall",
                "heimdall-fafnir-wallet",
            ),
            "provider": Stack(
                "provider",
                d / "docker-compose.standalone.provider.yaml",
                (1200, port("EUNOMIA_PROVIDER_DB_PORT", 1400)),
                "/api/v1/readiness",
                "provider",
                "provider-fafnir-wallet",
            ),
            "consumer": Stack(
                "consumer",
                d / "docker-compose.standalone.consumer.yaml",
                (1100, port("EUNOMIA_CONSUMER_DB_PORT", 1300)),
                "/api/v1/readiness",
                "consumer",
                "consumer-fafnir-wallet",
            ),
            "demo": demo,
        }
    d = DEPLOYMENT_DIR / "prod"
    return {
        "authority": Stack(
            "authority",
            d / "docker-compose.heimdall.yaml",
            (443, 8443, 8200),
            "/readiness",
            "heimdall",
            "heimdall-fafnir-wallet",
        ),
        "provider": Stack(
            "provider",
            d / "docker-compose.provider.yaml",
            (443, 8200),
            "/api/v1/readiness",
            "provider",
            "provider-fafnir-wallet",
        ),
        "consumer": Stack(
            "consumer",
            d / "docker-compose.consumer.yaml",
            (443, 8200),
            "/api/v1/readiness",
            "consumer",
            "consumer-fafnir-wallet",
        ),
        "demo": demo,
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
# Participant URLs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Endpoints:
    """How to reach each participant.

    The plain URLs are how this process reaches the agents. The docker_* ones
    are how the agents reach each other: those travel inside DSP and GNAP
    messages, so in standalone 127.0.0.1 there would point a container at
    itself. In prod both are the public URL.
    """

    authority: str
    provider: str
    consumer: str
    docker_authority: str
    docker_provider: str
    docker_consumer: str

    def url(self, node: str) -> str:
        return getattr(self, node)

    def docker_url(self, node: str) -> str:
        return getattr(self, f"docker_{node}")


STANDALONE_PORTS = {"authority": 1500, "provider": 1200, "consumer": 1100}


def _standalone_defaults() -> Dict[str, str]:
    host = local_host()
    out = {f"{n.upper()}_URL": f"http://{host}:{p}" for n, p in STANDALONE_PORTS.items()}
    out.update({f"DOCKER_{n.upper()}_URL": f"http://host.docker.internal:{p}" for n, p in STANDALONE_PORTS.items()})
    return out


def node_url(env: str, node: str) -> str:
    """One participant's URL. Unlike endpoints(), needs only that node's setting."""
    name = f"{node.upper()}_URL"
    if env == "standalone":
        return (os.environ.get(name) or _standalone_defaults()[name]).rstrip("/")
    value = os.environ.get(name)
    if not value:
        raise log.fail(f"{name} is not set. Prod has no default URLs: add it to .env.")
    return value.rstrip("/")


def endpoints(env: str) -> Endpoints:
    def pick(name: str, fallback: Optional[str] = None) -> str:
        value = os.environ.get(name) or fallback
        if not value:
            raise log.fail(f"{name} is not set. Prod has no default URLs: add it to .env.")
        return value.rstrip("/")

    if env == "standalone":
        defaults = _standalone_defaults()
        return Endpoints(
            *(pick(f"{n.upper()}_URL", defaults[f"{n.upper()}_URL"]) for n in DATASPACE_NODES),
            *(pick(f"DOCKER_{n.upper()}_URL", defaults[f"DOCKER_{n.upper()}_URL"]) for n in DATASPACE_NODES),
        )

    authority, provider, consumer = (pick(f"{n}_URL") for n in ("AUTHORITY", "PROVIDER", "CONSUMER"))
    return Endpoints(
        authority,
        provider,
        consumer,
        pick("DOCKER_AUTHORITY_URL", authority),
        pick("DOCKER_PROVIDER_URL", provider),
        pick("DOCKER_CONSUMER_URL", consumer),
    )


# ---------------------------------------------------------------------------
# Demo backend (the factory the provider shares)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Demo:
    """The factory's URLs, seen from this process and from the provider agent.

    The docker_* ones go into the connector instances: the provider agent is
    the one that calls the factory, from inside its container.
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
