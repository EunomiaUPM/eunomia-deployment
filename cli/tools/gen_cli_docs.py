"""Regenerate docs-internal/reference/cli.md from the parser's own help.

    python3 cli/tools/gen_cli_docs.py
"""

import argparse
import os
import sys
from pathlib import Path

# argparse wraps help at the terminal width: fix it so the output is stable.
os.environ["COLUMNS"] = "100"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eunomia.cli import build_parser  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs-internal" / "reference" / "cli.md"

HEADER = """---
title: CLI reference
description: Every eunomia command and its options, generated from the CLI's own help.
---

Run it as `./eunomia <command>` (macOS, Linux) or `.\\eunomia.cmd <command>` (Windows), or `eunomia` after `pip install -e .`. Every command takes `--help`.

This page is generated: `python3 cli/tools/gen_cli_docs.py`.
"""


def _subparsers(parser: argparse.ArgumentParser):
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    return None


def _walk(parser: argparse.ArgumentParser, prefix: str, out: list) -> None:
    sub = _subparsers(parser)
    if sub is None:
        return
    helps = {a.dest: a.help for a in sub._choices_actions}
    for name, child in sub.choices.items():
        title = f"{prefix} {name}".strip()
        nested = _subparsers(child)
        out.append(f"\n## `eunomia {title}`\n\n" if not prefix else f"\n### `eunomia {title}`\n\n")
        if helps.get(name):
            out.append(f"{helps[name][0].upper()}{helps[name][1:]}.\n")
        if nested is None:
            usage = child.format_help().replace("usage: ", "", 1)
            out.append(f"\n```text\n{usage.rstrip()}\n```\n")
        else:
            _walk(child, title, out)


def main() -> None:
    out = [HEADER]
    _walk(build_parser(), "", out)
    OUT.write_text("".join(out))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
