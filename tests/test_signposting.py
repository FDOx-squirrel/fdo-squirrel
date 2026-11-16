"""Offline tests for the FAIR Signposting output (S24, PRIMER.md) and the
checker tool. Standard library only:

    python -m unittest discover -s tests -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import check_signposting as chk  # noqa: E402
from fdo_signposting import (  # noqa: E402
    LANDING_FILENAME,
    LINKSET_FILENAME,
    build_linkset,
    build_signposts,
    normalise_base_url,
    write_signposting,
)


def _cw(**over):
    base = dict(
        fdo_type="fdo:3DDataFDO",
        id="https://doi.org/10.5281/zenodo.1",
        title="Test <FDO> & co",
        description="A test.",
        version="1.0.0",
        license="CC-BY-4.0",
        creators=[("https://orcid.org/0000-0000-0000-0001", "A Author"), ("urn:fdo-squirrel:agent/x", "No IRI")],
    )
    base.update(over)
    return SimpleNamespace(**base)


FILES = [
    {"name": "data/a b.glb", "size": 3, "sha256": "a" * 64, "mediaType": "model/gltf-binary", "role": "model"},
    {"name": "MD.cff", "size": 5, "sha256": "b" * 64, "mediaType": "text/yaml", "role": "metadata"},
]


def _sp(cw=None, base=None):
    cw = cw or _cw()
    return build_signposts(
        cw, resolved_id=cw.id, citation_raw=None, package_files=FILES,
        base_url=base, bundle_name="x-fdo-bundle.zip",
    )


def rels(sp, rel):
    return [s for s in sp if s["rel"] == rel]


class SignpostTests(unittest.TestCase):
    def test_level1_relations(self):
        sp = _sp()
        self.assertEqual(rels(sp, "cite-as")[0]["href"], "https://doi.org/10.5281/zenodo.1")
        db = rels(sp, "describedby")
        self.assertEqual(db[0]["href"], "ro-crate-metadata.json")
        self.assertEqual(db[0]["profile"], "https://w3id.org/ro/crate")
        self.assertEqual(db[1]["type"], "text/turtle")
        self.assertEqual(rels(sp, "license")[0]["href"], "https://spdx.org/licenses/CC-BY-4.0.html")
        # only creators with an http(s) IRI become author links
        self.assertEqual([a["href"] for a in rels(sp, "author")], ["https://orcid.org/0000-0000-0000-0001"])
        self.assertEqual(rels(sp, "type")[0]["href"], "https://schema.org/Dataset")
        self.assertEqual(rels(sp, "type")[1]["href"], "https://w3id.org/fdo-squirrel/3DDataFDO")

    def test_items_sorted_and_encoded_without_bundle_or_linkset(self):
        items = [i["href"] for i in rels(_sp(), "item")]
        self.assertEqual(items, ["MD.cff", "data/a%20b.glb"])
        self.assertEqual(rels(_sp(), "linkset"), [])

    def test_no_cite_as_for_urn_ids(self):
        cw = _cw(id="urn:fdo-squirrel:unpublished/x")
        self.assertEqual(rels(_sp(cw), "cite-as"), [])

    def test_software_type(self):
        sp = _sp(_cw(fdo_type="fdo:SoftwareFDO"))
        self.assertEqual(rels(sp, "type")[0]["href"], "https://schema.org/SoftwareSourceCode")

    def test_base_url_makes_links_absolute_and_adds_bundle_and_linkset(self):
        sp = _sp(base="https://ex.org/f")
        self.assertEqual(rels(sp, "describedby")[0]["href"], "https://ex.org/f/ro-crate-metadata.json")
        zips = [i for i in rels(sp, "item") if i.get("type") == "application/zip"]
        self.assertEqual(zips[0]["href"], "https://ex.org/f/x-fdo-bundle.zip")
        self.assertEqual(rels(sp, "linkset")[0]["href"], "https://ex.org/f/" + LINKSET_FILENAME)

    def test_base_url_validation(self):
        self.assertEqual(normalise_base_url("https://ex.org/f/"), "https://ex.org/f")
        self.assertIsNone(normalise_base_url(None))
        with self.assertRaises(ValueError):
            normalise_base_url("ex.org/f")

    def test_linkset_has_back_links_and_no_self_reference(self):
        base = "https://ex.org/f"
        ls = build_linkset(_sp(base=base), base)["linkset"]
        landing = f"{base}/{LANDING_FILENAME}"
        self.assertEqual(ls[0]["anchor"], landing)
        self.assertNotIn("linkset", ls[0])
        item_hrefs = [i["href"] for i in ls[0]["item"]]
        back = {e["anchor"]: e["collection"][0]["href"] for e in ls[1:]}
        self.assertEqual(set(back), set(item_hrefs))
        self.assertTrue(all(v == landing for v in back.values()))

    def test_written_files_are_deterministic_and_escaped(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            for d in (d1, d2):
                write_signposting(Path(d), _cw(), resolved_id=_cw().id, citation_raw=None,
                                  package_files=FILES, base_url="https://ex.org/f", bundle_name="b.zip")
            for name in (LANDING_FILENAME, LINKSET_FILENAME):
                self.assertEqual((Path(d1) / name).read_bytes(), (Path(d2) / name).read_bytes())
            page = (Path(d1) / LANDING_FILENAME).read_text(encoding="utf-8")
            self.assertIn("Test &lt;FDO&gt; &amp; co", page)
            self.assertNotIn("Test <FDO>", page)
            json.loads((Path(d1) / LINKSET_FILENAME).read_text(encoding="utf-8"))

    def test_no_linkset_file_without_base_url(self):
        with tempfile.TemporaryDirectory() as d:
            written = write_signposting(Path(d), _cw(), resolved_id=_cw().id, citation_raw=None,
                                        package_files=FILES, base_url=None, bundle_name="b.zip")
            self.assertEqual([p.name for p in written], [LANDING_FILENAME])


class CheckerTests(unittest.TestCase):
    def test_parse_link_header_multiple_and_quoted(self):
        v = ('<https://doi.org/10.1/x>; rel="cite-as", '
             '<https://e.org/a,b.json>; rel="describedby"; type="application/ld+json"; '
             'profile="https://w3id.org/ro/crate", <https://e.org/z>; rel="item license"')
        links = chk.parse_link_header(v)
        self.assertEqual([(l["rel"], l["href"]) for l in links],
                         [("cite-as", "https://doi.org/10.1/x"),
                          ("describedby", "https://e.org/a,b.json"),
                          ("item", "https://e.org/z"),
                          ("license", "https://e.org/z")])
        self.assertEqual(links[1]["profile"], "https://w3id.org/ro/crate")

    def test_html_links_roundtrip_from_generated_page(self):
        with tempfile.TemporaryDirectory() as d:
            write_signposting(Path(d), _cw(), resolved_id=_cw().id, citation_raw=None,
                              package_files=FILES, base_url=None, bundle_name="b.zip")
            links = chk.parse_html_links((Path(d) / LANDING_FILENAME).read_text(encoding="utf-8"))
        have = {l["rel"] for l in links}
        self.assertTrue({"cite-as", "describedby", "item", "license", "author", "type"} <= have)

    def test_report_exit_codes(self):
        full = [{"rel": r, "href": "https://e.org/" + r, "source": "header"} for r in ("cite-as", "describedby", "item")]
        self.assertEqual(chk.report(full, "x"), 0)
        self.assertEqual(chk.report(full[:1], "x"), 1)

    def test_linkset_to_links(self):
        data = {"linkset": [{"anchor": "https://e.org/p", "item": [{"href": "https://e.org/f", "type": "text/plain"}]}]}
        links = chk.linkset_to_links(data)
        self.assertEqual(links[0]["rel"], "item")
        self.assertEqual(links[0]["anchor"], "https://e.org/p")


if __name__ == "__main__":
    unittest.main()
