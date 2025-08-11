.. _changelog:

Changelog
=========

.. _`release:1.0.0`:

1.0.0
-----

:Released: 12.08.2025

New and Improved
................

- ✨ Added a new ``analyse`` CLI command and corresponding API.

  The ``analyse`` command parses source files (Python, C/C++) and extracts markers from comments.
  It can extract three types of markers, as documented in the :ref:`analyse <analyse>` section:

  - One-line need definitions
  - Need ID references
  - Marked RST blocks

  The extracted markers and their metadata are saved to a JSON file for further processing.

- 🔨 Replaced ``virtual_docs`` with the new ``analyse`` module.

  The ``virtual_docs`` feature, which handled one-line need definitions (:ref:`OneLineCommentStyle <oneline>`),
  has been migrated into the new ``analyse`` module and removed from the core.
  The caching feature of ``virtual_docs`` is temporarily removed and may be reintroduced later.

- 🔨 Updated the ``src-trace`` Sphinx directive.

  The ``src-trace`` directive now uses the new ``analyse`` API instead of the old ``virtual_docs`` one.
  Note that the configuration files for ``src-trace`` and the ``analyse`` CLI are not yet compatible; this will be addressed in a future release.

.. _`release:0.1.2`:

0.1.2
-----

:Released: 16.07.2025

Fixes
.....

- 🐛 Applying default configuration value when not given

  When a user does not specify certain configuration options, the extension will automatically use predefined default
  values, allowing users to get started quickly without needing to customize every option.
  Users can override these defaults by explicitly providing their own configuration values.

- 🐛 Fix local links for multi project configurations

  Local links between docs and one-line need definitions work correctly, when :ref:`src_dir <source_dir>` in multiple
  project configurations point at different locations.

.. _`release:0.1.1`:

0.1.1
-----

:Released: 11.07.2025

Initial release of ``Sphinx-CodeLinks``

This version features:

- ✨ Sphinx Directive ``src-trace``
- ✨ Virtual Docs and Source Discovery CLI
- ✨ One-line comment to define a ``Sphinx-Needs`` need item
