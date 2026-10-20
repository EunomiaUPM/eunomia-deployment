"""Unit tests for the parts that need no running stack.

    python3 -m unittest discover -s cli/tests
"""

import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eunomia import settings  # noqa: E402
from eunomia.cli import build_parser  # noqa: E402
from eunomia.commands import catalog, images, instances, restart, stack  # noqa: E402

ROOT = settings.REPO_ROOT


class ParseDotenv(unittest.TestCase):
    def test_comments_quotes_and_hashes(self):
        env = settings.parse_dotenv(
            "# comment\n"
            "\n"
            "A=1\n"
            "B = spaced \n"
            "C=\"quoted # kept\"\n"
            "D='single'\n"
            "E=value # inline comment\n"
            "F=pa#ss\n"
            "export G=exported\n"
            "not a pair\n"
        )
        self.assertEqual(
            env,
            {"A": "1", "B": "spaced", "C": "quoted # kept", "D": "single", "E": "value", "F": "pa#ss", "G": "exported"},
        )


class ResolveNodes(unittest.TestCase):
    def test_default_is_everything(self):
        self.assertEqual(stack.resolve_nodes([]), ["authority", "provider", "consumer", "demo"])
        self.assertEqual(stack.resolve_nodes(["all"]), ["authority", "provider", "consumer", "demo"])

    def test_dependency_order_wins_over_typed_order(self):
        self.assertEqual(stack.resolve_nodes(["consumer", "authority"]), ["authority", "consumer"])


class ImageRefs(unittest.TestCase):
    def test_split(self):
        self.assertEqual(images._split("quay.io/eunomia_upm/ds-agent:v0.4.0"), ("quay.io", "eunomia_upm/ds-agent", "v0.4.0"))
        self.assertEqual(images._split("rmenendez8/fafnir:v0.2.0"), ("docker.io", "rmenendez8/fafnir", "v0.2.0"))
        self.assertEqual(images._split("postgres:18"), ("docker.io", "library/postgres", "18"))
        self.assertEqual(images._split("postgres"), ("docker.io", "library/postgres", ""))

    def test_resolve_versions(self):
        values = {"EUNOMIA_IMAGE": "quay.io/x/agent", "EUNOMIA_TAG": "v1"}
        self.assertEqual(
            images.resolve("${EUNOMIA_IMAGE:?set EUNOMIA_IMAGE in versions.env}:${EUNOMIA_TAG}", values), "quay.io/x/agent:v1"
        )

    def test_every_image_is_pinned(self):
        for env in settings.ENVIRONMENTS:
            refs = images.pinned(env)
            self.assertTrue(any("ds-agent" in r for r in refs), "the versions.env images are resolved")
            for ref in refs:
                self.assertNotIn("${", ref)
                self.assertTrue(images._split(ref)[2], f"{ref} has no tag")
                self.assertNotIn(":latest", ref)


class Catalog(unittest.TestCase):
    def test_payloads_exist(self):
        for name in catalog.PAYLOADS:
            self.assertTrue((settings.CATALOG_DIR / name).is_file(), name)

    def test_fill_connector(self):
        demo = settings.demo()
        payload = catalog._payload(catalog.PULL_CONNECTOR)
        filled = catalog.fill_connector(payload, {"name": "urn:t", "version": "1.0"}, "urn:d", demo)
        self.assertEqual(filled["templateName"], "urn:t")
        self.assertEqual(filled["distributionId"], "urn:d")
        self.assertEqual(filled["parameters"]["ACCESS_URL"], f"{demo.docker_static_api}/robots/")
        self.assertEqual(filled["parameters"]["TOKEN_URL"], f"{demo.docker_keycloak}/realms/factory/protocol/openid-connect/token")

    def test_no_placeholder_left(self):
        demo = settings.demo()
        for name, tpl in ((catalog.PULL_CONNECTOR, None), (catalog.PUSH_CONNECTOR, None)):
            filled = catalog.fill_connector(catalog._payload(name), {"name": "n", "version": "v"}, "d", demo)
            self.assertNotIn("__", str(filled["parameters"]), name)


