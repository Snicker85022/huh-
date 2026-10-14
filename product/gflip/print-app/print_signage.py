#!/usr/bin/env python3
"""
Station / sanitation / storage signage on the Zebra TLP2844-Z.
4 x 1 in stock, 203 dpi -> 812 x 203 dots (KB PROD-13).

Centered, text-only, no QR. Sent through the running print-app's /api/print/raw
(port 8096) so every job lands in print_log.jsonl exactly like a kanban label.

ZPL note: ^ and ~ are control characters and may not appear in field data.

Usage
  python3 print_signage.py --list
  python3 print_signage.py --preview
  python3 print_signage.py --names=scrub-comet,polish-microfiber
  python3 print_signage.py --only=3,4
"""
import json, sys, time, urllib.request

W, H = 812, 203
API  = "http://127.0.0.1:8096/api/print/raw"
FONT = "^A0N"                      # scalable sans

# name, lines, [(font_height, char_width) in dots], copies
SIGNAGE = [
    # --- batch 1: sink stations + routine cleaning -------------------------
    dict(name="wipe-daily",          lines=["WIPE INSIDE & OUT", "DAILY"],           sizes=[(66, 42), (48, 42)], copies=1),
    dict(name="floor-drain",         lines=["CLEAN FLOOR DRAIN", "EVERY 2 WEEKS"],   sizes=[(66, 42), (44, 42)], copies=1),
    dict(name="wash-here",           lines=["WASH HERE"],                            sizes=[(92, 72)],           copies=1),
    dict(name="rinse-here",          lines=["RINSE HERE"],                           sizes=[(92, 66)],           copies=1),
    dict(name="sanitize-here",       lines=["SANITIZE HERE"],                        sizes=[(84, 56)],           copies=1),
    # --- batch 2: equipment care + clean/dirty dish zones ------------------
    dict(name="scrub-comet",         lines=["SCRUB WITH COMET", "AFTER USE"],        sizes=[(66, 42), (44, 42)], copies=2),
    dict(name="polish-microfiber",   lines=["POLISH WITH MICROFIBER", "NIGHTLY"],    sizes=[(56, 32), (40, 32)], copies=1),
    dict(name="clean-dishes-above",  lines=["CLEAN DISHES", "HERE & ABOVE ONLY"],    sizes=[(66, 44), (44, 38)], copies=1),
    dict(name="dirty-dishes-below",  lines=["DIRTY DISHES", "HERE AND BELOW ONLY"],  sizes=[(66, 44), (42, 36)], copies=1),
    # --- batch 3: walk-in / reach-in door ID -------------------------------
    dict(name="reach-in-door-6",     lines=['REACH IN DOOR 6"'],                      sizes=[(96, 42)],           copies=1),
]


def build_zpl(lines, sizes, copies=1, gap=14):
    total = sum(fh for fh, _ in sizes) + gap * (len(lines) - 1)
    y = max(4, (H - total) // 2)                 # centre the block vertically
    z = ["^XA", "^CI28", "^PW%d" % W, "^LL%d" % H, "^LH0,0"]
    for txt, (fh, fw) in zip(lines, sizes):
        x = max(8, (W - len(txt) * fw) // 2)     # and each line horizontally
        z.append("^FO%d,%d%s,%d,%d^FD%s^FS" % (x, y, FONT, fh, fw, txt))
        y += fh + gap
    z += ["^PQ%d" % max(1, int(copies)), "^XZ"]
    return "\n".join(z)


def send(zpl, tries=6, backoff=2.5):
    """The TLP2844-Z print server accepts ONE connection at a time and refuses the rest
    with ECONNREFUSED while it is still buffering the previous job (seen 2026-10-09:
    3 labels fine, labels 4 and 5 refused). Retry with a growing pause."""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(API, data=json.dumps({"zpl": zpl}).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except Exception as e:
            last = e
            time.sleep(backoff * (i + 1))
    return {"ok": False, "detail": "gave up after %d tries: %s" % (tries, last)}


def main():
    argv = sys.argv[1:]
    preview = "--preview" in argv
    if "--list" in argv:
        for i, s in enumerate(SIGNAGE):
            print("%2d  %-20s x%d  %s" % (i, s["name"], s["copies"], " / ".join(s["lines"])))
        return
    only = None
    for a in argv:
        if a.startswith("--only="):
            only = {int(x) for x in a.split("=", 1)[1].split(",")}
    names = None
    for a in argv:
        if a.startswith("--names="):
            names = [x.strip() for x in a.split("=", 1)[1].split(",")]

    todo = [s for s in SIGNAGE
            if (names is None or s["name"] in names)
            and (only is None or SIGNAGE.index(s) in only)]
    if not todo:
        print("nothing selected"); return

    for i, s in enumerate(todo):
        zpl = build_zpl(s["lines"], s["sizes"], s["copies"])
        print("=" * 62)
        print(" %s  (x%d)" % (" / ".join(s["lines"]), s["copies"]))
        print(zpl)
        if preview:
            continue
        if i:
            time.sleep(2.5)                      # let the print server finish the last job
        r = send(zpl)
        print(">>> %-20s %s  %s" % (s["name"], "SENT" if r.get("ok") else "FAIL", r.get("detail")))


if __name__ == "__main__":
    main()
