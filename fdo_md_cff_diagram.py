"""fdo_md_cff_diagram.py — "MD.cff filled out": the ingested MD.cff as a
populated fact sheet, real values instead of field names (S8, PRIMER.md).
Structurally related to fdox-visuals' MD.cff schema diagram (S5 there),
but that one draws the *schema* (field names/types); this one draws one
specific, real MD.cff's *content*.

Deterministic by construction: field order is fixed by _SECTIONS below,
never by dict iteration order, and nothing here reads a clock.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    esc,
    font_face_css,
    render_svg_to_png,
    truncate,
    wrap_text,
)


def _id_label_str(v: Any) -> Optional[str]:
    if isinstance(v, dict):
        label = v.get("label")
        id_ = v.get("id")
        if label and id_:
            return f"{label}  ({id_})"
        return label or id_
    if isinstance(v, str):
        return v
    return None


def _list_of_id_label(v: Any) -> List[str]:
    if not isinstance(v, list):
        return []
    out = []
    for item in v:
        s = _id_label_str(item)
        if s:
            out.append(s)
    return out


def _rows_core(md: Dict[str, Any]) -> List[Tuple[str, str]]:
    rows = []
    for key, label in (
        ("id", "id"),
        ("title", "title"),
        ("description", "description"),
        ("fdo_type", "fdo_type"),
        ("version", "version"),
        ("date_created", "date_created"),
        ("date_released", "date_released"),
        ("date_modified", "date_modified"),
    ):
        v = md.get(key)
        if v is None:
            continue
        if isinstance(v, list):
            v = ", ".join(str(x) for x in v)
        rows.append((label, str(v)))
    return rows


def _rows_agents(md: Dict[str, Any]) -> List[Tuple[str, str]]:
    rows = []
    for key, label in (
        ("publishers", "publishers"),
        ("creators", "creators"),
        ("contributors", "contributors"),
    ):
        items = _list_of_id_label(md.get(key))
        if items:
            rows.append((label, "; ".join(items)))
    funding = md.get("funding")
    if funding:
        if isinstance(funding, list):
            funding = ", ".join(str(x) for x in funding)
        rows.append(("funding", str(funding)))
    return rows


def _rows_classification(md: Dict[str, Any]) -> List[Tuple[str, str]]:
    rows = []
    license_ = _id_label_str(md.get("license"))
    if license_:
        rows.append(("license", license_))
    keywords = _list_of_id_label(md.get("keywords"))
    if keywords:
        rows.append(("keywords", ", ".join(keywords)))
    identifiers = md.get("identifiers")
    if isinstance(identifiers, list) and identifiers:
        parts = []
        for ident in identifiers:
            if isinstance(ident, dict):
                parts.append(f"{ident.get('label') or ident.get('scheme')}: {ident.get('value')}")
        if parts:
            rows.append(("identifiers", "; ".join(parts)))
    related = md.get("related_resources")
    if isinstance(related, list) and related:
        parts = []
        for r in related:
            if isinstance(r, dict):
                target = _id_label_str(r.get("target"))
                if target:
                    parts.append(f"{r.get('relation')}: {target}")
        if parts:
            rows.append(("related_resources", "; ".join(parts)))
    return rows


def _rows_space_time(md: Dict[str, Any]) -> List[Tuple[str, str]]:
    rows = []
    spatial = md.get("spatial")
    if isinstance(spatial, dict):
        label = spatial.get("label") or ""
        coords = ""
        if spatial.get("lat") is not None and spatial.get("lon") is not None:
            coords = f" ({spatial['lat']}, {spatial['lon']})"
        rows.append(("spatial", f"{label}{coords}".strip() or str(spatial.get("id", ""))))
    temporal = md.get("temporal")
    if isinstance(temporal, dict):
        label = temporal.get("label") or ""
        span = ""
        if temporal.get("start") is not None or temporal.get("end") is not None:
            span = f" ({temporal.get('start', '?')}\u2013{temporal.get('end', '?')})"
        rows.append(("temporal", f"{label}{span}".strip()))
    return rows


def _rows_heritage_technique(md: Dict[str, Any]) -> List[Tuple[str, str]]:
    rows = []
    ho = md.get("heritage_object")
    if isinstance(ho, dict):
        for key, label in (
            ("object_type", "object_type"),
            ("monument", "monument"),
            ("material", "material"),
        ):
            s = _id_label_str(ho.get(key))
            if s:
                rows.append((label, s))
        for key in ("context", "documentation_purpose", "overall_condition", "conservation_urgency"):
            v = ho.get(key)
            if v:
                rows.append((key, str(v)))
    tech = md.get("technique")
    if isinstance(tech, dict):
        acq = tech.get("acquisition")
        if isinstance(acq, dict):
            parts = [f"{k}: {v}" for k, v in acq.items() if v]
            if parts:
                rows.append(("acquisition", "; ".join(parts)))
        proc = tech.get("processing")
        if isinstance(proc, dict):
            parts = [f"{k}: {v}" for k, v in proc.items() if v]
            if parts:
                rows.append(("processing", "; ".join(parts)))
        elif isinstance(proc, str) and proc:
            rows.append(("processing", proc))
    return rows


_SECTIONS = [
    ("Core", FDO_BLUE, FDO_BLUE_TINT, _rows_core),
    ("Agents", TEAL, TEAL_TINT, _rows_agents),
    ("Classification", PURPLE, PURPLE_TINT, _rows_classification),
    ("Space & Time", ORANGE, ORANGE_TINT, _rows_space_time),
    ("Heritage Object & Technique", FDO_BLUE, FDO_BLUE_TINT, _rows_heritage_technique),
]


def build_svg(md: Dict[str, Any], title: str) -> Tuple[str, int, int]:
    width = 980
    x_margin = 40
    panel_w = width - 2 * x_margin
    y = 130
    row_h = 26
    label_w = 232
    value_max_chars = 78

    body: List[str] = []
    for name, color, tint, rows_fn in _SECTIONS:
        rows = rows_fn(md)
        if not rows:
            continue

        wrapped_rows: List[Tuple[str, List[str]]] = []
        for label, value in rows:
            wrapped_rows.append((label, wrap_text(value, value_max_chars)))

        content_lines = sum(len(v) for _, v in wrapped_rows)
        panel_h = 50 + content_lines * row_h + 14

        body.append(
            f'<rect x="{x_margin}" y="{y}" width="{panel_w}" height="{panel_h}" '
            f'rx="16" fill="{tint}" stroke="{color}" stroke-width="2.5"/>'
        )
        body.append(
            f'<text x="{x_margin + 20}" y="{y + 32}" font-family="Fira Sans" '
            f'font-weight="700" font-size="22" fill="{color}">{esc(name)}</text>'
        )

        ry = y + 62
        for label, value_lines in wrapped_rows:
            body.append(
                f'<text x="{x_margin + 20}" y="{ry}" font-family="Fira Sans" '
                f'font-weight="700" font-size="16" fill="{color}">{esc(label)}</text>'
            )
            for i, vline in enumerate(value_lines):
                body.append(
                    f'<text x="{x_margin + label_w}" y="{ry + i * row_h}" '
                    f'font-family="Fira Sans" font-weight="400" font-size="16" '
                    f'fill="{INK}">{esc(vline)}</text>'
                )
            ry += len(value_lines) * row_h

        y += panel_h + 20

    height = y + 20

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        font_face_css(),
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="{BG}"/>',
        f'<text x="{x_margin}" y="56" font-family="Fira Sans" font-weight="700" '
        f'font-size="34" fill="{FDO_BLUE}">MD.cff, filled out</text>',
        f'<text x="{x_margin}" y="90" font-family="Fira Sans" font-weight="400" '
        f'font-size="20" fill="{MUTED}">{esc(truncate(title, 76))}</text>',
    ]
    svg.extend(body)
    svg.append("</svg>")
    return "\n".join(svg), width, height


def write_md_cff_diagram(md: Dict[str, Any], title: str, output_svg: Path) -> Path:
    svg, width, height = build_svg(md, title)
    output_svg.write_text(svg, encoding="utf-8")

    try:
        render_svg_to_png(
            output_svg, output_svg.with_suffix(".png"), width=width, height=height
        )
    except ImportError:
        pass  # resvg-py not installed - SVG still written, PNG best-effort only

    return output_svg
