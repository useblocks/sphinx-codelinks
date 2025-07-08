Quick Start
===========

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
