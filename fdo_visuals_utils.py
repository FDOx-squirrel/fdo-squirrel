"""fdo_visuals_utils.py — shared style constants and render helpers for
fdo-squirrel's own SVG diagrams (S8, PRIMER.md).

Deliberately mirrors fdox-visuals' py/visuals_utils.py rather than
inventing a second house style: same palette, same vendored Fira Sans,
same resvg-py rendering approach. Copied, not imported across repos
(PRIMER.md A3, "reuse means copying") - fonts/ here is fdo-squirrel's own
copy of the two TTFs, not a reference back to fdox-visuals.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
FONTS_DIR = ROOT / "fonts"

FONT_REGULAR = FONTS_DIR / "FiraSans-Regular.ttf"
FONT_BOLD = FONTS_DIR / "FiraSans-Bold.ttf"
FONT_FAMILY = "Fira Sans"

INK = "#161B2E"
MUTED = "#5B6478"
BG = "#FFFFFF"

# The same "one family palette" fdox-visuals uses, read from the same
# values rather than re-guessed - #004473 is the canonical FDOx blue.
FDO_BLUE = "#004473"
FDO_BLUE_TINT = "#E6ECF1"
TEAL = "#0E9488"
TEAL_TINT = "#E6F6F4"
PURPLE = "#8034C9"
PURPLE_TINT = "#F3E9FC"
ORANGE = "#C2790C"
ORANGE_TINT = "#FCF1E1"


def esc(text: object) -> str:
    """Escape the handful of characters that appear in real MD.cff/CITATION.cff text."""
    s = str(text)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def wrap_text(text: str, max_chars: int = 40) -> list[str]:
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        # A single "word" longer than the whole line (a bare URL, an
        # IRI with no spaces) can't be wrapped by the loop below at all -
        # split it into fixed-size chunks first, or it runs straight off
        # the right edge of the panel (found rendering a real MD.cff's
        # related_resources, S8, PRIMER.md).
        while len(w) > max_chars:
            if cur:
                lines.append(cur)
                cur = ""
            lines.append(w[:max_chars])
            w = w[max_chars:]
        trial = (cur + " " + w).strip()
        if len(trial) > max_chars and cur:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "\u2026"


# Default `output/` sits directly under the repo root, a sibling of
# fonts/ - same one-level-up relationship fdox-visuals' img/ has to its
# own fonts/. Only correct for that default location; a custom --outdir
# elsewhere won't resolve this relative path, same limitation fdox-visuals
# accepts for its fixed img/ directory. resvg's own PNG rendering does not
# depend on this URL resolving either way - see render_svg_to_png, which
# passes the font files directly.
_FONT_REL_PREFIX = "../fonts"


def font_face_css() -> str:
    """@font-face block pointing at the two vendored weights."""
    return (
        "<style>"
        f'@font-face {{ font-family: "{FONT_FAMILY}"; '
        f'src: url("{_FONT_REL_PREFIX}/FiraSans-Regular.ttf"); font-weight: 400; }} '
        f'@font-face {{ font-family: "{FONT_FAMILY}"; '
        f'src: url("{_FONT_REL_PREFIX}/FiraSans-Bold.ttf"); font-weight: 700; }}'
        "</style>"
    )


def render_svg_to_png(svg_path: Path, png_path: Path, width: int, height: int) -> None:
    """Rasterise via resvg - see fdox-visuals' visuals_utils.py for why
    (single self-contained wheel, no system libcairo/rsvg needed). Optional:
    callers should catch ImportError and skip the PNG, same pattern as
    render_mermaid_to_png's mmdc dependency.
    """
    import resvg_py

    png_bytes = resvg_py.svg_to_bytes(
        svg_path=str(svg_path),
        width=width,
        height=height,
        font_files=[str(FONT_REGULAR), str(FONT_BOLD)],
        skip_system_fonts=True,
    )
    png_path.write_bytes(png_bytes)


def arrow_marker_defs() -> str:
    """Same arrowhead marker fdox-visuals' architecture diagram uses -
    one <marker> def, referenced by every connector line/path."""
    return (
        '<marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/></marker>'
    )


def curved_connector(ax: float, ay: float, bx: float, by: float, color: str = MUTED) -> str:
    """A smooth S-curve connector from (ax,ay) to (bx,by) with an
    arrowhead at the end, matching the node-graph reference style
    (Flo, S8, PRIMER.md) rather than the architecture diagram's straight
    lines/polylines."""
    mid_x = (ax + bx) / 2
    return (
        f'<path d="M{ax},{ay} C{mid_x},{ay} {mid_x},{by} {bx},{by}" '
        f'fill="none" stroke="{color}" stroke-width="2.5" marker-end="url(#arrow)"/>'
    )
