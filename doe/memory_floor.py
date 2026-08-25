#!/usr/bin/env python3
"""Memory-floor DOE for Ornith-1.5 (Piece 2): find the real GTT ceiling floor.

Approach (runtime, no reboot):
  * The enforced GTT ceiling on this box is /sys/module/ttm/parameters/pages_limit
    (pages). 13107200 pages = 50 GiB (matches mem_info_gtt_total 53687091200).
    Lowering it at runtime caps how much system RAM the GPU driver may use for
    GTT allocations. amdgpu keeps reporting gtt_total=50 GiB, so we report the
    pages_limit-derived cap as the REAL ceiling and gtt_used as actual usage.

Per cap:
  1. set pages_limit = cap_gib
  2. (re)start ornith-1.5.service (fresh load under the cap)
  3. wait for /props ready; record load_ok + load_s + gtt_used after load
  4. run a realistic mixed batch (8 text/coding/tool tasks + 4 vision tasks,
     incl. two real app screenshots) with production sampling
  5. record per-task ok/err + gen_tps + any server allocation errors, append CSV

Usage: memory_floor.py <cap_gib> <out_csv> [--no-restart]
"""
import base64, csv, glob, io, json, os, subprocess, sys, time, urllib.request
from PIL import Image, ImageDraw, ImageFont

BASE = "http://127.0.0.1:8082"
MODEL = "ornith-1.5-35b"
SVC = "ornith-1.5.service"
PAGES_LIMIT = "/sys/module/ttm/parameters/pages_limit"
GTT_USED = "/sys/class/drm/card1/device/mem_info_gtt_used"
GTT_TOTAL = "/sys/class/drm/card1/device/mem_info_gtt_total"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SCREENSHOT_DIR = "/home/taza/reports/spec-discovery/screenshots"
GIB = 1073741824.0
PAGES_PER_GIB = 1024**3 // 4096  # 262144

def rd(path, div=1.0):
    try:
        with open(path) as f: return float(f.read().strip()) / div
    except Exception: return None

