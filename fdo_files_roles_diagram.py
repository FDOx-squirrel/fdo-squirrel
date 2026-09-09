"""fdo_files_roles_diagram.py — "Files and Roles": which file in the
package got which fdo:role (S8, PRIMER.md). Reads the already-written
fdo-metadata.ttl with the same lightweight regex approach fdo_mermaid.py
already uses for its own distribution parsing, rather than adding an RDF
parser dependency just for this.

Deterministic by construction: every list this module builds is sorted
before it is drawn, and nothing here reads a clock.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple
import re

from fdo_visuals_utils import (
    BG,
    FDO_BLUE,
    INK,
    MUTED,
    TEAL,
    TEAL_TINT,
    esc,
    font_face_css,
    render_svg_to_png,
    truncate,
)

# A handful of family-palette colours, cycled across roles so each role
# gets a distinct badge without inventing a new colour per role - four is
# already the full palette fdox-visuals defines (PRIMER.md, S2/S8
# fdox-visuals).
_ROLE_COLORS = [
    "#004473",  # FDO_BLUE
    "#0E9488",  # TEAL
    "#8034C9",  # PURPLE
    "#C2790C",  # ORANGE
]

# Roles worth naming individually get this preferred order first; anything
# else (rare/custom roles from classification_rules.yaml) is appended
# after, alphabetically, so the diagram is deterministic regardless of the
# role vocabulary a given fdo_type happens to use.
_ROLE_ORDER = [
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
_GROUP_THRESHOLD = 6


def _extract_distributions(raw_ttl: str) -> List[Tuple[str, str]]:
    """Returns a sorted, deduplicated list of (path, role) pairs."""
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
            seen.add((path_m.group(1), role_m.group(1)))
    return sorted(seen)


def _group_for_display(paths: List[str]) -> List[str]:
    """Either the individual filenames (short list) or one summary line
    per top-level directory (long list, PRIMER.md S8)."""
    if len(paths) <= _GROUP_THRESHOLD:
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


def build_svg(raw_ttl: str, title: str) -> Tuple[str, int, int]:
    by_role: Dict[str, List[str]] = defaultdict(list)
    for path, role in _extract_distributions(raw_ttl):
        by_role[role].append(path)

    ordered_roles = [r for r in _ROLE_ORDER if r in by_role]
    ordered_roles += sorted(r for r in by_role if r not in _ROLE_ORDER)

    width = 900
    x_margin = 40
    y = 130
    section_gap = 22
    line_h = 30

    body: List[str] = []
    for i, role in enumerate(ordered_roles):
        color = _ROLE_COLORS[i % len(_ROLE_COLORS)]
        paths = by_role[role]
        display_lines = _group_for_display(paths)

        badge_w = 18 + 11 * len(role)
        body.append(
            f'<rect x="{x_margin}" y="{y}" width="{badge_w}" height="34" rx="17" '
            f'fill="{color}"/>'
        )
        body.append(
            f'<text x="{x_margin + badge_w / 2}" y="{y + 23}" text-anchor="middle" '
            f'font-family="Fira Sans" font-weight="700" font-size="17" fill="white">'
            f"{esc(role)}</text>"
        )
        body.append(
            f'<text x="{x_margin + badge_w + 16}" y="{y + 23}" '
            f'font-family="Fira Sans" font-weight="400" font-size="17" fill="{MUTED}">'
            f"{len(paths)} file{'s' if len(paths) != 1 else ''}</text>"
        )
        y += 34 + 14

        for dl in display_lines:
            body.append(
                f'<circle cx="{x_margin + 10}" cy="{y - 7}" r="3.5" fill="{color}"/>'
            )
            body.append(
                f'<text x="{x_margin + 26}" y="{y}" '
                f'font-family="Fira Sans" font-weight="400" font-size="17" fill="{INK}">'
                f"{esc(truncate(dl, 78))}</text>"
            )
            y += line_h
        y += section_gap

    height = y + 30

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        font_face_css(),
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="{BG}"/>',
        f'<text x="{x_margin}" y="56" font-family="Fira Sans" font-weight="700" '
        f'font-size="34" fill="{FDO_BLUE}">Files and Roles</text>',
        f'<text x="{x_margin}" y="90" font-family="Fira Sans" font-weight="400" '
        f'font-size="20" fill="{MUTED}">{esc(truncate(title, 70))}</text>',
        f'<line x1="{x_margin}" y1="106" x2="{width - x_margin}" y2="106" '
        f'stroke="{TEAL_TINT}" stroke-width="2"/>',
    ]
    svg.extend(body)
    svg.append("</svg>")
    return "\n".join(svg), width, height


def write_files_roles_diagram(ttl_path: Path, title: str, output_svg: Path) -> Path:
    raw_ttl = ttl_path.read_text(encoding="utf-8")
    svg, width, height = build_svg(raw_ttl, title)
    output_svg.write_text(svg, encoding="utf-8")

    try:
        render_svg_to_png(
            output_svg, output_svg.with_suffix(".png"), width=width, height=height
        )
    except ImportError:
        pass  # resvg-py not installed - SVG still written, PNG best-effort only

    return output_svg
