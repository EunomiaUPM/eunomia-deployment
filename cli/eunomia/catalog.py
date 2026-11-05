"""An agent's catalog API: datasets, distributions, policies and connectors.

The client every extension publishes with, and `eunomia catalog show`. What
goes into a catalog (the payloads) belongs to the extension that shares the
data; the demo's are in extensions/demo/payloads/.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import http, log


class Catalog:
    def __init__(self, agent_url: str) -> None:
        self.api = f"{agent_url}/api/v1"

    def get(self, path: str) -> Any:
        return http.get_json(f"{self.api}{path}")

    def post(self, path: str, body: Dict[str, Any]) -> Any:
        return http.post_json(f"{self.api}{path}", body)

    def main_catalog_id(self) -> str:
        return self.get("/catalog-agent/catalogs/main")["id"]

    def main_data_service_id(self) -> str:
        return self.get("/catalog-agent/data-services/main")["id"]

    def datasets(self) -> List[Dict[str, Any]]:
        return self.get("/catalog-agent/datasets") or []

    def distributions(self) -> List[Dict[str, Any]]:
        return self.get("/catalog-agent/distributions") or []

    def instance_for(self, distribution_id: str) -> Optional[Dict[str, Any]]:
        r = http.request("GET", f"{self.api}/connector/instances/distribution/{distribution_id}")
        return r.json() if r.ok and r.body.strip() else None

    def template(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Reuse an existing connector template with the same interaction and auth, or create it.

        Templates get a server-assigned urn as their name, so there is no
        stable key to look them up by; interaction mode plus authentication
        type is what tells one template from another.
        """
        mode = payload["interaction"]["mode"]
        auth = payload["authentication"]["type"]
        for existing in self.get("/connector/templates") or []:
            if (existing.get("interaction") or {}).get("mode") == mode and (
                existing.get("authentication") or {}
            ).get("type") == auth:
                log.info(f"  {mode.lower()} connector template exists: {existing['name']}")
                return existing
        created = self.post("/connector/templates", payload)
        log.ok(f"  {mode.lower()} connector template created: {created['name']}")
        return created


def show(agent: str, agent_url: str) -> None:
    """Print each dataset with its distributions and their connector instances."""
    cat = Catalog(agent_url)
    datasets = cat.datasets()
    if not datasets:
        log.info(f"The catalog of {agent} is empty. An extension publishes into it, e.g.: eunomia demo publish {agent}")
        return
    by_dataset: Dict[str, List[Dict[str, Any]]] = {}
    for dist in cat.distributions():
        by_dataset.setdefault(dist.get("datasetId") or "", []).append(dist)
    for ds in datasets:
        print(f"{ds['id']}  {ds.get('dctTitle')}")
        for dist in by_dataset.get(ds["id"], []):
            inst = cat.instance_for(dist["id"])
            conn = inst["id"] if inst else "no connector instance"
            fmt = dist.get("dctFormat") or dist.get("dctFormats") or "?"
            print(f"    {fmt:<10} {dist['id']}  -> {conn}")
