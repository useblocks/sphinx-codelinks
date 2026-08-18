# Configuration file for the Sphinx documentation builder.
project = "marked-rst-demo"
copyright = "2026, useblocks"
author = "useblocks"

extensions = ["sphinx_needs", "sphinx_codelinks"]

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

src_trace_config_from_toml = "src_trace.toml"

html_theme = "alabaster"
