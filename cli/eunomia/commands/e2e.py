"""End-to-end test: DSP contract negotiation, then a pull and a push transfer.

Assumes the deployment is up, onboarded and its catalog populated, which is
what `eunomia up` leaves behind. It checks those preconditions first and
names the missing one, instead of failing later with an opaque 502.

  Discovery     participant DIDs, consumer<->provider token, callback path,
                catalog request
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

The state is asserted at every step, so a call that answers 200 with an
embedded DSP rejection still fails the test.
"""

from __future__ import annotations

import json
import os
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

from .. import http, log, settings
from ..settings import Demo, Endpoints
from . import catalog as catalog_cmd

VERBOSE = False


def _dump(label: str, payload: Any) -> None:
    if VERBOSE:
        log.info(f"  {label}: {json.dumps(payload, indent=2, ensure_ascii=False)}")


def _dig(obj: Any, *keys: str) -> Any:
    for key in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def _rpc(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    _dump(f"-> {url}", payload)
    body = http.post_json(url, payload, timeout=60) or {}
    _dump("<-", body)
    return body


def _expect_state(body: Dict[str, Any], url: str, *accepted: str) -> str:
    """The state sits under different keys depending on the answer's shape."""
    state = (
        _dig(body, "response", "state")
        or _dig(body, "negotiationAgentModel", "state")
        or _dig(body, "transferAgentModel", "state")
        or _dig(body, "state")
    )
    pretty = json.dumps(body, indent=2, ensure_ascii=False)[:1500]
    if state is None:
        raise log.fail(f"{url}: no state in response\n{pretty}")
    short = state.rsplit(":", 1)[-1].upper()
    if short not in {s.upper() for s in accepted}:
        raise log.fail(f"{url}: expected {' or '.join(accepted)}, got {state}\n{pretty}")
    return short


def _pick_dataset(datasets: List[Dict[str, Any]], wanted: str, is_default: bool) -> Dict[str, Any]:
    """Datasets without a policy cannot be negotiated, so they are never candidates."""
    usable = [d for d in datasets if d.get("hasPolicy")]
    if not usable:
        raise log.fail("The catalog has no dataset with a policy. Run: eunomia catalog populate")
    needle = wanted.casefold()
    for d in usable:
        if needle in (d.get("title") or "").casefold() or needle in d.get("@id", "").casefold():
            return d
    if not is_default:
        titles = "\n".join(f"  - {d.get('title')}" for d in usable)
        raise log.fail(f"No dataset matches {wanted!r}. Available:\n{titles}")
    log.info(f"No dataset matches the default {wanted!r}, using the first one")
    return usable[0]


def _offer(policy: Dict[str, Any], target: str) -> Dict[str, Any]:
    """Echo the offer exactly as the catalog advertises it.

    Inventing permissions here would measure the agents' tolerance for
    mismatched offers instead of the real negotiation.
    """
    return {
        "@id": policy["@id"],
        "@type": "Offer",
        "target": target,
        "permission": policy.get("permission") or [],
        "obligation": policy.get("obligation") or [],
        "prohibition": policy.get("prohibition") or [],
    }


def _formats(dataset: Dict[str, Any]) -> List[str]:
    out = []
    for dist in dataset.get("distribution") or []:
        fmt = dist.get("formats") or dist.get("format") or dist.get("dctFormats")
        if fmt:
            out.append(fmt)
    return out


def _rewrite_authority(url: str, reachable_base: str) -> str:
    """Point an agent-minted URL at the address this process can reach."""
    p, b = urlsplit(url), urlsplit(reachable_base)
    return urlunsplit((b.scheme, b.netloc, p.path, p.query, p.fragment))


def _find_dataplane_url(body: Any) -> Optional[str]:
    """The data address is nested differently across agent versions; scan for it."""
    found: List[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for value in node.values():
                if isinstance(value, str) and "dataplane" in value:
                    found.append(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(body)
    return found[0] if found else None


def _check_pull(proxy_url: str, demo: Demo) -> None:
    log.step("Step 5 · Pulling the robots through the dataplane proxy")
    log.info(f"GET {proxy_url}")
    r = http.request("GET", proxy_url, timeout=90)
    if not r.ok:
        raise log.fail(
            f"Dataplane proxy -> HTTP {r.status}\n{r.text[:800]}\n"
            "The provider could not fetch from the factory. Look at: eunomia logs provider  and  eunomia logs demo"
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
    direct = f"{demo.static_api}/robots/"
    status = http.request("GET", direct, timeout=30).status
    if status != 401:
        raise log.fail(
            f"GET {direct} without a token -> HTTP {status}, expected 401. "
            "The factory is open, so the proxy pull proves nothing about the provider's token."
        )
    log.ok(f"      {direct} without a token -> 401: the provider added the token")


# ---------------------------------------------------------------------------
# Push sink
# ---------------------------------------------------------------------------


class EventSink:
    """A throwaway HTTP endpoint that collects what the dataspace pushes to it.

    It listens on every interface: the consumer agent reaches it from its
    container at http://host.docker.internal:<port>/events.
    """

    def __init__(self, port: int) -> None:
        self.port = port
        self.events: "queue.Queue[Any]" = queue.Queue()
        events = self.events

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 (http.server API)
                raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                try:
                    events.put(json.loads(raw))
                except ValueError:
                    events.put(raw.decode("utf-8", errors="replace"))
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args: Any) -> None:
                pass

        try:
            self.server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
        except OSError as e:
            raise log.fail(f"Cannot listen on port {port} for the pushed events ({e}). Set EUNOMIA_SINK_PORT to a free port.")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def docker_url(self) -> str:
        return f"http://host.docker.internal:{self.port}/events"

    def __enter__(self) -> "EventSink":
        self.thread.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.server.shutdown()
        self.server.server_close()

    def wait(self, timeout: float) -> Optional[Any]:
        try:
            return self.events.get(timeout=timeout)
        except queue.Empty:
            return None


def sink_port() -> int:
    return settings.port("EUNOMIA_SINK_PORT", 1290)


def _describe(event: Any) -> str:
    if isinstance(event, dict) and "item_type" in event:
        value = event.get("last_value")
        value = f"{value:.2f}" if isinstance(value, (int, float)) else value
        return f"{event['item_type']} = {value}  ({event.get('last_measured_at')})"
    return json.dumps(event, ensure_ascii=False)[:200]


# ---------------------------------------------------------------------------
# Transfers
# ---------------------------------------------------------------------------


class Session:
    """One consumer<->provider pair after discovery: what every transfer needs."""

    def __init__(self, ep: Endpoints) -> None:
        self.ep = ep
        self.consumer = ep.consumer
        self.provider = ep.provider
        self.provider_did = ""
        self.provider_dsp = ""
        self.callback = ""

    def discover(self) -> List[Dict[str, Any]]:
        log.step("Step 1 · Discovering participants")
        consumer_did = http.get_json(f"{self.consumer}/api/v1/mates/myself")["participant_id"]
        self.provider_did = http.get_json(f"{self.provider}/api/v1/mates/myself")["participant_id"]
        log.info(f"Consumer DID : {consumer_did}")
        log.info(f"Provider DID : {self.provider_did}")

        mates = http.get_json(f"{self.consumer}/api/v1/mates/all") or []
        if not any(m.get("participant_id") == self.provider_did and (m.get("token") or "") for m in mates):
            raise log.fail("The consumer holds no token for the provider. Run: eunomia onboard")
        log.ok("Consumer is connected to the provider")

        version = http.get_json(f"{self.consumer}/.well-known/dspace-version/2025-1")
        self.callback = self.ep.docker_consumer + version["path"]
        log.info(f"Consumer callback: {self.callback}")

        log.step("Step 2 · Requesting the provider catalog")
        cat = _rpc(
            f"{self.consumer}/dsp/current/catalog/rpc/setup-catalog-request",
            {"associatedAgentPeer": self.provider_did, "filter": [], "noCache": True},
        )
        response = cat.get("response") or {}
        datasets = response.get("dataset") or []
        if not datasets:
            raise log.fail("The provider catalog is empty. Run: eunomia catalog populate")
        self.provider_dsp = _dig(response, "service", "endpointURL")
        if not self.provider_dsp:
            raise log.fail("The catalog response carries no service endpointURL")
        log.ok(f"Catalog returned {len(datasets)} dataset(s)")
        return datasets

    def negotiate(self, offer: Dict[str, Any]) -> str:
        log.step("Step 3 · Contract negotiation")
        consumer, provider = self.consumer, self.provider
        url = f"{consumer}/dsp/current/negotiations/rpc/setup-request-init"
        body = _rpc(
            url,
            {
                "associatedAgentPeer": self.provider_did,
                "providerAddress": self.provider_dsp,
                "callbackAddress": self.callback,
                "offer": offer,
            },
        )
        pids = {"consumerPid": _dig(body, "response", "consumerPid"), "providerPid": _dig(body, "response", "providerPid")}
        if not all(pids.values()):
            raise log.fail(f"setup-request-init returned no PIDs\n{json.dumps(body, indent=2)[:1500]}")
        _expect_state(body, url, "REQUESTED")
        log.ok(f"  1/8 REQUESTED  consumerPid={pids['consumerPid']} providerPid={pids['providerPid']}")

        steps = (
            (provider, "setup-offer", {"offer": offer}, "OFFERED", "2/8 OFFERED    (provider)"),
            (consumer, "setup-request", {"offer": offer}, "REQUESTED", "3/8 REQUESTED  (consumer)"),
            (provider, "setup-offer", {"offer": offer}, "OFFERED", "4/8 OFFERED    (provider, final terms)"),
            (consumer, "setup-acceptance", {}, "ACCEPTED", "5/8 ACCEPTED   (consumer)"),
            (provider, "setup-agreement", {}, "AGREED", "6/8 AGREED     (provider)"),
            (consumer, "setup-verification", {}, "VERIFIED", "7/8 VERIFIED   (consumer)"),
        )
        for base, rpc_name, extra, state, label in steps:
            url = f"{base}/dsp/current/negotiations/rpc/{rpc_name}"
            _expect_state(_rpc(url, {**pids, **extra}), url, state)
            log.ok(f"  {label}")

        url = f"{provider}/dsp/current/negotiations/rpc/setup-finalization"
        body = _rpc(url, pids)
        _expect_state(body, url, "FINALIZED")
        agreement = _dig(body, "negotiationAgentModel", "agreement", "id") or _dig(body, "response", "agreement", "@id")
        if not agreement:
            raise log.fail(f"Finalization carried no agreement id\n{json.dumps(body, indent=2)[:1500]}")
        log.ok(f"  8/8 FINALIZED  agreement={agreement}")
        return agreement

    def request_transfer(self, agreement: str, fmt: str, data_address: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        url = f"{self.consumer}/dsp/current/transfers/rpc/setup-request"
        payload: Dict[str, Any] = {
            "associatedAgentPeer": self.provider_did,
            "providerAddress": self.provider_dsp,
            "callbackAddress": self.callback,
            "agreementId": agreement,
            "format": fmt,
        }
        if data_address:
            payload["dataAddress"] = data_address
        body = _rpc(url, payload)
        pids = {"consumerPid": _dig(body, "response", "consumerPid"), "providerPid": _dig(body, "response", "providerPid")}
        if not all(pids.values()):
            raise log.fail(f"Transfer setup-request returned no PIDs\n{json.dumps(body, indent=2)[:1500]}")
        _expect_state(body, url, "REQUESTED")
        log.ok(f"  REQUESTED  consumerPid={pids['consumerPid']} providerPid={pids['providerPid']}")
        return pids

    def start(self, pids: Dict[str, str]) -> Dict[str, Any]:
        url = f"{self.provider}/dsp/current/transfers/rpc/setup-start"
        body = _rpc(url, pids)
        _expect_state(body, url, "STARTED")
        log.ok("  STARTED    (provider)")
        return body

    def suspend_resume(self, pids: Dict[str, str]) -> None:
        url = f"{self.consumer}/dsp/current/transfers/rpc/setup-suspension"
        body = _rpc(url, {**pids, "code": "SUSPEND", "reason": ["eunomia e2e suspension"]})
        _expect_state(body, url, "SUSPENDED")
        log.ok("  SUSPENDED  (consumer)")
        url = f"{self.consumer}/dsp/current/transfers/rpc/setup-start"
        _expect_state(_rpc(url, pids), url, "STARTED")
        log.ok("  STARTED    (consumer, resumed)")

    def complete(self, pids: Dict[str, str]) -> None:
        url = f"{self.provider}/dsp/current/transfers/rpc/setup-completion"
        _expect_state(_rpc(url, pids), url, "COMPLETED")
        log.ok("  COMPLETED  (provider)")


def push_address(sink: EventSink) -> Dict[str, Any]:
    return {"endpointType": "HTTP", "endpoint": sink.docker_url, "endpointProperties": []}


def _choose(session: Session, datasets: List[Dict[str, Any]], dataset: Optional[str]) -> "tuple[Dict[str, Any], Dict[str, Any]]":
    default = catalog_cmd.title()
    chosen = _pick_dataset(datasets, dataset or default, dataset is None)
    target = chosen["@id"]
    policy = chosen["hasPolicy"][0]
    log.info(f"Dataset  : {chosen.get('title') or target}")
    log.info(f"Target   : {target}")
    log.info(f"Policy   : {policy['@id']}")
    log.info(f"Provider : {session.provider_dsp}")
    log.info(f"Formats  : {', '.join(_formats(chosen)) or 'none advertised'}")
    return chosen, _offer(policy, target)


def run(
    ep: Endpoints,
    demo: Demo,
    dataset: Optional[str] = None,
    list_datasets: bool = False,
    suspend: bool = True,
    data_pull: bool = True,
    push: bool = True,
    keep_open: bool = False,
    verbose: bool = False,
) -> int:
    global VERBOSE
    VERBOSE = verbose
    session = Session(ep)
    datasets = session.discover()

    if list_datasets:
        for d in datasets:
            print(f"{d['@id']}\t{len(d.get('hasPolicy') or [])} policy(ies)\t{d.get('title')}")
        return 0

    chosen, offer = _choose(session, datasets, dataset)
    title = chosen.get("title") or chosen["@id"]
    formats = _formats(chosen)
    agreement = session.negotiate(offer)

    # -- Step 4 · Pull transfer -----------------------------------------------
    log.step("Step 4 · Pull transfer")
    pids = session.request_transfer(agreement, "HTTP_PULL")
    dataplane = _find_dataplane_url(session.start(pids))
    proxy_url = _rewrite_authority(dataplane, ep.provider) if dataplane else None
    log.info(f"      dataplane: {proxy_url or 'none in the start response'}")

    # -- Step 5 · Data --------------------------------------------------------
    if not data_pull:
        log.info("Skipping the data pull (--no-data-pull)")
    elif not proxy_url:
        raise log.fail("The transfer started but carried no dataplane address to pull from")
    else:
        _check_pull(proxy_url, demo)

    # -- Step 6 · Lifecycle ---------------------------------------------------
    if suspend:
        log.step("Step 6 · Suspend and resume")
        session.suspend_resume(pids)
    else:
        log.info("Skipping the suspend/resume leg (--no-suspend)")

    if keep_open:
        log.step("Pull transfer left open (--keep-open)")
        if proxy_url:
            log.ok(f"Dataplane proxy URL:\n  {proxy_url}")
    else:
        session.complete(pids)

    # -- Step 7 · Push transfer -----------------------------------------------
    pushed = None
    if not push:
        log.info("Skipping the push transfer (--no-push)")
    elif "HTTP_PUSH" not in formats:
        log.info("The dataset offers no HTTP_PUSH distribution, so there is no push leg")
    else:
        log.step("Step 7 · Push transfer: robot events to a local endpoint")
        with EventSink(sink_port()) as sink:
            log.info(f"Listening on :{sink.port}, the consumer pushes to {sink.docker_url}")
            push_pids = session.request_transfer(agreement, "HTTP_PUSH", push_address(sink))
            session.start(push_pids)
            pushed = sink.wait(timeout=float(os.environ.get("EUNOMIA_PUSH_TIMEOUT", "30")))
            session.complete(push_pids)
        if pushed is None:
            raise log.fail(
                f"No event reached :{sink.port} within the timeout. The provider subscribes to the factory and\n"
                "forwards each event to the consumer, which POSTs it to the endpoint. Look at:\n"
                "  eunomia logs demo   eunomia logs provider   eunomia logs consumer\n"
                "On Linux, the firewall may block containers from reaching the host (allow docker0)."
            )
        log.ok(f"  event received: {_describe(pushed)}")

    log.step("=" * 60)
    log.ok(
        "END-TO-END TEST PASSED\n"
        f"  Dataset    : {title}\n"
        f"  Agreement  : {agreement}\n"
        f"  Pull       : {pids['consumerPid']} / {pids['providerPid']}"
        + (f"\n  Dataplane  : {proxy_url}" if proxy_url and keep_open else "")
        + (f"\n  Push event : {_describe(pushed)}" if pushed is not None else "")
    )
    log.step("=" * 60)
    return 0
