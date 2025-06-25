Configuration
-------------

The config for source tracing can be specified in ``conf.py`` or ``toml`` file.
In the case where the config is introduced in ``toml`` file, the config path needs to be specified in ``conf.py``

.. code-block:: python

   # Specify the config path for source tracing in conf.py
   src_trace_config_from_toml = "src_trace.toml"

**Example Config**

.. literalinclude:: ./../src_trace.toml
   :language: toml
