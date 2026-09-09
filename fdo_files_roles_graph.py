"""fdo_files_roles_graph.py — "Files and Roles" as a node graph: each
file (or, for a role with many files, a grouped summary) as its own box,
connected by curved arrows to a shared, coloured role node. The
graph-style sibling to fdo_files_roles_common.py's data - which used to
back a fact-sheet layout too (fdo_files_roles_diagram.py), dropped in
S15 after Flo compared it side by side with this graph and found it
added nothing the graph didn't already show more clearly.

Reuses fdo_files_roles_common's extraction/grouping logic rather than
re-deriving it, so the two styles can never silently disagree about
which files exist or how they're grouped.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from fdo_files_roles_common import (
    GROUP_THRESHOLD,
    ROLE_COLORS,
    ROLE_ORDER,
    extract_distributions,
    group_for_display,
)
from fdo_visuals_utils import (
    BG,
    FDO_BLUE,
    INK,
    MUTED,
    arrow_marker_defs,
    curved_connector,
    esc,
    font_face_css,
    render_svg_to_png,
    truncate,
)


def build_svg(raw_ttl: str, title: str) -> Tuple[str, int, int]:
    by_role: Dict[str, List[str]] = defaultdict(list)
    for path, role in extract_distributions(raw_ttl):
        by_role[role].append(path)

    ordered_roles = [r for r in ROLE_ORDER if r in by_role]
    ordered_roles += sorted(r for r in by_role if r not in ROLE_ORDER)

    file_box_w, file_box_h, file_gap = 320, 46, 12
    pill_w, pill_h = 190, 46
    left_x = 60
    right_x = 620
    y = 140

    body: List[str] = []
    for i, role in enumerate(ordered_roles):
        color = ROLE_COLORS[i % len(ROLE_COLORS)]
        paths = by_role[role]
        display_lines = group_for_display(paths)

        block_top = y
        for dl in display_lines:
            body.append(
                f'<rect x="{left_x}" y="{y}" width="{file_box_w}" height="{file_box_h}" '
                f'rx="8" fill="white" stroke="{color}" stroke-width="2"/>'
            )
            body.append(
                f'<text x="{left_x + 16}" y="{y + file_box_h / 2 + 6}" '
                f'font-family="Fira Sans" font-weight="400" font-size="16" fill="{INK}">'
                f"{esc(truncate(dl, 34))}</text>"
            )
            body.append(
                curved_connector(
                    left_x + file_box_w,
                    y + file_box_h / 2,
                    right_x,
                    block_top + (len(display_lines) * (file_box_h + file_gap) - file_gap) / 2,
                    color=color,
                )
            )
            y += file_box_h + file_gap
        block_bottom = y - file_gap
        pill_y = (block_top + block_bottom) / 2 - pill_h / 2

        body.append(
            f'<rect x="{right_x}" y="{pill_y}" width="{pill_w}" height="{pill_h}" '
            f'rx="{pill_h / 2}" fill="{color}"/>'
        )
        body.append(
            f'<text x="{right_x + pill_w / 2}" y="{pill_y + pill_h / 2 + 6}" '
            f'text-anchor="middle" font-family="Fira Sans" font-weight="700" '
            f'font-size="18" fill="white">{esc(role.upper())}</text>'
        )

        y += 34  # gap between role blocks

    width = right_x + pill_w + 60
    height = y + 20

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        font_face_css(),
        f"<defs>{arrow_marker_defs()}</defs>",
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="{BG}"/>',
        f'<text x="60" y="56" font-family="Fira Sans" font-weight="700" '
        f'font-size="34" fill="{FDO_BLUE}">Files and Roles</text>',
        f'<text x="60" y="90" font-family="Fira Sans" font-weight="400" '
        f'font-size="20" fill="{MUTED}">{esc(truncate(title, 70))}</text>',
    ]
    svg.extend(body)
    svg.append("</svg>")
    return "\n".join(svg), width, height


def write_files_roles_graph(ttl_path: Path, title: str, output_svg: Path) -> Path:
    raw_ttl = ttl_path.read_text(encoding="utf-8")
    svg, width, height = build_svg(raw_ttl, title)
    output_svg.write_text(svg, encoding="utf-8")

    try:
        render_svg_to_png(
            output_svg, output_svg.with_suffix(".png"), width=width, height=height
        )
    except ImportError:
        pass

    return output_svg
