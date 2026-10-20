"""Notebooks against two agents of this data space, one session per pair.

An extension brings its notebooks (ext.NotebookSet); eunomia adds the core
ones: 01_auth.ipynb (the two agents, their DIDs and GNAP tokens), helpers.py
(every API call as a card, lists as tables) and the JupyterLab theme.
`eunomia <extension> notebook <provider> <consumer>` logs the two agents in,
then opens JupyterLab on the pair's session; with --execute it runs the
extension's flows headless.

Each session is independent, so several run at once (alice → bob next to
bob → inaki): its own copy of the notebooks in
notebooks/sessions/<extension>/<provider>-<consumer>/, where its outputs and
edits stay; its own port for the pushed events; its own JupyterLab
workspace. The sources are copied in again when they change (or always,
with --fresh).

Jupyter lives in a virtualenv under notebooks/.venv, created the first time
and refreshed when notebooks/requirements.txt changes.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

from . import compose, exchange, log, settings
from .commands import onboard
from .commands.onboard import Peer
from .settings import REPO_ROOT

NOTEBOOKS_DIR = REPO_ROOT / "notebooks"
VENV_DIR = NOTEBOOKS_DIR / ".venv"
RUNS_DIR = NOTEBOOKS_DIR / ".runs"
SESSIONS_DIR = NOTEBOOKS_DIR / "sessions"
# JupyterLab's custom.css, dressed like the docs. Jupyter only reads it from
# its config dir, so JupyterLab runs with that dir pointed here.
CONFIG_DIR = NOTEBOOKS_DIR / "jupyter"
REQUIREMENTS = NOTEBOOKS_DIR / "requirements.txt"
# Ports for the pushed events, one per session. The CLI's own push legs use 1290.
SINK_PORTS = range(1291, 1400)


def environment(provider: Peer, consumer: Peer, port: int) -> Dict[str, str]:
    """What every notebook reads with os.environ; the extension adds its own.

    EUNOMIA_CONSUMER_DOCKER_URL is the consumer as the provider reaches it
    from its container: the callback address in DSP messages.
    """
    return {
        "EUNOMIA_PROVIDER": provider.name,
        "EUNOMIA_PROVIDER_URL": provider.url,
        "EUNOMIA_CONSUMER": consumer.name,
        "EUNOMIA_CONSUMER_URL": consumer.url,
        "EUNOMIA_CONSUMER_DOCKER_URL": consumer.docker_url,
        "EUNOMIA_SINK_PORT": str(port),
        "EUNOMIA_SINK_DOCKER_URL": f"http://host.docker.internal:{port}/events",
    }


def core_notebooks() -> List[Path]:
    return sorted(NOTEBOOKS_DIR.glob("*.ipynb"))


class Session:
    """One extension and provider/consumer pair: its folder, its port, its workspace."""

    def __init__(self, extension: str, provider: Peer, consumer: Peer) -> None:
        self.name = f"{provider.name}-{consumer.name}"
        self.dir = SESSIONS_DIR / extension / self.name
        self.runs = RUNS_DIR / extension / self.name
        self.workspaces = self.dir / ".workspaces"
        self._record = self.dir / ".session.json"

    def sink_port(self) -> int:
        """The session's port, kept for as long as the session exists.

        EUNOMIA_SINK_PORT wins when set. Otherwise the first port no other
        session holds and nothing listens on.
        """
        if os.environ.get("EUNOMIA_SINK_PORT"):
            return exchange.sink_port()
        if self._record.exists():
            return int(json.loads(self._record.read_text())["sink_port"])
        taken = set()
        for record in SESSIONS_DIR.glob("*/*/.session.json"):
            try:
                taken.add(int(json.loads(record.read_text())["sink_port"]))
            except (ValueError, KeyError):
                continue
        port = next((p for p in SINK_PORTS if p not in taken and not compose.port_in_use(p)), None)
        if port is None:
            raise log.fail(f"Every port in {SINK_PORTS.start}-{SINK_PORTS.stop - 1} is taken. Remove old sessions in {SESSIONS_DIR}.")
        self.dir.mkdir(parents=True, exist_ok=True)
        self._record.write_text(json.dumps({"sink_port": port}) + "\n")
        return port

    def sync(self, sources: List[Path], fresh: bool) -> None:
        """Copy the source notebooks in: the missing ones, the ones changed since, or all with fresh."""
        self.dir.mkdir(parents=True, exist_ok=True)
        copied = []
        for source in sources:
            target = self.dir / source.name
            if fresh or not target.exists() or source.stat().st_mtime > target.stat().st_mtime:
                shutil.copy2(source, target)
                copied.append(source.name)
        if copied:
            log.info(f"  {', '.join(copied)} copied into {self.dir.relative_to(REPO_ROOT)}")


def _bin(name: str) -> Path:
    return VENV_DIR / ("Scripts" if os.name == "nt" else "bin") / name


def _venv() -> None:
    """Create the virtualenv, or reinstall into it when the requirements changed."""
    digest = hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()
    stamp = VENV_DIR / ".requirements.sha256"
    if stamp.exists() and stamp.read_text().strip() == digest and _bin("jupyter").exists():
        return
    if not VENV_DIR.exists():
        log.step(f"Creating a virtualenv for Jupyter in {VENV_DIR.relative_to(REPO_ROOT)} (first time only)")
        if subprocess.call([sys.executable, "-m", "venv", str(VENV_DIR)]) != 0:
            raise log.fail("Could not create the virtualenv. On Debian or Ubuntu: sudo apt install python3-venv")
    log.step("Installing JupyterLab and the notebooks' requirements")
    pip = [str(_bin("python")), "-m", "pip", "install", "--quiet", "--disable-pip-version-check"]
    if subprocess.call(pip + ["-r", str(REQUIREMENTS)]) != 0:
        raise log.fail(f"pip could not install {REQUIREMENTS.relative_to(REPO_ROOT)}")
    stamp.write_text(digest + "\n")


def _prepare(provider: Peer, consumer: Peer, session: Session, extension_env: Dict[str, str]) -> Dict[str, str]:
    if settings.local_host() != "127.0.0.1":
        raise log.fail(
            "The notebooks run on this machine, not in the tools container: they need Python 3.8+ here.\n"
            "Install Python and run the command again (or open the repository in GitHub Codespaces)."
        )
    if provider.name == consumer.name:
        raise log.fail("The provider and the consumer must be two different agents.")
    if not onboard.has_token(consumer, onboard.did(provider.url)):
        onboard.login(provider, consumer)
    else:
        log.ok(f"{provider.name} and {consumer.name} are logged in with each other")
    _venv()
    env = {**environment(provider, consumer, session.sink_port()), **extension_env}
    log.info("\n".join(f"  {k}={v}" for k, v in env.items()))
    # helpers.py stays in notebooks/; the kernels find it from any session.
    path = os.pathsep.join(filter(None, [str(NOTEBOOKS_DIR), os.environ.get("PYTHONPATH")]))
    return {**os.environ, **env, "PYTHONPATH": path}


def lab(extension: str, sources: List[Path], extension_env: Dict[str, str], provider: Peer, consumer: Peer,
        no_browser: bool, fresh: bool) -> int:
    session = Session(extension, provider, consumer)
    env = _prepare(provider, consumer, session, extension_env)
    env.update(
        {
            "JUPYTER_CONFIG_DIR": str(CONFIG_DIR),
            # The person's own settings stay where they are; the workspace is the session's.
            "JUPYTERLAB_SETTINGS_DIR": env.get("JUPYTERLAB_SETTINGS_DIR") or str(Path.home() / ".jupyter" / "lab" / "user-settings"),
            "JUPYTERLAB_WORKSPACES_DIR": str(session.workspaces),
        }
    )
    session.sync(core_notebooks() + sources, fresh)
    log.step(
        f"JupyterLab on {session.dir.relative_to(REPO_ROOT)}: {provider.name} is the provider, "
        f"{consumer.name} the consumer (Ctrl+C to stop)"
    )
    cmd = [str(_bin("jupyter")), "lab", "--custom-css", "--notebook-dir", str(session.dir)] + (["--no-browser"] if no_browser else [])
    try:
        return subprocess.call(cmd, env=env, cwd=session.dir)
    except KeyboardInterrupt:
        return 0


def execute(extension: str, sources: List[Path], extension_env: Dict[str, str], provider: Peer, consumer: Peer,
            flows: List[str]) -> int:
    """Run the flows headless, from a scratch copy; the executed copies go to notebooks/.runs/<extension>/<pair>."""
    session = Session(extension, provider, consumer)
    env = _prepare(provider, consumer, session, extension_env)
    work = session.runs / ".work"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    for source in core_notebooks() + sources:
        shutil.copy2(source, work / source.name)
    failed = []
    for name in flows:
        log.step(f"Running {name}")
        cmd = [
            str(_bin("jupyter")), "nbconvert", "--to", "notebook", "--execute",
            "--ExecutePreprocessor.timeout=300", "--output-dir", str(session.runs), str(work / name),
        ]
        if subprocess.call(cmd, env=env, cwd=work) == 0:
            log.ok(f"  {name} ran to the end: {(session.runs / name).relative_to(REPO_ROOT)}")
        else:
            failed.append(name)
    shutil.rmtree(work, ignore_errors=True)
    if failed:
        raise log.fail(f"Failed: {', '.join(failed)}. The traceback above names the cell.")
    log.ok(f"\nEvery notebook ran with {provider.name} as the provider and {consumer.name} as the consumer.")
    return 0
