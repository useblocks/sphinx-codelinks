.. _analyse:

Source Analyse
==============

The **Source Analyse** module is a powerful component of **Sphinx-CodeLinks** that extracts documentation-related content from source code comments. It provides both CLI and API interfaces for flexible integration into documentation workflows.

**Key Capabilities:**

- Extract **Sphinx-Needs** ID references from source code comments
- Process custom one-line comment patterns for rapid documentation
- Extract marked reStructuredText (RST) blocks embedded in comments
- Generate structured JSON output for further processing
- Support for multiple programming language comment styles

Overview
--------

Source Analyse works by parsing source code files and identifying specially marked comments that contain documentation information. This enables developers to embed documentation directly in their source code while maintaining clean separation between code and documentation.

The module supports three primary extraction modes:

1. **Sphinx-Needs ID References** - Links between code and requirements/specifications
2. **One-line Needs** - Simplified syntax for creating documentation needs
3. **Marked RST Blocks** - Full reStructuredText content embedded in comments

Supported Content Types
-----------------------

Sphinx-Needs ID References
~~~~~~~~~~~~~~~~~~~~~~~~~~

Extract references to **Sphinx-Needs** items directly from source code comments, enabling traceability between code implementations and requirements.

One-line Needs
~~~~~~~~~~~~~~

Use simplified comment patterns to define **Sphinx-Needs** items without complex RST syntax. See :ref:`OneLineCommentStyle <oneline>` for detailed information.

Marked RST Blocks
~~~~~~~~~~~~~~~~~

Embed complete reStructuredText directives which is extracted and parsed as the grammar of **Sphinx-Needs** definition blocks.

Limitations
-----------

**Current Limitations:**

