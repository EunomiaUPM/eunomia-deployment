"""The demo's end-to-end test: `eunomia demo test --consumer A --provider B`.

Any two agents will do; the provider needs the factory in its catalog
(`eunomia demo publish <provider>`).

  Discovery     participant DIDs, GNAP login, callback path, catalog request
  Negotiation   REQUESTED -> OFFERED -> REQUESTED -> OFFERED -> ACCEPTED
                -> AGREED -> VERIFIED -> FINALIZED -> agreement id
  Pull          REQUESTED -> STARTED -> dataplane address. A GET through the
                dataplane proxy must return the factory's robots, while the
                same factory URL without a token returns 401: together that
                proves the provider fetched the token itself and the
                consumer never saw it.
  Lifecycle     SUSPENDED -> STARTED -> COMPLETED
  Push          a second transfer on the same agreement, HTTP_PUSH: the
                provider subscribes to the factory and the robot events must
                reach a temporary HTTP endpoint this process listens on.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from eunomia.ext import Peer, exchange, http, log

from . import publish
from .factory import Factory


def add_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument("--dataset", help="substring of the dataset title (default: the demo factory dataset)")
    p.add_argument("--list-datasets", action="store_true", help="list the provider's catalog and exit")
    p.add_argument("--keep-open", action="store_true", help="leave the pull transfer STARTED")
    p.add_argument("--no-suspend", action="store_true", help="skip the suspend/resume leg")
    p.add_argument("--no-data-pull", action="store_true", help="skip the data pull through the proxy")
    p.add_argument("--no-push", action="store_true", help="skip the push transfer")
    p.add_argument("-v", "--verbose", action="store_true", help="dump every request and response")


def session(consumer: Peer, provider: Peer) -> exchange.Session:
    return exchange.Session(consumer, provider, empty_hint=f"eunomia demo publish {provider.name}")


def choose(s: exchange.Session, datasets: List[Dict[str, Any]], dataset: Optional[str]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """The dataset to negotiate (the factory's by default) and the offer to send."""
    chosen = exchange.pick_dataset(datasets, dataset or publish.title(), dataset is None)
    target = chosen["@id"]
    policy = chosen["hasPolicy"][0]
    log.info(f"Dataset  : {chosen.get('title') or target}")
    log.info(f"Target   : {target}")
    log.info(f"Policy   : {policy['@id']}")
    log.info(f"Provider : {s.provider_dsp}")
    log.info(f"Formats  : {', '.join(exchange.formats(chosen)) or 'none advertised'}")
    return chosen, exchange.offer(policy, target)


def describe(event: Any) -> str:
    if isinstance(event, dict) and "item_type" in event:
        value = event.get("last_value")
        value = f"{value:.2f}" if isinstance(value, (int, float)) else value
        return f"{event['item_type']} = {value}  ({event.get('last_measured_at')})"
    return json.dumps(event, ensure_ascii=False)[:200]


def check_pull(proxy_url: str, factory: Factory, provider: str) -> None:
    log.step("Step 5 · Pulling the robots through the dataplane proxy")
    log.info(f"GET {proxy_url}")
    r = http.request("GET", proxy_url, timeout=90)
    if not r.ok:
        raise log.fail(
            f"Dataplane proxy -> HTTP {r.status}\n{r.text[:800]}\n"
            f"{provider} could not fetch from the factory. Look at: eunomia logs {provider}  and  eunomia logs demo"
        )
    data = r.json()
    # The factory answers with a JSON array; an object here is an error
    # envelope forwarded by the proxy.
    if not isinstance(data, list):
        raise log.fail(f"Expected the factory's robot list (a JSON array), got:\n{r.text[:800]}")
    if not data:
        raise log.fail("The factory returned an empty robot list through the proxy")
    first = data[0] if isinstance(data[0], dict) else {}
    log.ok(f"Dataplane proxy -> HTTP {r.status}, {len(data)} robot(s), {len(r.body)} bytes")
    if first:
        log.info(f"      first robot: {first.get('name')} ({first.get('model')}, {first.get('line')})")

    # The positive half proves the proxy forwards. The negative half proves
    # the token was added by the provider: the same upstream refuses us.
    direct = f"{factory.static_api}/robots/"
    status = http.request("GET", direct, timeout=30).status
    if status != 401:
        raise log.fail(
            f"GET {direct} without a token -> HTTP {status}, expected 401. "
            "The factory is open, so the proxy pull proves nothing about the provider's token."
        )
    log.ok(f"      {direct} without a token -> 401: the provider added the token")


def run(consumer: Peer, provider: Peer, factory: Factory, args: argparse.Namespace) -> int:
    exchange.verbose(args.verbose)
    s = session(consumer, provider)
    datasets = s.discover()

    if args.list_datasets:
        for d in datasets:
            print(f"{d['@id']}\t{len(d.get('hasPolicy') or [])} policy(ies)\t{d.get('title')}")
        return 0

    chosen, the_offer = choose(s, datasets, args.dataset)
    title = chosen.get("title") or chosen["@id"]
    formats = exchange.formats(chosen)
    agreement = s.negotiate(the_offer)

    # -- Step 4 · Pull transfer -----------------------------------------------
    log.step("Step 4 · Pull transfer")
    pids = s.request_transfer(agreement, "HTTP_PULL")
    proxy_url = exchange.dataplane_url(s.start(pids), provider)
    log.info(f"      dataplane: {proxy_url or 'none in the start response'}")

    # -- Step 5 · Data --------------------------------------------------------
    if args.no_data_pull:
        log.info("Skipping the data pull (--no-data-pull)")
    elif not proxy_url:
        raise log.fail("The transfer started but carried no dataplane address to pull from")
    else:
        check_pull(proxy_url, factory, provider.name)

    # -- Step 6 · Lifecycle ---------------------------------------------------
    if not args.no_suspend:
        log.step("Step 6 · Suspend and resume")
        s.suspend_resume(pids)
    else:
        log.info("Skipping the suspend/resume leg (--no-suspend)")

    if args.keep_open:
        log.step("Pull transfer left open (--keep-open)")
        if proxy_url:
            log.ok(f"Dataplane proxy URL:\n  {proxy_url}")
    else:
        s.complete(pids)

    # -- Step 7 · Push transfer -----------------------------------------------
    pushed = None
    if args.no_push:
        log.info("Skipping the push transfer (--no-push)")
    elif "HTTP_PUSH" not in formats:
        log.info("The dataset offers no HTTP_PUSH distribution, so there is no push leg")
    else:
        log.step("Step 7 · Push transfer: robot events to a local endpoint")
        with exchange.EventSink(exchange.sink_port()) as sink:
            log.info(f"Listening on :{sink.port}, the consumer pushes to {sink.docker_url}")
            push_pids = s.request_transfer(agreement, "HTTP_PUSH", sink.data_address)
            s.start(push_pids)
            pushed = sink.wait(timeout=float(os.environ.get("EUNOMIA_PUSH_TIMEOUT", "30")))
            s.complete(push_pids)
        if pushed is None:
            raise log.fail(
                f"No event reached :{sink.port} within the timeout. {provider.name} subscribes to the factory and\n"
                f"forwards each event to {consumer.name}, which POSTs it to the endpoint. Look at:\n"
                f"  eunomia logs demo   eunomia logs {provider.name}   eunomia logs {consumer.name}\n"
                "On Linux, the firewall may block containers from reaching the host (allow docker0)."
            )
        log.ok(f"  event received: {describe(pushed)}")

    log.step("=" * 60)
    log.ok(
        "END-TO-END TEST PASSED\n"
        f"  Consumer   : {consumer.name}\n"
        f"  Provider   : {provider.name}\n"
        f"  Dataset    : {title}\n"
        f"  Agreement  : {agreement}\n"
        f"  Pull       : {pids['consumerPid']} / {pids['providerPid']}"
        + (f"\n  Dataplane  : {proxy_url}" if proxy_url and args.keep_open else "")
        + (f"\n  Push event : {describe(pushed)}" if pushed is not None else "")
    )
    log.step("=" * 60)
    return 0
