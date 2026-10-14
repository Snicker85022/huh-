#!/usr/bin/env python3
"""Taza OS inference performance logger.

Appends one row every INTERVAL seconds to inference_perf_log.csv.
Runs independently of dashboard.py (own systemd service, own cadence).
Background data capture only -- no UI, no visualization.
"""
import csv, glob, json, subprocess, time, urllib.request
from datetime import datetime
from pathlib import Path

CSV = Path("/home/taza/reports/inference_perf_log.csv")
INTERVAL = 60  # seconds; within the 30-60s window, kept light
HDR = ["timestamp", "cpu_util_pct", "cpu_freq_mhz", "cpu_temp_c",
       "thermal_throttle_flag", "line_voltage", "tokens_per_sec",
       "prompt_tokens", "completion_tokens", "total_tokens", "context_used", "model"]


def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return r.stdout.strip()
    except Exception:
        return ""


def read_cpu_times():
    # aggregate cpu line from /proc/stat; idle bucket = idle + iowait
    with open("/proc/stat") as f:
        p = f.readline().split()
    vals = [int(x) for x in p[1:]]
    return sum(vals), vals[3] + vals[4]


def cpu_util(prev, cur):
    dtot = cur[0] - prev[0]
    didle = cur[1] - prev[1]
    if dtot <= 0:
        return ""
    return round((1 - didle / dtot) * 100, 1)


def cpu_freq_mhz():
    o = run("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null")
    try:
        return int(o.strip()) // 1000
    except Exception:
        return ""


def cpu_temp_c():
    # same source dashboard.py uses: `sensors`, Package id 0 (fallback temp1)
    raw = run("sensors 2>/dev/null")
    t = {}
    for line in raw.splitlines():
        if "+" in line and "C" in line:
            try:
                label = line.split(":")[0].strip()
                val = float(line.split("+")[1].split("\xb0")[0])
                t[label] = val
            except Exception:
                pass
    v = t.get("Package id 0", t.get("temp1"))
    return round(v, 1) if v is not None else ""


def throttle_count():
    # cumulative core+package throttle events across all CPUs (sysfs)
    tot = 0
    found = False
    for f in glob.glob("/sys/devices/system/cpu/cpu*/thermal_throttle/*_throttle_count"):
        try:
            with open(f) as fh:
                tot += int(fh.read().strip())
                found = True
        except Exception:
            pass
    return tot if found else None


def line_voltage():
    raw = run("apcaccess status 2>/dev/null")
    for line in raw.splitlines():
        if line.startswith("LINEV"):
            try:
                return float(line.split(":")[1].split()[0])
            except Exception:
                return ""
    return ""


def _poll_slots(port):
    """Poll /slots on given port. Returns (tps, prompt_tokens, completion_tokens, context_used, busy)."""
    try:
        req = urllib.request.urlopen(f"http://localhost:{port}/slots", timeout=2)
        data = json.loads(req.read())
        if isinstance(data, list) and data:
            slot = data[0]
            if slot.get("state", 0) == 1:  # 1 = processing/serving
                tm = slot.get("timings", {})
                tps = round(tm.get("predicted_per_second", 0), 1)
                pt = int(tm.get("prompt_n", 0) or 0)
                ct = int(tm.get("predicted_n", 0) or 0)
                ctx = int(slot.get("n_ctx", 0) or 0)
                return tps, pt, ct, ctx, True
    except Exception:
        pass
    return "", "", "", "", False


def main():
    if not CSV.exists() or CSV.stat().st_size == 0:
        with open(CSV, "a", newline="") as f:
            csv.writer(f).writerow(HDR)
    prev = read_cpu_times()
    prev_thr = throttle_count()
    while True:
        time.sleep(INTERVAL)
        try:
            cur = read_cpu_times()
            util = cpu_util(prev, cur)
            prev = cur
            thr = throttle_count()
            if thr is None or prev_thr is None:
                flag = ""
            else:
                flag = 1 if thr > prev_thr else 0
            if thr is not None:
                prev_thr = thr

            tps_q, pt_q, ct_q, ctx_q, busy_q = _poll_slots(8081)
            tps_o, pt_o, ct_o, ctx_o, busy_o = _poll_slots(8082)

            # always write the system-health + qwen7b row
            with open(CSV, "a", newline="") as f:
                w = csv.writer(f)
                w.writerow([
                    datetime.now().isoformat(timespec="seconds"),
                    util, cpu_freq_mhz(), cpu_temp_c(), flag, line_voltage(),
                    tps_q, pt_q, ct_q, (pt_q + ct_q) if (pt_q != "" and ct_q != "") else "",
                    ctx_q, "qwen7b",
                ])
                # ornith row only when server is reachable (tps_o != "" means /slots answered)
                if tps_o != "" or busy_o:
                    w.writerow([
                        datetime.now().isoformat(timespec="seconds"),
                        "", "", "", "", "",
                        tps_o, pt_o, ct_o,
                        (pt_o + ct_o) if (pt_o != "" and ct_o != "") else "",
                        ctx_o, "ornith-35b",
                    ])
        except Exception:
            # never die on a single bad sample
            pass


if __name__ == "__main__":
    main()
