"""
Global pytest conftest.py.

This is needed due to:

pytest test discovery error for workspace:  /home/marco/ub/ubtrace
 Failed: Defining 'pytest_plugins' in a non-top-level conftest is no longer supported:
It affects the entire test suite instead of just below the conftest as expected.
  /home/marco/ub/ubtrace/python/ubt_connect_core/tests/conftest.py
Please move it to a top level conftest file at the rootdir:
  /home/marco/ub/ubtrace
For more information, visit:
  https://docs.pytest.org/en/stable/deprecations.html#pytest-plugins-in-non-top-level-conftest-files

See also the root README.md.
"""

# Makes make_app avaialble
pytest_plugins = ("sphinx.testing.fixtures",)
