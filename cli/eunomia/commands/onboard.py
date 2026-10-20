"""Onboarding: link wallets, get credentials from the authority, connect.

  1. Wallets      every participant links its Fafnir wallet
  2. Register     provider and consumer get a DataSpaceParticipant credential
  3. Gaia-X       the consumer gets the legal VC (gx:VatId), generates its
                  self-attested Gaia-X VCs and gets the label VC
                  (gx:LabelCredential): the provider only accepts consumers
                  that hold it
  4. Connect      GNAP handshake that gives the consumer a token for the provider

Every step checks first and skips when already done, so the whole sequence is
safe to re-run after a redeploy or an interrupted run.

The functions take Peers rather than the standalone Endpoints, so the extra
connectors and authorities of `eunomia connector add` reuse them.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, List

from .. import http, log
from ..settings import Endpoints

PARTICIPANT_VC = "DataSpaceParticipant_jwt_vc_json"
VAT_VC = "gx_VatId_jwt_vc_json"
LABEL_VC = "gx_LabelCredential_jwt_vc_json"


@dataclass(frozen=True)
class Peer:
    """A participant: a name for the logs, its URL from here and from the containers."""

    name: str
    url: str
    docker_url: str


def peers(ep: Endpoints) -> "tuple[Peer, Peer, Peer]":
    return (
        Peer("authority", ep.authority, ep.docker_authority),
        Peer("provider", ep.provider, ep.docker_provider),
        Peer("consumer", ep.consumer, ep.docker_consumer),
    )


def did(base_url: str) -> str:
    return http.get_json(f"{base_url}/.well-known/did.json")["id"]


def _poll(check: Callable[[], bool], timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            return True
        time.sleep(1)
    return check()


def link_wallets(participants: List[Peer]) -> None:
    log.step("Linking wallets")
    for p in participants:
        # Linking an already linked wallet answers 200 too, so no check first.
        http.checked("POST", f"{p.url}/api/v1/wallet/link")
    log.ok("Wallets linked: " + ", ".join(p.name for p in participants))


def _requests(participant: Peer) -> List[dict]:
    return http.get_json(f"{participant.url}/api/v1/vc-request/all") or []


def holds(participant: Peer, authority_did: str, vc_type: str) -> bool:
    return any(
        r.get("participant_id") == authority_did
        and r.get("status") == "Finalized"
        and vc_type in (r.get("vc_type_config") or [])
        for r in _requests(participant)
    )


def _last_status(participant: Peer, authority_did: str, vc_type: str) -> str:
    matching = [
        r
        for r in _requests(participant)
        if r.get("participant_id") == authority_did and vc_type in (r.get("vc_type_config") or [])
    ]
    matching.sort(key=lambda r: r.get("created_at") or "")
    return matching[-1].get("status", "unknown") if matching else "no request"


def request_vc(participant: Peer, authority: Peer, vc_type: str, method: str, hint: str = "") -> None:
    """Ask the authority for a credential and wait until it is Finalized."""
    authority_did = did(authority.url)
    # /vc-request/beg never deduplicates: every call files a fresh petition
    # with the authority, so without this guard each run piles up another one.
    if holds(participant, authority_did, vc_type):
        log.info(f"{participant.name} already holds {vc_type}, skipping")
        return
    # The field is "nick", not "slug": "slug" fails with HTTP 400
    # "Error extracting Json payload".
    http.checked(
        "POST",
        f"{participant.url}/api/v1/vc-request/beg",
        {
            "url": f"{authority.docker_url}/api/v1/gate/access",
            "id": authority_did,
            "nick": authority.name,
            "vc_type": vc_type,
            "method": method,
            "auto": True,
        },
    )
    if not _poll(lambda: holds(participant, authority_did, vc_type)):
        status = _last_status(participant, authority_did, vc_type)
        raise log.fail(
            f"{participant.name} asked {authority.name} for {vc_type}, but the request is {status!r}, not Finalized.\n"
            f"Look at the logs: eunomia logs {authority.name}  and  eunomia logs {participant.name}{hint}"
        )
    log.ok(f"{participant.name} holds {vc_type}")


def register(participant: Peer, authority: Peer) -> None:
    """Get the participant a DataSpaceParticipant credential from the authority."""
    log.step(f"Registering {participant.name} with {authority.name}")
    request_vc(participant, authority, PARTICIPANT_VC, "cert")


def gaia(consumer: Peer, authority: Peer) -> None:
    """Gaia-X credentials for the consumer: legal VC, self-attested VCs, label VC."""
    log.step(f"Gaia-X credentials for {consumer.name} from {authority.name}")
    authority_did = did(authority.url)
    if holds(consumer, authority_did, LABEL_VC):
        log.info(f"{consumer.name} already holds {LABEL_VC}, skipping")
        return
    # The authority reads the VAT number from the organizationIdentifier of
    # the participant's certificate (vault/<role>/secrets/cert.pem.example).
    request_vc(
        consumer,
        authority,
        VAT_VC,
        "cert",
        "\nThe VAT number comes from the organizationIdentifier of the participant certificate, and the\n"
        "authority must have the EcoAuthority role to issue Gaia-X credentials.",
    )
    log.info("Generating the self-attested Gaia-X VCs")
    http.checked("POST", f"{consumer.url}/api/v1/gaia/generate")
    request_vc(consumer, authority, LABEL_VC, "oidc4vp")


def _has_token(consumer: Peer, provider_did: str) -> bool:
    # Check the token, not the mate: a tokenless mate row means the handshake
    # never completed, and the provider then answers 401 to every DSP call
    # (surfaced as 502 by the consumer BFF).
    mates = http.get_json(f"{consumer.url}/api/v1/mates/all") or []
    return any(m.get("participant_id") == provider_did and (m.get("token") or "") for m in mates)


def _connection_status(consumer: Peer, provider_did: str) -> str:
    rows = http.get_json(f"{consumer.url}/api/v1/peer-connection/request/all") or []
    rows = [r for r in rows if r.get("participant_id") == provider_did]
    rows.sort(key=lambda r: r.get("created_at") or "")
    return rows[-1].get("status", "unknown") if rows else "no request"


def connect(consumer: Peer, provider: Peer) -> None:
    """GNAP handshake that mints the consumer's mate token for the provider."""
    log.step(f"Connecting {consumer.name} to {provider.name}")
    provider_did = did(provider.url)
    if _has_token(consumer, provider_did):
        log.info(f"{consumer.name} already holds a token for {provider.name}, skipping")
        return

    # POST /api/v1/mates is NOT equivalent: it only inserts the row. The
    # payload is ReachProvider (ds-agent crates/auth/src/types/entities/reacher.rs);
    # actions accepts "talk" and "request-vc".
    http.checked(
        "POST",
        f"{consumer.url}/api/v1/peer-connection/connect",
        {
            "id": provider_did,
            "nick": provider.name,
            "url": f"{provider.docker_url}/api/v1/gate/access",
            "actions": ["talk"],
            "auto": True,
        },
    )
    if not _poll(lambda: _has_token(consumer, provider_did)):
        status = _connection_status(consumer, provider_did)
        raise log.fail(
            f"The connection from {consumer.name} to {provider.name} is {status!r}, not Approved.\n"
            f"The provider only accepts consumers holding gx:LabelCredential: run\n"
            f"  eunomia gaia --consumer {consumer.name}\n"
            f"and look at the logs: eunomia logs {provider.name}"
        )
    log.ok(f"{consumer.name} is connected to {provider.name}")


def run_all(ep: Endpoints) -> None:
    authority, provider, consumer = peers(ep)
    link_wallets([authority, provider, consumer])
    register(consumer, authority)
    register(provider, authority)
    gaia(consumer, authority)
    connect(consumer, provider)
    log.ok("\nOnboarding complete")
