#!/usr/bin/env python3
"""
test_burn.py — TONIGHT'S TEST BURN. Staged and safety-gated.

Two-phase by design so nobody fires a laser by accident:

  Phase 1 (default):  generate QR panel -> gcode -> connect -> FRAME the outline
                      with the laser OFF. Nothing burns. Use this to position
                      the spatula and confirm the box lands on the wood.

  Phase 2 (--fire):   after Phase 1 looks right AND a human is watching AND
                      eye protection is on, re-run with --fire to actually burn.

Examples
  # Phase 1 — dry frame, no burning:
  /home/taza/laser/venv/bin/python test_burn.py

  # Phase 2 — real burn on a scrap spatula, supervised:
  /home/taza/laser/venv/bin/python test_burn.py --fire --power 650 --speed 3000

Run from the repo's referral/laser/ dir (imports elidor.py + ../qrgen.py).
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # referral/ for qrgen

from burn import burn  # noqa: E402
from qrgen import save_qr_panel  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Elidor Z6 staged test burn")
    ap.add_argument("--data", default="https://tazacateringphoenix.com?s=TESTBURN",
                    help="what the QR encodes")
    ap.add_argument("--caption", default="Refer a friend - 10% off")
    ap.add_argument("--out", default="/home/taza/laser/test_burn_qr.png")
    ap.add_argument("--port", default=None, help="serial port (default /dev/taza-laser, autodetect)")
    ap.add_argument("--power", type=int, default=650, help="max S value 0..1000 (start low!)")
    ap.add_argument("--speed", type=int, default=3000, help="feed mm/min")
    ap.add_argument("--pixelsize", type=float, default=0.12, help="mm/pixel")
    ap.add_argument("--fire", action="store_true",
                    help="ACTUALLY BURN. Without this flag it only frames (no laser).")
    args = ap.parse_args()

    print("== Elidor Z6 test burn ==")
    png = save_qr_panel(args.data, args.out, caption=args.caption)
    print(f"[1/3] QR panel written: {png}")
    print(f"      encodes: {args.data}")

    def progress(i, line, resp):
        if i % 50 == 0:
            print(f"      line {i}: {line} -> {resp}")

    mode = "FIRING" if args.fire else "FRAME ONLY (no burn)"
    print(f"[2/3] Mode: {mode}")
    if args.fire:
        print("      *** LASER WILL FIRE. Eye protection on. Human supervising. "
              "Scrap spatula in place. Ctrl-C to abort. ***")

    summary = burn(
        png, port=args.port, do_frame=True, armed=args.fire, progress=progress,
        maxpower=args.power, speed=args.speed, pixelsize=args.pixelsize,
    )
    print(f"[3/3] Done. GRBL: {summary.get('banner','?')}")
    print(f"      bbox(mm): {summary['bbox_mm']}  size: "
          f"{summary['width_mm']} x {summary['height_mm']} mm")
    print(f"      framed: {summary.get('framed', False)}  fired: {summary['fired']}")
    if not args.fire:
        print("\nFrame looked right? Re-run with --fire to burn (supervised).")


if __name__ == "__main__":
    main()
