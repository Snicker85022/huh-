#!/usr/bin/env python3
"""Spaghetti movement logger — receives POST from device vision scripts, stores to Postgres."""
import http.server, socketserver, os, json, subprocess, threading, time

PORT = 9004

def _pg_insert(device, session_id, obj_class, x_norm, y_norm, confidence, track_id):
    tid_sql = 'NULL' if track_id is None else str(int(track_id))
    sid = session_id or ''
    sql = (
        f"INSERT INTO movement_log (device, session_id, object_class, x_norm, y_norm, confidence, track_id) "
        f"VALUES ('{device}', '{sid}', '{obj_class}', {x_norm}, {y_norm}, {confidence}, {tid_sql});"
    )
    try:
        subprocess.run(["psql", "-U", "taza", "-d", "tazaos", "-c", sql],
                       capture_output=True, timeout=3)
    except Exception:
        pass

class SpaghettiHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_POST(self):
        if self.path == '/movement':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                entry = json.loads(body)
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error":"invalid json"}')
                return
            device    = str(entry.get('device', 'unknown'))
            session   = str(entry.get('session_id', ''))
            obj_class = str(entry.get('object_class', ''))
            x         = float(entry.get('x', 0.0))
            y         = float(entry.get('y', 0.0))
            conf      = float(entry.get('confidence', 0.0))
            track_id  = entry.get('track_id')
            threading.Thread(target=_pg_insert,
                             args=(device, session, obj_class, x, y, conf, track_id),
                             daemon=True).start()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        elif self.path == '/session/start':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                entry = json.loads(body)
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                return
            notes    = str(entry.get('notes', ''))
            event_id = entry.get('event_id')
            eid_sql  = 'NULL' if event_id is None else str(int(event_id))
            sql = f"INSERT INTO spaghetti_sessions (notes, event_id) VALUES ('{notes}', {eid_sql}) RETURNING id;"
            try:
                result = subprocess.run(["psql", "-U", "taza", "-d", "tazaos", "-t", "-c", sql],
                                        capture_output=True, timeout=3, text=True)
                session_id = result.stdout.strip()
            except Exception:
                session_id = ''
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "session_id": session_id}).encode())
        elif self.path == '/session/end':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                entry = json.loads(body)
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                return
            sid = str(entry.get('session_id', ''))
            sql = f"UPDATE spaghetti_sessions SET ended_at=NOW() WHERE id='{sid}';"
            try:
                subprocess.run(["psql", "-U", "taza", "-d", "tazaos", "-c", sql],
                               capture_output=True, timeout=3)
            except Exception:
                pass
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

socketserver.ThreadingTCPServer.allow_reuse_address = True
print(f"Spaghetti logger listening on :{PORT}")
with socketserver.ThreadingTCPServer(('', PORT), SpaghettiHandler) as s:
    s.serve_forever()
