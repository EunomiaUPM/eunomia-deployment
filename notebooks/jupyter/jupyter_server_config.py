"""JupyterLab as `eunomia <extension> notebook` runs it (JUPYTER_CONFIG_DIR=notebooks/jupyter).

`eunomia <extension> notebook` opens a session (notebooks/sessions/<ext>/<pair>/), which
keeps its outputs. Should a Jupyter ever save the sources in notebooks/
themselves, they are saved without outputs: those carry the DIDs and GNAP
tokens of whoever ran them, and the sources are in git.
"""

import os

c = get_config()  # noqa: F821 (Jupyter provides it)

SOURCES = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def strip_outputs(model, path, contents_manager, **kwargs):
    full = os.path.join(contents_manager.root_dir, path.strip("/"))
    if model.get("type") != "notebook" or os.path.dirname(os.path.abspath(full)) != SOURCES:
        return
    for cell in model["content"].get("cells", []):
        if cell.get("cell_type") == "code":
            cell["outputs"] = []
            cell["execution_count"] = None


c.FileContentsManager.pre_save_hook = strip_outputs

# The theme's own folder is no part of the tutorial: keep it out of the file browser.
c.ContentsManager.hide_globs = ["jupyter", "__pycache__", "*.pyc", ".DS_Store", ".ipynb_checkpoints"]
