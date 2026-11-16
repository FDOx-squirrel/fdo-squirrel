# RO-Crate export: mapping and scope

Since v1.1.0 every finished bundle (`<slug>-fdo-bundle.zip`) carries a
`ro-crate-metadata.json` at its root. The bundle is therefore a valid
RO-Crate 1.2 *folder* (a ZIP of one), and — once published on the Web with
FAIR Signposting — a lightweight "Webby" FAIR Digital Object.

**The crate is a view, not a second source of truth.** `fdo-metadata.ttl`
stays the lossless, CIDOC-CRM-anchored carrier of all metadata. The crate is
generated from the same inputs in the same run (`MD.cff`, `CITATION.cff`,
the package's file list) by `fdo_rocrate.py` and maps the core that
RO-Crate / schema.org can express. Nothing is maintained by hand.

## Mapping

| Crate | Source | Notes |
|---|---|---|
| root `@type` | `fdo_type` | `Dataset` plus `fdo:3DDataFDO` (etc.), `crm:E73_Information_Object`, `crmdig:D1_Digital_Object` — the same classes the TTL assigns |
| `name`, `description`, `version` | MD.cff `title`, `description`, `version` | |
| `datePublished` | MD.cff `date_released`, else `date_created` | RO-Crate requires it; omitted (with the crate still written) if MD.cff has neither |
| `dateCreated`, `dateModified` | MD.cff `date_created`, `date_modified` | |
| `identifier` | resolved FDO `id`, plus MD.cff `identifiers` with scheme `doi` or `url` | other schemes stay in the TTL |
| `license` | MD.cff `license` | same SPDX IRI as `dct:license` in the TTL; contextual `CreativeWork` entity |
| `creator` | CITATION.cff `authors`, else MD.cff `creators` | same IRIs as the TTL (`fdo.derive_creators`) |
| `contributor` | MD.cff `contributors` | |
| `publisher` | first MD.cff `publishers` entry | `Organization` |
| `keywords` | MD.cff `keywords[].label` | keyword IRIs stay in the TTL |
| `contentLocation` | MD.cff `spatial` | `Place` with `GeoCoordinates` (`lat`/`lon`) or `GeoShape` (`bounding_box`) |
| `hasPart` / `File` | every package member plus every generated companion file | `contentSize`, `encodingFormat`, `fdo:sha256`, `fdo:role` — values identical to the TTL's `dcat:Distribution` entries |
| `CreateAction` | the build | `instrument` is the `fdo-squirrel` `SoftwareApplication` (name, version); `result` lists the generated files — mirrors the TTL's `prov:Activity` |

Package members that the bundle supersedes (same basename as a generated
file, e.g. a stale `fdo-metadata.ttl`) are left out, exactly as
`build_finished_bundle()` leaves them out of the ZIP.

## Deliberately not in the crate (yet)

These remain in `fdo-metadata.ttl` only: `temporal`, `heritage_object`,
`technique`, `funding`, `related_resources`, WKT geometries, keyword and
other IRIs beyond labels, identifier schemes other than `doi`/`url`.
RO-Crate has no agreed place for most of them; guessing one would put
fdo-squirrel-specific meaning into terms other tools read differently.

## `fdo-metadata.ttl` has no size or hash in the crate

A manifest cannot contain a hash of its own final bytes. `fdo-metadata.ttl`
is finalised *after* the crate (it lists the crate as a distribution), so
the crate describes it without `contentSize` and `fdo:sha256`. This is the
same limitation the TTL already has for its description of itself.

## Validating

The official validator needs network access (it fetches the RO-Crate
JSON-LD context), so it is not part of the offline test-suite
(`python -m unittest discover -s tests`). Run it on a finished bundle:

    pip install roc-validator && rocrate-validator validate <folder-with-ro-crate-metadata.json>

where `<folder>` is the bundle ZIP extracted to a directory.
