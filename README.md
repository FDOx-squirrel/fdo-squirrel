# FAIR Data Object, exchangeable — Squirrel Implementation (FDOx Squirrel)

![FDOx Squirrel logo](logo.png)

**v1.2.1 – Reference implementation (ZIP-based FDOx → RDF, with RO-Crate export)**

> *FDOx (FAIR Data Object, exchangeable) is a reference implementation of the FAIR Digital Object (FDO) framework, emphasising exchangeability through Linked Open Data and a Wikibase-compatible RDF vocabulary.*

`fdo-squirrel` is a **reference implementation for modelling FAIR Data Objects, exchangeable (FDOx)** from self-contained ZIP packages into **machine-readable RDF**.  
It demonstrates a **package-centric, reproducible crosswalk** from community-standard metadata files to interoperable knowledge graph representations.

---

## What it does

Given a **ZIP package as Source of Truth**, `fdo-squirrel`:

- reads **descriptive metadata** from `MD.cff`
- reads **citation metadata** from `CITATION.cff`
- inspects the **ZIP contents** (files, sizes, checksums)
- generates a **single RDF/Turtle representation** of the FDOx
- records **provenance** for every mapped field

The result is a **self-describing FDOx** that can be ingested into RDF-based infrastructures and knowledge graphs.

### Architecture overview

