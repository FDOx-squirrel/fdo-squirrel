"""Typed `related_resources` links in the TTL and the RO-Crate (S29, PRIMER.md).

Standard library only - run from the repository root with:

    python -m unittest discover -s tests -v

MD.cff `related_resources[].relation` used to be flattened to a bare
`dct:relation`, so a scan and the reconstruction derived from it could not be
told apart from any other pair of linked objects. The relation now selects a
typed predicate on top of the generic one.
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fdo.fdo_rdf import ProvenanceTracker, _apply_md_cff_mapping  # noqa: E402
from fdo_rocrate import build_ro_crate  # noqa: E402

SUBJ = "<urn:fdo-squirrel:unpublished/test>"
SCAN = "https://sketchfab.com/3d-models/scan-0123"
DOI = "https://doi.org/10.5281/zenodo.123"


def _related(*items):
    return {"related_resources": list(items)}


def _item(relation, target_id=SCAN, label="Scan", **extra):
    target = {"label": label}
    if target_id:
        target["id"] = target_id
    return {"relation": relation, "target": target, **extra}


def _emit(md):
    inline, post = _apply_md_cff_mapping(md, SUBJ, ProvenanceTracker())
    return "\n".join(inline), "\n".join(post)


class TurtleTests(unittest.TestCase):
    def test_typed_predicates(self):
        expected = {
            "isDerivedFrom": "prov:wasDerivedFrom",
            "isReferencedBy": "dct:isReferencedBy",
            "references": "dct:references",
            "isPartOf": "dct:isPartOf",
            "hasPart": "dct:hasPart",
        }
        for relation, predicate in expected.items():
            with self.subTest(relation=relation):
                inline, _ = _emit(_related(_item(relation)))
                self.assertIn(f"    {predicate} <{SCAN}> ;", inline)

    def test_generic_relation_is_always_written(self):
        for relation in (
            "isDerivedFrom",
            "isReferencedBy",
            "isSupplementTo",
            "isDocumentedBy",
        ):
            with self.subTest(relation=relation):
                inline, _ = _emit(_related(_item(relation)))
                self.assertIn(f"    dct:relation <{SCAN}> ;", inline)

    def test_relation_without_standard_predicate_stays_generic(self):
        for relation in ("isSupplementTo", "isDocumentedBy"):
            with self.subTest(relation=relation):
                inline, _ = _emit(_related(_item(relation)))
                self.assertEqual(inline.count("<"), 1, inline)

    def test_each_item_keeps_its_own_relation(self):
        inline, _ = _emit(
            _related(
                _item("isDerivedFrom", SCAN, "Scan"),
                _item("isReferencedBy", DOI, "Reconstruction"),
            )
        )
        self.assertIn(f"prov:wasDerivedFrom <{SCAN}>", inline)
        self.assertIn(f"dct:isReferencedBy <{DOI}>", inline)
        self.assertNotIn(f"prov:wasDerivedFrom <{DOI}>", inline)
        self.assertNotIn(f"dct:isReferencedBy <{SCAN}>", inline)

    def test_label_is_written_for_the_target(self):
        _, post = _emit(_related(_item("isDerivedFrom")))
        self.assertIn(f'<{SCAN}> rdfs:label "Scan" .', post)

    def test_target_without_iri_gets_a_labelled_node(self):
        inline, post = _emit(_related(_item("isDerivedFrom", target_id=None)))
        self.assertIn("prov:wasDerivedFrom _:related_resources0_1 ;", inline)
        self.assertIn('rdfs:label "Scan"', post)

    def test_unknown_relation_does_not_break(self):
        inline, _ = _emit(_related(_item("somethingElse")))
        self.assertIn(f"dct:relation <{SCAN}>", inline)

    def test_provenance_report_names_the_typed_link(self):
        tracker = ProvenanceTracker()
        _apply_md_cff_mapping(_related(_item("isDerivedFrom")), SUBJ, tracker)
        fields = {e["field"] for e in tracker._events}
        self.assertIn("dataset.related_resources.target", fields)
        self.assertIn("dataset.related_resources.target.isDerivedFrom", fields)


class BlankNodeTests(unittest.TestCase):
    """Label-only values must not share a blank node (S29, PRIMER.md)."""

    @staticmethod
    def _nodes(inline, predicate):
        return [
            line.split()[1]
            for line in inline.splitlines()
            if line.strip().startswith(predicate + " _:")
        ]

    def test_contributors_and_object_type_do_not_share_a_node(self):
        md = {
            "contributors": [{"label": "Claude"}, {"label": "Second"}],
            "heritage_object": {"object_type": {"label": "LEGO model"}},
        }
        inline, post = _emit(md)
        contributors = self._nodes(inline, "dct:contributor")
        types = self._nodes(inline, "dct:type")
        self.assertEqual(len(contributors), 2, inline)
        self.assertEqual(len(types), 1, inline)
        self.assertEqual(len(set(contributors + types)), 3, inline)
        for node, label in zip(contributors + types, ("Claude", "Second", "LEGO model")):
            self.assertIn(f'{node} rdfs:label "{label}" .', post)

    def test_label_only_related_resources_stay_apart(self):
        inline, post = _emit(
            _related(
                _item("isDerivedFrom", target_id=None, label="One"),
                _item("isDerivedFrom", target_id=None, label="Two"),
            )
        )
        nodes = self._nodes(inline, "prov:wasDerivedFrom")
        self.assertEqual(len(set(nodes)), 2, inline)

    def test_generic_and_typed_link_share_one_node_and_one_label(self):
        inline, post = _emit(_related(_item("isDerivedFrom", target_id=None)))
        self.assertEqual(
            self._nodes(inline, "dct:relation"),
            self._nodes(inline, "prov:wasDerivedFrom"),
        )
        self.assertEqual(post.count("rdfs:label"), 1, post)

    def test_label_triple_for_an_iri_target_is_not_duplicated(self):
        _, post = _emit(_related(_item("isDerivedFrom")))
        self.assertEqual(post.count("rdfs:label"), 1, post)

    def test_output_is_deterministic(self):
        md = _related(_item("isDerivedFrom", target_id=None))
        self.assertEqual(_emit(md), _emit(md))


class NoteTests(unittest.TestCase):
    """The `note` of a related resource, on a DCAT qualified relation."""

    def test_note_becomes_a_qualified_relation(self):
        _, post = _emit(_related(_item("isDerivedFrom", note="Scanned 12.11.26")))
        self.assertIn(f"{SUBJ} dcat:qualifiedRelation _:related_resources0_rel .", post)
        self.assertIn("_:related_resources0_rel a dcat:Relationship .", post)
        self.assertIn(f"_:related_resources0_rel dct:relation <{SCAN}> .", post)
        self.assertIn("_:related_resources0_rel dcat:hadRole prov:wasDerivedFrom .", post)
        self.assertIn('_:related_resources0_rel rdfs:comment "Scanned 12.11.26" .', post)

    def test_no_note_writes_no_qualified_relation(self):
        for note in (None, "", "   "):
            with self.subTest(note=note):
                _, post = _emit(_related(_item("isDerivedFrom", note=note)))
                self.assertNotIn("qualifiedRelation", post)
                self.assertNotIn("rdfs:comment", post)

    def test_the_note_is_not_attached_to_the_target(self):
        _, post = _emit(_related(_item("isDerivedFrom", note="n")))
        self.assertNotIn(f"<{SCAN}> rdfs:comment", post)

    def test_role_for_values_without_a_typed_predicate(self):
        expected = {
            "isSupplementTo": "<http://www.iana.org/assignments/relation/related>",
            "isDocumentedBy": "<http://www.iana.org/assignments/relation/describedby>",
        }
        for relation, role in expected.items():
            with self.subTest(relation=relation):
                _, post = _emit(_related(_item(relation, note="n")))
                self.assertIn(f"dcat:hadRole {role} .", post)

    def test_label_only_target_shares_the_node_of_the_plain_link(self):
        inline, post = _emit(_related(_item("isDerivedFrom", None, "Scan", note="n")))
        self.assertIn("    dct:relation _:related_resources0_1 ;", inline)
        self.assertIn("_:related_resources0_rel dct:relation _:related_resources0_1 .", post)
        self.assertEqual(post.count('_:related_resources0_1 rdfs:label "Scan"'), 1)

    def test_each_item_gets_its_own_relationship_node(self):
        _, post = _emit(
            _related(
                _item("isDerivedFrom", SCAN, "Scan", note="a"),
                _item("isReferencedBy", DOI, "Reconstruction", note="b"),
            )
        )
        self.assertIn(f"_:related_resources0_rel dct:relation <{SCAN}> .", post)
        self.assertIn(f"_:related_resources1_rel dct:relation <{DOI}> .", post)
        self.assertIn('_:related_resources1_rel rdfs:comment "b" .', post)

    def test_note_is_escaped(self):
        _, post = _emit(_related(_item("isDerivedFrom", note='say "hi"\nthere')))
        self.assertIn('rdfs:comment "say \\"hi\\"', post)

    def test_provenance_report_names_the_note(self):
        tracker = ProvenanceTracker()
        _apply_md_cff_mapping(_related(_item("isDerivedFrom", note="n")), SUBJ, tracker)
        self.assertIn("dataset.related_resources.note", repr(vars(tracker)))

    def test_output_is_deterministic(self):
        md = _related(_item("isDerivedFrom", None, "Scan", note="n"))
        self.assertEqual(_emit(md), _emit(md))


def _cw(related):
    return SimpleNamespace(
        fdo_type="fdo:3DDataFDO",
        id=DOI,
        title="Test FDO",
        description="A test.",
        publisher_id="http://www.wikidata.org/entity/Q73901970",
        publisher_label="Research Squirrel Engineers Network",
        creators=[("urn:fdo-squirrel:agent/c", "C")],
        contributors=[],
        version=None,
        date_created="2026-11-17",
        date_released="2026-11-17",
        date_modified=None,
        license={"id": "https://spdx.org/licenses/CC-BY-4.0.html", "label": "CC-BY-4.0"},
        keywords=[],
        spatial=None,
        md_raw={},
        related_resources=related,
    )


def _crate(related):
    return build_ro_crate(
        _cw(related),
        resolved_id=DOI,
        citation_raw=None,
        package_files=[],
        generated_files=[],
        fdo_squirrel_version="9.9.9",
    )


def _by_id(crate):
    return {e["@id"]: e for e in crate["@graph"]}


class RoCrateTests(unittest.TestCase):
    def test_derived_from_becomes_is_based_on(self):
        g = _by_id(_crate([_item("isDerivedFrom")]))
        self.assertEqual(g["./"]["isBasedOn"], [{"@id": SCAN}])
        self.assertEqual(g[SCAN]["@type"], "CreativeWork")
        self.assertEqual(g[SCAN]["name"], "Scan")

    def test_part_of_and_references(self):
        g = _by_id(
            _crate([_item("isPartOf", DOI, "Collection"), _item("references")])
        )
        self.assertEqual(g["./"]["isPartOf"], [{"@id": DOI}])
        self.assertEqual(g["./"]["citation"], [{"@id": SCAN}])

    def test_relations_without_schema_org_term_are_left_out(self):
        g = _by_id(
            _crate(
                [
                    _item("isReferencedBy"),
                    _item("isSupplementTo"),
                    _item("isDocumentedBy"),
                ]
            )
        )
        for prop in ("isBasedOn", "isPartOf", "citation"):
            self.assertNotIn(prop, g["./"])
        self.assertNotIn(SCAN, g)

    def test_target_without_iri_is_left_out(self):
        g = _by_id(_crate([_item("isDerivedFrom", target_id=None)]))
        self.assertNotIn("isBasedOn", g["./"])

    def test_duplicates_collapse_and_no_related_resources_is_fine(self):
        g = _by_id(_crate([_item("isDerivedFrom"), _item("isDerivedFrom")]))
        self.assertEqual(g["./"]["isBasedOn"], [{"@id": SCAN}])
        self.assertNotIn("isBasedOn", _by_id(_crate(None))["./"])

    def test_output_is_deterministic(self):
        related = [_item("isPartOf", DOI, "Collection"), _item("isDerivedFrom")]
        self.assertEqual(_crate(related), _crate(list(related)))

    def test_note_becomes_the_description_of_the_target(self):
        g = _by_id(_crate([_item("isDerivedFrom", note="Scanned 12.11.26")]))
        self.assertEqual(g[SCAN]["description"], "Scanned 12.11.26")
        self.assertEqual(g["./"]["isBasedOn"], [{"@id": SCAN}])

    def test_no_note_no_description(self):
        g = _by_id(_crate([_item("isDerivedFrom")]))
        self.assertNotIn("description", g[SCAN])

    def test_note_on_a_later_duplicate_still_arrives(self):
        g = _by_id(_crate([_item("isDerivedFrom"), _item("isDerivedFrom", note="n")]))
        self.assertEqual(g[SCAN]["description"], "n")

    def test_notes_on_one_target_are_joined_in_order(self):
        g = _by_id(
            _crate(
                [
                    _item("isDerivedFrom", note="first"),
                    _item("references", note="second"),
                    _item("references", note="second"),
                ]
            )
        )
        self.assertEqual(g[SCAN]["description"], "first second")

    def test_note_of_a_relation_left_out_of_the_crate_is_left_out(self):
        g = _by_id(_crate([_item("isReferencedBy", note="n")]))
        self.assertNotIn(SCAN, g)


if __name__ == "__main__":
    unittest.main()
