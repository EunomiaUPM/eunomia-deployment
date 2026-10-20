"""Try the demo factory through the dataspace, the way a consumer application would.

  robots   negotiate, pull the robots through the provider, print them as JSON
  events   negotiate, open a push transfer to a local endpoint and print the
           robot events as they arrive, until Ctrl+C
  token    a Keycloak token for the factory, to call its API directly
           (without the dataspace: what the provider does behind the scenes)
"""

from __future__ import annotations

import json
import sys
import urllib.request
from typing import Optional
from urllib.parse import urlencode

from .. import http, log, settings
from ..settings import Demo, Endpoints
from . import e2e


def _agreement(ep: Endpoints, verbose: bool) -> "tuple[e2e.Session, str, list]":
    e2e.VERBOSE = verbose
    session = e2e.Session(ep)
    datasets = session.discover()
    chosen, offer = e2e._choose(session, datasets, None)
    return session, session.negotiate(offer), e2e._formats(chosen)


def robots(ep: Endpoints, verbose: bool) -> int:
    session, agreement, _ = _agreement(ep, verbose)
    log.step("Pull transfer")
    pids = session.request_transfer(agreement, "HTTP_PULL")
    dataplane = e2e._find_dataplane_url(session.start(pids))
    if not dataplane:
        raise log.fail("The transfer started but carried no dataplane address")
    proxy = e2e._rewrite_authority(dataplane, ep.provider)
    try:
        r = http.checked("GET", proxy, timeout=90)
        log.ok(f"GET {proxy} -> {r.status}\n")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    finally:
        session.complete(pids)
    return 0


def events(ep: Endpoints, count: Optional[int], verbose: bool) -> int:
    session, agreement, formats = _agreement(ep, verbose)
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
                    log.warn("no event in the last 60 seconds; is the demo factory up? (eunomia status)")
                    continue
                received += 1
                print(e2e._describe(event), flush=True)
        except KeyboardInterrupt:
            print(file=sys.stderr)
        finally:
            log.step("Completing the transfer: the provider unsubscribes from the factory")
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
        raise log.fail(f"POST {demo.token_url} -> {e}. Is the demo up? (eunomia status)")
    print(access)
    log.info(f"\ncurl -H \"Authorization: Bearer $TOKEN\" {settings.for_humans(demo.static_api)}/robots/")
    log.info("The token expires after 5 minutes.")
    return 0
