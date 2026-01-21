RST directive Parser
====================

The :ref:`analyse <analyse>` module provides a simplified parser for reStructuredText (reST) directives using the ``Lark`` parsing library.
It is designed to only parse the RST text extracted by :ref:`RST markers <analyse_rst>`, focusing on specific directive types and their associated options and content.
By doing so, the parser avoids the complexity of a full reST parser while still capturing the essential structure needed for Sphinx-Needs integration from the source code.

The parser doesn't have the Sphinx-Needs directive validation logic. It only checks the syntax of the RST directives and extracts:
   - directive type
   - argument (title)
   - options
   - content

These extracted data will be furthered used with :external+needs:ref:`add_need <api>` function to create Sphinx-Needs items in ``src-trace`` directive.

**Limitations**

Since the parser does not implement the full reST specification, it has some limitations:

- Comments in the RST text are not supported.
- The parser expects consistent indentation for options and content blocks.
- It only takes an inline directive argument/title (no multi-line arguments/titles).
- It only takes inline option values (no multi-line option values).
