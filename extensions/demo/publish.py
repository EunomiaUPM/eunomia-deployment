"""Publish the demo factory in an agent's catalog: `eunomia demo publish <agent>`.

It creates the dataset, an HTTP pull and an HTTP push distribution, three
ODRL policies, the pull and push connector templates and one connector
instance per distribution.

Payloads live in payloads/; the __PLACEHOLDERS__ in them are filled in here
with the ids the agent returns and the factory URLs. The connector instances
get the URLs the agent uses (host.docker.internal for local ones): the agent
is the one that calls the factory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from eunomia.ext import Peer, catalog, log

from .factory import Factory

PAYLOADS_DIR = Path(__file__).resolve().parent / "payloads"

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


def payload(name: str) -> Dict[str, Any]:
    return json.loads((PAYLOADS_DIR / name).read_text())


def title() -> str:
    return payload(DATASET)["dctTitle"]


def fill_connector(body: Dict[str, Any], template: Dict[str, Any], distribution_id: str, factory: Factory) -> Dict[str, Any]:
    body["templateName"] = template["name"]
    body["templateVersion"] = template["version"]
    body["distributionId"] = distribution_id
    urls = {
        "__STATIC_API_URL__": factory.docker_static_api,
        "__DYNAMIC_API_URL__": factory.docker_dynamic_api,
        "__KEYCLOAK_URL__": factory.docker_keycloak,
    }
    for key, value in body["parameters"].items():
        if isinstance(value, str):
            for marker, url in urls.items():
                value = value.replace(marker, url)
            body["parameters"][key] = value
    return body


def publish(agent: Peer, factory: Factory, force: bool = False) -> int:
    """Create the demo dataset in an agent's catalog if it is missing. With force, create it again."""
    cat = catalog.Catalog(agent.url)
    log.step(f"Publishing the demo factory in the catalog of {agent.name} (factory: {factory.docker_static_api})")

    existing = {d.get("dctTitle"): d for d in cat.datasets()}
    if title() in existing and not force:
        log.ok(f"Already published ({existing[title()]['id']})")
        return 0

    catalog_id = cat.main_catalog_id()
    data_service_id = cat.main_data_service_id()
    pull_tpl = cat.template(payload(PULL_TEMPLATE))
    push_tpl = cat.template(payload(PUSH_TEMPLATE))

    ds = payload(DATASET)
    ds["catalogId"] = catalog_id
    dataset_id = cat.post("/catalog-agent/datasets", ds)["id"]
    log.ok(f"  dataset      {dataset_id}")

    dist_ids = {}
    for kind, name in (("pull", PULL_DISTRIBUTION), ("push", PUSH_DISTRIBUTION)):
        dist = payload(name)
        dist["dcatAccessService"] = data_service_id
        dist["datasetId"] = dataset_id
        dist_ids[kind] = cat.post("/catalog-agent/distributions", dist)["id"]
        log.ok(f"  {kind} dist    {dist_ids[kind]}")

    tpl = payload(POLICY_TEMPLATE)
    tpl["entityId"] = dataset_id
    cat.post("/catalog-agent/policy-templates/instantiate-odrl-offer", tpl)
    for name in POLICIES:
        policy = payload(name)
        policy["entityId"] = dataset_id
        cat.post("/catalog-agent/odrl-policies", policy)
    log.ok(f"  policies     {1 + len(POLICIES)}")

    cat.post("/connector/instances", fill_connector(payload(PULL_CONNECTOR), pull_tpl, dist_ids["pull"], factory))
    cat.post("/connector/instances", fill_connector(payload(PUSH_CONNECTOR), push_tpl, dist_ids["push"], factory))
    log.ok("  connectors   pull + push")
    log.ok(f"\nThe factory is in the catalog of {agent.name}. Test it: eunomia demo test --consumer <agent> --provider {agent.name}")
    return 0