![ZIP-centric FDOx modelling workflow](https://raw.githubusercontent.com/FDOx-squirrel/fdox-visuals/main/img/fdox-fdo-squirrel-architecture.png)

*(Diagram maintained in [`fdox-visuals`](https://github.com/FDOx-squirrel/fdox-visuals), redrawn from this
repo's own [`architecture.mermaid`](architecture.mermaid) — see `PRIMER.md` S11 for why this is a
deliberate exception to this family's usual "reuse means copying" rule.)*

---

## Input requirements

The input **must be a ZIP file** containing at least:

### 1. `CITATION.cff`
- Valid according to the **Citation File Format (CFF)** specification  
  https://citation-file-format.github.io/
- Used for:
  - creators / authors
  - citation-related metadata

### 2. `MD.cff`
- Valid according to the **project-specific MD.cff schema**
- Used for:
  - FDOx type (`fdo:SoftwareFDO`, `fdo:AnalysisFDO`, `fdo:3DDataFDO`, `fdo:RegistryFDO`)
  - title, description, version, release/modification dates
  - licence, publisher(s), creators, contributors
  - keywords, identifiers, related resources
  - spatial and temporal extent
  - heritage-object and technique/acquisition metadata (for 3D/heritage packages)
  - funding (optional)

### 3. Arbitrary package content
- data, software, models, documentation, etc.
- each file becomes a `dcat:Distribution`
- roles are assigned via rule-based classification

---

## Output

Running the pipeline writes to `output/` (or `--outdir`; the folder is
cleared at the start of every run):

- the finished bundle, `<name>-fdo-bundle.zip`, which contains everything below;
- four files next to it that are handy to open directly:
  `fdo-metadata.ttl`, `ro-crate-metadata.json`, `rdf_modelling_report.html`
  and `fdo_overview.png` (the PNG only if the Mermaid CLI is available);
- `_work/`, holding every file the run generated (diagrams, `FDOx.yaml`, the
  JSON report, landing page and linkset) for inspection.

The generated files in detail:

- **`fdo-metadata.ttl`**  
  RDF/Turtle representation of the FDOx, combining:
  - DCAT
  - FDOx vocabulary
  - CIDOC CRM / CRMdig
  - GeoSPARQL (if applicable)

- **`rdf_modelling_report.json`**  
  A machine-readable provenance report documenting:
  - which field came from which source
  - how many triples were generated per mapping step

- **`rdf_modelling_report.html`**  
  Human-readable HTML version of the modelling report

- **`FDOx.yaml`**  
  A short, human-readable build manifest: which `fdo-squirrel` version
  produced this FDO, and — best-effort, structural guess only — which
  upstream tool likely built the *input* package (e.g. `fdo-3d-packager`,
  inferred from telltale files like a 3DHOP viewer plus Nexus meshes).
  Distinct from the modelling report above: this is about how the FDO
  itself was built, not which source field mapped to which RDF property.

- **`ro-crate-metadata.json`**  
  An [RO-Crate 1.2](https://w3id.org/ro/crate/1.2) view of the finished
  bundle: with this file at its root, the bundle ZIP is an RO-Crate (and,
  published with FAIR Signposting, a lightweight "Webby" FDO). Generated
  from the same inputs as `fdo-metadata.ttl`, which stays the lossless
  carrier — see [docs/ro-crate-mapping.md](docs/ro-crate-mapping.md) and
  the [FDOx profile](docs/ro-crate-profile.md). To check a bundle yourself
  with the community validator, follow
  [Validating the RO-Crate in a bundle](docs/validate-ro-crate.md).

- **`fdo-landing-page.html`** *(and `fdo-linkset.json` with `--base-url`)*  
  A small landing page whose `<head>` carries
  [FAIR Signposting](https://signposting.org/FAIR/) links (`cite-as`,
  `describedby`, `item`, `license`, `author`, `type`) for static hosting
  such as GitHub Pages; with `--base-url` the links are absolute and an
  RFC 9264 linkset (Level 2) is written too. See
  [docs/signposting.md](docs/signposting.md) and `tools/check_signposting.py`,
  which reports what a URL actually serves.

- **`fdo_overview.mermaid`**  
  A Mermaid flowchart summarising the FDO (core metadata, distributions by role)

- **`fdo_overview.png`** *(optional)*  
  A high-resolution render of the diagram above. Needs `mmdc`
  ([Mermaid CLI](https://github.com/mermaid-js/mermaid-cli)) on `PATH`;
  if it's missing, this step is skipped with a one-line warning and
  everything else still runs.

- **`fdo_files_roles_graph.svg`+`.png`** *(optional PNG)*  
  Which file in the package got which `fdo:role`: each file (or, for a
  role with many files, a directory-grouped summary) as its own box, with
  a curved connector into a shared, coloured role node. (An earlier
  fact-sheet-style version was dropped - side by side with this graph it
  didn't add anything the graph didn't already show more clearly.)

- **`fdo_md_cff.svg`+`.png`** and **`fdo_md_cff_graph.svg`+`.png`** *(optional PNG)*  
  The ingested `MD.cff`, populated with this package's real values
  (not a schema diagram - one specific FDO's actual content). Two styles:
  a stacked fact sheet (denser, better for a lot of text), or a node
  graph with a central `MD_cff` node and one satellite box per populated
  group (agents, classification, space & time, heritage object &
  technique).

- **`fdo_ttl_snippet_metadata.svg`+`.png`**, **`fdo_ttl_snippet_distributions.svg`+`.png`** and **`fdo_ttl_snippet_links.svg`+`.png`** *(optional PNG)*  
  Three small, dark "code cards" for dropping straight into a slide,
  each showing a real excerpt of `fdo-metadata.ttl` rather than the
  whole file, syntax-coloured, rendered at 2.5x for a crisp result on a
  slide. PNG has real alpha transparency around the rounded corners,
  rendered straight from `resvg-py`'s own bytes:
  - **metadata** — the core dataset block, everything except the two
    lines that are unreadable on a slide anyway (the full distribution
    id list, a JSON-in-a-literal blob).
  - **distributions** — two or three real `dcat:Distribution` blocks in
    full, one per role where possible, so the shape of an entry is
    visible, not just its name.
  - **links** — `rdfs:label`/`owl:sameAs` lines whose subject (or, for
    `owl:sameAs`, target) is a genuine external IRI - Wikidata,
    OpenStreetMap, ChronOntology, ORCID, SPDX - ranked by how
    well-known the linked-open-data hub is, not by file order. A card
    is skipped, not written empty, if a given FDO has nothing to show
    for it (e.g. no external links at all).

  All diagram PNGs need the optional `resvg-py` extra
  (`pip install fdo-squirrel[diagrams]`); without it, the SVGs are still
  written, just not rasterised. Fonts (Fira Sans) are vendored under
  `fonts/`, same as `fdox-visuals`, so rendering doesn't depend on what's
  installed system-wide.

- **`<package-name>-fdo-bundle.zip`**  
  The original source ZIP plus all of the files above, packaged into one
  self-contained, ready-to-(re)publish archive - replacing any stale copies
  of those same filenames the source ZIP already carried (from a previous
  manual round of this same workflow, for example).

All of the generated files - including the TTL and the bundle's own
contents - are themselves described as `dcat:Distribution` entries inside
`fdo-metadata.ttl`, using the same content-addressing and role
classification as the original ZIP's members: the finished bundle is fully
self-describing, not just a folder of loosely related files.

---

## How to run

### Option A – via local config (recommended for development)

Create a local file **`config.local.json`** (not committed):

```json
{
  "package_source": "C:/tmp/fdox/ogham-analysis.zip"
}
```

Then run:

```bash
python main.py
```

---

### Option B – via command line (one-off runs)

```bash
python main.py --package "C:/tmp/fdox/GEARS_1.zip"
```

`--package` (or its short form `-p`) accepts a local path or a direct ZIP
URL, and takes priority over `config.local.json` and the hardcoded
`PACKAGE_SOURCE` fallback in `main.py` for that one run - nothing else
needs to change to try a different package.

---

### Optional – high-resolution diagram render

`fdo_overview.png` needs Node.js plus the Mermaid CLI:

```bash
npm install -g @mermaid-js/mermaid-cli
```

The `fdo_files_roles_graph`/`fdo_md_cff*`/`fdo_ttl_snippet` PNGs (S8)
need a separate, lighter dependency instead - no Node.js involved:

```bash
pip install fdo-squirrel[diagrams]   # or: pip install resvg-py
```

Without these, `python main.py` still produces everything else - each
missing-dependency step is skipped on its own with a one-line warning,
never the whole run.

---

## Requirements

- Python ≥ 3.9
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

---

## Status

This is a **v1.2.1 reference implementation**.

- ✔ stable RDF output
- ✔ valid Turtle
- ✔ deterministic identifiers
- ✔ deterministic, byte-identical output across repeated runs against the same package (RDF, both provenance reports, the overview diagram, and the finished bundle ZIP)
- ✔ explicit provenance
- ✔ the RO-Crate export validates as RO-Crate 1.2 (`roc-validator`)
- ✔ suitable for documentation and scientific publication

The focus is **correctness, transparency, and explainability**, not performance or completeness.

---

## Why this matters

`fdo-squirrel` shows how **FAIR Data Objects, exchangeable (FDOx) can be modelled as self-contained, package-based entities**, where:

- metadata and data stay together
- RDF is derived, not manually curated
- provenance is explicit and reproducible

This makes FDOx suitable for **long-term reuse, federation, and knowledge graph integration**.