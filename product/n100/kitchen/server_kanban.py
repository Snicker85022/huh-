import http.server, socketserver, os, json, threading, time, subprocess, re, io

KITCHEN = '/home/taza/kitchen'
EXCEPTIONS_FILE = os.path.join(KITCHEN, 'exceptions.json')
PREP_PHOTOS = os.path.join(KITCHEN, 'prep-photos')
PREP_LOG = os.path.join(KITCHEN, 'prep_completions.json')
os.makedirs(PREP_PHOTOS, exist_ok=True)
os.chdir(KITCHEN)

_vibe_lock = threading.Lock()
_vibe_state = {"vibe": None, "confidence": 0.0, "ts": 0.0, "device": None}

def _pg_log_vibe(entry):
    sql = (
        f"INSERT INTO kitchen_vibe_log (device, vibe, confidence, raw_label) "
        f"VALUES ('{entry['device']}', '{entry['vibe']}', {entry['confidence']}, '{entry['vibe']}');"
    )
    try:
        subprocess.run(["psql", "-U", "taza", "-d", "tazaos", "-c", sql],
                       capture_output=True, timeout=3)
    except Exception:
        pass

class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        if self.path == '/api/vibe-status':
            with _vibe_lock:
                active = (
                    _vibe_state["vibe"] == "positive"
                    and _vibe_state["confidence"] > 0.75
                    and (time.time() - _vibe_state["ts"]) < 30
                )
                resp = {"active": active, "vibe": _vibe_state["vibe"],
                        "confidence": _vibe_state["confidence"],
                        "device": _vibe_state["device"],
                        "age_s": round(time.time() - _vibe_state["ts"], 1)}
            body = json.dumps(resp).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/vibe':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                entry = json.loads(body)
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"error":"invalid json"}')
                return
            vibe = str(entry.get('vibe', ''))
            conf = float(entry.get('confidence', 0.0))
            dev = str(entry.get('device', 'unknown'))
            with _vibe_lock:
                _vibe_state["vibe"] = vibe
                _vibe_state["confidence"] = conf
                _vibe_state["ts"] = time.time()
                _vibe_state["device"] = dev
            threading.Thread(target=_pg_log_vibe,
                             args=({"vibe": vibe, "confidence": conf, "device": dev},),
                             daemon=True).start()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "active": vibe == "positive" and conf > 0.75}).encode())

        elif self.path == '/api/timer':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                entry = json.loads(body)
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"error":"invalid json"}')
                return
            label = str(entry.get('label', 'timer'))
            duration = int(entry.get('duration_seconds', 0))
            device = str(entry.get('device', 'unknown'))
            def _pg_log_timer(l, d, dev):
                sql = "INSERT INTO timers (label, duration_seconds, device) VALUES (%s, %s, %s);"
                try:
                    subprocess.run(
                        ["psql", "-U", "taza", "-d", "tazaos", "-c",
                         f"INSERT INTO timers (label, duration_seconds, device) VALUES ('{l}', {d}, '{dev}');"],
                        capture_output=True, timeout=3)
                except Exception:
                    pass
            threading.Thread(target=_pg_log_timer, args=(label, duration, device), daemon=True).start()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "label": label, "duration": duration}).encode())

        elif self.path == '/api/movement':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                entry = json.loads(body)
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"error":"invalid json"}')
                return
            device = str(entry.get('device', 'unknown'))
            obj_class = str(entry.get('object_class', ''))
            x_norm = float(entry.get('x', 0.0))
            y_norm = float(entry.get('y', 0.0))
            confidence = float(entry.get('confidence', 0.0))
            track_id = entry.get('track_id')
            session_id = str(entry.get('session_id', ''))
            def _pg_log_movement(dev, cls, x, y, conf, tid, sid):
                try:
                    tid_sql = 'NULL' if tid is None else str(int(tid))
                    subprocess.run(
                        ["psql", "-U", "taza", "-d", "tazaos", "-c",
                         f"INSERT INTO movement_log (device, session_id, object_class, x_norm, y_norm, confidence, track_id) "
                         f"VALUES ('{dev}', '{sid}', '{cls}', {x}, {y}, {conf}, {tid_sql});"],
                        capture_output=True, timeout=3)
                except Exception:
                    pass
            threading.Thread(target=_pg_log_movement,
                             args=(device, obj_class, x_norm, y_norm, confidence, track_id, session_id),
                             daemon=True).start()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        elif self.path == '/api/prep-photo':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            ct = self.headers.get('Content-Type', '')
            boundary = None
            for part in ct.split(';'):
                part = part.strip()
                if part.startswith('boundary='):
                    boundary = part[9:].strip('"')
            photo_bytes = None
            card_id = 'unknown'
            if boundary:
                sep = ('--' + boundary).encode()
                parts = body.split(sep)
                for p in parts:
                    if b'name="card_id"' in p:
                        card_id = p.split(b'\r\n\r\n', 1)[-1].strip().decode('utf-8', errors='replace').strip()
                    elif b'name="photo"' in p:
                        photo_bytes = p.split(b'\r\n\r\n', 1)[-1].rstrip(b'\r\n--')
            if photo_bytes:
                ts = time.strftime('%Y%m%d_%H%M%S')
                fname = f'{ts}_{card_id}.jpg'
                fpath = os.path.join(PREP_PHOTOS, fname)
                with open(fpath, 'wb') as f:
                    f.write(photo_bytes)
                resp = {"ok": True, "path": fpath}
            else:
                resp = {"ok": False, "error": "no photo data"}
            body_out = json.dumps(resp).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body_out)

        elif self.path == '/api/prep-completion':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                entry = json.loads(body)
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"error":"invalid json"}')
                return
            completions = []
            if os.path.exists(PREP_LOG):
                try:
                    with open(PREP_LOG, 'r') as f:
                        completions = json.load(f)
                except (json.JSONDecodeError, IOError):
                    completions = []
            entry['ts'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
            completions.append(entry)
            with open(PREP_LOG, 'w') as f:
                json.dump(completions, f, indent=2)
            def _pg_log_prep(e):
                card_id = str(e.get('card_id', '')).replace("'", "''")
                card_title = str(e.get('card_title', '')).replace("'", "''")
                crew = str(e.get('crew_member', '')).replace("'", "''")
                loc = str(e.get('location', '')).replace("'", "''")
                qty = float(e.get('leftover_qty', 0))
                unit = str(e.get('leftover_unit', '')).replace("'", "''")
                photo = str(e.get('photo_path', '')).replace("'", "''")
                sql = (f"INSERT INTO prep_completions (card_id, card_title, crew_member, location, "
                       f"leftover_qty, leftover_unit, photo_path) VALUES "
                       f"('{card_id}', '{card_title}', '{crew}', '{loc}', {qty}, '{unit}', '{photo}');")
                try:
                    subprocess.run(["psql", "-U", "taza", "-d", "tazaos", "-c", sql],
                                   capture_output=True, timeout=3)
                except Exception:
                    pass
            threading.Thread(target=_pg_log_prep, args=(entry,), daemon=True).start()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "count": len(completions)}).encode())

        elif self.path == '/api/exception':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                entry = json.loads(body)
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"error":"invalid json"}')
                return
            exceptions = []
            if os.path.exists(EXCEPTIONS_FILE):
                try:
                    with open(EXCEPTIONS_FILE, 'r') as f:
                        exceptions = json.load(f)
                except (json.JSONDecodeError, IOError):
                    exceptions = []
            exceptions.append(entry)
            with open(EXCEPTIONS_FILE, 'w') as f:
                json.dump(exceptions, f, indent=2)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "count": len(exceptions)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

socketserver.ThreadingTCPServer.allow_reuse_address = True
with socketserver.ThreadingTCPServer(('', 9003), H) as s:
    s.serve_forever()
