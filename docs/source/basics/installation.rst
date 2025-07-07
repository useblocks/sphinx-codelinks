.. _installation:

Installation
============

Using Pip
----------

.. code-block:: bash

   pip install sphinx-codelinks

Activation
----------

For activation, please add `sphinx_needs` and `sphinx-codelinks` to the projects's extension list of your **conf.py** file

.. code-block:: python

    extensions = [
        'sphinx_needs',
        'sphinx_codelinks'
    ]
