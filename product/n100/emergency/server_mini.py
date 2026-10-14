#!/usr/bin/env python3
"""Taza OS Crew Service - minimal stdlib HTTP server, zero dependencies.
Serves phone.html for /, /emergency, and /siteguide. Client-side JS reads
window.location.pathname to select the correct tab on load."""
import http.server
import socketserver
import os
import subprocess
import json
from datetime import datetime

PORT = 9001
HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phone.html")

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/emergency", "/siteguide", "/emergency/", "/siteguide/"):
            with open(HTML_PATH, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path in ("/status", "/status/"):
            self._handle_status()
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_status(self):
        try:
            result = subprocess.run(
                ["/sbin/apcaccess", "status"],
                capture_output=True, text=True, timeout=5
            )
            data = {}
            for line in result.stdout.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    data[key.strip()] = val.strip()
            response = {
                "status": data.get("STATUS", "UNKNOWN"),
                "bcharge": data.get("BCHARGE", "?").split()[0] if data.get("BCHARGE") else "?",
                "timeleft": data.get("TIMELEFT", "?").split()[0] if data.get("TIMELEFT") else "?",
                "linev": data.get("LINEV", "?").split()[0] if data.get("LINEV") else "?",
                "timestamp": datetime.now().strftime("%H:%M"),
            }
            # Check /tmp/taza_power_state for RESTORED info
            try:
                state_file = "/tmp/taza_power_state"
                if os.path.exists(state_file):
                    with open(state_file, "r") as sf:
                        content = sf.read().strip()
                    if content.startswith("RESTORED:"):
                        response["power_restored"] = content
            except Exception:
                pass  # non-critical, skip silently
        except Exception as e:
            response = {"error": str(e)}
        body = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # keep it quiet; systemd journal doesn't need per-request spam

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    with ReusableTCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Taza OS Crew Service on :{PORT}")
        httpd.serve_forever()