def set_cap(gib):
    pages = int(round(gib * PAGES_PER_GIB))
    r = subprocess.run(["sudo", "sh", "-c", f"echo {pages} > {PAGES_LIMIT}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"set_cap failed: {r.stderr[-300:]}")
    back = rd(PAGES_LIMIT)
    return pages, int(back) if back else None

def wait_ready(timeout=240):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(BASE + "/props", timeout=3) as r:
                if json.loads(r.read()).get("model_alias"): return round(time.time() - t0, 1)
        except Exception: pass
        time.sleep(1)
    return None

def restart():
    r = subprocess.run(["sudo", "systemctl", "restart", SVC], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"restart failed: {r.stderr[-300:]}")

def server_errors_since(start_ts):
    """Pull recent allocation/OOM/vulkan errors from the service journal."""
    out = subprocess.run(
        ["sudo", "journalctl", "-u", SVC, "--since", start_ts, "--no-pager", "-n", "200"],
        capture_output=True, text=True).stdout
    hits = [l for l in out.splitlines() if any(k in l.lower() for k in
            ("vkallocation", "out of memory", "oom", "failed to allocate",
             "allocation failed", "vulkan error", "not enough memory", "cuda", "ggml_vulkan"))]
    return hits[-6:]

def b64(img, max_dim=1024):
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def request(messages, max_tokens=200, tools=None):
    body = {"model": MODEL, "messages": messages, "max_tokens": max_tokens,
            "stream": False, "temperature": 0.2, "top_p": 0.95, "top_k": 20}
    if tools: body["tools"] = tools
    req = urllib.request.Request(BASE + "/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        j = json.loads(r.read())
    t = j.get("timings", {})
    m = j["choices"][0]["message"]
    return {"text": (m.get("content") or ""), "tool_calls": m.get("tool_calls"),
            "gen_tps": round(t.get("predicted_per_second", 0), 1),
            "prompt_n": t.get("prompt_n", 0), "predicted_n": t.get("predicted_n", 0)}

# ---- image generators (deterministic) ----
def text_img(text, size=(512,160)):
    img = Image.new("RGB", size, (0,0,0)); d = ImageDraw.Draw(img)
    try: f = ImageFont.truetype(FONT, 60)
    except Exception: f = ImageFont.load_default()
    d.text((20,30), text, font=f, fill=(255,255,255)); return img

def circles(n):
    img = Image.new("RGB", (300,150), (255,255,255)); d = ImageDraw.Draw(img)
    for i in range(n): d.ellipse([40+i*70,40,40+i*70+50,90], fill=(220,20,20))
    return img

def solid(color, size=(256,256)):
    return Image.new("RGB", size, color)

def load_screenshot(name):
    p = os.path.join(SCREENSHOT_DIR, name)
    return Image.open(p).convert("RGB")

# ---- the realistic mixed batch: 8 text + 4 vision ----
def build_batch():
    B = []
    # pure-text coding/ops tasks
    B.append(("qa-mult", [{"role":"user","content":"What is 17 multiplied by 23? Just the number."}], None))
    B.append(("bash-ls5", [{"role":"user","content":"Write a bash one-liner that lists the 5 largest files in /var/log by size."}], None))
    B.append(("py-nth-prime", [{"role":"user","content":"Write a Python function that returns the nth prime number."}], None))
    B.append(("bash-wc", [{"role":"user","content":"Write a bash command to count the lines in log.txt."}], None))
    B.append(("exit-code", [{"role":"user","content":"In one sentence: what does an exit code of 0 mean on Linux?"}], None))
    B.append(("tool-run-shell", [{"role":"user","content":"Use the run_shell tool to run: echo hello world"}],
        [{"type":"function","function":{"name":"run_shell","description":"Run a shell command","parameters":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}}}]))
    B.append(("tool-calc", [{"role":"user","content":"Use the calculate tool to compute 17 times 23"}],
        [{"type":"function","function":{"name":"calculate","description":"Evaluate a math expression","parameters":{"type":"object","properties":{"expression":{"type":"string"}},"required":["expression"]}}}]))
    B.append(("qa-capital", [{"role":"user","content":"What is the capital of Japan? One word."}], None))
    # vision tasks: 2 synthetic + 2 real app screenshots
    B.append(("vis-color", [{"role":"user","content":[{"type":"text","text":"What color is this image? One word."},
        {"type":"image_url","image_url":{"url":"data:image/png;base64,"+b64(solid((0,0,255)))}}]}], None))
    B.append(("vis-circles", [{"role":"user","content":[{"type":"text","text":"How many red circles are in this image? Just the number."},
        {"type":"image_url","image_url":{"url":"data:image/png;base64,"+b64(circles(3))}}]}], None))
    B.append(("vis-ocr-screen", [{"role":"user","content":[{"type":"text","text":"Read the exact text labels you can see in this application screenshot. Output the text labels only."},
        {"type":"image_url","image_url":{"url":"data:image/png;base64,"+b64(load_screenshot("dashboard.png"))}}]}], None))
    B.append(("vis-desc-screen", [{"role":"user","content":[{"type":"text","text":"In one sentence, describe what this application UI shows."},
        {"type":"image_url","image_url":{"url":"data:image/png;base64,"+b64(load_screenshot("van-loadout.png"))}}]}], None))
    return B

def run_batch():
    rows = []
    for name, msgs, tools in build_batch():
        t0 = time.time()
        try:
            r = request(msgs, tools=tools)
            rows.append({"name": name, "ok": 1, "err": "", "gen_tps": r["gen_tps"],
                         "prompt_n": r["prompt_n"], "pred_n": r["predicted_n"],
                         "wall_s": round(time.time()-t0,1),
                         "tool_ok": 1 if r["tool_calls"] else 0})
            print(f"  {name:16s} OK  gen={r['gen_tps']:6.1f} ptok={r['prompt_n']:5d} tok={r['predicted_n']:4d} wall={rows[-1]['wall_s']}s", flush=True)
        except Exception as e:
            rows.append({"name": name, "ok": 0, "err": str(e)[:120], "gen_tps": 0,
                         "prompt_n": 0, "pred_n": 0, "wall_s": round(time.time()-t0,1), "tool_ok": 0})
            print(f"  {name:16s} ERR {str(e)[:110]}", flush=True)
    ok = sum(1 for r in rows if r["ok"])
    gts = [r["gen_tps"] for r in rows if r["ok"]]
    return rows, ok, (round(sum(gts)/len(gts),1) if gts else 0)

def main():
    cap = float(sys.argv[1]); out = sys.argv[2]; no_restart = "--no-restart" in sys.argv
    print(f"=== MEMORY FLOOR: cap {cap:.0f} GiB ===", flush=True)
    want_pages, got_pages = set_cap(cap)
    print(f"  pages_limit: want {want_pages} ({cap:.0f} GiB), read back {got_pages} ({got_pages/PAGES_PER_GIB:.1f} GiB if set)", flush=True)
    ts0 = time.strftime("%Y-%m-%d %H:%M:%S")
    if no_restart:
        load_ok, load_s = 1, 0.0
        print("  no-restart mode: using currently running server", flush=True)
    else:
        restart()
        load_s = wait_ready(240)
        load_ok = 1 if load_s is not None else 0
        print(f"  load: ok={load_ok} load_s={load_s}", flush=True)
    if load_ok:
        gtt_used = rd(GTT_USED, GIB)
        gtt_total = rd(GTT_TOTAL, GIB)
        print(f"  gtt: used={gtt_used:.2f} GiB  total(reported)={gtt_total:.2f} GiB", flush=True)
        rows, ok, avg_gts = run_batch()
        errs = server_errors_since(ts0)
        if errs:
            print("  server journal allocation/oom lines:", flush=True)
            for e in errs: print("    " + e, flush=True)
    else:
        rows, ok, avg_gts = [], 0, 0
        gtt_used = gtt_total = None
        errs = []
        print("  FAILED TO LOAD under this cap", flush=True)
    row = {"cap_gib": round(cap,1), "pages_limit": got_pages, "load_ok": load_ok,
           "load_s": load_s, "gtt_used_gib": round(gtt_used,2) if gtt_used else None,
           "gtt_total_gib": round(gtt_total,2) if gtt_total else None,
           "batch_ok": ok, "batch_total": len(rows), "gen_tps_avg": avg_gts,
           "per_task": json.dumps(rows), "server_errs": json.dumps(errs),
           "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    new = not os.path.exists(out)
    with open(out, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new: w.writeheader()
        w.writerow(row)
    print("RESULT " + json.dumps({k: v for k, v in row.items() if k != "per_task"}), flush=True)
    return 0 if load_ok and ok == len(rows) else (2 if not load_ok else 3)

if __name__ == "__main__":
    sys.exit(main())
