"""check_signposting.py - what FAIR Signposting does a URL (or a local
landing page) actually offer? (S24, PRIMER.md)

Standard library only, ASCII output (safe on a Windows cmd code page).

    python tools\\check_signposting.py https://doi.org/10.5281/zenodo.18724635
    python tools\\check_signposting.py https://zenodo.org/records/18724635 --linkset
    python tools\\check_signposting.py --file output\\fdo-landing-page.html

For a URL it sends a HEAD request (GET if the server sends no Link header
on HEAD), follows redirects, and reads the typed links from the HTTP Link
header(s) of the final response and from <link> elements in an HTML body.
With --linkset it also fetches an advertised linkset (RFC 9264 JSON) and
summarises it. It reports which Level 1 relations are present and whether a
RO-Crate can be retrieved via Signposting (rel=describedby for the metadata
document or rel=item for a ZIP archive, as RO-Crate 1.2 describes it).

Exit code 0 if cite-as, a describedby/linkset and an item/linkset are all
present, 1 otherwise, 2 on a request error.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

SIGNPOSTING_RELS = ["cite-as", "describedby", "item", "license", "author", "type", "linkset", "collection"]
RO_CRATE_PROFILE = "https://w3id.org/ro/crate"
UA = "fdo-squirrel-check-signposting/1.0 (+https://github.com/FDOx-squirrel/fdo-squirrel)"

Link = Dict[str, str]  # keys: rel, href, type?, profile?, source


def parse_link_header(value: str, base: str = "") -> List[Link]:
    """Parse one HTTP Link header value (RFC 8288) into links. Handles
    several comma-separated links and quoted parameter values that contain
    commas or semicolons."""
    links: List[Link] = []
    i, n = 0, len(value)
    while i < n:
        lt = value.find("<", i)
        if lt < 0:
            break
        gt = value.find(">", lt)
        if gt < 0:
            break
        href = value[lt + 1 : gt]
        i = gt + 1
        params: Dict[str, str] = {}
        while i < n:
            while i < n and value[i] in " \t":
                i += 1
            if i >= n or value[i] == ",":
                i += 1
                break
            if value[i] != ";":
                i += 1
                continue
            i += 1
            j = i
            while j < n and value[j] not in "=;,":
                j += 1
            name = value[i:j].strip().lower()
            val = ""
            if j < n and value[j] == "=":
                j += 1
                if j < n and value[j] == '"':
                    k = j + 1
                    while k < n and value[k] != '"':
                        k += 2 if value[k] == "\\" else 1
                    val = value[j + 1 : k]
                    j = k + 1
                else:
                    k = j
                    while k < n and value[k] not in ";,":
                        k += 1
                    val = value[j:k].strip()
                    j = k
            if name:
                params[name] = val
            i = j
        for rel in params.get("rel", "").split():
            link: Link = {"rel": rel.lower(), "href": urljoin(base, href), "source": "header"}
            for k in ("type", "profile", "anchor"):
                if k in params:
                    link[k] = params[k]
            links.append(link)
    return links


class _LinkElements(HTMLParser):
    def __init__(self, base: str) -> None:
        super().__init__()
        self.base = base
        self.links: List[Link] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: D401
        if tag != "link":
            return
        a = {k.lower(): (v or "") for k, v in attrs}
        if not a.get("href") or not a.get("rel"):
            return
        for rel in a["rel"].split():
            link: Link = {"rel": rel.lower(), "href": urljoin(self.base, a["href"]), "source": "html"}
            for k in ("type", "profile"):
                if a.get(k):
                    link[k] = a[k]
            self.links.append(link)


def parse_html_links(text: str, base: str = "") -> List[Link]:
    p = _LinkElements(base)
    p.feed(text)
    return p.links


def _open(url: str, method: str, accept: str = "*/*"):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept": accept})
    return urllib.request.urlopen(req, timeout=30)


def fetch_links(url: str) -> Tuple[str, List[Link]]:
    """(final URL, links from Link headers and HTML <link> elements)."""
    with _open(url, "HEAD", "text/html") as r:
        final = r.geturl()
        headers = r.headers.get_all("Link") or []
        ctype = r.headers.get("Content-Type", "")
    links: List[Link] = []
    for h in headers:
        links += parse_link_header(h, final)
    if not links or "html" in ctype:
        with _open(url, "GET", "text/html") as r:
            final = r.geturl()
            for h in r.headers.get_all("Link") or []:
                for l in parse_link_header(h, final):
                    if l not in links:
                        links.append(l)
            ctype = r.headers.get("Content-Type", "")
            if "html" in ctype:
                body = r.read(2_000_000).decode("utf-8", errors="replace")
                links += parse_html_links(body, final)
    return final, links


def fetch_linkset(url: str) -> List[Link]:
    with _open(url, "GET", "application/linkset+json, application/json") as r:
        data = json.loads(r.read().decode("utf-8"))
    return linkset_to_links(data, url)


def linkset_to_links(data: dict, base: str = "") -> List[Link]:
    out: List[Link] = []
    for ctx in data.get("linkset", []):
        anchor = ctx.get("anchor", "")
        for rel, targets in ctx.items():
            if rel == "anchor" or not isinstance(targets, list):
                continue
            for t in targets:
                link: Link = {"rel": rel.lower(), "href": urljoin(base, t.get("href", "")), "source": "linkset", "anchor": anchor}
                for k in ("type", "profile"):
                    if k in t:
                        link[k] = t[k]
                out.append(link)
    return out


def report(links: List[Link], where: str) -> int:
    print(f"Signposting for: {where}")
    print(f"{len(links)} link(s) found")
    rels = SIGNPOSTING_RELS + sorted({l["rel"] for l in links} - set(SIGNPOSTING_RELS) - {"stylesheet", "icon"})
    for rel in rels:
        mine = [l for l in links if l["rel"] == rel]
        if not mine:
            continue
        print(f"\n  rel={rel} ({len(mine)})")
        for l in mine[:12]:
            extra = "".join(f"  {k}={l[k]}" for k in ("type", "profile") if k in l)
            print(f"    [{l['source']}] {l['href']}{extra}")
        if len(mine) > 12:
            print(f"    ... and {len(mine) - 12} more")

    have = {l["rel"] for l in links}
    has_linkset = "linkset" in have
    checks = [
        ("cite-as (persistent identifier)", "cite-as" in have),
        ("describedby (metadata) or linkset", "describedby" in have or has_linkset),
        ("item (content) or linkset", "item" in have or has_linkset),
    ]
    print("\nLevel 1 check")
    for label, ok in checks:
        print(f"  {'OK     ' if ok else 'MISSING'} {label}")

    crate_meta = [l for l in links if l["rel"] == "describedby" and (RO_CRATE_PROFILE in l.get("profile", "") or l["href"].endswith("ro-crate-metadata.json"))]
    zips = [l for l in links if l["rel"] == "item" and l.get("type", "").lower() in ("application/zip", "application/x-zip-compressed")]
    print("\nRO-Crate retrieval via Signposting")
    print(f"  describedby -> RO-Crate metadata document: {'yes' if crate_meta else 'no'}")
    print(f"  item -> ZIP archive: {'yes (%d)' % len(zips) if zips else 'no'}")
    if zips and not any(RO_CRATE_PROFILE in z.get("profile", "") for z in zips):
        print("  note: the ZIP item has no profile=\"https://w3id.org/ro/crate\" attribute")
    return 0 if all(ok for _, ok in checks) else 1


def main(argv: Optional[List[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Report the FAIR Signposting of a URL or a local landing page.")
    ap.add_argument("url", nargs="?", help="URL or DOI URL to check")
    ap.add_argument("--file", help="local HTML landing page (offline check of <link> elements)")
    ap.add_argument("--linkset", action="store_true", help="also fetch and summarise an advertised linkset")
    args = ap.parse_args(argv)
    if not args.url and not args.file:
        ap.error("give a URL or --file")

    try:
        if args.file:
            with open(args.file, encoding="utf-8") as f:
                links = parse_html_links(f.read(), "")
            where = args.file
        else:
            where, links = fetch_links(args.url)
            if where != args.url:
                print(f"(redirected to {where})")
        if args.linkset:
            for ls in [l for l in links if l["rel"] == "linkset"][:3]:
                try:
                    links += fetch_linkset(ls["href"])
                except Exception as e:  # report, do not abort
                    print(f"could not read linkset {ls['href']}: {e}")
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"Request failed: {e}")
        return 2
    return report(links, where)


if __name__ == "__main__":
    sys.exit(main())
