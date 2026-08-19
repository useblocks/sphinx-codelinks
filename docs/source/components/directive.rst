.. _directive:

Directive
=========

``CodeLinks`` provides ``src-trace`` directive and it can be used in the following ways:

.. code-block:: rst

   .. src-trace::
      :project: project_config
      :file: example.cpp

or

.. code-block:: rst

   .. src-trace::
      :project: project_config
      :directory: ./example

The ``src-trace`` directive has the following options:

* **project**: the project config specified in ``conf.py`` or TOML file to be used for source tracing.
* **file**: the source file to be traced.
* **directory**: the source files in the directory to be traced recursively.

Regarding the **file** and **directory** options:

- They are optional and mutually exclusive.
- The given paths are relative to ``src_dir`` defined in the source tracing configuration.
- If not given, the whole project will be examined.

Example
-------

With the following configuration for a demo source code project `dcdc <https://github.com/useblocks/sphinx-codelinks/tree/main/tests/data/dcdc>`_,

.. code-block:: python
   :caption: conf.py

   src_trace_config_from_toml = "src_trace.toml"

.. literalinclude:: ./../../src_trace.toml
   :caption: src_trace.toml
   :language: toml

The ``src-trace`` directive can be used with the **file** option:

.. code-block:: rst

   .. src-trace::
      :project: dcdc
      :file: ./charge/demo_1.cpp

The needs defined in source code are extracted and rendered to:

.. src-trace::
   :project: dcdc
   :file: ./charge/demo_1.cpp

The ``src-trace`` directive can be used with the **directory** option:

.. code-block:: rst

   .. src-trace::
      :project: dcdc
      :directory: ./discharge

The needs defined in source code are extracted and rendered to:

.. src-trace::
   :project: dcdc
   :directory: ./discharge

To have a more customized configuration of ``CodeLinks``, please refer to :ref:`configuration <configuration>`.

.. _marked_rst:

Marked reStructuredText
-----------------------

In addition to :ref:`one-line needs <oneline>`, the ``src-trace`` directive can
render marked reStructuredText blocks extracted from source
code comments. Marked-RST support is opt-in and requires enabling
``get_rst = true`` for the project in your ``src_trace.toml`` (or via
``src_trace_projects`` in ``conf.py``).

.. code-block:: toml
   :caption: src_trace.toml

   [codelinks.projects.dcdc.analyse]
   get_rst = true

Each marked block is parsed inline into the current document, so the author has
full control over what is emitted — including custom directives such as
``.. impl::`` from sphinx-needs, cross-references, admonitions, or plain
paragraphs. Example marker in C++:

.. code-block:: cpp

   /*
   @rst
   .. impl:: implement dummy function 1
      :id: IMPL_71
   @endrst
   */
   void dummy_func1() {}

When source page generation is enabled (``set_local_url = true``), the source
file line containing the marker is linked back to the document that hosts the
``src-trace`` directive.
