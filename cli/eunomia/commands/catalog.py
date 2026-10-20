"""Provider catalog: the demo factory dataset and everything hanging off it.

It creates the dataset, an HTTP pull and an HTTP push distribution, three
ODRL policies, the pull and push connector templates and one connector
instance per distribution.

Payloads live in static/catalog/; the __PLACEHOLDERS__ in them are filled in
here with the ids the provider returns and the factory URLs. The connector
instances get the URLs the provider agent uses (host.docker.internal in
standalone): the agent is the one that calls the factory.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .. import http, log
from ..settings import CATALOG_DIR, Demo

DATASET = "01-dataset-robots.json"
PULL_DISTRIBUTION = "02-distribution-pull-robots.json"
PUSH_DISTRIBUTION = "03-distribution-push-robot-events.json"
POLICY_TEMPLATE = "04-policy-template-instantiate.json"
POLICIES = ("05-policy-commercial.json", "06-policy-research-trial.json")
PULL_TEMPLATE = "07-connector-template-pull.json"
PUSH_TEMPLATE = "08-connector-template-push.json"
PULL_CONNECTOR = "09-connector-instance-pull-robots.json"
PUSH_CONNECTOR = "10-connector-instance-push-robot-events.json"

PAYLOADS = (
    DATASET,
    PULL_DISTRIBUTION,
    PUSH_DISTRIBUTION,
    POLICY_TEMPLATE,
    *POLICIES,
    PULL_TEMPLATE,
    PUSH_TEMPLATE,
    PULL_CONNECTOR,
    PUSH_CONNECTOR,
)


def _payload(name: str) -> Dict[str, Any]:
    return json.loads((CATALOG_DIR / name).read_text())


def title() -> str:
    return _payload(DATASET)["dctTitle"]


class Catalog:
    def __init__(self, provider_url: str) -> None:
        self.api = f"{provider_url}/api/v1"

    def get(self, path: str) -> Any:
        return http.get_json(f"{self.api}{path}")

    def post(self, path: str, body: Dict[str, Any]) -> Any:
        return http.post_json(f"{self.api}{path}", body)

    def datasets(self) -> List[Dict[str, Any]]:
        return self.get("/catalog-agent/datasets") or []

    def distributions(self) -> List[Dict[str, Any]]:
        return self.get("/catalog-agent/distributions") or []

    def instance_for(self, distribution_id: str) -> Optional[Dict[str, Any]]:
        r = http.request("GET", f"{self.api}/connector/instances/distribution/{distribution_id}")
        return r.json() if r.ok and r.body.strip() else None

    def template(self, payload_name: str) -> Dict[str, Any]:
        """Reuse an existing template with the same interaction and auth, or create it.

        Templates get a server-assigned urn as their name, so there is no
        stable key to look them up by; interaction mode plus authentication
        type is what tells the pull and the push template apart.
        """
        payload = _payload(payload_name)
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


def fill_connector(payload: Dict[str, Any], template: Dict[str, Any], distribution_id: str, demo: Demo) -> Dict[str, Any]:
    payload["templateName"] = template["name"]
    payload["templateVersion"] = template["version"]
    payload["distributionId"] = distribution_id
    urls = {
        "__STATIC_API_URL__": demo.docker_static_api,
        "__DYNAMIC_API_URL__": demo.docker_dynamic_api,
        "__KEYCLOAK_URL__": demo.docker_keycloak,
    }
    for key, value in payload["parameters"].items():
        if isinstance(value, str):
            for marker, url in urls.items():
                value = value.replace(marker, url)
            payload["parameters"][key] = value
    return payload


def populate(provider_url: str, demo: Demo, force: bool = False) -> None:
    """Create the demo dataset if it is missing. With force, create it again."""
    cat = Catalog(provider_url)
    log.step(f"Populating the provider catalog (factory: {demo.docker_static_api})")

    existing = {d.get("dctTitle"): d for d in cat.datasets()}
    if title() in existing and not force:
        log.ok(f"Catalog already populated ({existing[title()]['id']})")
        return

    catalog_id = cat.get("/catalog-agent/catalogs/main")["id"]
    data_service_id = cat.get("/catalog-agent/data-services/main")["id"]
    pull_tpl = cat.template(PULL_TEMPLATE)
    push_tpl = cat.template(PUSH_TEMPLATE)

    ds = _payload(DATASET)
    ds["catalogId"] = catalog_id
    dataset_id = cat.post("/catalog-agent/datasets", ds)["id"]
    log.ok(f"  dataset      {dataset_id}")

    dist_ids = {}
    for kind, name in (("pull", PULL_DISTRIBUTION), ("push", PUSH_DISTRIBUTION)):
        dist = _payload(name)
        dist["dcatAccessService"] = data_service_id
        dist["datasetId"] = dataset_id
        dist_ids[kind] = cat.post("/catalog-agent/distributions", dist)["id"]
        log.ok(f"  {kind} dist    {dist_ids[kind]}")

    tpl = _payload(POLICY_TEMPLATE)
    tpl["entityId"] = dataset_id
    cat.post("/catalog-agent/policy-templates/instantiate-odrl-offer", tpl)
    for name in POLICIES:
        policy = _payload(name)
        policy["entityId"] = dataset_id
        cat.post("/catalog-agent/odrl-policies", policy)
    log.ok(f"  policies     {1 + len(POLICIES)}")

    cat.post("/connector/instances", fill_connector(_payload(PULL_CONNECTOR), pull_tpl, dist_ids["pull"], demo))
    cat.post("/connector/instances", fill_connector(_payload(PUSH_CONNECTOR), push_tpl, dist_ids["push"], demo))
    log.ok("  connectors   pull + push")
    log.ok("\nCatalog populated")


def show(provider_url: str) -> None:
    """Print each dataset with its distributions and their connector instances."""
    cat = Catalog(provider_url)
    datasets = cat.datasets()
    if not datasets:
        log.info("The provider catalog is empty. Run: eunomia catalog populate")
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
