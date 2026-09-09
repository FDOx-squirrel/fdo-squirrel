from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional
import re


# --------------------------------------------------
# Helpers
# --------------------------------------------------


def resolve_id_label(obj: Dict[str, Any], ctx: str) -> Tuple[str, str]:
    """Resolve an {id,label} entity, tolerating a missing/empty `id`.

    The MD.cff schema (`idLabelEntityOptionalId`) marks `id` optional
    everywhere this is used (creators, contributors, publishers) - only
    `label` is required. But the returned `id` ends up wrapped directly
    in `<...>` as an RDF subject IRI further downstream (fdo_rdf.py's
    agent nodes), so something syntactically valid has to stand in when
    `id` is genuinely absent, rather than crashing or emitting a broken
    IRIREF.

    Previously named `require_id_label()` and hard-required `id`,
    contradicting the schema it was meant to enforce - any real `--local`
    fetch without `--creator-profile` (fdo-3d-packager's flag for
    supplying one) hit this in production, not just a synthetic test
    (found and reported from fdo-3d-packager's own S9, PRIMER.md Teil D).

    Falls back to a urn: built from the label - not a resolvable
    identifier, but syntactically valid and still traceable to the
    entity's name. Same pattern as fdo_rdf.py's resolve_dataset_id() for
    MD.cff's own `id` (A3: reuse means copying, not referencing - the
    two live in different packages, so the slugify logic is duplicated
    here on purpose rather than importing across the crosswalks/fdo
    package boundary, which would create a circular import: fdo_rdf.py
    already imports from crosswalks).
    """
    if not isinstance(obj, dict):
        raise ValueError(f"{ctx} must be an object with {{id,label}}, got {type(obj)}")
    if "label" not in obj:
        raise ValueError(f"{ctx} must contain key 'label'")
    label = str(obj["label"]).strip()
    if not label:
        raise ValueError(f"{ctx} requires a non-empty 'label'")

    raw_id = str(obj.get("id") or "").strip()
    if raw_id:
        return raw_id, label

    slug = re.sub(r"[^A-Za-z0-9._-]", "-", label) or "unknown"
    return f"urn:fdo-squirrel:agent/{slug}", label


