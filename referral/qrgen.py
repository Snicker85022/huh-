"""
qrgen.py — compose the burnable image for one spatula.

One SIDE of the spatula = QR + a caption line. (The other side — the Taza logo
+ "Refer Taza to your friends so they get 10% off" — is a fixed art asset burned
from its own PNG; see referral/static/.)

Output is a high-contrast 1-bit-friendly PNG sized for the engraver. Pure black
on white so image2gcode maps ink->power cleanly.
"""

from __future__ import annotations

import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageDraw, ImageFont


def make_qr(data: str, box_size: int = 10, border: int = 2) -> Image.Image:
    """High error-correction QR (H = 30% recoverable) — survives wood grain,
    scorch, and hand-wear far better than default L."""
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=box_size, border=border)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("L")


def _load_font(size: int):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def qr_panel(data: str, caption: str | None = None,
             qr_px: int = 500, pad: int = 30) -> Image.Image:
    """QR with an optional caption underneath. Returns an 'L' (grayscale) image
    at print resolution; burn.py's pixelsize maps px->mm."""
    qr = make_qr(data).resize((qr_px, qr_px), Image.NEAREST)
    cap_h = 70 if caption else 0
    canvas = Image.new("L", (qr_px + 2 * pad, qr_px + cap_h + 2 * pad), 255)
    canvas.paste(qr, (pad, pad))
    if caption:
        draw = ImageDraw.Draw(canvas)
        font = _load_font(38)
        w = draw.textlength(caption, font=font)
        draw.text(((canvas.width - w) / 2, qr_px + pad + 8), caption, fill=0, font=font)
    return canvas


def save_qr_panel(data: str, out_path: str, caption: str | None = None, **kw) -> str:
    qr_panel(data, caption=caption, **kw).save(out_path)
    return out_path


if __name__ == "__main__":
    import sys
    data = sys.argv[1] if len(sys.argv) > 1 else "https://tazacateringphoenix.com"
    out = sys.argv[2] if len(sys.argv) > 2 else "qr_test.png"
    cap = sys.argv[3] if len(sys.argv) > 3 else "Scan for 10% off"
    print(save_qr_panel(data, out, caption=cap))
