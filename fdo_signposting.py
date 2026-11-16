"""
fdo_signposting.py - FAIR Signposting for the finished FDOx bundle (S24,
PRIMER.md): a small HTML landing page whose <head> carries the signposts as
<link> elements (Level 1), and - when the public base URL is known - an
RFC 9264 JSON linkset (Level 2).

Why a generated landing page at all: a repository such as Zenodo serves
Signposting itself, but on plain static hosting (GitHub Pages) there are no
custom HTTP headers; FAIR Signposting allows the same typed links as HTML
<link> elements, which is the only route there. See docs/signposting.md.

Signposts (IANA link relations, as in the FAIR Signposting profile):

- cite-as      the FDO's persistent identifier (only if it is an http(s) IRI)
- describedby  ro-crate-metadata.json (application/ld+json, RO-Crate profile)
               and fdo-metadata.ttl (text/turtle)
- item         every file of the original package
- license      the SPDX licence IRI
- author       creators with an http(s) IRI (e.g. ORCID)
- type         schema.org type plus the FDOx class IRI
- linkset      (only with a base URL) the Level 2 linkset

Relative links by default (the page works inside the unzipped bundle);
absolute ones with a base URL, which is also what the linkset needs.

Deterministic (S4): no clock, sorted inputs, fixed order of rels. Standard
library only.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote

from fdo import derive_creators, spdx_license_url

LANDING_FILENAME = "fdo-landing-page.html"
LINKSET_FILENAME = "fdo-linkset.json"
CRATE_FILENAME = "ro-crate-metadata.json"
TTL_FILENAME = "fdo-metadata.ttl"

RO_CRATE_PROFILE = "https://w3id.org/ro/crate"
FDOX_NS = "https://w3id.org/fdo-squirrel/"

# Fixed order in which rels are written (HTML and linkset alike).
REL_ORDER = ["cite-as", "describedby", "license", "author", "type", "item", "linkset"]

SCHEMA_TYPE = {
    "fdo:SoftwareFDO": "https://schema.org/SoftwareSourceCode",
}
DEFAULT_SCHEMA_TYPE = "https://schema.org/Dataset"


def normalise_base_url(base_url: Optional[str]) -> Optional[str]:
    """Validated base URL without trailing slash, or None."""
    if not base_url:
        return None
    b = base_url.strip()
    if not b.startswith(("http://", "https://")):
        raise ValueError(f"--base-url must start with http:// or https://, got {base_url!r}")
    return b.rstrip("/")


def _href(path: str, base_url: Optional[str]) -> str:
    q = quote(path, safe="/")
    return f"{base_url}/{q}" if base_url else q


def _is_http(iri: Any) -> bool:
    return isinstance(iri, str) and iri.startswith(("http://", "https://"))


def _expand_fdo_type(fdo_type: str) -> str:
    return FDOX_NS + fdo_type[4:] if fdo_type.startswith("fdo:") else fdo_type


def build_signposts(
    cw: Any,
    *,
    resolved_id: str,
    citation_raw: Optional[Dict[str, Any]],
    package_files: Iterable[Dict[str, Any]],
    base_url: Optional[str] = None,
    bundle_name: Optional[str] = None,
) -> List[Dict[str, str]]:
    """The signposts as dicts {rel, href, type?, profile?}, in REL_ORDER,
    each rel's entries in a stable order."""
    sp: List[Dict[str, str]] = []

    if _is_http(resolved_id):
        sp.append({"rel": "cite-as", "href": resolved_id})

    sp.append(
        {
            "rel": "describedby",
            "href": _href(CRATE_FILENAME, base_url),
            "type": "application/ld+json",
            "profile": RO_CRATE_PROFILE,
        }
    )
    sp.append(
        {"rel": "describedby", "href": _href(TTL_FILENAME, base_url), "type": "text/turtle"}
    )

    lic = spdx_license_url(cw.license)
    if lic:
        sp.append({"rel": "license", "href": lic})

    creators, _ = derive_creators(citation_raw, list(cw.creators or []))
    for cid, _label in creators:
        if _is_http(cid):
            sp.append({"rel": "author", "href": cid})

    sp.append({"rel": "type", "href": SCHEMA_TYPE.get(cw.fdo_type, DEFAULT_SCHEMA_TYPE)})
    sp.append({"rel": "type", "href": _expand_fdo_type(cw.fdo_type)})

    for f in sorted(package_files, key=lambda d: d["name"]):
        item = {"rel": "item", "href": _href(f["name"], base_url)}
        if f.get("mediaType"):
            item["type"] = f["mediaType"]
        sp.append(item)

    if base_url:
        if bundle_name:
            sp.append(
                {
                    "rel": "item",
                    "href": _href(bundle_name, base_url),
                    "type": "application/zip",
                    "profile": RO_CRATE_PROFILE,
                }
            )
        sp.append(
            {
                "rel": "linkset",
                "href": _href(LINKSET_FILENAME, base_url),
                "type": "application/linkset+json",
            }
        )

    return sorted(sp, key=lambda s: REL_ORDER.index(s["rel"]))  # stable sort


def _link_element(s: Dict[str, str]) -> str:
    attrs = [f'rel="{html.escape(s["rel"], quote=True)}"', f'href="{html.escape(s["href"], quote=True)}"']
    if s.get("type"):
        attrs.append(f'type="{html.escape(s["type"], quote=True)}"')
    if s.get("profile"):
        attrs.append(f'profile="{html.escape(s["profile"], quote=True)}"')
    return "<link " + " ".join(attrs) + ">"


