"""fdo_files_roles_common.py — shared extraction/grouping logic for
"Files and Roles" (S8, PRIMER.md): which file in the package got which
fdo:role. Reads the already-written fdo-metadata.ttl with the same
lightweight regex approach fdo_mermaid.py already uses for its own
distribution parsing, rather than adding an RDF parser dependency just
for this.

Originally paired with a fact-sheet diagram module of its own
(fdo_files_roles_diagram.py); that style was dropped after Flo compared
it side by side with the node-graph version and found it added nothing
the graph didn't already show more clearly (S8 nachtrag, PRIMER.md) - the
graph module (fdo_files_roles_graph.py) is now the only consumer of the
functions here.

Deterministic by construction: every list this module builds is sorted
before it is returned, and nothing here reads a clock.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple
import re

# A handful of family-palette colours, cycled across roles so each role
# gets a distinct badge without inventing a new colour per role - four is
# already the full palette fdox-visuals defines (PRIMER.md, S2/S8
# fdox-visuals).
ROLE_COLORS = [
    "#004473",  # FDO_BLUE
    "#0E9488",  # TEAL
    "#8034C9",  # PURPLE
    "#C2790C",  # ORANGE
]

# Roles worth naming individually get this preferred order first; anything
# else (rare/custom roles from classification_rules.yaml) is appended
# after, alphabetically, so the diagram is deterministic regardless of the
# role vocabulary a given fdo_type happens to use.
ROLE_ORDER = [
    "metadata",
    "model",
    "documentation",
    "data",
    "software",
    "script",
    "configuration",
    "result",
    "auxiliary",
]

# Roles with more files than this get grouped by their top-level directory
# instead of listed file-by-file - a 3DHOP viewer bundle alone is ~24
# files, and listing each one is noise, not information (Flo, S8).
GROUP_THRESHOLD = 6

# fdo-squirrel's own output filenames - if these show up as *package*
# content, the input was almost certainly an already-finished
# <slug>-fdo-bundle.zip fed back in as a fresh --package (rather than the
# pre-bundle package fdo-3d-packager's own `bundle` step produces),
# carrying a previous run's own output along as if it were package
# content. Excluded here rather than shown as "documentation"/"data" -
# found testing S8 against a real, already-finished CIIC 81 bundle
# (Flo, PRIMER.md).
FDO_SQUIRREL_OWN_FILES = {
    "fdo-metadata.ttl",
    "rdf_modelling_report.json",
    "rdf_modelling_report.html",
    "fdox.yaml",
    "fdo_overview.mermaid",
    "fdo_overview.jpg",
    "fdo_overview.png",  # older naming convention, found in Flo's local raw-fdo test zip
    "fdo_files_roles_graph.svg",
    "fdo_files_roles_graph.png",
    "fdo_md_cff.svg",
    "fdo_md_cff.png",
    "fdo_md_cff_graph.svg",
    "fdo_md_cff_graph.png",
    "fdo_ttl_snippet_metadata.svg",
    "fdo_ttl_snippet_metadata.png",
    "fdo_ttl_snippet_metadata.jpg",
    "fdo_ttl_snippet_distributions.svg",
    "fdo_ttl_snippet_distributions.png",
    "fdo_ttl_snippet_distributions.jpg",
    "fdo_ttl_snippet_links.svg",
    "fdo_ttl_snippet_links.png",
    "fdo_ttl_snippet_links.jpg",
}


def extract_distributions(raw_ttl: str) -> List[Tuple[str, str]]:
    """Returns a sorted, deduplicated list of (path, role) pairs, with
    fdo-squirrel's own known output filenames filtered out (see
    FDO_SQUIRREL_OWN_FILES)."""
    dist_blocks = re.findall(
        r'<urn:fdo-squirrel:dist/[^>]+>\s+a\s+dcat:Distribution.*?fdo:sha256\s+"[^"]*"\s*\.',
        raw_ttl,
        re.DOTALL,
    )
    seen: set[Tuple[str, str]] = set()
    for block in dist_blocks:
        path_m = re.search(r'fdo:path\s+"([^"]+)"', block)
        role_m = re.search(r'fdo:role\s+"([^"]+)"', block)
        if path_m and role_m:
            path = path_m.group(1)
            if Path(path).name.lower() in FDO_SQUIRREL_OWN_FILES:
                continue
            seen.add((path, role_m.group(1)))
    return sorted(seen)


def group_for_display(paths: List[str]) -> List[str]:
    """Either the individual filenames (short list) or one summary line
    per top-level directory (long list, PRIMER.md S8)."""
    if len(paths) <= GROUP_THRESHOLD:
        return sorted(Path(p).name for p in paths)

    by_dir: Dict[str, int] = defaultdict(int)
    top_level: List[str] = []
    for p in paths:
        parts = Path(p).parts
        if len(parts) > 1:
            by_dir[parts[0] + "/"] += 1
        else:
            top_level.append(p)
    lines = [f"{d} \u2014 {n} file{'s' if n != 1 else ''}" for d, n in sorted(by_dir.items())]
    lines += sorted(top_level)
    return lines