def _citation_authors_to_idlabel(citation: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Best-effort (id,label) from CITATION.cff authors."""
    authors = citation.get("authors") or []
    out: List[Tuple[str, str]] = []
    for a in authors:
        if not isinstance(a, dict):
            continue
        given = str(a.get("given-names") or "").strip()
        family = str(a.get("family-names") or "").strip()
        name = " ".join([p for p in [given, family] if p]).strip()
        if not name:
            continue
        orcid = str(a.get("orcid") or a.get("ORCID") or "").strip()
        if orcid:
            cid = orcid if orcid.startswith("http") else f"https://orcid.org/{orcid}"
        else:
            # Same urn: fallback as resolve_id_label() above, and for the
            # same reason: an unescaped "name:Florian Thiery"-style id
            # wrapped in <...> produces an IRIREF with a space in it,
            # which is exactly the class of bug S13 already fixed for
            # MD.cff's own dataset id (PRIMER.md).
            slug = re.sub(r"[^A-Za-z0-9._-]", "-", name) or "unknown"
            cid = f"urn:fdo-squirrel:agent/{slug}"
        out.append((cid, name))
    return out


def _normalise_agents(md: Dict[str, Any], key: str) -> List[Tuple[str, str]]:
    """Normalise a list of {id,label} entries."""
    out: List[Tuple[str, str]] = []
    raw = md.get(key) or []
    if not isinstance(raw, list):
        return out
    for i, a in enumerate(raw):
        if not isinstance(a, dict):
            continue
        out.append(resolve_id_label(a, f"{key}[{i}]"))  # (id,label)
    return out


def _normalise_publishers(md: Dict[str, Any]) -> List[Tuple[str, str]]:
    """
    Accept either:
      - publisher: {id,label} (legacy)
      - publishers: [{id,label}, ...] (new)
    Returns a non-empty list.
    """
    pubs: List[Tuple[str, str]] = []
    if isinstance(md.get("publishers"), list):
        for i, p in enumerate(md["publishers"]):
            pubs.append(resolve_id_label(p, f"publishers[{i}]"))  # (id,label)
    elif isinstance(md.get("publisher"), dict):
        pubs.append(resolve_id_label(md["publisher"], "publisher"))

    if not pubs:
        raise ValueError(
            "MD.cff requires 'publisher' or 'publishers' with at least one entry."
        )
    return pubs


# --------------------------------------------------
# Crosswalk record (MD.cff -> internal normalised fields)
# --------------------------------------------------


@dataclass(frozen=True)
class CrosswalkRecord:
    # required
    fdo_type: str
    id: str
    title: str
    description: str

    # legacy + convenience
    publisher_id: str
    publisher_label: str

    # preferred lists
    publishers: List[Tuple[str, str]]
    creators: List[Tuple[str, str]]
    contributors: List[Tuple[str, str]]

    # optional core
    version: Optional[str] = None
    date_created: Optional[str] = None
    date_released: Optional[str] = None
    date_modified: Optional[List[str]] = None
    funding: Optional[List[Any]] = None
    license: Optional[Any] = None

    # enrichment
    keywords: Optional[List[Any]] = None
    related_resources: Optional[List[Any]] = None

    # spatiotemporal + domain blocks (pass-through dicts)
    spatial: Optional[Dict[str, Any]] = None
    temporal: Optional[Dict[str, Any]] = None
    heritage_object: Optional[Dict[str, Any]] = None
    technique: Optional[Dict[str, Any]] = None

    # optional enrichment from citation
    repository_url: Optional[str] = None

    # keep full MD.cff for mapping-driven writer (guarantees nothing gets lost)
    md_raw: Optional[Dict[str, Any]] = None


def md_cff_to_crosswalk(
    md: Dict[str, Any], *, citation: Optional[Dict[str, Any]] = None
) -> CrosswalkRecord:
    """
    Crosswalk MD.cff -> internal normalised record.

    Important:
    - We keep *all* MD.cff content available via `md_raw` so fdo_rdf.py can apply
      crosswalk_md_cff_to_rdf.yaml mapping comprehensively.
    - We also surface the most common fields as direct attributes for convenience.
    """
    fdo_type = str(md["fdo_type"]).strip()
    rid = str(md["id"]).strip()
    title = str(md["title"]).strip()
    description = str(md.get("description") or "").strip()
    if not description:
        raise ValueError("MD.cff requires a non-empty 'description'")

    publishers = _normalise_publishers(md)
    pub_id, pub_label = publishers[0]  # primary = first

    creators = _normalise_agents(md, "creators")
    contributors = _normalise_agents(md, "contributors")

    repo_url: Optional[str] = None
    if citation and isinstance(citation, dict):
        repo_url = citation.get("repository-code") or citation.get("url") or None
        if not creators:
            creators = _citation_authors_to_idlabel(citation)

    # dates
    dm = md.get("date_modified")
    if isinstance(dm, str) and dm.strip():
        date_modified = [dm.strip()]
    elif isinstance(dm, list):
        date_modified = [str(x).strip() for x in dm if isinstance(x, str) and x.strip()]
    else:
        date_modified = None

    return CrosswalkRecord(
        fdo_type=fdo_type,
        id=rid,
        title=title,
        description=description,
        publisher_id=pub_id,
        publisher_label=pub_label,
        publishers=publishers,
        creators=creators,
        contributors=contributors,
        version=(
            str(md.get("version")).strip()
            if isinstance(md.get("version"), str) and md.get("version").strip()
            else None
        ),
        date_created=(
            str(md.get("date_created")).strip()
            if isinstance(md.get("date_created"), str)
            and md.get("date_created").strip()
            else None
        ),
        date_released=(
            str(md.get("date_released")).strip()
            if isinstance(md.get("date_released"), str)
            and md.get("date_released").strip()
            else None
        ),
        date_modified=date_modified,
        funding=(
            md.get("funding")
            if isinstance(md.get("funding"), list)
            else (
                [md.get("funding")]
                if isinstance(md.get("funding"), str) and md.get("funding").strip()
                else None
            )
        ),
        license=md.get("license"),
        keywords=md.get("keywords") if isinstance(md.get("keywords"), list) else None,
        related_resources=(
            md.get("related_resources")
            if isinstance(md.get("related_resources"), list)
            else None
        ),
        spatial=md.get("spatial") if isinstance(md.get("spatial"), dict) else None,
        temporal=md.get("temporal") if isinstance(md.get("temporal"), dict) else None,
        heritage_object=(
            md.get("heritage_object")
            if isinstance(md.get("heritage_object"), dict)
            else None
        ),
        technique=(
            md.get("technique") if isinstance(md.get("technique"), dict) else None
        ),
        repository_url=str(repo_url).strip() if repo_url else None,
        md_raw=md,
    )
