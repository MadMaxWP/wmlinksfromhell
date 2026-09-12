from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

project = "wmlinksfromhell"
author = "Max"
copyright = "2026, Max"
version = "0.1.2"
release = "0.1.2"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
]

autosummary_generate = True
autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
}
autodoc_typehints = "description"

templates_path = ["_templates"]
exclude_patterns = []

html_theme = "sphinx_rtd_theme"
html_title = "wmlinksfromhell"
html_static_path = []
html_show_sphinx = False

html_context = {
    "display_github": True,
    "github_user": "MadMaxWP",
    "github_repo": "wmlinksfromhell",
    "github_version": "main",
    "conf_py_path": "/docs/source/",
}

html_theme_options = {
    "vcs_pageview_mode": "edit",
}

master_doc = "index"