class Compose(unittest.TestCase):
    def test_every_compose_file_exists(self):
        for env in settings.ENVIRONMENTS:
            for node, s in settings.stacks(env).items():
                self.assertTrue(s.compose.is_file(), f"{env}/{node}: {s.compose}")

    def test_prefix_is_configurable(self):
        for s in settings.stacks("standalone").values():
            text = s.compose.read_text()
            names = re.findall(r"container_name:\s*\"?([^\"\n]+)", text)
            for name in names:
                self.assertTrue(name.startswith("${EUNOMIA_PREFIX:-eunomia}-"), f"{s.compose.name}: {name}")


class Instances(unittest.TestCase):
    def test_connector_config_uses_its_own_services_and_port(self):
        for role in ("consumer", "provider"):
            agent, fafnir = instances.render_connector_config(role, 1777, "my-conn")
            self.assertNotIn(f"{role}-db", agent + fafnir)
            self.assertNotIn(f"{role}-redis", agent)
            self.assertNotIn(f"{role}-fafnir-wallet", agent)
            self.assertIn('port: "1777"', agent)
            self.assertNotIn(f'"{settings.STANDALONE_PORTS[role]}"', agent)
            self.assertIn('"MyConn"', agent)

    def test_authority_config(self):
        for role in ("eco", "dataspace"):
            authority, fafnir = instances.render_authority_config(role, 1888)
            self.assertIn("port: '1888'", authority)
            self.assertNotIn("heimdall-db", authority + fafnir)
            self.assertNotIn("heimdall-fafnir-wallet", authority)

    def test_identity_is_stable_and_distinct(self):
        self.assertEqual(instances._identity("buyer"), instances._identity("buyer"))
        self.assertNotEqual(instances._identity("buyer")[1], instances._identity("seller")[1])
        self.assertRegex(instances._identity("buyer")[1], r"^VATES-\d{9}$")


class Restart(unittest.TestCase):
    def test_agent_restart_keeps_the_database(self):
        script = restart._remote_script("/srv/x", "docker-compose.provider.yaml", "provider", "provider-fafnir-wallet")
        self.assertIn("--no-deps provider-fafnir-wallet provider", script)
        self.assertIn("--env-file ../../versions.env", script)
        self.assertNotIn("down", script)


class Parser(unittest.TestCase):
    def test_up_without_nodes(self):
        args = build_parser().parse_args(["up"])
        self.assertEqual((args.nodes, args.env), ([], "standalone"))

    def test_onboard_register_node(self):
        args = build_parser().parse_args(["onboard", "register", "provider"])
        self.assertEqual((args.step, args.node), ("register", "provider"))

    def test_peers(self):
        args = build_parser().parse_args(["e2e", "--consumer", "buyer", "--provider", "seller"])
        self.assertEqual((args.consumer, args.provider), ("buyer", "seller"))

    def test_connector_add(self):
        args = build_parser().parse_args(["connector", "add", "x", "--role", "provider"])
        self.assertEqual((args.name, args.role, args.onboard), ("x", "provider", False))


def _tracked_text_files():
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard"], capture_output=True, text=True
    )
    if out.returncode != 0:
        raise unittest.SkipTest("not a git checkout")
    for rel in out.stdout.splitlines():
        path = ROOT / rel
        if not path.is_file() or path.suffix in (".png", ".svg", ".pem", ".sum"):
            continue
        try:
            yield rel, path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue


class Repo(unittest.TestCase):
    """What this public, generic repo must not contain."""

    def test_no_use_case_leftovers(self):
        pattern = re.compile(r"ecostars|esds|\bhotels?\b", re.IGNORECASE)
        allowed = {"PLAN.md", "cli/tests/test_cli.py"}
        offenders = [rel for rel, text in _tracked_text_files() if rel not in allowed and pattern.search(text)]
        self.assertEqual(offenders, [])

    def test_hackathon_only_in_its_landing(self):
        pattern = re.compile(r"hackat|hackath", re.IGNORECASE)
        # The docs root lists the folder so the site shows it; nothing else points there.
        allowed = ("docs-internal/hackathon/", "docs-internal/meta.json", "PLAN.md", "cli/tests/test_cli.py")
        offenders = [
            rel for rel, text in _tracked_text_files() if not rel.startswith(allowed) and pattern.search(text + rel)
        ]
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
