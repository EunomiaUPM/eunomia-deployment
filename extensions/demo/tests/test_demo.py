"""Unit tests of the demo extension: what needs no running stack.

They run with the core ones (python3 -m unittest discover -s cli/tests).
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "cli"))

from eunomia import extensions, notebooks  # noqa: E402
from eunomia.commands.onboard import Peer  # noqa: E402

LOADED = extensions.load(builtin_only=True)["demo"]
DEMO = LOADED.extension
publish = sys.modules["eunomia_ext_demo.publish"]
factory = sys.modules["eunomia_ext_demo.factory"]
demo_package = sys.modules["eunomia_ext_demo"]


class Payloads(unittest.TestCase):
    def test_payloads_exist(self):
        for name in publish.PAYLOADS:
            self.assertTrue((publish.PAYLOADS_DIR / name).is_file(), name)

    def test_fill_connector(self):
        f = factory.urls()
        body = publish.payload(publish.PULL_CONNECTOR)
        filled = publish.fill_connector(body, {"name": "urn:t", "version": "1.0"}, "urn:d", f)
        self.assertEqual(filled["templateName"], "urn:t")
        self.assertEqual(filled["distributionId"], "urn:d")
        self.assertEqual(filled["parameters"]["ACCESS_URL"], f"{f.docker_static_api}/robots/")
        self.assertEqual(filled["parameters"]["TOKEN_URL"], f.docker_token_url)

    def test_no_placeholder_left(self):
        f = factory.urls()
        for name in (publish.PULL_CONNECTOR, publish.PUSH_CONNECTOR):
            filled = publish.fill_connector(publish.payload(name), {"name": "n", "version": "v"}, "d", f)
            self.assertNotIn("__", str(filled["parameters"]), name)


class Service(unittest.TestCase):
    def test_compose_file_exists(self):
        (svc,) = LOADED.services
        self.assertTrue(svc.compose_file.is_file())
        self.assertEqual(svc.ports, factory.ports())


class Notebooks(unittest.TestCase):
    def test_flows_exist(self):
        nb = DEMO.notebooks()
        for name in nb.flows.values():
            self.assertTrue((nb.directory / name).is_file(), name)

    def test_every_variable_they_read_is_set(self):
        """What the core sets plus what the demo adds covers every env("...") in the notebooks."""
        peer = Peer("alice", "http://127.0.0.1:1601", "http://host.docker.internal:1601")
        provided = set(notebooks.environment(peer, peer, 1291)) | set(demo_package.notebook_vars(factory.urls()))
        for path in sorted(DEMO.notebooks().directory.glob("*.ipynb")):
            for name in re.findall(r'env\(\\?"(EUNOMIA_[A-Z_]+)', path.read_text()):
                self.assertIn(name, provided, f"{path.name} reads {name}")
