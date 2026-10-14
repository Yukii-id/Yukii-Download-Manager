"""Remote control lokal: HTTP API kecil yang HANYA bind ke 127.0.0.1.

Keamanan: semua request wajib membawa token (header X-YDM-Token atau ?token=)
yang disimpan di data/remote_token.txt dan dibuat acak saat pertama kali.
Dipakai mis. dari HP di jaringan yang sama melalui tunnel, atau skrip lokal.
Secara bawaan server ini MATI; aktifkan di Pengaturan > Remote.
"""
import json, os, secrets, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

def load_or_create_token(data_dir):
    path = os.path.join(data_dir, "remote_token.txt")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            t = f.read().strip()
            if t:
                return t
    t = secrets.token_urlsafe(24)
    os.makedirs(data_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(t)
    return t

class RemoteServer:
    def __init__(self, port, token, list_fn, add_fn):
        self.port = port
        self.token = token
        self._httpd = None
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass
            def _ok(self):
                return self.headers.get("X-YDM-Token") == outer.token or \
                    ("token=" + outer.token) in (self.path or "")
            def _send(self, code, obj):
                body = json.dumps(obj).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def do_GET(self):
                if not self._ok():
                    return self._send(401, {"error": "token salah"})
                if self.path.startswith("/api/downloads"):
                    return self._send(200, {"downloads": list_fn()})
                return self._send(404, {"error": "tidak ditemukan"})
            def do_POST(self):
                if not self._ok():
                    return self._send(401, {"error": "token salah"})
                if self.path.startswith("/api/downloads"):
                    n = int(self.headers.get("Content-Length") or 0)
                    try:
                        data = json.loads(self.rfile.read(n) or b"{}")
                    except Exception:
                        data = {}
                    url = (data.get("url") or "").strip()
                    if not url:
                        return self._send(400, {"error": "url kosong"})
                    did = add_fn(url)
                    return self._send(201, {"id": did})
                return self._send(404, {"error": "tidak ditemukan"})

        self._handler = H

    def start(self):
        self._httpd = ThreadingHTTPServer(("127.0.0.1", self.port), self._handler)
        th = threading.Thread(target=self._httpd.serve_forever, daemon=True, name="ydm-remote")
        th.start()
        return th

    def stop(self):
        if self._httpd:
            self._httpd.shutdown()
            self._httpd = None
