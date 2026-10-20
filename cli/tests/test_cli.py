"""Unit tests for the parts that need no running stack.

    python3 -m unittest discover -s cli/tests

The built-in extensions' own tests (extensions/*/tests/) run with these: see
test_extension_suites.py.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eunomia import extensions, log, notebooks, settings  # noqa: E402
from eunomia.cli import build_parser  # noqa: E402
from eunomia.commands import images, instances, restart  # noqa: E402
from eunomia.commands.onboard import Peer  # noqa: E402

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
        args = build_parser().parse_args(["demo", "test", "--consumer", "bob", "--provider", "alice"])
        self.assertEqual((args.consumer, args.provider), ("bob", "alice"))

    def test_exchange_needs_both_roles(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["demo", "test", "--consumer", "bob"])

    def test_agent_add(self):
        args = build_parser().parse_args(["agent", "add", "alice", "--authority", "auth"])
        self.assertEqual((args.name, args.authority, args.no_onboard), ("alice", "auth", False))

    def test_catalog_show_needs_an_agent(self):
        self.assertEqual(build_parser().parse_args(["catalog", "show", "alice"]).agent, "alice")
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["catalog", "show"])

    def test_the_demo_lives_under_its_extension(self):
        for old in (["e2e"], ["catalog", "populate", "alice"]):
            with self.assertRaises(SystemExit):
                build_parser().parse_args(old)

    def test_notebooks_are_core_and_per_extension(self):
        core = build_parser().parse_args(["notebook", "alice", "bob", "--dataset", "weather", "--execute", "--flow", "push"])
        self.assertEqual((core.provider, core.consumer, core.dataset, core.flow), ("alice", "bob", "weather", ["push"]))
        demo = build_parser().parse_args(["demo", "notebook", "alice", "bob"])
        self.assertFalse(hasattr(demo, "dataset"))

    def test_extension_actions_run_through_dispatch(self):
        self.assertTrue(callable(build_parser().parse_args(["demo", "publish", "alice"]).run))


class Notebooks(unittest.TestCase):
    """The core notebook (01_auth) and helpers, shared by every extension's notebooks."""

    def test_core_notebooks_read_only_core_variables(self):
        """01_auth and the generic flows work with no extension at all."""
        peer = Peer("alice", "http://127.0.0.1:1601", "http://host.docker.internal:1601")
        provided = set(notebooks.environment(peer, peer, 1291))
        for path in notebooks.core_notebooks() + sorted(notebooks.generic().directory.glob("*.ipynb")):
            for name in re.findall(r'env\(\\?"(EUNOMIA_[A-Z_]+)', path.read_text()):
                self.assertIn(name, provided, f"{path.name} reads {name}")

    def test_generic_flows_exist(self):
        nb = notebooks.generic()
        for name in nb.flows.values():
            self.assertTrue((nb.directory / name).is_file(), name)
        # They chain with %run, so the catalog notebook sits next to them.
        self.assertTrue((nb.directory / "02_catalog.ipynb").is_file())

    def test_committed_without_outputs(self):
        # The outputs carry DIDs and GNAP tokens of whoever ran them last.
        sources = notebooks.core_notebooks() + sorted(notebooks.generic().directory.glob("*.ipynb"))
        sources += sorted((ROOT / "extensions").glob("*/notebooks/*.ipynb"))
        self.assertTrue(sources)
        for path in sources:
            for cell in json.loads(path.read_text())["cells"]:
                self.assertFalse(cell.get("outputs"), f"{path.name} has outputs")


EXTERNAL = textwrap.dedent(
    """
    from eunomia.ext import Extension


    class Lab(Extension):
        name = "{name}"
        help = "an extension from another repository"

        def commands(self, parser, actions):
            actions.add_parser("hello").set_defaults(run=lambda args: 7)


    extension = Lab()
    """
)


class Extensions(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.get("EUNOMIA_EXTENSIONS")
        extensions._loaded = None

    def tearDown(self):
        if self._env is None:
            os.environ.pop("EUNOMIA_EXTENSIONS", None)
        else:
            os.environ["EUNOMIA_EXTENSIONS"] = self._env
        extensions._loaded = None

    def _external(self, name):
        root = Path(tempfile.mkdtemp()) / name
        root.mkdir()
        (root / "__init__.py").write_text(EXTERNAL.format(name=name))
        os.environ["EUNOMIA_EXTENSIONS"] = str(root)
        return root

    def test_the_demo_is_built_in(self):
        loaded = extensions.load()
        self.assertIn("demo", loaded)
        self.assertTrue(loaded["demo"].builtin)
        self.assertTrue(loaded["demo"].extension.has_test())
        self.assertIsNotNone(loaded["demo"].extension.notebooks())

    def test_services_reach_the_core(self):
        names = [svc.name for _, svc in extensions.services()]
        self.assertIn("demo", names)
        self.assertIn(extensions.load()["demo"].services[0].compose_file, images.compose_files())

    def test_an_external_extension_adds_its_commands(self):
        self._external("lab")
        args = build_parser().parse_args(["lab", "hello"])
        self.assertEqual(args.run(args), 7)
        self.assertFalse(extensions.load()["lab"].builtin)

    def test_the_reference_lists_only_built_in_extensions(self):
        self._external("lab")
        with self.assertRaises(SystemExit):
            build_parser(builtin_extensions_only=True).parse_args(["lab", "hello"])

    def test_an_extension_cannot_take_a_core_command(self):
        self._external("notebook")
        with self.assertRaises(log.Abort):
            build_parser()

    def test_names_are_unique(self):
        self._external("demo")
        with self.assertRaises(log.Abort):
            extensions.load()


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
