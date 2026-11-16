"""Output layout (S25): --outdir holds the bundle plus four files worth
opening directly; everything else this run writes sits in --outdir/_work.

Runs main.py end to end on a tiny synthetic package, so it needs the
runtime dependencies from requirements.txt but no network.
"""
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MD_CFF = """md_cff_version: "0.1"
fdo_type: "fdo:3DDataFDO"
id: "https://doi.org/10.5281/zenodo.1234567"
title: "Layout test stone"
description: "Synthetic package for the output layout test."
version: "1.0.0"
date_created: "2025-01-02"
date_released: "2025-01-05"
publishers:
  - id: "http://www.wikidata.org/entity/Q73901970"
    label: "Research Squirrel Engineers Network"
creators:
  - id: "https://orcid.org/0000-0002-3246-3531"
    label: "Thiery, Florian"
license:
  id: "https://spdx.org/licenses/CC-BY-4.0.html"
  label: "CC-BY-4.0"
keywords:
  - label: "Ogham stones"
identifiers:
  - scheme: doi
    value: "10.5281/zenodo.1234567"
    label: "Zenodo DOI"
"""

CITATION_CFF = """cff-version: 1.2.0
message: "Please cite as below."
title: "Layout test stone"
type: dataset
version: "1.0.0"
date-released: "2025-01-05"
authors:
  - given-names: "Florian"
    family-names: "Thiery"
license: "CC-BY-4.0"
"""

LOOSE = {
    "rdf_modelling_report.html",
    "fdo_overview.png",
    "fdo-metadata.ttl",
    "ro-crate-metadata.json",
}


def _make_package(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("MD.cff", MD_CFF)
        z.writestr("CITATION.cff", CITATION_CFF)
        z.writestr("data/model/stone.glb", b"glTF-stub")


class OutputLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls._tmp.name)
        cls.package = tmp / "layout-test.zip"
        _make_package(cls.package)
        cls.out = tmp / "out"
        cls.out.mkdir()
        (cls.out / "stale.txt").write_text("left over from an earlier run")
        cls.proc = subprocess.run(
            [sys.executable, str(ROOT / "main.py"), "--package", str(cls.package), "--outdir", str(cls.out)],
            cwd=tmp,
            # what a Windows user gets when piping: cp1252 unless forced
            env={**os.environ, "PYTHONIOENCODING": "cp1252"},
            capture_output=True,
            text=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_run_succeeds(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)

    def test_top_level_has_bundle_and_loose_files(self):
        names = {p.name for p in self.out.iterdir() if p.is_file()}
        # fdo_overview.png needs the Mermaid CLI and is only there if it rendered
        required = (LOOSE - {"fdo_overview.png"}) | {"layout-test-fdo-bundle.zip"}
        self.assertTrue(required <= names, required - names)

    def test_no_loose_generated_files_besides_the_list(self):
        names = {p.name for p in self.out.iterdir()}
        self.assertEqual(names - LOOSE - {"layout-test-fdo-bundle.zip", "_work"}, set())

    def test_stale_file_is_gone(self):
        self.assertFalse((self.out / "stale.txt").exists())

    def test_rest_is_in_work_dir(self):
        work = {p.name for p in (self.out / "_work").iterdir()}
        for name in ("FDOx.yaml", "rdf_modelling_report.json", "fdo-landing-page.html", "fdo_overview.mermaid"):
            self.assertIn(name, work)

    def test_loose_files_are_copies_of_the_work_files(self):
        for name in LOOSE:
            loose = self.out / name
            if loose.exists():
                self.assertEqual(loose.read_bytes(), (self.out / "_work" / name).read_bytes(), name)

    def test_bundle_still_carries_everything(self):
        with zipfile.ZipFile(self.out / "layout-test-fdo-bundle.zip") as z:
            members = set(z.namelist())
        for name in ("fdo-metadata.ttl", "ro-crate-metadata.json", "FDOx.yaml", "fdo-landing-page.html", "MD.cff"):
            self.assertIn(name, members)
        self.assertFalse(any(m.startswith("_work") for m in members))


if __name__ == "__main__":
    unittest.main()
