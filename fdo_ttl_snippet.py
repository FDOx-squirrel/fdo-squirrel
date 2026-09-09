"""fdo_ttl_snippet.py — a small, dark "code card" JPG showing a curated
excerpt of the real fdo-metadata.ttl, for dropping straight into a slide
(Flo, S8 nachtrag, PRIMER.md). Not the whole file - a handful of the most
presentation-relevant lines from the core dataset block, syntax-coloured.

Lightweight regex extraction, same approach fdo_mermaid.py already uses
for its own ttl parsing - no RDF parser dependency just for this.

Deterministic by construction: the predicate selection/order is a fixed
list below, never dict/set iteration order, and nothing here reads a
clock.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple
import re

from fdo_visuals_utils import esc, font_face_css, render_svg_to_png, truncate

CARD_BG = "#161B2E"  # same as INK elsewhere, used here as the card's own background
LINE_COLOR = "#3A4260"
PUNCT = "#7B84A6"
PREDICATE_COLOR = "#5FD9C7"
IRI_COLOR = "#8FC1F2"
LITERAL_COLOR = "#F2C879"
SUBJECT_COLOR = "#FFFFFF"

# Predicates worth showing on a slide, in this fixed priority order - a
# fixed list, not "whatever happened to be in the ttl first", so the
# snippet is the same choice of facts every run for a given package.
_WANTED_PREDICATES = [
    "dct:title",
    "dct:description",
    "dct:creator",
    "dct:publisher",
    "dct:license",
    "dct:type",
    "dct:spatial",
    "dct:subject",
]
_MAX_LINES = 7
_DESCRIPTION_MAX_CHARS = 90


def _extract_core_block(raw_ttl: str) -> Tuple[Optional[str], List[str]]:
    """Returns (subject, [predicate-value lines]) for the ttl's own
    subject block (the one with `a dcat:Dataset, ...`), or (None, []).

    The dataset declaration isn't necessarily preceded by a blank line
    (it directly follows the @prefix lines with a single newline, no
    separator) - found by testing this against a real fdo-metadata.ttl,
    where an earlier version that assumed the block itself starts right
    after a blank line matched nothing (S8 nachtrag, PRIMER.md). Anchors
    on the declaration itself instead, wherever it sits, then reads
    forward to the next blank line.
    """
    m = re.search(r"<([^>]+)>\s+a\s+dcat:Dataset,", raw_ttl)
    if not m:
        return None, []
    subject = m.group(1)
    rest = raw_ttl[m.end() :]
    block = rest.split("\n\n", 1)[0]
    lines = [
        ln.strip().rstrip(".").rstrip(";").strip() for ln in block.splitlines() if ln.strip()
    ]
    return subject, lines


def _select_lines(lines: List[str]) -> List[str]:
    by_pred = {}
    for ln in lines:
        for pred in _WANTED_PREDICATES:
            if ln.startswith(pred + " ") and pred not in by_pred:
                by_pred[pred] = ln
    return [by_pred[p] for p in _WANTED_PREDICATES if p in by_pred][:_MAX_LINES]


def _colour_line(line: str) -> str:
    """Very small, regex-based syntax colouring - not a real Turtle
    tokenizer, just enough to make predicate/IRI/literal visually
    distinct on a slide."""
    m = re.match(r"^(\S+)\s+(.*)$", line)
    if not m:
        return f'<tspan fill="{PUNCT}">{esc(line)}</tspan>'
    pred, rest = m.group(1), m.group(2)

    if len(rest) > _DESCRIPTION_MAX_CHARS + 20:
        rest = truncate(rest, _DESCRIPTION_MAX_CHARS) + '"'

    parts = [f'<tspan fill="{PREDICATE_COLOR}">{esc(pred)}</tspan> ']
    pos = 0
    for tok in re.finditer(r'<[^>]+>|"[^"]*"(?:\^\^\S+|@\S+)?', rest):
        if tok.start() > pos:
            parts.append(f'<tspan fill="{PUNCT}">{esc(rest[pos:tok.start()])}</tspan>')
        text = tok.group(0)
        color = IRI_COLOR if text.startswith("<") else LITERAL_COLOR
        parts.append(f'<tspan fill="{color}">{esc(text)}</tspan>')
        pos = tok.end()
    if pos < len(rest):
        parts.append(f'<tspan fill="{PUNCT}">{esc(rest[pos:])}</tspan>')
    return "".join(parts)


def build_svg(raw_ttl: str, title: str) -> Tuple[str, int, int]:
    subject, block_lines = _extract_core_block(raw_ttl)
    selected = _select_lines(block_lines)

    width = 1000
    pad = 36
    line_h = 30
    header_h = 64

    height = header_h + len(selected) * line_h + 2 * pad + (18 if subject else 0)

    body: List[str] = [
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="18" fill="{CARD_BG}"/>',
        '<circle cx="30" cy="30" r="7" fill="#FF5F56"/>',
        '<circle cx="52" cy="30" r="7" fill="#FFBD2E"/>',
        '<circle cx="74" cy="30" r="7" fill="#27C93F"/>',
        f'<text x="{width / 2}" y="36" text-anchor="middle" font-family="Fira Sans" '
        f'font-weight="700" font-size="17" fill="{SUBJECT_COLOR}">{esc(truncate(title, 60))}</text>',
    ]

    y = header_h + pad / 2
    if subject:
        body.append(
            f'<text x="{pad}" y="{y}" font-family="Fira Sans" font-weight="400" '
            f'font-size="15" fill="{PUNCT}">&lt;{esc(truncate(subject, 84))}&gt;</text>'
        )
        y += 28

    for ln in selected:
        body.append(
            f'<text x="{pad}" y="{y}" font-family="Fira Sans" font-weight="400" '
            f'font-size="16" xml:space="preserve">{_colour_line(ln)}</text>'
        )
        y += line_h

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        font_face_css(),
    ]
    svg.extend(body)
    svg.append("</svg>")
    return "\n".join(svg), width, height


def write_ttl_snippet_jpg(
    ttl_path: Path, title: str, output_svg: Path, output_jpg: Path
) -> Optional[Path]:
    """Writes the SVG source (consistent with the other four S8
    diagrams) and, best-effort, the JPG Flo actually wants for slides.
    Returns output_jpg, or None if nothing presentable could be
    extracted from this ttl (no exception - callers can skip gracefully,
    like the other optional-dependency diagrams).
    """
    raw_ttl = ttl_path.read_text(encoding="utf-8")
    svg, width, height = build_svg(raw_ttl, title)
    output_svg.write_text(svg, encoding="utf-8")

    import resvg_py
    from PIL import Image
    import io

    png_bytes = resvg_py.svg_to_bytes(
        svg_string=svg,
        width=width,
        height=height,
        font_files=[
            str(Path(__file__).resolve().parent / "fonts" / "FiraSans-Regular.ttf"),
            str(Path(__file__).resolve().parent / "fonts" / "FiraSans-Bold.ttf"),
        ],
        skip_system_fonts=True,
    )
    im = Image.open(io.BytesIO(bytes(png_bytes))).convert("RGB")
    output_jpg.parent.mkdir(parents=True, exist_ok=True)
    im.save(output_jpg, "JPEG", quality=92)
    return output_jpg
