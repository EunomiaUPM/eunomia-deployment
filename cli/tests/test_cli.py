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
from eunomia.commands import catalog, images, instances, restart  # noqa: E402

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
        refs = images.pinned()
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
        for f in images.compose_files():
            self.assertTrue(f.is_file(), f)

    def test_one_template_per_kind(self):
        for kind in settings.KINDS:
            self.assertTrue((settings.TEMPLATES_DIR / f"docker-compose.{kind}.yaml").is_file(), kind)

    def test_no_provider_or_consumer_stacks(self):
        """Agents are all the same: no compose file or config is per role."""
        names = [p.name for p in settings.DEPLOYMENT_DIR.rglob("*.yaml")] + [p.name for p in settings.CONFIG_DIR.rglob("*.yaml")]
        self.assertEqual([n for n in names if "provider" in n or "consumer" in n], [])


class Instances(unittest.TestCase):
    def test_agent_config(self):
        agent, fafnir = instances.render_agent_config("my-agent", 1777)
        self.assertIn('port: "1777"', agent)
        self.assertIn('class_id: "my-agent"', agent)
        self.assertIn('"MyAgent"', agent)
        self.assertIn(instances.identity("my-agent")[1], agent)
        for host in ('url: "db"', 'url: "redis"', 'url: "wallet"'):
            self.assertIn(host, agent)
        self.assertIn('url: "db"', fafnir)
        self.assertNotIn("${", agent + fafnir)

    def test_authority_config(self):
        for role in ("eco", "dataspace"):
            authority, fafnir = instances.render_authority_config(role, 1888)
            self.assertIn("port: '1888'", authority)
            self.assertIn("url: 'db'", authority)
            self.assertIn("url: 'wallet'", authority)
            self.assertNotIn("${", authority + fafnir)

    def test_identity_is_stable_and_distinct(self):
        self.assertEqual(instances.identity("alice"), instances.identity("alice"))
        self.assertNotEqual(instances.identity("alice")[1], instances.identity("bob")[1])
        self.assertRegex(instances.identity("alice")[1], r"^VATES-\d{9}$")

    def test_remote_peer_uses_its_url(self):
        inst = instances.Instance("far", "agent", "remote", url="https://agent.example.org")
        self.assertEqual(inst.peer.url, "https://agent.example.org")
        self.assertEqual(inst.peer.docker_url, "https://agent.example.org")

    def test_local_peer_uses_its_port(self):
        inst = instances.Instance("near", "agent", "local", http_port=1650)
        self.assertTrue(inst.peer.url.endswith(":1650"))
        self.assertEqual(inst.peer.docker_url, "http://host.docker.internal:1650")


class Restart(unittest.TestCase):
    def test_agent_restart_keeps_the_database(self):
        script = restart._remote_script("/srv/x", "docker-compose.provider.yaml", "provider", "provider-fafnir-wallet")
        self.assertIn("--no-deps provider-fafnir-wallet provider", script)
        self.assertIn("--env-file ../../versions.env", script)
        self.assertNotIn("down", script)


class Parser(unittest.TestCase):
    def test_up_without_names(self):
        self.assertEqual(build_parser().parse_args(["up"]).names, [])

    def test_exchange_roles(self):
        args = build_parser().parse_args(["e2e", "--consumer", "bob", "--provider", "alice"])
        self.assertEqual((args.consumer, args.provider), ("bob", "alice"))

    def test_exchange_needs_both_roles(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["e2e", "--consumer", "bob"])

    def test_agent_add(self):
        args = build_parser().parse_args(["agent", "add", "alice", "--authority", "auth"])
        self.assertEqual((args.name, args.authority, args.no_onboard), ("alice", "auth", False))

    def test_catalog_needs_an_agent(self):
        self.assertEqual(build_parser().parse_args(["catalog", "populate", "alice"]).agent, "alice")
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["catalog", "populate"])


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
        allowed = (
            "docs/lib/hackathon.ts",
            "docs/components/hackathon/",
            "docs/app/(home)/hackathon/",
            # The home page shows the event banner, the one link towards it.
            "docs/app/(home)/page.tsx",
            # The site's maintainer notes say where those files are.
            "docs/README.md",
            "PLAN.md",
            "cli/tests/test_cli.py",
        )
        offenders = [
            rel for rel, text in _tracked_text_files() if not rel.startswith(allowed) and pattern.search(text + rel)
        ]
        self.assertEqual(offenders, [])

    def test_docs_never_mention_the_event(self):
        """The documentation is universal: the event lives on its own page."""
        content = ROOT / "docs" / "content"
        offenders = [
            str(p.relative_to(ROOT)) for p in content.rglob("*") if p.is_file() and re.search(r"hackat", p.read_text(), re.IGNORECASE)
        ]
        self.assertEqual(offenders, [])

    def test_cli_reference_is_up_to_date(self):
        sys.path.insert(0, str(ROOT / "cli" / "tools"))
        import gen_cli_docs

        out = []
        gen_cli_docs._walk(build_parser(), "", out)
        self.assertEqual(gen_cli_docs.OUT.read_text(), gen_cli_docs.HEADER + "".join(out), "run: python3 cli/tools/gen_cli_docs.py")

if __name__ == "__main__":
    unittest.main()
