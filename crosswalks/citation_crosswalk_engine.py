from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Iterable
import csv
import yaml


def _person_names(entries: Any) -> List[str]:
    """Best-effort human-readable name for each CFF Person/Entity in a
    list (authors, contact, contributors all share this shape): prefer
    an Entity's plain `name`, fall back to a Person's given+family names.
    """
    names: List[str] = []
    for a in entries if isinstance(entries, list) else []:
        if not isinstance(a, dict):
            continue
        name = a.get("name") or " ".join(
            p for p in (a.get("given-names"), a.get("family-names")) if p
        )
        if name:
            names.append(name)
    return names


def _normalize_citation(cff: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rich normalization of CITATION.cff restoring the original FDO metadata output.

    Forwards every one of the 22 CFF fields that
    crosswalks/crosswalk.fdo-metadata.yaml has a `cff:<field>` rule for,
    under that same field name, so the generic `citation.get(source_field)`
    lookup in CitationCrosswalkEngine.crosswalk() can find it. Before this
    (PRIMER.md S3, 2026-09-08) only 6 of the 22 were forwarded at all;
    author/identifier detail was computed into `author_name`/`author_orcid`/
    `identifier_<scheme>` but under names no rule ever asked for, so it was
    silently unused - kept below for whatever else in the family may read
    those specific keys, alongside the new literal `authors`/`identifiers`
    keys the crosswalk rules actually match on.

    Note: forwarding a field here is necessary but not sufficient. Five of
    the 22 (`cff-version`, `commit`, `message`, `references`, `type`) have
    no `to_term` at all in crosswalk.fdo-metadata.yaml - the crosswalk
    graph documents them as CFF-only concepts with no RDF predicate chosen
    yet. They are still forwarded here (harmless, and it means nothing
    needs touching again if a to_term is added later), but they will not
    produce a triple until crosswalk.fdo-metadata.yaml gets one. See
    PRIMER.md S3 for the full breakdown.
    """
    flat: Dict[str, Any] = {}

    # --- direct string passthroughs: everything that is CFF-spec plain
    # text/URL and has at least one usable to_term (or might get one) ---
    for key in (
        "abstract",
        "url",
        "repository-code",
        "repository",
        "license",
        "license-url",
        "cff-version",
        "commit",
        "date-released",
        "doi",
        "message",
        "repository-artifact",
        "title",
        "type",
        "version",
    ):
        if key in cff and cff[key]:
            flat[key] = cff[key]

    # --- keywords ---
    if "keywords" in cff and isinstance(cff["keywords"], list):
        flat["keywords"] = cff["keywords"]

    # --- identifiers (DOI etc.) ---
    id_values: List[str] = []
    for ident in cff.get("identifiers", []):
        if not isinstance(ident, dict):
            continue
        scheme = ident.get("type") or ident.get("scheme")
        value = ident.get("value")
        if scheme and value:
            flat[f"identifier_{scheme.lower()}"] = value
            id_values.append(value)
    if id_values:
        flat["identifiers"] = id_values

    # --- authors ---
    authors = cff.get("authors", [])
    if isinstance(authors, list):
        orcids = []
        for a in authors:
            if not isinstance(a, dict):
                continue
            orcid = a.get("orcid") or a.get("ORCID")
            if orcid:
                if not orcid.startswith("http"):
                    orcid = "https://orcid.org/" + orcid
                orcids.append(orcid)
        if orcids:
            flat["author_orcid"] = orcids
        names = _person_names(authors)
        if names:
            flat["author_name"] = names
            flat["authors"] = names

    # --- contact / contributors: same Person/Entity shape as authors ---
    contact_names = _person_names(cff.get("contact"))
    if contact_names:
        flat["contact"] = contact_names

    contributor_names = _person_names(cff.get("contributors"))
    if contributor_names:
        flat["contributors"] = contributor_names

    # --- preferred-citation: nested citation object; forward a label,
    # not the raw dict (the crosswalk loop stringifies non-str values,
    # which would put a Python dict repr into the triple) ---
    pref = cff.get("preferred-citation")
    if isinstance(pref, dict):
        label = pref.get("title") or pref.get("doi") or pref.get("url")
        if label:
            flat["preferred-citation"] = label

    # --- references: list of Reference objects; forward their titles ---
    ref_titles = [
        r["title"]
        for r in cff.get("references", [])
        if isinstance(r, dict) and r.get("title")
    ]
    if ref_titles:
        flat["references"] = ref_titles

    return flat


class CitationCrosswalkEngine:
    def __init__(self, crosswalk_yaml: Path, crosswalk_dir: Path):
        self.crosswalk_yaml = crosswalk_yaml
        self.crosswalk_dir = crosswalk_dir
        self.rules = self._load_rules()

    # --------------------------------------------------
    # Load YAML rules
    # --------------------------------------------------

    def _load_rules(self) -> List[Dict[str, Any]]:
        cfg = yaml.safe_load(self.crosswalk_yaml.read_text(encoding="utf-8"))

        if isinstance(cfg, list):
            return cfg
        if isinstance(cfg, dict):
            return cfg.get("crosswalks", list(cfg.values()))

        raise ValueError("Invalid crosswalk.fdo-metadata.yaml")

    # --------------------------------------------------
    # Main execution
    # --------------------------------------------------

    def crosswalk(self, citation: Dict[str, Any], subject_uri: str) -> List[str]:
        """
        Execute crosswalks correctly:
        - CSVs are reference/provenance, NOT multiplicators
        - Each semantic triple is emitted exactly once
        """

        triples: set[str] = set()

        # Normalize CFF once
        citation = _normalize_citation(citation)

        for cw in self.rules:
            # ------------------------------------------
            # Determine source field (from_term wins)
            # ------------------------------------------
            from_term = cw.get("from_term")
            if not isinstance(from_term, str) or ":" not in from_term:
                continue

            source_field = from_term.split(":", 1)[1]

            value = citation.get(source_field)
            if not value:
                continue

            # ------------------------------------------
            # Target predicate
            # ------------------------------------------
            to_term = cw.get("to_term")
            if not isinstance(to_term, str) or ":" not in to_term:
                continue

            target_predicate = to_term

            values = value if isinstance(value, list) else [value]

            for v in values:
                if isinstance(v, str) and v.startswith(("http://", "https://")):
                    obj = f"<{v}>"
                else:
                    obj = f'"{v}"'

                triples.add(f"<{subject_uri}> {target_predicate} {obj} .")

        # Deterministic output order
        return sorted(triples)
