"""Onboarding: link wallets, get credentials from an authority, connect.

  1. Wallets      the agent and the authority link their Fafnir wallets
  2. Register     the agent gets a DataSpaceParticipant credential
  3. Gaia-X       the agent gets the legal VC (gx:VatId), generates its
                  self-attested Gaia-X VCs and gets the label VC
                  (gx:LabelCredential): agents only accept peers that hold it
  4. Login        GNAP grant between two agents, per pair, with `eunomia
                  login`: once approved, both hold a token for the other

Every agent gets all three credentials, so any agent can connect to any other
and play either role in an exchange. Every step checks first and skips when
already done, so the whole sequence is safe to re-run.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, List

from .. import http, log

PARTICIPANT_VC = "DataSpaceParticipant_jwt_vc_json"
VAT_VC = "gx_VatId_jwt_vc_json"
LABEL_VC = "gx_LabelCredential_jwt_vc_json"


@dataclass(frozen=True)
class Peer:
    """A participant: a name for the logs, its URL from here and from the containers."""

    name: str
    url: str
    docker_url: str


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


def gaia(agent: Peer, authority: Peer) -> None:
    """Gaia-X credentials for an agent: legal VC, self-attested VCs, label VC."""
    log.step(f"Gaia-X credentials for {agent.name} from {authority.name}")
    authority_did = did(authority.url)
    if holds(agent, authority_did, LABEL_VC):
        log.info(f"{agent.name} already holds {LABEL_VC}, skipping")
        return
    # The authority reads the VAT number from the organizationIdentifier of
    # the participant's certificate (vault/<role>/secrets/cert.pem.example).
    request_vc(
        agent,
        authority,
        VAT_VC,
        "cert",
        "\nThe VAT number comes from the organizationIdentifier of the participant certificate, and the\n"
        "authority must have the EcoAuthority role to issue Gaia-X credentials.",
    )
    log.info("Generating the self-attested Gaia-X VCs")
    http.checked("POST", f"{agent.url}/api/v1/gaia/generate")
    request_vc(agent, authority, LABEL_VC, "oidc4vp")


def has_token(source: Peer, target_did: str) -> bool:
    # Check the token, not the mate: a tokenless mate row means the handshake
    # never completed, and the target then answers 401 to every DSP call
    # (surfaced as 502 by the source agent's BFF).
    mates = http.get_json(f"{source.url}/api/v1/mates/all") or []
    return any(m.get("participant_id") == target_did and (m.get("token") or "") for m in mates)


def _connection_status(source: Peer, target_did: str) -> str:
    rows = http.get_json(f"{source.url}/api/v1/peer-connection/request/all") or []
    rows = [r for r in rows if r.get("participant_id") == target_did]
    rows.sort(key=lambda r: r.get("created_at") or "")
    return rows[-1].get("status", "unknown") if rows else "no request"


def connect(source: Peer, target: Peer) -> None:
    """GNAP grant from `source` to `target`; once approved both hold a token."""
    log.step(f"Connecting {source.name} to {target.name}")
    target_did = did(target.url)
    if has_token(source, target_did):
        log.info(f"{source.name} already holds a token for {target.name}, skipping")
        return

    # POST /api/v1/mates is NOT equivalent: it only inserts the row. The
    # payload is ReachProvider (ds-agent crates/auth/src/types/entities/reacher.rs);
    # actions accepts "talk" and "request-vc".
    http.checked(
        "POST",
        f"{source.url}/api/v1/peer-connection/connect",
        {
            "id": target_did,
            "nick": target.name,
            "url": f"{target.docker_url}/api/v1/gate/access",
            "actions": ["talk"],
            "auto": True,
        },
    )
    if not _poll(lambda: has_token(source, target_did)):
        status = _connection_status(source, target_did)
        raise log.fail(
            f"The connection from {source.name} to {target.name} is {status!r}, not Approved.\n"
            f"{target.name} only accepts agents holding gx:LabelCredential: onboard {source.name} first\n"
            f"  eunomia onboard {source.name}\n"
            f"and look at the logs: eunomia logs {target.name}"
        )
    log.ok(f"{source.name} is connected to {target.name}")


def login(a: Peer, b: Peer) -> None:
    """GNAP login between two agents.

    One grant is enough: when `a` connects to `b` and `b` approves, both end
    up holding a token for the other, and either can browse the other's
    catalog and negotiate with it. If `a` already holds a token for `b`
    (from an earlier login either way) nothing is requested.
    """
    link_wallets([a, b])
    connect(a, b)
    a_did, b_did = did(a.url), did(b.url)
    # The grant is mutual; if the other side somehow lacks its token, ask from there too.
    if not has_token(b, a_did):
        connect(b, a)
    status = _connection_status(a, b_did)
    if status == "no request":
        status = _connection_status(b, a_did)
    log.ok(
        f"\n{a.name} and {b.name} are logged in over GNAP (grant {status}):\n"
        f"  {a.name:<12} holds a token for {b.name}: {'yes' if has_token(a, b_did) else 'no'}\n"
        f"  {b.name:<12} holds a token for {a.name}: {'yes' if has_token(b, a_did) else 'no'}"
    )


def onboard_agent(agent: Peer, authority: Peer, with_gaia: bool = True) -> None:
    """Everything an agent needs from an authority: wallet, membership, Gaia-X.

    Only an authority with the eco role issues Gaia-X credentials; with any
    other the agent gets membership only.
    """
    link_wallets([authority, agent])
    register(agent, authority)
    if with_gaia:
        gaia(agent, authority)
    else:
        log.info(f"{authority.name} does not issue Gaia-X credentials: {agent.name} gets membership only")
    log.ok(f"\n{agent.name} is onboarded with {authority.name}")
