#!/usr/bin/env python3
"""
ADB Fleet Watchdog  (Dispatch D-H)
Polls the fleet every 5 min (via systemd timer). Identifies devices by MAC
through the kernel neighbor table (ARP), NOT fixed IP, because DHCP reservations
are unreliable (TCL2 confirmed drifting from reserved .101 to dynamic .111).

Per cycle:
  1. Resolve current IP for each known MAC via `ip neigh show`.
  2. adb connect <ip>:5555 ; adb devices.
  3. Classify: connected / needs_human_tap / offline / needs_manual_repair.
  4. Write status JSON (per-device mac/current_ip/status/last_success + ts).
  5. Alert if a device is stuck needs_manual_repair for 3+ consecutive cycles.
  6. z33: read-only. Never connect, never disconnect, never touch its network.

No root on the devices means adb-tcp is NOT reboot-persistent; a rebooted device
that drops to 'refused' requires a manual USB re-pair. The watchdog cannot fix
that itself — it detects it and escalates via the alerts log.
"""

import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone

REPORTS = "/home/taza/reports"
STATUS_FILE = os.path.join(REPORTS, "adb_watchdog_status.json")
ALERTS_LOG = os.path.join(REPORTS, "adb_watchdog_alerts.log")
ADB_PORT = 5555
REPAIR_ALERT_THRESHOLD = 3  # consecutive needs_manual_repair cycles before alerting

# Blockable / managed devices — MAC is authoritative, reserved IP is a fallback.
DEVICES = [
    {"name": "MT1",   "mac": "48:5a:67:a0:4c:3e", "reserved": "192.168.2.104", "read_only": False},
    {"name": "MT2",   "mac": "48:5a:67:a0:74:31", "reserved": "192.168.2.108", "read_only": False},
    {"name": "TCL1",  "mac": "38:26:56:d5:b6:ad", "reserved": "192.168.2.106", "read_only": False},
    {"name": "TCL2",  "mac": "38:26:56:d5:b6:ab", "reserved": "192.168.2.101", "read_only": False},
    {"name": "ALEXA", "mac": "a8:4a:63:b4:f7:1f", "reserved": "192.168.2.109", "read_only": False},
    # z33: EXCLUDED from any blocking. Read-only monitor via global `adb devices`.
    # MAC/IP from ops memory (z33=.105); used only to identify it in the listing.
    {"name": "z33",   "mac": "20:18:0e:d5:a4:e3", "reserved": "192.168.2.105", "read_only": True},
]

