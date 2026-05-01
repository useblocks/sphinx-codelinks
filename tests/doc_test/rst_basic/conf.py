# Configuration file for the Sphinx documentation builder.

project = "rst-block-test"
copyright = "2025, useblocks"
author = "useblocks"

extensions = ["sphinx_needs", "sphinx_codelinks"]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

src_trace_config_from_toml = "src_trace.toml"

html_theme = "alabaster"
html_static_path = ["_static"]
