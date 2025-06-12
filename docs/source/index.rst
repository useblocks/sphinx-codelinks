CodeLinks
=========

``CodeLinks`` is a sphinx extension that provides a directive ``src-trace`` to trace the needs of source files.

Usage
-----

.. code-block:: rst

   .. src-trace:: example_with_file
      :project: project_config
      :file: example.cpp


or

.. code-block:: rst

   .. src-trace:: example_with_directory
      :project: project_config
      :directory: ./example


``src-trace`` directive has the following options:

* **project**: the project config specified in ``conf.py`` or ``toml`` to be used for source tracing.
* **file**: the source file to be traced.
* **directory**: the source files in the directory to be traced recursively.

Regarding the options **file** and **directory**:

- they are optional and mutually exclusive.
- the given paths of them are relative to ``src_dir`` defined in the source tracing configuration
- if not given, the whole project will be examined.

**Example**

.. src-trace:: dcdc demo_1
   :project: dcdc
   :file: ./charge/demo_1.cpp

.. src-trace:: dcdc charge
   :project: dcdc
   :directory: ./discharge

Config
------

The config for source tracing can be specified in ``conf.py`` or ``toml`` file.
In the case where the config is introduced in ``toml`` file, the config path needs to be specified in ``conf.py``

.. code-block:: python

   # Specify the config path for source tracing in conf.py
   src_trace_config_from_toml = "src_trace.toml"

**Example Config**

 .. literalinclude:: ./../src_trace.toml
   :language: toml
