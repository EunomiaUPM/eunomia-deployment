"""Finding and loading extensions, and wiring their extension points into the CLI.

Built-in extensions live in extensions/ of this repository. EUNOMIA_EXTENSIONS
adds more: paths separated like PATH (":" on Linux and macOS, ";" on
Windows), each one an extension directory or a directory of them. A real
project keeps its extension in its own repository and points there.

An extension directory is a Python package: its __init__.py defines
`extension`. It is imported as eunomia_ext_<name>, so its modules import
each other relatively (`from . import publish`).
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from . import log, notebooks
from .ext import Extension, Loaded
from .settings import REPO_ROOT

BUILTIN_DIR = REPO_ROOT / "extensions"

_loaded: Optional[Dict[str, Loaded]] = None


def _candidates(root: Path) -> List[Path]:
    if (root / "__init__.py").is_file():
        return [root]
    return sorted(p for p in root.iterdir() if (p / "__init__.py").is_file()) if root.is_dir() else []


def _import(path: Path) -> Extension:
    module_name = f"eunomia_ext_{path.name.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, path / "__init__.py", submodule_search_locations=[str(path)])
    if spec is None or spec.loader is None:
        raise log.fail(f"Cannot load the extension in {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    extension = getattr(module, "extension", None)
    if not isinstance(extension, Extension) or not extension.name:
        raise log.fail(f"{path}/__init__.py must define `extension`, an Extension with a name")
    return extension


def load(builtin_only: bool = False) -> Dict[str, Loaded]:
    """Every extension by name, built-in ones first. An extension's name must be unique."""
    global _loaded
    if _loaded is not None and not builtin_only:
        return _loaded
    roots = [(BUILTIN_DIR, True)]
    if not builtin_only:
        for raw in filter(None, (os.environ.get("EUNOMIA_EXTENSIONS") or "").split(os.pathsep)):
            path = Path(raw).expanduser().resolve()
            if not path.exists():
                raise log.fail(f"EUNOMIA_EXTENSIONS names {raw}, which does not exist")
            roots.append((path, False))
    found: Dict[str, Loaded] = {}
    for root, builtin in roots:
        for path in _candidates(root):
            ext = _import(path)
            if ext.name in found:
                raise log.fail(f"Two extensions are called {ext.name!r}: {found[ext.name].path} and {path}")
            found[ext.name] = Loaded(ext, path, builtin, ext.services())
    if not builtin_only:
        _loaded = found
    return found


def services():
    """Every service of every extension, as (extension name, service)."""
    return [(name, svc) for name, loaded in load().items() for svc in loaded.services]


def register(sub: "argparse._SubParsersAction", reserved: List[str], builtin_only: bool = False) -> None:
    """A command group per extension, with its actions plus `test` and `notebook` when it has them."""
    for name, loaded in load(builtin_only).items():
        ext = loaded.extension
        if name in reserved:
            raise log.fail(f"The extension in {loaded.path} is called {name!r}, which is a core command")
        parser = sub.add_parser(name, help=ext.help)
        actions = parser.add_subparsers(dest="action", metavar="<action>")
        actions.required = True
        ext.commands(parser, actions)
        if ext.has_test():
            _add_test(ext, actions)
        if ext.notebooks() is not None:
            _add_notebook(ext, actions)


def _add_test(ext: Extension, actions: "argparse._SubParsersAction") -> None:
    from .ext import add_exchange_roles, agent

    p = actions.add_parser("test", help=f"the {ext.name} extension's end-to-end test between two agents")
    add_exchange_roles(p)
    ext.test_arguments(p)
    p.set_defaults(run=lambda args: ext.test(agent(args.consumer), agent(args.provider), args))


def _add_notebook(ext: Extension, actions: "argparse._SubParsersAction") -> None:
    nb = ext.notebooks()
    assert nb is not None
    notebooks.add_command(
        actions, ext.name, nb, help="the extension's notebooks, with one agent as the provider and another as the consumer"
    )
