"""fdo_md_cff_graph.py — "MD.cff, filled out" as a node graph: one
central MD_cff node carrying the scalar core fields, surrounded by
satellite boxes for every populated nested group (keywords, license,
publishers, creators, identifiers, spatial, temporal, heritage object,
technique), connected by curved arrows. The graph-style sibling to
fdo_md_cff_diagram.py's fact-sheet layout - Flo wanted both (S8,
PRIMER.md), not one replacing the other.

Reuses fdo_md_cff_diagram's field-extraction helpers so the two styles
can never silently disagree about what a given MD.cff actually contains.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from fdo_md_cff_diagram import (
    _rows_agents,
    _rows_classification,
    _rows_core,
    _rows_heritage_technique,
    _rows_space_time,
)
from fdo_visuals_utils import (
    BG,
    FDO_BLUE,
    FDO_BLUE_TINT,
    INK,
    MUTED,
    ORANGE,
    ORANGE_TINT,
    PURPLE,
    PURPLE_TINT,
    TEAL,
    TEAL_TINT,
    arrow_marker_defs,
    curved_connector,
    esc,
    font_face_css,
    render_svg_to_png,
    truncate,
    wrap_text,
)

_SATELLITES = [
    ("Agents", TEAL, TEAL_TINT, _rows_agents),
    ("Classification", PURPLE, PURPLE_TINT, _rows_classification),
    ("Space & Time", ORANGE, ORANGE_TINT, _rows_space_time),
    ("Heritage Object\n& Technique", FDO_BLUE, FDO_BLUE_TINT, _rows_heritage_technique),
]

_SAT_W = 340
_ROW_H = 22
_VALUE_MAX_CHARS = 36


def _satellite_box(x: float, y: float, name: str, color: str, tint: str, rows) -> Tuple[str, float]:
    wrapped = [(label, wrap_text(value, _VALUE_MAX_CHARS)) for label, value in rows]
    # +1 per row for the label's own line, which the loop below draws
    # separately before its value line(s) - omitting it here undercounts
    # the box height and lets later rows run past the bottom edge (found
    # rendering CIIC 81's real MD.cff, S8, PRIMER.md).
    n_lines = sum(1 + len(v) for _, v in wrapped)
    title_lines = name.split("\n")
    h = 34 + len(title_lines) * 22 + n_lines * _ROW_H + 14

    parts = [
        f'<rect x="{x}" y="{y}" width="{_SAT_W}" height="{h}" rx="12" '
        f'fill="{tint}" stroke="{color}" stroke-width="2.2"/>'
    ]
    ty = y + 26
    for tl in title_lines:
        parts.append(
            f'<text x="{x + 16}" y="{ty}" font-family="Fira Sans" font-weight="700" '
            f'font-size="18" fill="{color}">{esc(tl)}</text>'
        )
        ty += 22
    ty += 6
    for label, value_lines in wrapped:
        parts.append(
            f'<text x="{x + 16}" y="{ty}" font-family="Fira Sans" font-weight="700" '
            f'font-size="13" fill="{color}">{esc(label)}</text>'
        )
        ty += _ROW_H
        for vline in value_lines:
            parts.append(
                f'<text x="{x + 16}" y="{ty}" font-family="Fira Sans" font-weight="400" '
                f'font-size="13" fill="{INK}">{esc(vline)}</text>'
            )
            ty += _ROW_H
    return "\n".join(parts), h


def build_svg(md: Dict[str, Any], title: str) -> Tuple[str, int, int]:
    core_rows = _rows_core(md)
    satellites = [
        (name, color, tint, rows_fn(md))
        for name, color, tint, rows_fn in _SATELLITES
    ]
    satellites = [s for s in satellites if s[3]]  # drop empty groups

    left_sats = satellites[0::2]
    right_sats = satellites[1::2]

    center_w = 380
    col_gap = 90
    left_x = 40
    center_x = left_x + _SAT_W + col_gap
    right_x = center_x + center_w + col_gap
    y0 = 140

    # Central MD_cff node
    core_wrapped = [(label, wrap_text(value, 30)) for label, value in core_rows]
    core_lines = sum(len(v) for _, v in core_wrapped)
    center_h = 46 + core_lines * _ROW_H + 14

    body: List[str] = []

    def render_column(sats, x):
        parts = []
        boxes = []
        y = y0
        for name, color, tint, rows in sats:
            svg_box, h = _satellite_box(x, y, name, color, tint, rows)
            parts.append(svg_box)
            boxes.append((y, h, color))
            y += h + 30
        return "\n".join(parts), boxes, y

    left_svg, left_boxes, left_end_y = render_column(left_sats, left_x)
    right_svg, right_boxes, right_end_y = render_column(right_sats, right_x)

    content_bottom = max(left_end_y, right_end_y, y0 + center_h)
    center_y = y0 + max(0, (content_bottom - y0 - center_h) / 2)

    body.append(left_svg)
    body.append(right_svg)

    body.append(
        f'<rect x="{center_x}" y="{center_y}" width="{center_w}" height="{center_h}" '
        f'rx="14" fill="{FDO_BLUE}"/>'
    )
    ty = center_y + 30
    body.append(
        f'<text x="{center_x + center_w / 2}" y="{ty}" text-anchor="middle" '
        f'font-family="Fira Sans" font-weight="700" font-size="20" fill="white">MD_cff</text>'
    )
    ty += 28
    for label, value_lines in core_wrapped:
        body.append(
            f'<text x="{center_x + 18}" y="{ty}" font-family="Fira Sans" font-weight="700" '
            f'font-size="13" fill="white">{esc(label)}</text>'
        )
        body.append(
            f'<text x="{center_x + 150}" y="{ty}" font-family="Fira Sans" font-weight="400" '
            f'font-size="13" fill="white">{esc(truncate(" / ".join(value_lines), 32))}</text>'
        )
        ty += _ROW_H

    for y, h, color in left_boxes:
        body.append(
            curved_connector(
                left_x + _SAT_W, y + h / 2, center_x, center_y + center_h / 2, color=color
            )
        )
    for y, h, color in right_boxes:
        body.append(
            curved_connector(
                right_x, y + h / 2, center_x + center_w, center_y + center_h / 2, color=color
            )
        )

    width = right_x + _SAT_W + 40
    height = int(content_bottom) + 30

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        font_face_css(),
        f"<defs>{arrow_marker_defs()}</defs>",
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="{BG}"/>',
        f'<text x="40" y="56" font-family="Fira Sans" font-weight="700" '
        f'font-size="34" fill="{FDO_BLUE}">MD.cff, filled out</text>',
        f'<text x="40" y="90" font-family="Fira Sans" font-weight="400" '
        f'font-size="20" fill="{MUTED}">{esc(truncate(title, 76))}</text>',
    ]
    svg.extend(body)
    svg.append("</svg>")
    return "\n".join(svg), width, height


def write_md_cff_graph(md: Dict[str, Any], title: str, output_svg: Path) -> Path:
    svg, width, height = build_svg(md, title)
    output_svg.write_text(svg, encoding="utf-8")

    try:
        render_svg_to_png(
            output_svg, output_svg.with_suffix(".png"), width=width, height=height
        )
    except ImportError:
        pass

    return output_svg
