"""fdo_ttl_snippet.py — small, dark "code card" JPGs showing real excerpts
of fdo-metadata.ttl, for dropping straight into a slide (Flo, S8/S15/S16
nachtrag, PRIMER.md). Three targeted cards instead of one generic one,
after Flo's feedback on the first version (too little content, resolution
too soft):

- **metadata**: the core dataset block, fuller than S15's first attempt
  (an exclude-list now, not a capped include-list - shows everything
  except the two lines that are unreadable on a slide anyway: the full
  dcat:distribution id list, and the JSON-in-a-literal dct:provenance
  blob).
- **distributions**: two or three real dcat:Distribution blocks in full,
  one per role where possible, so the shape of a Distribution entry
  (path/mediaType/byteSize/role/sha256) is visible, not just named.
- **links**: rdfs:label/owl:sameAs lines whose subject is a genuine
  external IRI (Wikidata, OpenStreetMap, ChronOntology, ORCID, SPDX,
  ...), not one of fdo-squirrel's own urn:fdo-squirrel: nodes - the
  "this joins a federated knowledge graph" story in one card.

Lightweight regex extraction throughout, same approach fdo_mermaid.py
already uses for its own ttl parsing - no RDF parser dependency just for
this.

Deterministic by construction: every selection below is a fixed rule
(an exclude-list, a fixed role order, file order) or an explicit sort,
never dict/set iteration order, and nothing here reads a clock.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

from fdo_visuals_utils import esc, font_face_css, truncate

CARD_BG = "#161B2E"  # same as INK elsewhere, used here as the card's own background
CARD_BG_RGB = (0x16, 0x1B, 0x2E)  # same colour, as an (r, g, b) tuple for PIL compositing
PUNCT = "#7B84A6"
PREDICATE_COLOR = "#5FD9C7"
IRI_COLOR = "#8FC1F2"
LITERAL_COLOR = "#F2C879"
SUBJECT_COLOR = "#FFFFFF"

# Rendered at this multiple of the SVG's own logical size - vector
# content, so this is free resolution, not raster upscaling. Flo found
# the first (1x) version too soft for a slide (S16 nachtrag, PRIMER.md).
RENDER_SCALE = 2.5

# --- metadata card -----------------------------------------------------

# Excluded rather than a capped include-list (S15's first version showed
# at most 7 predicates picked from a fixed wishlist; Flo wanted it fuller,
# not narrower). These two are the only lines that are actively bad on a
# slide: dcat:distribution is a long list of internal urn:fdo-squirrel:
# ids (shown properly in the distributions card instead), and
# dct:provenance is a JSON string crammed into a literal.
_METADATA_EXCLUDE_PREDICATES = {"dcat:distribution", "dct:provenance", "prov:wasGeneratedBy"}
_METADATA_MAX_LINES = 20
_VALUE_MAX_CHARS = 92

# --- distributions card -------------------------------------------------

_DIST_ROLE_ORDER = ["metadata", "model", "documentation", "data"]
_DIST_MAX_BLOCKS = 3

# --- links card -----------------------------------------------------

# fdo-squirrel's own minted namespace - a subject under any of these is
# an internal node, not a link into someone else's knowledge graph, so it
# doesn't belong on the "this joins a federated KG" card.
_OWN_NAMESPACE_PREFIXES = ("urn:fdo-squirrel:",)
_LINKS_MAX_LINES = 7


def _extract_core_block(raw_ttl: str) -> Tuple[Optional[str], List[str]]:
    """Returns (subject, [predicate-value lines]) for the ttl's own
    subject block (the one with `a dcat:Dataset, ...`), or (None, []).

    The dataset declaration isn't necessarily preceded by a blank line
    (it directly follows the @prefix lines with a single newline, no
    separator) - found by testing this against a real fdo-metadata.ttl,
    where an earlier version that assumed the block itself starts right
    after a blank line matched nothing (S15, PRIMER.md). Anchors on the
    declaration itself instead, wherever it sits, then reads forward to
    the next blank line.
    """
    m = re.search(r"<([^>]+)>\s+a\s+dcat:Dataset,", raw_ttl)
    if not m:
        return None, []
    subject = m.group(1)
    rest = raw_ttl[m.end() :]
    block = rest.split("\n\n", 1)[0]
    raw_lines = block.splitlines()
    # The first "line" here is actually the tail of the `a dcat:Dataset,
    # <more types> ;` declaration that started before m.end() - not a
    # real predicate-value pair, so it doesn't belong in a list of
    # lines meant to each read as "predicate: value" (found rendering a
    # real card: it showed up coloured as if crmdig:D1_Digital_Object
    # were a predicate, S16 nachtrag, PRIMER.md).
    lines = [
        ln.strip().rstrip(".").rstrip(";").strip() for ln in raw_lines[1:] if ln.strip()
    ]
    return subject, lines


def _select_metadata_lines(lines: List[str]) -> List[str]:
    out = []
    for ln in lines:
        pred = ln.split(" ", 1)[0]
        if pred in _METADATA_EXCLUDE_PREDICATES:
            continue
        out.append(ln)
    return out[:_METADATA_MAX_LINES]


def _extract_distribution_blocks(raw_ttl: str) -> List[Tuple[str, str, List[str]]]:
    """Returns [(subject, role, [raw predicate lines])] for every
    dcat:Distribution block, in file order."""
    out = []
    for block in re.findall(
        r"<urn:fdo-squirrel:dist/[^>]+>\s+a\s+dcat:Distribution.*?fdo:sha256\s+\"[^\"]*\"\s*\.",
        raw_ttl,
        re.DOTALL,
    ):
        subj_m = re.match(r"<([^>]+)>", block)
        role_m = re.search(r'fdo:role\s+"([^"]+)"', block)
        if not (subj_m and role_m):
            continue
        lines = [
            ln.strip().rstrip(".").rstrip(";").strip()
            for ln in block.splitlines()[1:]
            if ln.strip()
        ]
        out.append((subj_m.group(1), role_m.group(1), lines))
    return out


def _select_distribution_blocks(
    blocks: List[Tuple[str, str, List[str]]],
) -> List[Tuple[str, List[str]]]:
    by_role: Dict[str, Tuple[str, List[str]]] = {}
    for subj, role, lines in blocks:
        if role not in by_role:
            by_role[role] = (subj, lines)
    selected = [by_role[r] for r in _DIST_ROLE_ORDER if r in by_role]
    if len(selected) < _DIST_MAX_BLOCKS:
        for role, (subj, lines) in by_role.items():
            if role not in _DIST_ROLE_ORDER and len(selected) < _DIST_MAX_BLOCKS:
                selected.append((subj, lines))
    return selected[:_DIST_MAX_BLOCKS]


# Domains worth leading with on the "this joins a federated knowledge
# graph" card, in priority order - genuine, well-known linked-open-data
# hubs first. Everything else (the FDO's own DOI self-labelling its own
# temporal node, a Sketchfab source link, an archaeosquirrels.cloud
# mirror) is real data too, but it's "this package points back at
# itself/its own hosting", not "this joins a federated knowledge graph" -
# found rendering a real card, where file order alone buried every
# Wikidata/ChronOntology line under those (S16 nachtrag, PRIMER.md).
_LINK_DOMAIN_PRIORITY = [
    "wikidata.org",
    "openstreetmap.org",
    "chronontology.dainst.org",
    "orcid.org",
    "ror.org",
    "spdx.org",
]


def _link_domain_rank(iri: str) -> int:
    for i, domain in enumerate(_LINK_DOMAIN_PRIORITY):
        if domain in iri:
            return i
    return len(_LINK_DOMAIN_PRIORITY)


def _extract_link_lines(raw_ttl: str) -> List[str]:
    """rdfs:label/owl:sameAs lines whose subject is a genuine external
    IRI, formatted as `<iri> predicate value .` single lines, ranked by
    _LINK_DOMAIN_PRIORITY (not file order - see that list's docstring)."""
    candidates = []
    seen = set()
    for m in re.finditer(
        r'<([^>]+)>\s+(rdfs:label|owl:sameAs)\s+((?:"[^"]*")|(?:<[^>]+>))\s*\.',
        raw_ttl,
    ):
        subject, pred, value = m.group(1), m.group(2), m.group(3)
        if subject.startswith(_OWN_NAMESPACE_PREFIXES):
            continue
        if not subject.startswith(("http://", "https://")):
            continue
        key = (subject, pred, value)
        if key in seen:
            continue
        seen.add(key)
        candidates.append((subject, pred, value))

    candidates.sort(
        key=lambda c: (
            min(_link_domain_rank(c[0]), _link_domain_rank(c[2])),
            c[0],
            c[1],
        )
    )
    return [f"<{subj}> {pred} {value}" for subj, pred, value in candidates[:_LINKS_MAX_LINES]]


def _colour_predicate_line(line: str) -> str:
    """`predicate value` - predicate one colour, IRIs/literals in the
    value picked out from the rest. Not a real Turtle tokenizer, just
    enough to make a slide readable."""
    m = re.match(r"^(\S+)\s+(.*)$", line)
    if not m:
        return f'<tspan fill="{PUNCT}">{esc(line)}</tspan>'
    pred, rest = m.group(1), m.group(2)

    if len(rest) > _VALUE_MAX_CHARS + 20:
        rest = truncate(rest, _VALUE_MAX_CHARS) + '"'

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


def _colour_subject_line(subject: str, suffix: str = "") -> str:
    return (
        f'<tspan fill="{PUNCT}">&lt;</tspan>'
        f'<tspan fill="{SUBJECT_COLOR}">{esc(truncate(subject, 78))}</tspan>'
        f'<tspan fill="{PUNCT}">&gt;{esc(suffix)}</tspan>'
    )


def _render_card(card_title: str, subtitle: str, coloured_lines: List[str]) -> Tuple[str, int, int]:
    width = 1000
    pad = 36
    line_h = 30
    header_h = 64

    height = header_h + max(len(coloured_lines), 1) * line_h + pad

    body: List[str] = [
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="18" fill="{CARD_BG}"/>',
        '<circle cx="30" cy="30" r="7" fill="#FF5F56"/>',
        '<circle cx="52" cy="30" r="7" fill="#FFBD2E"/>',
        '<circle cx="74" cy="30" r="7" fill="#27C93F"/>',
        f'<text x="{width / 2}" y="34" text-anchor="middle" font-family="Fira Sans" '
        f'font-weight="700" font-size="17" fill="{SUBJECT_COLOR}">{esc(truncate(card_title, 60))}</text>',
        f'<text x="{width / 2}" y="52" text-anchor="middle" font-family="Fira Sans" '
        f'font-weight="400" font-size="13" fill="{PUNCT}">{esc(truncate(subtitle, 90))}</text>',
    ]

    y = header_h + pad / 2
    for ln in coloured_lines:
        body.append(
            f'<text x="{pad}" y="{y}" font-family="Fira Sans" font-weight="400" '
            f'font-size="15" xml:space="preserve">{ln}</text>'
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


def build_metadata_svg(raw_ttl: str, title: str) -> Optional[Tuple[str, int, int]]:
    subject, block_lines = _extract_core_block(raw_ttl)
    selected = _select_metadata_lines(block_lines)
    if not subject and not selected:
        return None
    lines = ([_colour_subject_line(subject)] if subject else []) + [
        _colour_predicate_line(ln) for ln in selected
    ]
    return _render_card("Metadata", title, lines)


def build_distributions_svg(raw_ttl: str, title: str) -> Optional[Tuple[str, int, int]]:
    blocks = _select_distribution_blocks(_extract_distribution_blocks(raw_ttl))
    if not blocks:
        return None
    lines: List[str] = []
    for i, (subj, pred_lines) in enumerate(blocks):
        if i > 0:
            lines.append("")
        lines.append(_colour_subject_line(subj, " a dcat:Distribution ..."))
        lines.extend(_colour_predicate_line(ln) for ln in pred_lines)
    return _render_card("Distributions", title, lines)


def build_links_svg(raw_ttl: str, title: str) -> Optional[Tuple[str, int, int]]:
    link_lines = _extract_link_lines(raw_ttl)
    if not link_lines:
        return None
    coloured = []
    for ln in link_lines:
        m = re.match(r"^(<[^>]+>)\s+(.*)$", ln)
        if not m:
            continue
        subj_part, rest = m.group(1), m.group(2)
        coloured.append(
            f'<tspan fill="{IRI_COLOR}">{esc(truncate(subj_part, 46))}</tspan> '
            + _colour_predicate_line(rest)
        )
    if not coloured:
        return None
    return _render_card("Linked Open Data", title, coloured)


def _rasterise(svg: str, width: int, height: int, output_png: Path, output_jpg: Path) -> None:
    """Writes a real, alpha-transparent PNG straight from resvg's own
    bytes (no PIL round-trip needed - resvg already renders PNG), plus a
    JPG for anyone who wants a flat file for a slide tool that dislikes
    transparency.

    The first version only wrote a JPG, built by dropping the alpha
    channel with `Image.convert("RGB")` - for the card's rounded
    corners, "dropped" meant "whatever RGB happened to sit under alpha
    0", which rendered as solid black wedges instead of the intended
    dark card background (found from Flo's real render, S17 nachtrag,
    PRIMER.md). The JPG here is composited onto CARD_BG explicitly
    instead, so the corners come out looking like the corners, not like
    a rendering bug.
    """
    import resvg_py
    from PIL import Image
    import io

    png_bytes = resvg_py.svg_to_bytes(
        svg_string=svg,
        width=int(width * RENDER_SCALE),
        height=int(height * RENDER_SCALE),
        font_files=[
            str(Path(__file__).resolve().parent / "fonts" / "FiraSans-Regular.ttf"),
            str(Path(__file__).resolve().parent / "fonts" / "FiraSans-Bold.ttf"),
        ],
        skip_system_fonts=True,
    )
    output_png.parent.mkdir(parents=True, exist_ok=True)
    output_png.write_bytes(bytes(png_bytes))

    im = Image.open(io.BytesIO(bytes(png_bytes))).convert("RGBA")
    flat = Image.new("RGBA", im.size, CARD_BG_RGB + (255,))
    flat.alpha_composite(im)
    flat.convert("RGB").save(output_jpg, "JPEG", quality=92)


def write_ttl_snippet_cards(ttl_path: Path, title: str, output_dir: Path) -> List[Path]:
    """Writes three SVG+PNG+JPG card sets (metadata/distributions/links)
    into output_dir - PNG for a transparent-cornered result consistent
    with the other S8 diagrams, JPG for anyone who specifically wants a
    flat file for a slide tool. Returns the list of paths actually
    written (a card with nothing to show - e.g. no external links found
    - is skipped, not written empty).
    """
    raw_ttl = ttl_path.read_text(encoding="utf-8")
    written: List[Path] = []

    for name, builder in (
        ("metadata", build_metadata_svg),
        ("distributions", build_distributions_svg),
        ("links", build_links_svg),
    ):
        result = builder(raw_ttl, title)
        if result is None:
            continue
        svg, width, height = result
        svg_path = output_dir / f"fdo_ttl_snippet_{name}.svg"
        png_path = output_dir / f"fdo_ttl_snippet_{name}.png"
        jpg_path = output_dir / f"fdo_ttl_snippet_{name}.jpg"
        svg_path.write_text(svg, encoding="utf-8")
        written.append(svg_path)
        try:
            _rasterise(svg, width, height, png_path, jpg_path)
            written.append(png_path)
            written.append(jpg_path)
        except ImportError:
            pass  # resvg-py not installed - SVG still written, PNG/JPG best-effort only

    return written