_CSS = (
    "body{font-family:'Fira Sans',Arial,sans-serif;background:#fbf7ef;color:#222;"
    "margin:0;padding:2rem}main{max-width:60rem;margin:auto;background:#fff;"
    "border-radius:8px;padding:2rem}h1{color:#9a3412;margin-top:0}"
    "table{border-collapse:collapse;width:100%;font-size:.9rem}"
    "th,td{text-align:left;padding:.3rem .5rem;border-bottom:1px solid #eee}"
    "code{background:#f3efe6;padding:0 .25rem}"
)


def render_landing_page(
    cw: Any,
    signposts: List[Dict[str, str]],
    *,
    resolved_id: str,
    citation_raw: Optional[Dict[str, Any]],
    package_files: Iterable[Dict[str, Any]],
    base_url: Optional[str] = None,
) -> str:
    e = html.escape
    package_files = sorted(package_files, key=lambda d: d["name"])
    creators, _ = derive_creators(citation_raw, list(cw.creators or []))

    head = [
        '<meta charset="utf-8">',
        f"<title>{e(cw.title)}</title>",
        f"<style>{_CSS}</style>",
    ] + [_link_element(s) for s in signposts]

    rows = []
    for f in package_files:
        size = f["size"] if isinstance(f.get("size"), int) else ""
        rows.append(
            "<tr><td><a href=\"{h}\">{n}</a></td><td>{r}</td><td>{m}</td><td>{s}</td></tr>".format(
                h=e(_href(f["name"], base_url), quote=True),
                n=e(f["name"]),
                r=e(str(f.get("role") or "")),
                m=e(str(f.get("mediaType") or "")),
                s=size,
            )
        )

    body = [
        f"<h1>{e(cw.title)}</h1>",
        f"<p>{e(cw.description)}</p>",
        "<dl>",
        f"<dt>Identifier</dt><dd><code>{e(resolved_id)}</code></dd>",
        f"<dt>Type</dt><dd><code>{e(cw.fdo_type)}</code></dd>",
    ]
    if cw.version:
        body.append(f"<dt>Version</dt><dd>{e(cw.version)}</dd>")
    if creators:
        body.append("<dt>Creators</dt><dd>" + "; ".join(e(lbl) for _, lbl in creators) + "</dd>")
    lic = spdx_license_url(cw.license)
    if lic:
        body.append(f'<dt>Licence</dt><dd><a href="{e(lic, quote=True)}">{e(lic)}</a></dd>')
    body += [
        "</dl>",
        "<h2>Machine-readable description</h2>",
        "<ul>",
        f'<li><a href="{e(_href(CRATE_FILENAME, base_url), quote=True)}">{CRATE_FILENAME}</a> (RO-Crate 1.2)</li>',
        f'<li><a href="{e(_href(TTL_FILENAME, base_url), quote=True)}">{TTL_FILENAME}</a> (RDF/Turtle, lossless)</li>',
        "</ul>",
        "<h2>Files</h2>",
        "<table><tr><th>File</th><th>Role</th><th>Media type</th><th>Bytes</th></tr>",
        *rows,
        "</table>",
        "<p><small>FAIR Signposting links for machines are in this page's "
        "<code>&lt;head&gt;</code>. Generated by fdo-squirrel.</small></p>",
    ]

    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        + "\n".join(head)
        + "\n</head>\n<body>\n<main>\n"
        + "\n".join(body)
        + "\n</main>\n</body>\n</html>\n"
    )


def build_linkset(
    signposts: List[Dict[str, str]], base_url: str
) -> Dict[str, Any]:
    """RFC 9264 JSON linkset (FAIR Signposting Level 2): the landing page's
    outgoing links, plus - per item - the back link rel=collection."""
    landing = _href(LANDING_FILENAME, base_url)
    outgoing: Dict[str, List[Dict[str, str]]] = {}
    for s in signposts:
        if s["rel"] == "linkset":
            continue  # a linkset does not list itself
        target = {k: v for k, v in s.items() if k != "rel"}
        outgoing.setdefault(s["rel"], []).append(target)
    entry: Dict[str, Any] = {"anchor": landing}
    entry.update({rel: outgoing[rel] for rel in REL_ORDER if rel in outgoing})
    linkset: List[Dict[str, Any]] = [entry]
    for item in outgoing.get("item", []):
        linkset.append(
            {
                "anchor": item["href"],
                "collection": [{"href": landing, "type": "text/html"}],
            }
        )
    return {"linkset": linkset}


def write_signposting(
    output_dir: Path,
    cw: Any,
    *,
    resolved_id: str,
    citation_raw: Optional[Dict[str, Any]],
    package_files: Iterable[Dict[str, Any]],
    base_url: Optional[str],
    bundle_name: Optional[str],
) -> List[Path]:
    """Write the landing page (always) and the linkset (only with a base
    URL). Returns the files written, landing page first."""
    package_files = list(package_files)
    sp = build_signposts(
        cw,
        resolved_id=resolved_id,
        citation_raw=citation_raw,
        package_files=package_files,
        base_url=base_url,
        bundle_name=bundle_name,
    )
    written: List[Path] = []
    page = output_dir / LANDING_FILENAME
    page.write_text(
        render_landing_page(
            cw,
            sp,
            resolved_id=resolved_id,
            citation_raw=citation_raw,
            package_files=package_files,
            base_url=base_url,
        ),
        encoding="utf-8",
    )
    written.append(page)
    if base_url:
        ls = output_dir / LINKSET_FILENAME
        ls.write_text(
            json.dumps(build_linkset(sp, base_url), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(ls)
    return written
