"""Structural tests for the RO-Crate export (S22, PRIMER.md).

Standard library only - run from the repository root with:

    python -m unittest discover -s tests -v

They check the RO-Crate 1.2 requirements that can be checked offline (the
official validator, roc-validator, needs network access to fetch the
RO-Crate JSON-LD context - see docs/ro-crate-mapping.md for that run).
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fdo_rocrate import (  # noqa: E402
    CRATE_FILENAME,
    PROFILE_IRI,
    RO_CRATE_SPEC,
    build_ro_crate,
    write_ro_crate,
)


def _cw(**over):
    base = dict(
        fdo_type="fdo:3DDataFDO",
        id="https://doi.org/10.5281/zenodo.1",
        title="Test FDO",
        description="A test.",
        publisher_id="http://www.wikidata.org/entity/Q73901970",
        publisher_label="Research Squirrel Engineers Network",
        creators=[("urn:fdo-squirrel:agent/md-creator", "MD Creator")],
        contributors=[],
        version="1.0.0",
        date_created="2025-01-02",
        date_released="2025-01-05",
        date_modified=None,
        license={"id": "https://spdx.org/licenses/CC-BY-4.0.html", "label": "CC-BY-4.0"},
        keywords=[{"label": "a"}, "b", {"label": "a"}],
        spatial={"label": "Cork", "lat": 51.9, "lon": -8.5},
        md_raw={"identifiers": [{"scheme": "doi", "value": "10.5281/zenodo.2"}]},
    )
    base.update(over)
    return SimpleNamespace(**base)


def _f(name, role="data", sha="a" * 64, size=3):
    return {"name": name, "size": size, "sha256": sha, "mediaType": "text/plain", "role": role}


def _build(cw=None, citation=None, pkg=None, gen=None):
    return build_ro_crate(
        cw or _cw(),
        resolved_id=(cw or _cw()).id,
        citation_raw=citation,
        package_files=pkg if pkg is not None else [_f("data/a b.txt")],
        generated_files=gen if gen is not None else [_f("fdo-metadata.ttl"), _f("FDOx.yaml")],
        fdo_squirrel_version="9.9.9",
    )


def _by_id(crate):
    return {e["@id"]: e for e in crate["@graph"]}


class RoCrateTests(unittest.TestCase):
    def test_descriptor_and_root(self):
        g = _by_id(_build())
        d = g[CRATE_FILENAME]
        self.assertEqual(d["conformsTo"], {"@id": RO_CRATE_SPEC})
        self.assertEqual(d["about"], {"@id": "./"})
        root = g["./"]
        self.assertIn("Dataset", root["@type"])
        for required in ("name", "description", "datePublished", "license"):
            self.assertIn(required, root, required)
        self.assertEqual(root["conformsTo"], {"@id": PROFILE_IRI})

    def test_context_is_ro_crate_1_2_plus_extension(self):
        ctx = _build()["@context"]
        self.assertEqual(ctx[0], "https://w3id.org/ro/crate/1.2/context")
        self.assertEqual(ctx[1]["fdo"], "https://w3id.org/fdo-squirrel/")

    def test_creators_prefer_citation_cff(self):
        cit = {"authors": [{"given-names": "F", "family-names": "T", "orcid": "https://orcid.org/0000-0000-0000-0001"}]}
        g = _by_id(_build(citation=cit))
        self.assertEqual(
            g["./"]["creator"], [{"@id": "https://orcid.org/0000-0000-0000-0001"}]
        )
        self.assertEqual(g["https://orcid.org/0000-0000-0000-0001"]["@type"], "Person")

    def test_creators_fall_back_to_md_cff(self):
        g = _by_id(_build(citation=None))
        self.assertEqual(g["./"]["creator"], [{"@id": "urn:fdo-squirrel:agent/md-creator"}])

    def test_every_reference_resolves(self):
        g = _by_id(_build())
        def refs(v):
            if isinstance(v, dict):
                if set(v) == {"@id"}:
                    yield v["@id"]
                else:
                    for x in v.values():
                        yield from refs(x)
            elif isinstance(v, list):
                for x in v:
                    yield from refs(x)
        for e in g.values():
            for r in refs({k: v for k, v in e.items() if k != "@id"}):
                if r == PROFILE_IRI or r == RO_CRATE_SPEC:
                    continue
                self.assertIn(r, g, f"dangling reference {r}")

    def test_files_have_encoded_ids_and_hashes(self):
        g = _by_id(_build())
        e = g["data/a%20b.txt"]
        self.assertEqual(e["name"], "data/a b.txt")
        self.assertEqual(e["contentSize"], "3")
        self.assertEqual(e["fdo:sha256"], "a" * 64)
        self.assertIn({"@id": "data/a%20b.txt"}, g["./"]["hasPart"])

    def test_ttl_is_described_without_size_or_hash(self):
        g = _by_id(_build())
        ttl = g["fdo-metadata.ttl"]
        self.assertNotIn("fdo:sha256", ttl)
        self.assertNotIn("contentSize", ttl)
        self.assertIn("fdo:sha256", g["FDOx.yaml"])

    def test_keywords_deduplicated_and_dois_added(self):
        root = _by_id(_build())["./"]
        self.assertEqual(root["keywords"], ["a", "b"])
        self.assertEqual(
            root["identifier"],
            ["https://doi.org/10.5281/zenodo.1", "https://doi.org/10.5281/zenodo.2"],
        )

    def test_spatial_and_build_action(self):
        g = _by_id(_build())
        self.assertEqual(g["#spatial-geo"]["latitude"], 51.9)
        act = g["urn:fdo-squirrel:activity/build"]
        self.assertEqual(act["@type"], "CreateAction")
        self.assertEqual(act["result"], [{"@id": "FDOx.yaml"}, {"@id": "fdo-metadata.ttl"}])

    def test_software_application_declares_required_properties(self):
        # RO-Crate 1.2: a SoftwareApplication MUST declare name, url, version
        app = _by_id(_build())["urn:fdo-squirrel:agent/fdo-squirrel"]
        for key in ("name", "url", "version"):
            self.assertTrue(app.get(key), key)
        self.assertEqual(app["version"], app["softwareVersion"])

    def test_deterministic_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a.json", Path(d) / "b.json"
            write_ro_crate(a, _build())
            write_ro_crate(b, _build())
            self.assertEqual(a.read_bytes(), b.read_bytes())
            json.loads(a.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
