.. _roadmap:

Roadmap
=======

Command-Line Interface
----------------------

- Introduce configurable ``--verbose`` and ``--quiet`` logging options.

Configuration Files
-------------------

- Unify TOML configuration for the ``src-trace`` directive and the ``analyse`` CLI.
- Support automatic discovery of TOML configuration files (e.g., ``pyproject.toml``).
- Discourage global configuration in TOML files to promote project-specific settings.
- Improve integration with the ``ubCode`` and ``Sphinx-Needs`` ecosystems.

Source Code Parsing
-------------------

- Introduce a configurable option to strip leading characters (e.g., ``*``) from commented RST blocks.
- Enrich tagged scopes with additional metadata.
- Extend language support by adding parsers for more comment styles, including:

  - Rust
  - YAML

- Enhance ``.gitignore`` handling to support nested ``.gitignore`` files.

Defining Needs in Source Code
-----------------------------

- Introduce flexible ways to define ``Sphinx-Needs`` items in source code, such as using raw RST text and multi-line comments.
- Implement a feature to export needs defined in source code to a ``needs.json`` file, improving CI workflows and portability.
