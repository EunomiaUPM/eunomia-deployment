"""The factory through the data space, as an application would see it.

  robots   negotiate between two agents, pull the robots through the one
           that publishes the factory, print them as JSON
  events   negotiate, open a push transfer to a local endpoint and print the
           robot events as they arrive, until Ctrl+C
"""

from __future__ import annotations

import json
import sys
from typing import List, Optional, Tuple

from eunomia.ext import Peer, exchange, http, log

from . import e2e


def _agreement(consumer: Peer, provider: Peer, verbose: bool) -> Tuple[exchange.Session, str, List[str]]:
    exchange.verbose(verbose)
    s = e2e.session(consumer, provider)
    chosen, the_offer = e2e.choose(s, s.discover(), None)
    return s, s.negotiate(the_offer), exchange.formats(chosen)


def robots(consumer: Peer, provider: Peer, verbose: bool) -> int:
    s, agreement, _ = _agreement(consumer, provider, verbose)
    log.step("Pull transfer")
    pids = s.request_transfer(agreement, "HTTP_PULL")
    proxy = exchange.dataplane_url(s.start(pids), provider)
    if not proxy:
        raise log.fail("The transfer started but carried no dataplane address")
    try:
        r = http.checked("GET", proxy, timeout=90)
        log.ok(f"GET {proxy} -> {r.status}\n")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    finally:
        s.complete(pids)
    return 0


def events(consumer: Peer, provider: Peer, count: Optional[int], verbose: bool) -> int:
    s, agreement, formats = _agreement(consumer, provider, verbose)
    if "HTTP_PUSH" not in formats:
        raise log.fail("The dataset offers no HTTP_PUSH distribution")
    log.step("Push transfer")
    received = 0
    with exchange.EventSink(exchange.sink_port()) as sink:
        pids = s.request_transfer(agreement, "HTTP_PUSH", sink.data_address)
        s.start(pids)
        log.ok(f"\nRobot events pushed to {sink.docker_url}" + (f" (stopping after {count})" if count else ", Ctrl+C to stop") + "\n")
        try:
            while count is None or received < count:
                event = sink.wait(timeout=60)
                if event is None:
                    log.warn("no event in the last 60 seconds; is the demo factory up? (eunomia demo up)")
                    continue
                received += 1
                print(e2e.describe(event), flush=True)
        except KeyboardInterrupt:
            print(file=sys.stderr)
        finally:
            log.step(f"Completing the transfer: {provider.name} unsubscribes from the factory")
            s.complete(pids)
    log.ok(f"{received} event(s) received")
    return 0