- **Language Support**: C/C++ (``//``, ``/* */``), C# (``//``, ``/* */``, ``///``), Python (``#``), YAML (``#``) and Rust (``//``, ``/* */``, ``///``) comment styles are supported
- **Single Comment Style**: Each analysis run processes only one comment style at a time

Extraction Examples
-------------------

The following examples are configured with :ref:`the analyse configuration <analyse_config>`,

.. _`analyse_need_id_refs`:

Sphinx-Needs ID References
~~~~~~~~~~~~~~~~~~~~~~~~~~

Below is an example of a C++ source file containing need ID references and the corresponding JSON output from the analyse.

.. tabs::

   .. code-tab:: cpp

        #include <iostream>

        // @need-ids: need_001, need_002, need_003, need_004
        void dummy_func1(){
            //...
        }

        // @need-ids: need_003
        int main() {
            std::cout << "Starting demo_1..." << std::endl;
            dummy_func1();
            std::cout << "Demo_1 finished." << std::endl;
            return 0;
        }

   .. code-tab:: json

        [
            {
                "filepath": "tests/data/need_id_refs/dummy_1.cpp",
                "remote_url": "https://github.com/useblocks/sphinx-codelinks/blob/fa5a9129d60203355ae9fe4a725246a88522c60c/tests/data/need_id_refs/dummy_1.cpp#L3",
                "source_map": {
                    "start": { "row": 2, "column": 13 },
                    "end": { "row": 2, "column": 51 }
                },
                "tagged_scope": "void dummy_func1(){\n     //...\n }",
                "need_ids": ["need_001", "need_002", "need_003", "need_004"],
                "marker": "@need-ids:",
                "type": "need-id-refs"
            },
            {
                "filepath": "tests/data/need_id_refs/dummy_1.cpp",
                "remote_url": "https://github.com/useblocks/sphinx-codelinks/blob/fa5a9129d60203355ae9fe4a725246a88522c60c/tests/data/need_id_refs/dummy_1.cpp#L8",
                "source_map": {
                    "start": { "row": 7, "column": 13 },
                    "end": { "row": 7, "column": 21 }
                },
                "tagged_scope": "int main() {\n   std::cout << \"Starting demo_1...\" << std::endl;\n   dummy_func1();\n   std::cout << \"Demo_1 finished.\" << std::endl;\n   return 0;\n }",
                "need_ids": ["need_003"],
                "marker": "@need-ids:",
                "type": "need-id-refs"
            }
        ]

**Output Structure:**

- ``filepath`` - Path to the source file containing the reference
- ``remote_url`` - URL to the source code in the remote repository
- ``source_map`` - Location information (row/column) of the marker
- ``tagged_scope`` - The code scope associated with the marker
- ``need_ids`` - List of referenced need IDs
- ``marker`` - The marker string used for identification
- ``type`` - Type of extraction ("need-id-refs")

.. _`analyse_rst`:

Marked RST Blocks
~~~~~~~~~~~~~~~~~

This example demonstrates how the analyse extracts RST blocks from comments.

.. tabs::

   .. code-tab:: cpp
      :linenos:

       #include <iostream>

       /*
       @rst
       .. impl:: implement dummy function 1
       :id: IMPL_71
       @endrst
       */
       void dummy_func1(){
           //...
       }

       // @rst..impl:: implement main function @endrst
       int main() {
           std::cout << "Starting demo_1..." << std::endl;
           dummy_func1();
           std::cout << "Demo_1 finished." << std::endl;
           return 0;
       }

   .. code-tab:: json

       [
           {
               "filepath": "marked_rst/dummy_1.cpp",
               "remote_url": "https://github.com/useblocks/sphinx-codelinks/blob/26b301138eef25c5130518d96eaa7a29a9c6c9fe/marked_rst/dummy_1.cpp#L4",
               "source_map": {
                   "start": { "row": 3, "column": 8 },
                   "end": { "row": 3, "column": 61 }
               },
               "tagged_scope": "void dummy_func1(){\n     //...\n }",
               "rst": ".. impl:: implement dummy function 1\n   :id: IMPL_71\n",
               "type": "rst"
           },
           {
               "filepath": "marked_rst/dummy_1.cpp",
               "remote_url": "https://github.com/useblocks/sphinx-codelinks/blob/26b301138eef25c5130518d96eaa7a29a9c6c9fe/marked_rst/dummy_1.cpp#L14",
               "source_map": {
                   "start": { "row": 13, "column": 7 },
                   "end": { "row": 13, "column": 40 }
               },
               "tagged_scope": "int main() {\n   std::cout << \"Starting demo_1...\" << std::endl;\n   dummy_func1();\n   std::cout << \"Demo_1 finished.\" << std::endl;\n   return 0;\n }",
               "rst": "..impl:: implement main function ",
               "type": "rst"
           }
       ]

**Output Structure:**

- ``filepath`` - Path to the source file containing the RST block
- ``remote_url`` - URL to the source code in the remote repository
- ``source_map`` - Location information of the RST markers
- ``tagged_scope`` - The code scope associated with the RST block
- ``rst`` - The extracted reStructuredText content
- ``type`` - Type of extraction ("rst")

**RST Block Formats:**

The module supports both multi-line and single-line RST blocks:

- **Multi-line blocks**: Use ``@rst`` and ``@endrst`` on separate lines
- **Single-line blocks**: Use ``@rst content @endrst`` on the same line

.. _`analyse_oneline`:

One-line Needs
--------------

**One-line Needs** provide a simplified syntax for creating **Sphinx-Needs** items directly in source code comments without requiring full RST syntax.

For comprehensive information about one-line needs configuration and usage, see :ref:`OneLineCommentStyle <oneline>`.

**Basic Example:**


.. tabs::

   .. code-tab:: c
      :linenos:

      // @Function Foo, IMPL_1
      void foo() {}

      // @Function Bar, IMPL_2
      void bar() {}

      // @Function Baz\, as I want it, IMPL_3
      void baz() {}

   .. code-tab:: json

      [
         {
            "filepath": "/home/jui-wen/git_repo/ub/sphinx-codelinks/tests/data/oneline_comment_default/default_oneliners.c",
            "remote_url": "https://github.com/useblocks/sphinx-codelinks/blob/951e40e7845f06d5cfc4ca20ebb984308fdaf985/tests/data/oneline_comment_default/default_oneliners.c#L1",
            "source_map": {
                  "start": { "row": 0, "column": 4 },
                  "end": { "row": 0, "column": 24 }
            },
            "tagged_scope": "void foo() {}",
            "need": {
                  "title": "Function Foo",
                  "id": "IMPL_1",
                  "type": "impl",
                  "links": []
            },
            "type": "need"
         },
         {
            "filepath": "/home/jui-wen/git_repo/ub/sphinx-codelinks/tests/data/oneline_comment_default/default_oneliners.c",
            "remote_url": "https://github.com/useblocks/sphinx-codelinks/blob/951e40e7845f06d5cfc4ca20ebb984308fdaf985/tests/data/oneline_comment_default/default_oneliners.c#L4",
            "source_map": {
                  "start": { "row": 3, "column": 4 },
                  "end": { "row": 3, "column": 24 }
            },
            "tagged_scope": "void bar() {}",
            "need": {
                  "title": "Function Bar",
                  "id": "IMPL_2",
                  "type": "impl",
                  "links": []
            },
            "type": "need"
         },
         {
            "filepath": "/home/jui-wen/git_repo/ub/sphinx-codelinks/tests/data/oneline_comment_default/default_oneliners.c",
            "remote_url": "https://github.com/useblocks/sphinx-codelinks/blob/951e40e7845f06d5cfc4ca20ebb984308fdaf985/tests/data/oneline_comment_default/default_oneliners.c#L7",
            "source_map": {
                  "start": { "row": 6, "column": 4 },
                  "end": { "row": 6, "column": 39 }
            },
            "tagged_scope": "void baz() {}",
            "need": {
                  "title": "Function Baz, as I want it",
                  "id": "IMPL_3",
                  "type": "impl",
                  "links": []
            },
            "type": "need"
         }
      ]
