"""Pinned images and, with --check, what the registries hold beyond them.

The EUNOMIA images are pinned in versions.env and the compose files refer to
them as ${EUNOMIA_IMAGE}:${EUNOMIA_TAG} and so on; infrastructure images are
pinned in the compose files themselves.

A newer tag is reported, never applied: the registries carry test builds with
no published source, so picking a tag stays a human decision.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from .. import http, log, settings

# Quoted values may hold spaces: ${EUNOMIA_TAG:?set EUNOMIA_TAG in versions.env}
IMAGE_RE = re.compile(r"""^\s*image:\s*(?:"([^"]+)"|'([^']+)'|(\S+))\s*$""")
VAR_RE = re.compile(r"\$\{(\w+)[^}]*\}")


def resolve(ref: str, values: Dict[str, str]) -> str:
    """Expand ${VAR} and ${VAR:?message} with the versions.env values."""
    return VAR_RE.sub(lambda m: values.get(m.group(1), m.group(0)), ref)


def compose_files() -> "list":
    """Every compose file eunomia runs: instance templates, prod and the demo."""
    files = sorted(settings.TEMPLATES_DIR.glob("docker-compose.*.yaml"))
    files += [s.compose for s in settings.prod_stacks().values()]
    return files + [settings.demo_stack().compose]


def pinned() -> Dict[str, Set[str]]:
    """image reference -> compose files that use it. Locally built images are left out."""
    values = settings.versions()
    found: Dict[str, Set[str]] = {}
    for compose_file in compose_files():
        if not compose_file.is_file():
            continue
        for line in compose_file.read_text().splitlines():
            m = IMAGE_RE.match(line)
            if m:
                ref = resolve(next(g for g in m.groups() if g), values)
                if ref.endswith(":local"):
                    continue
                found.setdefault(ref, set()).add(str(compose_file.relative_to(settings.REPO_ROOT)))
    return found


def _split(ref: str) -> Tuple[str, str, str]:
    """(registry, repository, tag)."""
    name, _, tag = ref.rpartition(":") if ":" in ref.split("/")[-1] else (ref, "", "")
    if "/" in name and ("." in name.split("/")[0] or ":" in name.split("/")[0]):
        registry, repo = name.split("/", 1)
    else:
        registry, repo = "docker.io", name if "/" in name else f"library/{name}"
    return registry, repo, tag


def _tags(registry: str, repo: str) -> Optional[List[Tuple[str, datetime]]]:
    """Tags with their push date, newest first; None if the registry is not supported."""
    if registry == "quay.io":
        r = http.request("GET", f"https://quay.io/api/v1/repository/{repo}/tag/?limit=50&onlyActiveTags=true")
        if not r.ok:
            return None
        return sorted(
            ((t["name"], datetime.fromtimestamp(t["start_ts"], timezone.utc)) for t in r.json().get("tags", [])),
            key=lambda t: t[1],
            reverse=True,
        )
    if registry == "docker.io":
        r = http.request("GET", f"https://hub.docker.com/v2/repositories/{repo}/tags?page_size=50&ordering=last_updated")
        if not r.ok:
            return None
        out = []
        for t in r.json().get("results", []):
            # e.g. 2026-06-30T17:06:21.262378Z; fromisoformat on 3.8 rejects
            # both the Z and the microseconds, so keep the seconds only.
            stamp = (t.get("last_updated") or "")[:19]
            if stamp:
                out.append((t["name"], datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc)))
        return out
    return None


def show(check: bool) -> int:
    images = pinned()
    for ref in sorted(images):
        registry, repo, tag = _split(ref)
        files = ", ".join(sorted(images[ref]))
        unpinned = "  (no tag: resolves to latest)" if not tag else ""
        print(f"{ref}{unpinned}\n    used in {files}")
        if not check or not tag:
            continue
        if repo.startswith("library/"):
            # Official images rebuild every tag constantly, so push dates say
            # nothing about what is newer.
            print("    (official image: not checked)")
            continue
        tags = _tags(registry, repo)
        if tags is None:
            print("    (registry not queried)")
            continue
        current = next((d for n, d in tags if n == tag), None)
        if current is None:
            print(f"    tag {tag} not among the 50 most recent tags: not compared")
            continue
        newer = [f"{n} ({d:%Y-%m-%d})" for n, d in tags if d > current and n != tag]
        print(f"    pinned {tag} ({current:%Y-%m-%d})" + (f"; newer: {', '.join(newer)}" if newer else "; up to date"))
    if check:
        log.info("\nNewer tags are reported, never applied. Check their source before bumping a pin.")
    return 0
