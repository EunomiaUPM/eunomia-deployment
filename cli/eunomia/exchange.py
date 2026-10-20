"""A DSP exchange between two agents, whatever data they share.

  Session        discovery (DIDs, GNAP login, callback, catalog request),
                 contract negotiation step by step, transfers and their
                 lifecycle; every step's state is asserted, so a 200 that
                 carries an embedded DSP rejection still fails
  offer()        the offer exactly as the catalog advertises it
  dataplane_url  the pull address in a transfer start, reachable from here
  EventSink      a throwaway endpoint the pushed data lands on

Extensions build their tests and tools on it; the demo's `test`, `robots`
and `events` are three examples.
"""

from __future__ import annotations

import json
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

from . import http, log, settings
from .commands import onboard
from .commands.onboard import Peer

VERBOSE = False


def verbose(on: bool) -> None:
    """Dump every request and response of the exchange."""
    global VERBOSE
    VERBOSE = on


def _dump(label: str, payload: Any) -> None:
    if VERBOSE:
        log.info(f"  {label}: {json.dumps(payload, indent=2, ensure_ascii=False)}")


def dig(obj: Any, *keys: str) -> Any:
    for key in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def rpc(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    _dump(f"-> {url}", payload)
    body = http.post_json(url, payload, timeout=60) or {}
    _dump("<-", body)
    return body


def expect_state(body: Dict[str, Any], url: str, *accepted: str) -> str:
    """The state sits under different keys depending on the answer's shape."""
    state = (
        dig(body, "response", "state")
        or dig(body, "negotiationAgentModel", "state")
        or dig(body, "transferAgentModel", "state")
        or dig(body, "state")
    )
    pretty = json.dumps(body, indent=2, ensure_ascii=False)[:1500]
    if state is None:
        raise log.fail(f"{url}: no state in response\n{pretty}")
    short = state.rsplit(":", 1)[-1].upper()
    if short not in {s.upper() for s in accepted}:
        raise log.fail(f"{url}: expected {' or '.join(accepted)}, got {state}\n{pretty}")
    return short


def pick_dataset(datasets: List[Dict[str, Any]], wanted: str, is_default: bool) -> Dict[str, Any]:
    """The first dataset whose title or id contains `wanted`. Datasets without a policy cannot be negotiated."""
    usable = [d for d in datasets if d.get("hasPolicy")]
    if not usable:
        raise log.fail("The catalog has no dataset with a policy.")
    needle = wanted.casefold()
    for d in usable:
        if needle in (d.get("title") or "").casefold() or needle in d.get("@id", "").casefold():
            return d
    if not is_default:
        titles = "\n".join(f"  - {d.get('title')}" for d in usable)
        raise log.fail(f"No dataset matches {wanted!r}. Available:\n{titles}")
    log.info(f"No dataset matches the default {wanted!r}, using the first one")
    return usable[0]


def offer(policy: Dict[str, Any], target: str) -> Dict[str, Any]:
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


def formats(dataset: Dict[str, Any]) -> List[str]:
    out = []
    for dist in dataset.get("distribution") or []:
        fmt = dist.get("formats") or dist.get("format") or dist.get("dctFormats")
        if fmt:
            out.append(fmt)
    return out


def rewrite_authority(url: str, reachable_base: str) -> str:
    """Point an agent-minted URL at the address this process can reach."""
    p, b = urlsplit(url), urlsplit(reachable_base)
    return urlunsplit((b.scheme, b.netloc, p.path, p.query, p.fragment))


def find_dataplane_url(body: Any) -> Optional[str]:
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


def dataplane_url(start_body: Any, provider: Peer) -> Optional[str]:
    """The pull address of a started transfer, as this process reaches the provider."""
    url = find_dataplane_url(start_body)
    return rewrite_authority(url, provider.url) if url else None


# ---------------------------------------------------------------------------
# Push sink
# ---------------------------------------------------------------------------


class EventSink:
    """A throwaway HTTP endpoint that collects what the data space pushes to it.

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

    @property
    def data_address(self) -> Dict[str, Any]:
        """What a push transfer request names as its destination."""
        return {"endpointType": "HTTP", "endpoint": self.docker_url, "endpointProperties": []}

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
    """Where the CLI's own push legs listen (EUNOMIA_SINK_PORT, default 1290)."""
    return settings.port("EUNOMIA_SINK_PORT", 1290)


# ---------------------------------------------------------------------------
# The exchange
# ---------------------------------------------------------------------------


class Session:
    """Two agents, consumer and provider in this exchange, after discovery.

    `empty_hint` is what to tell the person when the provider's catalog is
    empty: the command that publishes into it.
    """

    def __init__(self, consumer: Peer, provider: Peer, empty_hint: str = "") -> None:
        self.consumer_peer = consumer
        self.provider_peer = provider
        self.consumer = consumer.url
        self.provider = provider.url
        self.empty_hint = empty_hint
        self.provider_did = ""
        self.provider_dsp = ""
        self.callback = ""

    def discover(self) -> List[Dict[str, Any]]:
        """DIDs, the GNAP login if missing, the consumer's callback and the provider's catalog."""
        c, p = self.consumer_peer, self.provider_peer
        log.step(f"Step 1 · {c.name} (consumer) and {p.name} (provider)")
        consumer_did = http.get_json(f"{self.consumer}/api/v1/mates/myself")["participant_id"]
        self.provider_did = http.get_json(f"{self.provider}/api/v1/mates/myself")["participant_id"]
        log.info(f"{c.name:<9} DID: {consumer_did}")
        log.info(f"{p.name:<9} DID: {self.provider_did}")

        # The GNAP login is idempotent: it skips when the token is already there.
        if onboard.has_token(c, self.provider_did):
            log.ok(f"{c.name} is logged in with {p.name}")
        else:
            onboard.connect(c, p)

        version = http.get_json(f"{self.consumer}/.well-known/dspace-version/2025-1")
        self.callback = c.docker_url + version["path"]
        log.info(f"Consumer callback: {self.callback}")

        log.step(f"Step 2 · Requesting the catalog of {p.name}")
        cat = rpc(
            f"{self.consumer}/dsp/current/catalog/rpc/setup-catalog-request",
            {"associatedAgentPeer": self.provider_did, "filter": [], "noCache": True},
        )
        response = cat.get("response") or {}
        datasets = response.get("dataset") or []
        if not datasets:
            raise log.fail(f"The catalog of {p.name} is empty." + (f" Publish into it: {self.empty_hint}" if self.empty_hint else ""))
        self.provider_dsp = dig(response, "service", "endpointURL")
        if not self.provider_dsp:
            raise log.fail("The catalog response carries no service endpointURL")
        log.ok(f"Catalog returned {len(datasets)} dataset(s)")
        return datasets

    def negotiate(self, the_offer: Dict[str, Any]) -> str:
        """The whole contract negotiation, step by step. Returns the agreement id."""
        log.step("Step 3 · Contract negotiation")
        consumer, provider = self.consumer, self.provider
        url = f"{consumer}/dsp/current/negotiations/rpc/setup-request-init"
        body = rpc(
            url,
            {
                "associatedAgentPeer": self.provider_did,
                "providerAddress": self.provider_dsp,
                "callbackAddress": self.callback,
                "offer": the_offer,
            },
        )
        pids = {"consumerPid": dig(body, "response", "consumerPid"), "providerPid": dig(body, "response", "providerPid")}
        if not all(pids.values()):
            raise log.fail(f"setup-request-init returned no PIDs\n{json.dumps(body, indent=2)[:1500]}")
        expect_state(body, url, "REQUESTED")
        log.ok(f"  1/8 REQUESTED  consumerPid={pids['consumerPid']} providerPid={pids['providerPid']}")

        steps = (
            (provider, "setup-offer", {"offer": the_offer}, "OFFERED", "2/8 OFFERED    (provider)"),
            (consumer, "setup-request", {"offer": the_offer}, "REQUESTED", "3/8 REQUESTED  (consumer)"),
            (provider, "setup-offer", {"offer": the_offer}, "OFFERED", "4/8 OFFERED    (provider, final terms)"),
            (consumer, "setup-acceptance", {}, "ACCEPTED", "5/8 ACCEPTED   (consumer)"),
            (provider, "setup-agreement", {}, "AGREED", "6/8 AGREED     (provider)"),
            (consumer, "setup-verification", {}, "VERIFIED", "7/8 VERIFIED   (consumer)"),
        )
        for base, rpc_name, extra, state, label in steps:
            url = f"{base}/dsp/current/negotiations/rpc/{rpc_name}"
            expect_state(rpc(url, {**pids, **extra}), url, state)
            log.ok(f"  {label}")

        url = f"{provider}/dsp/current/negotiations/rpc/setup-finalization"
        body = rpc(url, pids)
        expect_state(body, url, "FINALIZED")
        agreement = dig(body, "negotiationAgentModel", "agreement", "id") or dig(body, "response", "agreement", "@id")
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
        body = rpc(url, payload)
        pids = {"consumerPid": dig(body, "response", "consumerPid"), "providerPid": dig(body, "response", "providerPid")}
        if not all(pids.values()):
            raise log.fail(f"Transfer setup-request returned no PIDs\n{json.dumps(body, indent=2)[:1500]}")
        expect_state(body, url, "REQUESTED")
        log.ok(f"  REQUESTED  consumerPid={pids['consumerPid']} providerPid={pids['providerPid']}")
        return pids

    def start(self, pids: Dict[str, str]) -> Dict[str, Any]:
        url = f"{self.provider}/dsp/current/transfers/rpc/setup-start"
        body = rpc(url, pids)
        expect_state(body, url, "STARTED")
        log.ok("  STARTED    (provider)")
        return body

    def suspend_resume(self, pids: Dict[str, str]) -> None:
        url = f"{self.consumer}/dsp/current/transfers/rpc/setup-suspension"
        body = rpc(url, {**pids, "code": "SUSPEND", "reason": ["eunomia suspension"]})
        expect_state(body, url, "SUSPENDED")
        log.ok("  SUSPENDED  (consumer)")
        url = f"{self.consumer}/dsp/current/transfers/rpc/setup-start"
        expect_state(rpc(url, pids), url, "STARTED")
        log.ok("  STARTED    (consumer, resumed)")

    def complete(self, pids: Dict[str, str]) -> None:
        url = f"{self.provider}/dsp/current/transfers/rpc/setup-completion"
        expect_state(rpc(url, pids), url, "COMPLETED")
        log.ok("  COMPLETED  (provider)")
