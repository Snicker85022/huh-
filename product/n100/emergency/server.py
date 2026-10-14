#!/usr/bin/env python3
"""Taza OS Crew Service — minimal stdlib HTTP server on :9001.

Serves the emergency ops brief and kitchen site guide from www/.
Routes:
  /             -> 302 redirect to /emergency
  /emergency    -> www/emergency.html
  /siteguide    -> www/siteguide.html
"""
import http.server
import os

PORT = 9001
BASE = os.path.dirname(os.path.abspath(__file__))
WWW = os.path.join(BASE, "www")

ROUTES = {
    "/emergency": "emergency.html",
    "/siteguide": "siteguide.html",
}


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "TazaCrew/1.0"

    def _send(self, code, body=b"", ctype="text/html; charset=utf-8", headers=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/") or "/"

        if path == "/":
            self._send(302, headers={"Location": "/emergency"})
            return

        fname = ROUTES.get(path)
        if not fname:
            self._send(404, b"<h1>404 Not Found</h1>")
            return

        fpath = os.path.join(WWW, fname)
        try:
            with open(fpath, "rb") as f:
                body = f.read()
        except OSError:
            self._send(500, b"<h1>500 Missing page file</h1>")
            return
        self._send(200, body)

    def log_message(self, fmt, *args):
        # Keep journald tidy; no token/secret exposure risk here.
        pass


if __name__ == "__main__":
    httpd = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Taza OS Crew Service listening on :{PORT}", flush=True)
    httpd.serve_forever()