# neigh states we consider usable, best first
STATE_RANK = {"REACHABLE": 0, "DELAY": 1, "PROBE": 2, "STALE": 3, "PERMANENT": 0}


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run(cmd, timeout=15):
    """Run a command, return (rc, stdout+stderr). Never raises."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    except Exception as e:  # noqa: BLE001
        return 1, f"ERROR:{e}"


def neigh_table():
    """Parse `ip neigh show` into list of dicts: {ip, mac, state}."""
    rc, out = run(["ip", "neigh", "show"])
    rows = []
    if rc != 0:
        return rows
    for line in out.splitlines():
        parts = line.split()
        if not parts:
            continue
        ip = parts[0]
        mac = None
        state = "UNKNOWN"
        if "lladdr" in parts:
            mac = parts[parts.index("lladdr") + 1].lower()
        # state is the trailing token(s); grab known keywords
        for tok in parts:
            if tok in STATE_RANK or tok in ("FAILED", "INCOMPLETE", "NOARP"):
                state = tok
        rows.append({"ip": ip, "mac": mac, "state": state})
    return rows


def resolve_ip(mac, reserved, table):
    """Best current IP for a MAC.
    Rule: among neigh entries with a valid (non-FAILED) lladdr for this MAC,
    prefer the reserved IP if it's present and valid; otherwise pick the entry
    with the best neigh state. Fall back to the reserved IP if nothing found
    (ARP may populate on the connect attempt)."""
    mac = mac.lower()
    cands = [r for r in table
             if r["mac"] == mac and r["state"] not in ("FAILED", "INCOMPLETE", "NOARP")]
    if not cands:
        return reserved, "fallback_reserved"
    for r in cands:
        if r["ip"] == reserved:
            return reserved, "neigh_reserved"
    cands.sort(key=lambda r: STATE_RANK.get(r["state"], 99))
    return cands[0]["ip"], f"neigh_drift({cands[0]['state']})"


def adb_devices_map():
    """Return {'ip:port': state} from `adb devices`."""
    rc, out = run(["adb", "devices"], timeout=20)
    m = {}
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices"):
            continue
        cols = line.split()
        if len(cols) >= 2:
            m[cols[0]] = cols[1]
    return m


def classify(target, dev_map, connect_out):
    """Map adb state + connect output to our status vocabulary."""
    state = dev_map.get(target)
    if state == "device":
        return "connected"
    if state == "unauthorized":
        return "needs_human_tap"
    if state == "offline":
        return "offline"
    # not in device list — infer from connect output
    low = connect_out.lower()
    if "refused" in low or "cannot connect" in low or "no route" in low or "actively refused" in low:
        return "needs_manual_repair"
    if "timeout" in low or "timed out" in low:
        return "offline"
    if "unauthorized" in low:
        return "needs_human_tap"
    return "needs_manual_repair"


def manage_device(dev, table, prev):
    target = None
    ip, how = resolve_ip(dev["mac"], dev["reserved"], table)
    target = f"{ip}:{ADB_PORT}"

    rc, connect_out = run(["adb", "connect", target], timeout=15)
    dev_map = adb_devices_map()
    status = classify(target, dev_map, connect_out)

    # offline → retry once (disconnect + reconnect)
    if status == "offline":
        run(["adb", "disconnect", target], timeout=10)
        run(["adb", "connect", target], timeout=15)
        dev_map = adb_devices_map()
        status = classify(target, dev_map, connect_out)

    prev_dev = prev.get(dev["name"], {})
    last_success = prev_dev.get("last_success")
    if status == "connected":
        last_success = now_iso()

    # consecutive needs_manual_repair counter
    repair_streak = prev_dev.get("repair_streak", 0)
    repair_streak = repair_streak + 1 if status == "needs_manual_repair" else 0

    return {
        "name": dev["name"],
        "mac": dev["mac"],
        "reserved_ip": dev["reserved"],
        "current_ip": ip,
        "ip_source": how,
        "target": target,
        "status": status,
        "last_success": last_success,
        "repair_streak": repair_streak,
        "read_only": False,
    }


def monitor_z33(dev, table, dev_map, prev):
    """Read-only. NEVER adb connect/disconnect. Just report presence."""
    ip, how = resolve_ip(dev["mac"], dev["reserved"], table)
    # Look for z33 in the already-fetched global device map (any port).
    state = dev_map.get(f"{ip}:{ADB_PORT}")
    if state is None:
        for tgt, st in dev_map.items():
            if tgt.startswith(ip + ":"):
                state = st
                break
    if state == "device":
        status = "connected"
    elif state in ("unauthorized", "offline"):
        status = state
    else:
        status = "not_connected"
    prev_dev = prev.get(dev["name"], {})
    last_success = prev_dev.get("last_success")
    if status == "connected":
        last_success = now_iso()
    return {
        "name": dev["name"],
        "mac": dev["mac"],
        "reserved_ip": dev["reserved"],
        "current_ip": ip,
        "ip_source": how,
        "target": f"{ip}:{ADB_PORT}",
        "status": status,
        "last_success": last_success,
        "read_only": True,
        "note": "read-only monitor; watchdog never connects, blocks, or modifies z33",
    }


def load_prev():
    try:
        with open(STATUS_FILE) as f:
            data = json.load(f)
        return {d["name"]: d for d in data.get("devices", [])}
    except Exception:  # noqa: BLE001
        return {}


def append_alert(dev):
    line = (f"{now_iso()} ALERT {dev['name']} stuck '{dev['status']}' for "
            f"{dev['repair_streak']} consecutive checks "
            f"(~{dev['repair_streak']*5}min); mac={dev['mac']} "
            f"current_ip={dev['current_ip']} — needs manual USB re-pair\n")
    with open(ALERTS_LOG, "a") as f:
        f.write(line)


def main():
    os.makedirs(REPORTS, exist_ok=True)
    prev = load_prev()
    table = neigh_table()
    dev_map = adb_devices_map()  # snapshot for z33 read-only

    results = []
    for dev in DEVICES:
        if dev["read_only"]:
            results.append(monitor_z33(dev, table, dev_map, prev))
        else:
            r = manage_device(dev, table, prev)
            if r["status"] == "needs_manual_repair" and r["repair_streak"] >= REPAIR_ALERT_THRESHOLD:
                append_alert(r)
            results.append(r)

    payload = {
        "timestamp": now_iso(),
        "cycle_epoch": int(time.time()),
        "devices": results,
    }
    tmp = STATUS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, STATUS_FILE)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
