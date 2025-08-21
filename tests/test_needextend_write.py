from pathlib import Path

import pytest

from sphinx_codelinks.analyse.models import MarkedContentType
from sphinx_codelinks.needextend_write import convert_marked_content


@pytest.mark.parametrize(
    "types",
    [
        None,  # Default case
        [MarkedContentType.need_id_refs],
        [MarkedContentType.need],
        [MarkedContentType.rst],
        [MarkedContentType.need, MarkedContentType.need_id_refs],
    ],
)
def test_convert_marked_content(types, tmp_path):
    jsonpath = Path(__file__).parent / "data" / "analyse" / "marked_content.json"
    outpath = tmp_path / "needextend.rst"
    convert_marked_content(jsonpath, outpath, types=types)

    assert outpath.exists()
