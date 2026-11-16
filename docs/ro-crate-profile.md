# FDOx RO-Crate profile 1.0

Profile IRI: `https://w3id.org/fdo-squirrel/profile/ro-crate/1.0`
(declared via `conformsTo` on the crate's root data entity, RO-Crate 1.2
profile mechanism).

A crate conforming to this profile is an RO-Crate 1.2 that fdo-squirrel
produced from an FDOx package, and additionally:

1. The root data entity has `@type` `Dataset` plus an FDOx class
   (`fdo:SoftwareFDO`, `fdo:AnalysisFDO`, `fdo:3DDataFDO` or
   `fdo:RegistryFDO`), where the `fdo:` prefix is
   `https://w3id.org/fdo-squirrel/`.
2. Every file of the bundle except the metadata descriptor is a `File`
   data entity with `fdo:role` (the role vocabulary of
   `fdo/classification_rules.yaml`) and — except `fdo-metadata.ttl` —
   `fdo:sha256`.
3. The crate sits in the same folder as `fdo-metadata.ttl`, which holds the
   complete, lossless RDF description of the same FDO. Where the two
   disagree, the TTL is authoritative.
4. The build is recorded as a `CreateAction` whose `instrument` is the
   generating `SoftwareApplication` with its version.

The mapping from `MD.cff` / `CITATION.cff` is documented in
[ro-crate-mapping.md](ro-crate-mapping.md).
