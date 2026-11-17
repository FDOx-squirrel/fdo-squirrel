"""
fdo_rocrate.py - writes ro-crate-metadata.json, an RO-Crate 1.2 view of the
finished FDO bundle (S22, PRIMER.md).

An RO-Crate is "a folder plus ro-crate-metadata.json": the bundle ZIP
fdo-squirrel already builds is exactly such a folder, so adding this one
file at the bundle root turns the bundle into an RO-Crate - and, via
FAIR Signposting, into a "Webby FDO" - without changing anything else about
it.

Role of this file (A4, PRIMER.md): fdo-metadata.ttl stays the lossless,
CIDOC-CRM-anchored carrier of the FDO's metadata. The crate is a *view*
generated from the very same inputs (MD.cff, CITATION.cff, the package's
file list), not a second place to maintain anything. It maps the core that
RO-Crate/schema.org can express and leaves the rest in the TTL; the
mapping and what is deliberately not mapped are documented in
docs/ro-crate-mapping.md.

Design rules, all inherited from the rest of the family:

- No new hard dependency: the crate is plain JSON built with the standard
  library (RDF stays in fdo/fdo_rdf.py).
- Deterministic by construction (S4): no clock, sorted graph, fixed key
  order, so two runs give a byte-identical file.
- Creator, licence and file facts come from the same helpers the TTL uses
  (fdo.derive_creators, fdo.spdx_license_url, fdo.describe_*), so the two
  outputs cannot drift apart.
- A manifest cannot hash its own final bytes. fdo-metadata.ttl is
  finalised *after* this file is written and carries this file's sha256, so
  the crate describes fdo-metadata.ttl without size or hash (the same
  limitation fdo_rdf.build_generated_distributions_ttl documents for the
  TTL's description of itself).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote

from fdo import derive_creators, spdx_license_url

CRATE_FILENAME = "ro-crate-metadata.json"

RO_CRATE_CONTEXT = "https://w3id.org/ro/crate/1.2/context"
RO_CRATE_SPEC = "https://w3id.org/ro/crate/1.2"

# FDOx profile of RO-Crate (docs/ro-crate-profile.md). Minted under the
# namespace the FDOx vocabulary already uses; the w3id redirect for the
# /profile/ path is a Teil-D item in PRIMER.md until it is registered.
PROFILE_IRI = "https://w3id.org/fdo-squirrel/profile/ro-crate/1.0"
PROFILE_DOC_URL = (
    "https://github.com/FDOx-squirrel/fdo-squirrel/blob/main/docs/ro-crate-profile.md"
)

REPOSITORY_URL = "https://github.com/FDOx-squirrel/fdo-squirrel"
GENERATOR_ID = "urn:fdo-squirrel:agent/fdo-squirrel"
BUILD_ACTION_ID = "urn:fdo-squirrel:activity/build"

# Extension terms beyond the RO-Crate 1.2 context. The prefixes are the
# same ones fdo-metadata.ttl declares, so a consumer sees one vocabulary.
EXTENSION_CONTEXT: Dict[str, str] = {
    "crm": "http://www.cidoc-crm.org/cidoc-crm/",
    "crmdig": "http://www.ics.forth.gr/isl/CRMdig/",
    "fdo": "https://w3id.org/fdo-squirrel/",
    "prof": "http://www.w3.org/ns/dx/prof/",
}

# MD.cff `related_resources[].relation` -> schema.org property on the crate
# root (S29, PRIMER.md). Only the values schema.org has an agreed term for;
# isReferencedBy, isSupplementTo and isDocumentedBy stay in the TTL, where
# they are dct:isReferencedBy / dct:relation.
RELATION_TO_SCHEMA_ORG: Dict[str, str] = {
    "isDerivedFrom": "isBasedOn",
    "isPartOf": "isPartOf",
    "references": "citation",
}

# The one file whose size/hash cannot be stated here (see module docstring).
SELF_DESCRIBING_FILE = "fdo-metadata.ttl"


def _ref(entity_id: str) -> Dict[str, str]:
    return {"@id": entity_id}


def _file_id(path: str) -> str:
    """Relative URI reference for a path inside the bundle (spaces etc.
    percent-encoded, as RO-Crate requires for local data entities)."""
    return quote(path, safe="/")


def _keyword_labels(keywords: Optional[List[Any]]) -> List[str]:
    out: List[str] = []
    for k in keywords or []:
        label = k.get("label") if isinstance(k, dict) else k
        if isinstance(label, str) and label.strip() and label.strip() not in out:
            out.append(label.strip())
    return out


def _identifiers(resolved_id: str, md_raw: Optional[Dict[str, Any]]) -> List[str]:
    """The FDO's own id first, then DOIs/URLs from MD.cff `identifiers`."""
    out: List[str] = [resolved_id]
    for ident in (md_raw or {}).get("identifiers") or []:
        if not isinstance(ident, dict):
            continue
        scheme = str(ident.get("scheme") or "").strip().lower()
        value = str(ident.get("value") or "").strip()
        if not value:
            continue
        if scheme == "doi":
            value = value if value.startswith("http") else f"https://doi.org/{value}"
        elif scheme == "url":
            pass
        else:
            continue  # other schemes stay in the TTL
        if value not in out:
            out.append(value)
    return out


