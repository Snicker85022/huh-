"""
burn.py — turn a PNG (QR + Taza logo/text) into G-code and run it on the Elidor.

Pipeline:  PNG --image2gcode--> .gcode --Elidor.stream--> engraving

Conservative defaults for a 12W diode on light wood (spatula). These are a
SAFE STARTING POINT, not gospel — the first test burn calibrates them. Diode
lasers vary; always start low and creep up.

  * speed 3000 mm/min, max S 700/1000 (~70% power) for engraving on wood
  * a framing pass traces the job's bounding box with the laser OFF so you can
    position the spatula before committing.
"""

from __future__ import annotations

import os
import subprocess

from elidor import Elidor

# image2gcode tuning (see: github.com/johannesnoordanus/image2gcode)
DEFAULTS = dict(
    pixelsize=0.10,     # mm per pixel — engraving resolution
    speed=3000,         # mm/min feed while burning
    maxpower=700,       # GRBL S value at black (0..1000). 700 ~= 70% of 12W. Start conservative.
    speedmoves=6000,    # rapid feed for non-burning moves
    noise=8,            # ignore near-white pixels below this (0..255)
    overscan=1,         # mm of overscan to avoid edge scorching
)


def png_to_gcode(png_path: str, gcode_path: str | None = None, **overrides) -> str:
    """Convert a PNG to GRBL G-code with image2gcode. Returns the .gcode path."""
    if not os.path.exists(png_path):
        raise FileNotFoundError(png_path)
    gcode_path = gcode_path or os.path.splitext(png_path)[0] + ".gcode"
    cfg = {**DEFAULTS, **overrides}
    cmd = [
        "image2gcode",
        "--pixelsize", str(cfg["pixelsize"]),
        "--speed", str(cfg["speed"]),
        "--maxpower", str(cfg["maxpower"]),
        "--speedmoves", str(cfg["speedmoves"]),
        "--noise", str(cfg["noise"]),
        "--overscan", str(cfg["overscan"]),
        png_path, gcode_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return gcode_path


def bounding_box(gcode_path: str) -> tuple[float, float, float, float]:
    """Cheap min/max X/Y scan of a G-code file for the framing pass."""
    xs, ys = [], []
    with open(gcode_path) as fh:
        for line in fh:
            for tok in line.split():
                try:
                    if tok[0] in "Xx":
                        xs.append(float(tok[1:]))
                    elif tok[0] in "Yy":
                        ys.append(float(tok[1:]))
                except (ValueError, IndexError):
                    pass
    if not xs or not ys:
        raise ValueError("no coordinates found in gcode")
    return min(xs), min(ys), max(xs), max(ys)


def frame_gcode(gcode_path: str) -> list[str]:
    """G-code that traces the job's bounding box with the laser OFF, for
    positioning the spatula. No burning."""
    x0, y0, x1, y1 = bounding_box(gcode_path)
    return [
        "G21", "G90", "M5",               # mm, absolute, laser off
        f"G0 X{x0:.2f} Y{y0:.2f}",
        f"G0 X{x1:.2f} Y{y0:.2f}",
        f"G0 X{x1:.2f} Y{y1:.2f}",
        f"G0 X{x0:.2f} Y{y1:.2f}",
        f"G0 X{x0:.2f} Y{y0:.2f}",
        "M5",
    ]


def frame(elidor: Elidor, gcode_path: str):
    """Run the no-fire framing pass. armed is irrelevant — M5 keeps it dark,
    but we still gate via stream(armed=True) since it moves the head."""
    elidor.stream(frame_gcode(gcode_path), armed=True)


def burn(png_path: str, port: str | None = None, do_frame: bool = True,
         armed: bool = False, progress=None, **gcode_overrides) -> dict:
    """Full path: convert -> (frame) -> burn. Requires armed=True to fire.

    Returns a summary dict. Caller MUST have a human supervising and the
    material placed. Never call with armed=True unattended.
    """
    gcode_path = png_to_gcode(png_path, **gcode_overrides)
    x0, y0, x1, y1 = bounding_box(gcode_path)
    summary = {
        "png": png_path, "gcode": gcode_path,
        "bbox_mm": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
        "width_mm": round(x1 - x0, 2), "height_mm": round(y1 - y0, 2),
        "fired": False,
    }
    with Elidor(port=port) as e:
        summary["banner"] = e.banner.strip()
        if do_frame:
            frame(e, gcode_path)
            summary["framed"] = True
        if armed:
            with open(gcode_path) as fh:
                lines = fh.readlines()
            e.stream(lines, armed=True, on_line=progress)
            summary["fired"] = True
            summary["lines"] = len(lines)
    return summary
