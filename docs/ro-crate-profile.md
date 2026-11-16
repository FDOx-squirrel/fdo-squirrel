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

## Validation

`roc-validator` 0.13.1 (profile `ro-crate-1.2`) reports a bundle built with
fdo-squirrel v1.1.0 from a real 3D package (Q60) as a valid RO-Crate 1.2: 63
checks passed, 0 failed, 3 skipped (2026-11-16). Its first run found one
problem, fixed since: a `SoftwareApplication` must carry `version`, so the
generating application now has both `version` and `softwareVersion`. The
validator also warns that conformance to the FDOx profile IRI itself could
not be verified; the IRI does not resolve yet (the w3id registration is an
open point in `PRIMER.md`).

A step-by-step guide for running the validator yourself is in
[Validating the RO-Crate in a bundle](validate-ro-crate.md).
