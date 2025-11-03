.. _directive:

Directive
=========

.. attention:: ``src-trace`` directive do NOT supports :ref:`Sphinx-Needs ID Refs <analyse_need_id_refs>`.

``src-trace`` Directive generates Sphinx-Needs items from source code comments. There are two ways to define need items in source code:

1. **One-line need definition**: Define needs in a single line comment.

   Example in C++:

   .. code-block:: cpp

      // @ title, id_123, implementation, [link1, link2]

2. **RST block need definition**: Define needs in a RST block comment.

   Example in C++:

   .. code-block:: cpp

      /*
       .. implementation:: title
         :id: id_123
         :links: link1, link2
      */

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
