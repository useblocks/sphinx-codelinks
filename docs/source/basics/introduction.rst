Introduction
============

``CodeLinks`` is a sphinx extension that provides a directive ``src-trace``
to trace the :external+needs:doc:`Sphinx-Needs <index>` defined in source files.

The provided directive leverages the other two modules ``SourceDiscovery`` and ``VirtualDocs``,
which are also packed in the extension,
to discover source files and create the virtual documents for ``src-trace`` to consume.

Both ``SourceDiscovery`` and ``VirtualDocs`` provide the followings for the developers :

- **Python API** to extend other further use cases.
- **CLI** to have atomic steps in CI/CD pipelines.
