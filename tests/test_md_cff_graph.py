"""MD.cff node graph (S27): the central node's height follows the number
of fields, not the length of the description.

Found with Govan 5 (2026-11-16): a 1,500-character description made the
node 1000 px tall with nothing in it, because its height was computed from
all wrapped description lines while only one truncated line is drawn.
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "fdo"))

from fdo_md_cff_graph import build_svg  # noqa: E402


def _md(description: str) -> dict:
    return {
        "md_cff_version": "0.1",
        "fdo_type": "fdo:3DDataFDO",
        "id": "https://doi.org/10.5281/zenodo.1",
        "title": "Stone",
        "description": description,
        "date_created": "2021-01-11",
        "date_released": "2021-01-11",
        "publishers": [{"label": "Publisher", "id": "http://example.org/p"}],
        "creators": [{"label": "Creator", "id": "http://example.org/c"}],
    }


def _centre_height(svg: str) -> float:
    m = re.search(r'<rect x="\d+" y="[\d.]+" width="380" height="([\d.]+)" rx="14"', svg)
    assert m, "central node not found"
    return float(m.group(1))


class MdCffGraphTests(unittest.TestCase):
    def test_long_description_does_not_stretch_centre_node(self):
        short, _, _ = build_svg(_md("A stone."), "Stone")
        long_, _, _ = build_svg(_md("word " * 400), "Stone")
        self.assertEqual(_centre_height(short), _centre_height(long_))

    def test_centre_node_is_compact(self):
        svg, _, height = build_svg(_md("word " * 400), "Stone")
        self.assertLess(_centre_height(svg), 300)
        self.assertLess(height, 700)


if __name__ == "__main__":
    unittest.main()
