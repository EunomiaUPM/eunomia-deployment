"""The demo factory: the backend an agent can share, and ways to use it.

  up / down  start or remove the factory (its APIs, database and Keycloak)
  robots     negotiate between two agents, pull the robots through the one
             that publishes the factory, print them as JSON
  events     negotiate, open a push transfer to a local endpoint and print the
             robot events as they arrive, until Ctrl+C
  token      a Keycloak token for the factory, to call its API directly
             (without the data space: what the publishing agent does)
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from typing import Optional
from urllib.parse import urlencode

from .. import compose, http, log, settings
from ..settings import Demo, REPO_ROOT
from . import e2e
from .onboard import Peer


def up(build: bool) -> None:
    compose.require_docker()
    stack = settings.demo_stack()
    busy = compose.busy_ports(stack.ports)
    running = compose.run(["docker", "ps", "-q", "--filter", f"name=^/{settings.container_prefix()}factory-"], capture=True, check=False)
    if busy and not running.strip():
        raise log.fail(f"Ports {', '.join(map(str, busy))} are in use. Free them, or move the demo ports in .env (see .env.example).")
    log.step("Starting the demo factory (the first time this builds its image)")
    compose.compose(stack, "up", "-d", "--wait", "--remove-orphans", *(["--build"] if build else []))
    d = settings.demo()
    h = settings.for_humans
    log.ok(
        "\nDemo factory ready:\n"
        f"  robots, pull        {h(d.static_api)}/docs\n"
        f"  robot events, push  {h(d.dynamic_api)}/docs\n"
        f"  Keycloak            {h(d.keycloak)}   (admin / admin)\n"
        "Publish it from an agent: eunomia catalog populate <agent>"
    )


def down() -> None:
    compose.require_docker()
    compose.compose(settings.demo_stack(), "down", "--volumes", "--remove-orphans")
    log.ok("Demo factory removed")


def is_running() -> bool:
    out = compose.run(["docker", "ps", "-q", "--filter", f"name=^/{settings.container_prefix()}factory-"], capture=True, check=False)
    return bool(out.strip())


def logs(follow: bool, tail: str, services: "list[str]") -> int:
    args = ["logs", "--tail", tail] + (["-f"] if follow else []) + list(services)
    return subprocess.call(compose.compose_cmd(settings.demo_stack(), *args), cwd=REPO_ROOT)


def _agreement(consumer: Peer, provider: Peer, verbose: bool) -> "tuple[e2e.Session, str, list]":
    e2e.VERBOSE = verbose
    session = e2e.Session(consumer, provider)
    datasets = session.discover()
    chosen, offer = e2e._choose(session, datasets, None)
    return session, session.negotiate(offer), e2e._formats(chosen)


def robots(consumer: Peer, provider: Peer, verbose: bool) -> int:
    session, agreement, _ = _agreement(consumer, provider, verbose)
    log.step("Pull transfer")
    pids = session.request_transfer(agreement, "HTTP_PULL")
    dataplane = e2e._find_dataplane_url(session.start(pids))
    if not dataplane:
        raise log.fail("The transfer started but carried no dataplane address")
    proxy = e2e._rewrite_authority(dataplane, provider.url)
    try:
        r = http.checked("GET", proxy, timeout=90)
        log.ok(f"GET {proxy} -> {r.status}\n")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    finally:
        session.complete(pids)
    return 0


def events(consumer: Peer, provider: Peer, count: Optional[int], verbose: bool) -> int:
    session, agreement, formats = _agreement(consumer, provider, verbose)
    if "HTTP_PUSH" not in formats:
        raise log.fail("The dataset offers no HTTP_PUSH distribution")
    log.step("Push transfer")
    received = 0
    with e2e.EventSink(e2e.sink_port()) as sink:
        pids = session.request_transfer(agreement, "HTTP_PUSH", e2e.push_address(sink))
        session.start(pids)
        log.ok(f"\nRobot events pushed to {sink.docker_url}" + (f" (stopping after {count})" if count else ", Ctrl+C to stop") + "\n")
        try:
            while count is None or received < count:
                event = sink.wait(timeout=60)
                if event is None:
                    log.warn("no event in the last 60 seconds; is the demo factory up? (eunomia demo up)")
                    continue
                received += 1
                print(e2e._describe(event), flush=True)
        except KeyboardInterrupt:
            print(file=sys.stderr)
        finally:
            log.step(f"Completing the transfer: {provider.name} unsubscribes from the factory")
            session.complete(pids)
    log.ok(f"{received} event(s) received")
    return 0


def token(demo: Demo) -> int:
    form = urlencode(
        {
            "grant_type": "password",
            "client_id": demo.client_id,
            "client_secret": demo.client_secret,
            "username": demo.username,
            "password": demo.password,
        }
    ).encode()
    req = urllib.request.Request(demo.token_url, data=form, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            access = json.loads(r.read())["access_token"]
    except OSError as e:
        raise log.fail(f"POST {demo.token_url} -> {e}. Is the demo factory up? (eunomia demo up)")
    print(access)
    log.info(f"\ncurl -H \"Authorization: Bearer $TOKEN\" {settings.for_humans(demo.static_api)}/robots/")
    log.info("The token expires after 5 minutes.")
    return 0
