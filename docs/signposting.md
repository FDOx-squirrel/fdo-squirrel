# FAIR Signposting

[FAIR Signposting](https://signposting.org/FAIR/) uses a small set of typed
web links (RFC 8288) so that a machine can go from a landing page to the
persistent identifier, the metadata and the content of a digital object
without scraping HTML. Together with the RO-Crate in the bundle it makes an
FDOx a lightweight "Webby" FAIR Digital Object: RO-Crate 1.2 describes
retrieving a crate via `rel="describedby"` (the metadata document) or
`rel="item"` (a ZIP archive).

## Two publishing routes

**1. A repository that does Signposting itself (Zenodo).** Upload the bundle
ZIP as the record's file. Zenodo is built on InvenioRDM, which documents
built-in FAIR Signposting (Level 2 by default, Level 1 configurable), so
nothing needs to be generated for this route. What a given record really
serves can be checked with the tool below.

**2. Static hosting (e.g. GitHub Pages).** No custom HTTP headers are
possible there, but FAIR Signposting allows the same links as HTML `<link>`
elements in the page head. For this route fdo-squirrel writes the landing
page.

## What fdo-squirrel writes

Every run puts `fdo-landing-page.html` into the bundle. Its `<head>` holds:

| rel | target |
|---|---|
| `cite-as` | the FDO's identifier, if it is an `http(s)` IRI (a `urn:` fallback id is skipped) |
| `describedby` | `ro-crate-metadata.json` (`application/ld+json`, `profile="https://w3id.org/ro/crate"`) and `fdo-metadata.ttl` (`text/turtle`) |
| `license` | the SPDX licence IRI |
| `author` | creators that have an `http(s)` IRI (e.g. ORCID) |
| `type` | the schema.org type (`Dataset`, `SoftwareSourceCode` for `fdo:SoftwareFDO`) and the FDOx class IRI |
| `item` | every file of the original package |

Links are relative by default, so the page works inside the unzipped bundle.

With `--base-url` (the public folder URL the bundle will be served from) the
links become absolute and fdo-squirrel additionally writes:

- `fdo-linkset.json`: an RFC 9264 JSON linkset (FAIR Signposting Level 2)
  with the landing page's links, plus a `collection` back link per item;
- an extra `item` for the bundle ZIP (`application/zip`, RO-Crate profile) and
  a `rel="linkset"` link in the page head.

```
python main.py --package package.zip --outdir output --base-url https://example.org/fdo/ciic81
```

The landing page is deliberately not called `index.html`: bundle members are
superseded by file name, and an `index.html` would remove the 3DHOP viewer's
`viewer/index.html`.

To publish on static hosting, unzip the bundle into the served folder
(together with the bundle ZIP next to it, if the ZIP `item` link should
resolve).

## Checking what a URL serves

`tools/check_signposting.py` (standard library only) reports the typed links
of a URL, from HTTP Link headers and HTML `<link>` elements, optionally the
linkset, and whether an RO-Crate can be retrieved via Signposting:

```
python tools\check_signposting.py https://doi.org/10.5281/zenodo.18724635 --linkset
python tools\check_signposting.py --file output\fdo-landing-page.html
```

Exit code 0 if `cite-as`, a `describedby` (or linkset) and an `item` (or
linkset) are present, 1 otherwise, 2 on a request error.

## Limits

- HTML `<link>` elements are an allowed carrier but are read less widely by
  clients than HTTP headers; on static hosting there is no alternative.
- Static hosts typically serve `.json` as `application/json`, not
  `application/linkset+json`; the `rel="linkset"` link states the intended
  type.
- The linkset is only written with `--base-url`; relative references are not
  a reliable anchor for it.
- The ZIP `item` link depends on the ZIP being published next to the page.
