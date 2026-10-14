#!/usr/bin/env python3
"""Taza OS system metrics logger.

Every INTERVAL seconds, inserts one row per metric into the existing
system_metrics table (PostgreSQL, db tazaos). Metric sources mirror
dashboard.py / inference_perf_logger.py exactly.

Connection uses peer auth over the unix socket as user taza -- no
password is stored in this file. Background capture only; no UI.

ups_status is text ("ONLINE", "ONBATT", ...) but the table's value
column is DOUBLE PRECISION, so it is encoded numerically
(ONLINE->1.0, else 0.0) with the raw status string kept in `unit`.
"""
import subprocess, time, urllib.request
import psycopg2

INTERVAL = 60  # seconds
HOST = "n100"
DB = "tazaos"


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
        return None
    return round((1 - didle / dtot) * 100, 1)


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
    return round(v, 1) if v is not None else None


def ram_used_pct():
    # from /proc/meminfo: used% = (MemTotal - MemAvailable) / MemTotal * 100
    mem = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                k, _, v = line.partition(":")
                mem[k.strip()] = float(v.split()[0])  # kB
        total = mem.get("MemTotal")
        avail = mem.get("MemAvailable")
        if total and avail is not None and total > 0:
            return round((total - avail) / total * 100, 1)
    except Exception:
        pass
    return None


def ups():
    # returns (status_text, status_numeric, linev, bcharge, timeleft) from apcaccess
    # bcharge (BCHARGE, "NN.N Percent") and timeleft (TIMELEFT, "NN.N Minutes")
    # are critical for the power-down load test. Parsed with the same
    # split(":",1)[1].split()[0] idiom as linev, which drops the unit suffix.
    raw = run("apcaccess status 2>/dev/null")
    status, linev, bcharge, timeleft = None, None, None, None
    for line in raw.splitlines():
        if line.startswith("STATUS"):
            status = line.split(":", 1)[1].strip()
        elif line.startswith("LINEV"):
            try:
                linev = float(line.split(":", 1)[1].split()[0])
            except Exception:
                pass
        elif line.startswith("BCHARGE"):
            try:
                bcharge = float(line.split(":", 1)[1].split()[0])
            except Exception:
                pass
        elif line.startswith("TIMELEFT"):
            try:
                timeleft = float(line.split(":", 1)[1].split()[0])
            except Exception:
                pass
    status_num = 1.0 if status == "ONLINE" else (0.0 if status is not None else None)
    return status, status_num, linev, bcharge, timeleft


def llama_latency_ms():
    # wall-clock round trip to :8081/health; 0 if unreachable (never fail)
    t0 = time.monotonic()
    try:
        urllib.request.urlopen("http://localhost:8081/health", timeout=5).read()
        return round((time.monotonic() - t0) * 1000, 1)
    except Exception:
        return 0.0


def gather():
    """Return list of (metric, value, unit) rows; skips None-valued metrics."""
    rows = []
    temp = cpu_temp_c()
    if temp is not None:
        rows.append(("cpu_temp_c", temp, "celsius"))
    # cpu_util is computed in main() across the sleep interval
    ram = ram_used_pct()
    if ram is not None:
        rows.append(("ram_used_pct", ram, "percent"))
    status_txt, status_num, linev, bcharge, timeleft = ups()
    if status_num is not None:
        rows.append(("ups_status", status_num, status_txt))
    if linev is not None:
        rows.append(("ups_line_v", linev, "volts"))
    if bcharge is not None:
        rows.append(("ups_bcharge", bcharge, "percent"))
    if timeleft is not None:
        rows.append(("ups_timeleft", timeleft, "minutes"))
    rows.append(("llama_latency_ms", llama_latency_ms(), "ms"))
    return rows


def connect():
    conn = psycopg2.connect(dbname=DB)  # peer auth, unix socket, user taza
    conn.autocommit = True
    return conn


def main():
    conn = connect()
    prev = read_cpu_times()
    while True:
        time.sleep(INTERVAL)
        try:
            cur = read_cpu_times()
            util = cpu_util(prev, cur)
            prev = cur
            rows = gather()
            if util is not None:
                rows.append(("cpu_util_pct", util, "percent"))
            try:
                with conn.cursor() as c:
                    c.executemany(
                        "INSERT INTO system_metrics (host, metric, value, unit) "
                        "VALUES (%s, %s, %s, %s)",
                        [(HOST, m, v, u) for (m, v, u) in rows],
                    )
            except Exception:
                # reconnect once on a DB error, retry this batch
                try:
                    conn.close()
                except Exception:
                    pass
                conn = connect()
                with conn.cursor() as c:
                    c.executemany(
                        "INSERT INTO system_metrics (host, metric, value, unit) "
                        "VALUES (%s, %s, %s, %s)",
                        [(HOST, m, v, u) for (m, v, u) in rows],
                    )
        except Exception:
            # never die on a single bad cycle
            pass


if __name__ == "__main__":
    main()