def _spatial_entities(
    spatial: Optional[Dict[str, Any]]
) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """contentLocation (Place + GeoCoordinates / GeoShape box). WKT stays in
    the TTL (GeoSPARQL) - schema.org has no WKT literal."""
    if not isinstance(spatial, dict) or not str(spatial.get("label") or "").strip():
        return None, []
    sid = str(spatial.get("id") or "").strip() or "#spatial"
    place: Dict[str, Any] = {
        "@id": sid,
        "@type": "Place",
        "name": str(spatial["label"]).strip(),
    }
    entities: List[Dict[str, Any]] = []
    lat, lon = spatial.get("lat"), spatial.get("lon")
    bbox = spatial.get("bounding_box")
    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        place["geo"] = _ref("#spatial-geo")
        entities.append(
            {
                "@id": "#spatial-geo",
                "@type": "GeoCoordinates",
                "latitude": lat,
                "longitude": lon,
            }
        )
    elif isinstance(bbox, str) and bbox.count(",") == 3:
        west, south, east, north = (p.strip() for p in bbox.split(","))
        place["geo"] = _ref("#spatial-geo")
        entities.append(
            {
                "@id": "#spatial-geo",
                "@type": "GeoShape",
                # schema.org `box`: "lat lon lat lon", lower then upper corner
                "box": f"{south},{west} {north},{east}",
            }
        )
    return sid, [place] + entities


def _file_entity(f: Dict[str, Any]) -> Dict[str, Any]:
    ent: Dict[str, Any] = {
        "@id": _file_id(f["name"]),
        "@type": "File",
        "name": f["name"],
    }
    # fdo-metadata.ttl is finalised after the crate: no size, no hash.
    if f["name"] != SELF_DESCRIBING_FILE:
        if isinstance(f.get("size"), int):
            ent["contentSize"] = str(f["size"])
        if isinstance(f.get("sha256"), str) and len(f["sha256"]) == 64:
            ent["fdo:sha256"] = f["sha256"]
    if f.get("mediaType"):
        ent["encodingFormat"] = f["mediaType"]
    if f.get("role"):
        ent["fdo:role"] = f["role"]
    return ent


