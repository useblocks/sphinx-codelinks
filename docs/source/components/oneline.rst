.. _oneline:

One Line Comment Style
======================

Many users raised the concerns about the complication of defining Sphinx-Needs with RST in source code.
Therefore, ``CodeLinks`` provides  a customizable one-line comment style pattern to define ``Sphinx-Needs``
in order to simplify the efforts to create a need in source code.

`Here <oneline_comment_style>`_ is the default one-line comment style.

Start and End sequences
-----------------------

To have better understanding of its the syntax of one-line comment, we will break it down to the following:

**start_sequence** defines the characters where the one-line comment starts.
**end_sequence** defines the characters where the one-line comment ends.

The text between **start_sequence** and **end_sequence** are fields of ``Sphinx-Needs``

field_split_char
----------------

There are always multiple fields for a need. Therefore,

**field_split_char** defines the character to split the text into multiple ``pieces/fields``.

needs_fields
------------

Each fields in a need may have different data types.
It could be a string if it is a field for ``id`` or ``title``. On the other hand,
it could be a list of string as well, if the field requires to have a list of string to represent ``links``

It's where **needs_fields** comes in.

**needs_fields** contains the fields that is required for needs:

Each field defines its:

- name
- data type (Optional)
- default value (Optional)

DataType
~~~~~~~~

By default, a field has the datatype of ``str``.

For example, if the field definition is as follows:

.. code-block:: python

    {
        "name": "title
    }

It's equivalent to:

.. code-block:: python

    {
        "name": "title",
        "type": "str"
    }

If the field is expected to have a list of strings, it shall be defined as the following:

.. code-block:: python

    {
        "name": "links",
        "type": "list[str]"
    }

Default
~~~~~~~




The ``order of needs_fields`` is important because it determines ``the position of the field`` in the one-line comment.
