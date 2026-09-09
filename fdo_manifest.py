"""
fdo_manifest.py — writes FDOx.yaml, a short, human-readable "how was this
FDO built" summary alongside fdo-metadata.ttl (Flo, 2026-09-09).

Distinct from rdf_modelling_report.json/.html: those track per-field RDF
provenance (which MD.cff/CITATION.cff/ZIP field mapped to which RDF
property, with examples). FDOx.yaml is a build manifest instead - which
software (and what version) produced this FDO, and, best-effort, which
upstream tool likely produced the *package* fdo-squirrel was handed. It
is fed from rdf_modelling_report.json rather than duplicating the
provenance tracker's bookkeeping.

Deliberately no wall-clock timestamp anywhere in here - this file becomes
a dcat:Distribution and gets hashed like everything else in
build_generated_distributions_ttl(); a build time would reintroduce the
non-determinism S4 removed (PRIMER.md).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import json
import zipfile
import yaml


def _detect_source_tool(zip_path: Optional[Path]) -> Dict[str, Any]:
    """
    Best-effort, structural guess at which tool produced the *input*
    package. fdo-squirrel has no direct knowledge of anything upstream of
    itself - it never sees fdo-3d-packager, Blender or nexus run - but a
    3DHOP viewer bundle plus Nexus multiresolution files is a distinctive
    enough combination that nothing else in this family builds a package
    that way. Confidence is reported as "heuristic", never "confirmed" -
    this is an inference from file layout, not something fdo-squirrel can
    actually verify.
    """
    if not zip_path or not Path(zip_path).exists():
        return {
            "name": None,
            "confidence": "unknown",
            "reason": "package not available for inspection",
        }
    try:
        with zipfile.ZipFile(zip_path) as z:
            names = z.namelist()
    except Exception:
        return {"name": None, "confidence": "unknown", "reason": "could not open package"}

    has_3dhop_viewer = (
        any(n.endswith("viewer/index.html") for n in names)
        and any(n.endswith("viewer/js/nexus.js") for n in names)
    )
    has_nexus_model = any(n.endswith(".nxs") or n.endswith(".nxz") for n in names)

    if has_3dhop_viewer and has_nexus_model:
        return {
            "name": "fdo-3d-packager",
            "confidence": "heuristic",
            "reason": (
                "viewer/ contains a 3DHOP viewer (index.html, js/nexus.js) "
                "and data/model/ contains Nexus .nxs/.nxz files - no other "
                "tool in this family builds a package that way"
            ),
        }
    return {"name": None, "confidence": "unknown", "reason": "no recognised structural pattern"}


def write_fdox_yaml(
    output_path: Path,
    cw: Any,
    json_report_path: Optional[Path],
    info: Dict[str, Any],
    fdo_squirrel_version: str,
) -> Path:
    """
    Write FDOx.yaml to output_path. Returns output_path.
    """
    report: Dict[str, Any] = {}
    if json_report_path and Path(json_report_path).exists():
        try:
            report = json.loads(Path(json_report_path).read_text(encoding="utf-8"))
        except Exception:
            report = {}

    summary = report.get("summary", {})
    sources_seen = sorted(
        {s for v in summary.values() for s in v.get("sources", []) if isinstance(v, dict)}
    )

    package_local_path = info.get("package_local_path")
    source_tool = _detect_source_tool(
        Path(package_local_path) if package_local_path else None
    )

    manifest: Dict[str, Any] = {
        "generator": {
            "name": "fdo-squirrel",
            "version": fdo_squirrel_version,
            "repository": "https://github.com/FDOx-squirrel/fdo-squirrel",
        },
        "source_package": {
            "file": Path(str(info.get("package_source", ""))).name or None,
            "likely_built_by": source_tool["name"],
            "likely_built_by_confidence": source_tool["confidence"],
            "likely_built_by_reason": source_tool["reason"],
        },
        "fdo": {
            "id": getattr(cw, "id", None),
            "fdo_type": getattr(cw, "fdo_type", None),
            "title": getattr(cw, "title", None),
        },
        "metadata_sources": sources_seen,
    }

    output_path.write_text(
        yaml.dump(
            manifest,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )
    return output_path
