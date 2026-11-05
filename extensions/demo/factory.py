"""The demo factory: a backend with robots any agent can share.

  pull   GET /robots/ on the static API (:1210)
  push   POST /subscriptions/subscribe on the dynamic API (:1220), then the
         robot events, POSTed to the URL given
  auth   Keycloak (:1230), realm factory, OAuth2 password grant

The Go service and its compose file are in service/; `eunomia demo up`
builds and starts it.
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple
from urllib.parse import urlencode

from eunomia.ext import ComposeService, log, settings

HERE = Path(__file__).resolve().parent


def ports() -> Tuple[int, int, int]:
    return (
        settings.port("EUNOMIA_FACTORY_STATIC_PORT", 1210),
        settings.port("EUNOMIA_FACTORY_DYNAMIC_PORT", 1220),
        settings.port("EUNOMIA_FACTORY_KEYCLOAK_PORT", 1230),
    )


def service() -> ComposeService:
    return ComposeService(
        name="demo",
        compose_file=HERE / "service" / "docker-compose.yaml",
        ports=ports(),
        label="demo factory",
        start_hint="eunomia demo up",
    )


@dataclass(frozen=True)
class Factory:
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

    @property
    def docker_token_url(self) -> str:
        return f"{self.docker_keycloak}/realms/{self.realm}/protocol/openid-connect/token"


def urls() -> Factory:
    host = settings.local_host()
    static, dynamic, keycloak = ports()

    def url(name: str, default: str) -> str:
        return (os.environ.get(name) or default).rstrip("/")

    return Factory(
        url("FACTORY_STATIC_URL", f"http://{host}:{static}"),
        url("FACTORY_DYNAMIC_URL", f"http://{host}:{dynamic}"),
        url("FACTORY_KEYCLOAK_URL", f"http://{host}:{keycloak}"),
        url("DOCKER_FACTORY_STATIC_URL", f"http://host.docker.internal:{static}"),
        url("DOCKER_FACTORY_DYNAMIC_URL", f"http://host.docker.internal:{dynamic}"),
        url("DOCKER_FACTORY_KEYCLOAK_URL", f"http://host.docker.internal:{keycloak}"),
    )


def require_running() -> None:
    if not service().is_running():
        raise log.fail("The demo factory is not running: eunomia demo up")


def up(build: bool) -> int:
    log.step("Starting the demo factory (the first time this builds its image)")
    service().up(build)
    f = urls()
    h = settings.for_humans
    log.ok(
        "\nDemo factory ready:\n"
        f"  robots, pull        {h(f.static_api)}/docs\n"
        f"  robot events, push  {h(f.dynamic_api)}/docs\n"
        f"  Keycloak            {h(f.keycloak)}   (admin / admin)\n"
        "Publish it from an agent: eunomia demo publish <agent>"
    )
    return 0


def down() -> int:
    service().down()
    log.ok("Demo factory removed")
    return 0


def token() -> int:
    """A Keycloak token for the factory, to call its API directly (what the publishing agent does)."""
    f = urls()
    form = urlencode(
        {
            "grant_type": "password",
            "client_id": f.client_id,
            "client_secret": f.client_secret,
            "username": f.username,
            "password": f.password,
        }
    ).encode()
    req = urllib.request.Request(f.token_url, data=form, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            access = json.loads(r.read())["access_token"]
    except OSError as e:
        raise log.fail(f"POST {f.token_url} -> {e}. Is the demo factory up? (eunomia demo up)")
    print(access)
    log.info(f"\ncurl -H \"Authorization: Bearer $TOKEN\" {settings.for_humans(f.static_api)}/robots/")
    log.info("The token expires after 5 minutes.")
    return 0