def build_ro_crate(
    cw: Any,
    *,
    resolved_id: str,
    citation_raw: Optional[Dict[str, Any]],
    package_files: Iterable[Dict[str, Any]],
    generated_files: Iterable[Dict[str, Any]],
    fdo_squirrel_version: str,
) -> Dict[str, Any]:
    """Assemble the RO-Crate metadata document as a dict.

    `package_files` must already exclude members the finished bundle
    supersedes (same basename as a generated file), `generated_files` are
    the companion files at the bundle root; both use the dict shape of
    fdo.describe_package_files()."""
    package_files = sorted(package_files, key=lambda d: d["name"])
    generated_files = sorted(generated_files, key=lambda d: d["name"])

    md_raw = getattr(cw, "md_raw", None)
    contextual: Dict[str, Dict[str, Any]] = {}

    def add(entity: Dict[str, Any]) -> None:
        contextual.setdefault(entity["@id"], entity)

    root: Dict[str, Any] = {
        "@id": "./",
        "@type": [
            "Dataset",
            cw.fdo_type,
            "crm:E73_Information_Object",
            "crmdig:D1_Digital_Object",
        ],
        "name": cw.title,
        "description": cw.description,
    }

    date_published = cw.date_released or cw.date_created
    if date_published:
        root["datePublished"] = date_published
    if cw.date_created:
        root["dateCreated"] = cw.date_created
    if cw.date_modified:
        root["dateModified"] = list(cw.date_modified)
    if cw.version:
        root["version"] = cw.version
    root["identifier"] = _identifiers(resolved_id, md_raw)

    # licence - same IRI as dct:license in the TTL
    lic = cw.license
    lic_iri = spdx_license_url(lic)
    if lic_iri:
        label = (
            (lic.get("label") or lic.get("id")) if isinstance(lic, dict) else lic
        )
        add(
            {
                "@id": lic_iri,
                "@type": "CreativeWork",
                "name": str(label).strip() if label else lic_iri,
            }
        )
        root["license"] = _ref(lic_iri)

    # creators - same IRIs as dct:creator in the TTL (CITATION.cff first)
    creators, _from_citation = derive_creators(citation_raw, list(cw.creators or []))
    for cid, clabel in creators:
        add({"@id": cid, "@type": "Person", "name": clabel})
    if creators:
        root["creator"] = [_ref(cid) for cid, _ in creators]

    contributors = list(cw.contributors or [])
    for cid, clabel in contributors:
        add({"@id": cid, "@type": "Person", "name": clabel})
    if contributors:
        root["contributor"] = [_ref(cid) for cid, _ in contributors]

    add(
        {
            "@id": cw.publisher_id,
            "@type": "Organization",
            "name": cw.publisher_label,
        }
    )
    root["publisher"] = _ref(cw.publisher_id)

    keywords = _keyword_labels(cw.keywords)
    if keywords:
        root["keywords"] = keywords

    loc_id, loc_entities = _spatial_entities(cw.spatial)
    for e in loc_entities:
        add(e)
    if loc_id:
        root["contentLocation"] = _ref(loc_id)

    # typed links to other resources (S29): the target becomes a
    # CreativeWork entity, the root points at it with the schema.org term
    # for the relation. Targets without an IRI have nothing to point at.
    linked: Dict[str, List[Dict[str, str]]] = {}
    target_notes: Dict[str, List[str]] = {}
    for item in getattr(cw, "related_resources", None) or []:
        if not isinstance(item, dict):
            continue
        prop = RELATION_TO_SCHEMA_ORG.get(item.get("relation"))
        target = item.get("target")
        tid = str(target.get("id") or "").strip() if isinstance(target, dict) else ""
        if not prop or not tid.startswith(("http://", "https://")):
            continue
        entity: Dict[str, Any] = {"@id": tid, "@type": "CreativeWork"}
        label = str(target.get("label") or "").strip()
        if label:
            entity["name"] = label
        # The crate has no relation with properties of its own, so the note
        # describes the target as seen from this package; several notes on
        # one target are joined in the order of the list.
        note = str(item.get("note") or "").strip()
        if note:
            notes = target_notes.setdefault(tid, [])
            if note not in notes:
                notes.append(note)
            entity["description"] = " ".join(notes)
            contextual.pop(tid, None)
        add(entity)
        refs = linked.setdefault(prop, [])
        if _ref(tid) not in refs:
            refs.append(_ref(tid))
    for prop in sorted(linked):
        root[prop] = linked[prop]

    root["conformsTo"] = _ref(PROFILE_IRI)
    add(
        {
            "@id": PROFILE_IRI,
            "@type": ["CreativeWork", "prof:Profile"],
            "name": "FDOx RO-Crate profile",
            "version": "1.0",
            "url": PROFILE_DOC_URL,
        }
    )

    # provenance: the same build the TTL records as prov:Activity
    add(
        {
            "@id": GENERATOR_ID,
            "@type": "SoftwareApplication",
            "name": "fdo-squirrel",
            "version": fdo_squirrel_version,
            "softwareVersion": fdo_squirrel_version,
            "url": REPOSITORY_URL,
        }
    )
    all_files = [(f, False) for f in package_files] + [
        (f, True) for f in generated_files
    ]
    root["hasPart"] = [_ref(_file_id(f["name"])) for f, _ in all_files]

    build_action = {
        "@id": BUILD_ACTION_ID,
        "@type": "CreateAction",
        "name": "FDOx build",
        "actionStatus": "http://schema.org/CompletedActionStatus",
        "instrument": _ref(GENERATOR_ID),
        "result": [_ref(_file_id(f["name"])) for f in generated_files],
    }

    descriptor = {
        "@id": CRATE_FILENAME,
        "@type": "CreativeWork",
        "conformsTo": _ref(RO_CRATE_SPEC),
        "about": _ref("./"),
    }

    graph: List[Dict[str, Any]] = [descriptor, root]
    graph += [contextual[k] for k in sorted(contextual)]
    graph += [_file_entity(f) for f, _ in all_files]
    graph.append(build_action)

    return {"@context": [RO_CRATE_CONTEXT, dict(EXTENSION_CONTEXT)], "@graph": graph}


def write_ro_crate(output_path: Path, crate: Dict[str, Any]) -> Path:
    """Write the crate as UTF-8 JSON, 2-space indent, trailing newline."""
    output_path.write_text(
        json.dumps(crate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return output_path
