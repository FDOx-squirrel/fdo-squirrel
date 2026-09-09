"""
Finishing touches for a fdo-squirrel run:

- render_mermaid_to_png(): best-effort high-resolution PNG render of the
  generated fdo_overview.mermaid diagram, via the Mermaid CLI (`mmdc`).
  Not a hard dependency of the rest of this tool; if it's missing, or
  rendering fails for any reason, this prints one short, actionable
  warning and returns None rather than failing the run - the same
  pattern main.py already uses around the mermaid *text* generation.
  Previously rendered a JPG (via Pillow, from mmdc's own PNG output) with
  PNG kept alongside as a copy of the intermediate file; S19 dropped the
  JPG entirely (Flo's wish, PRIMER.md - PNG+SVG only across every S8/S17
  diagram, no JPG) and with it the Pillow dependency this function no
  longer needs: mmdc already produces PNG directly, so the "conversion"
  step was pure overhead once the JPG target was removed.

- build_finished_bundle(): package the original source ZIP plus every
  freshly generated companion file (fdo-metadata.ttl, the two modelling
  reports, the mermaid diagram, its PNG render) into one self-contained
  "finished" ZIP, replacing any stale copies of those same filenames the
  original ZIP already carried. This automates a step that was previously
  done by hand before (re-)publishing a package.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Dict, Iterable, Optional


def render_mermaid_to_png(
    mermaid_path: Path,
    png_path: Path,
    width: int = 2400,
    height: int = 1600,
    scale: int = 3,
    timeout: int = 120,
) -> Optional[Path]:
    """Render `mermaid_path` to a high-resolution PNG at `png_path` via
    `mmdc`, which produces PNG natively - no conversion step needed.

    Returns the PNG's output path on success, None if rendering was
    skipped or failed (a warning is printed either way - never raises).
    """
    if not mermaid_path.exists():
        return None

    mmdc = shutil.which("mmdc") or shutil.which("mmdc.cmd")
    if not mmdc:
        print(
            "⚠ Mermaid image render skipped: 'mmdc' not found on PATH.\n"
            "   Install Node.js, then run:\n"
            "     npm install -g @mermaid-js/mermaid-cli\n"
            "   to enable the high-resolution PNG render."
        )
        return None

    tmp_png = png_path.with_suffix(".tmp.png")
    tmp_cfg: Optional[Path] = None
    cmd = [
        mmdc,
        "-i",
        str(mermaid_path),
        "-o",
        str(tmp_png),
        "-w",
        str(width),
        "-H",
        str(height),
        "--backgroundColor",
        "white",
        "--scale",
        str(scale),
    ]

    # Headless Chromium refuses to launch as root without --no-sandbox
    # (containers/CI); harmless to add anywhere else, so only bother when
    # actually running as root.
    try:
        is_root = hasattr(os, "geteuid") and os.geteuid() == 0
    except Exception:
        is_root = False
    if is_root:
        tmp_cfg = png_path.with_suffix(".puppeteer.json")
        tmp_cfg.write_text(json.dumps({"args": ["--no-sandbox"]}), encoding="utf-8")
        cmd += ["--puppeteerConfigFile", str(tmp_cfg)]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
        shutil.copyfile(tmp_png, png_path)
        print(f"✔ Mermaid diagram rendered as high-res PNG: {png_path}")
        return png_path
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or b"").decode("utf-8", errors="replace").strip()
        print(f"⚠ Mermaid image render skipped: mmdc failed - {stderr[-500:]}")
        return None
    except Exception as e:
        print(f"⚠ Mermaid image render skipped: {e}")
        return None
    finally:
        if tmp_png.exists():
            tmp_png.unlink()
        if tmp_cfg is not None and tmp_cfg.exists():
            tmp_cfg.unlink()


def build_finished_bundle(
    original_zip_path: Optional[Path],
    generated_files: Iterable[Path],
    output_zip_path: Path,
) -> Optional[Path]:
    """
    Build one self-contained "finished" FDO package at `output_zip_path`:
    every member of `original_zip_path`, plus the freshly generated
    companion files, added/overwritten at the ZIP root by filename. Members
    of the original ZIP whose basename matches a generated file's name are
    skipped in favour of the fresh version (superseding stale copies of
    fdo-metadata.ttl, the modelling reports, etc. that a previous manual
    round of this same workflow may have left in the package).

    Streams member content rather than loading the archive into memory,
    since real packages here run into the hundreds of MB.
    """
    if original_zip_path is None or not Path(original_zip_path).exists():
        print(
            f"⚠ Finished bundle skipped: original package not found at "
            f"{original_zip_path}"
        )
        return None

    generated_by_name: Dict[str, Path] = {
        p.name: p for p in generated_files if p.exists()
    }
    if not generated_by_name:
        print("⚠ Finished bundle skipped: no generated files to add.")
        return None

    try:
        with zipfile.ZipFile(original_zip_path, "r") as zin, zipfile.ZipFile(
            output_zip_path, "w", zipfile.ZIP_DEFLATED
        ) as zout:
            superseded = []
            for item in zin.infolist():
                base = Path(item.filename).name
                if base in generated_by_name:
                    superseded.append(item.filename)
                    continue
                with zin.open(item) as src, zout.open(item, "w") as dst:
                    shutil.copyfileobj(src, dst)

            for name, path in generated_by_name.items():
                # zipfile.write() would stamp each entry with the file's
                # real mtime, i.e. the wall-clock moment this run
                # happened to write it - two otherwise-identical runs
                # would then disagree on nothing but that timestamp
                # (found in S4, PRIMER.md). Fixed epoch + mode instead,
                # same convention as the rest of the family.
                zinfo = zipfile.ZipInfo(filename=name, date_time=(1980, 1, 1, 0, 0, 0))
                zinfo.compress_type = zipfile.ZIP_DEFLATED
                zinfo.external_attr = 0o644 << 16
                zout.writestr(zinfo, path.read_bytes())

        if superseded:
            print(
                f"ℹ Finished bundle: replaced {len(superseded)} stale "
                f"member(s) with freshly generated versions: "
                f"{', '.join(superseded)}"
            )
        return output_zip_path
    except Exception as e:
        print(f"⚠ Could not build finished bundle: {e}")
        return None
