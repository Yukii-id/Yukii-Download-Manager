"""Tes engine YDM tanpa GUI: server HTTP lokal dengan dukungan Range.

Jalankan: python tests/test_engine.py
Menguji: unduh multi-segmen + hash sama, pause lalu resume sampai selesai,
dan unduh aliran tunggal dari server tanpa Range.
"""
import hashlib, os, sys, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ydm.db import Store
from ydm.manager import DownloadManager
from ydm.settings import Settings

DATA = os.urandom(5 * 1024 * 1024 + 12345)  # ~5 MB pola acak tetap per proses
DIGEST = hashlib.sha256(DATA).hexdigest()

class RangeHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass
    def _send(self, body, status=200, extra=None):
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Accept-Ranges", "bytes")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
    def do_GET(self):
        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):
            spec = rng[6:].split(",")[0]
            a, _, b = spec.partition("-")
            start = int(a) if a else 0
            end = int(b) if b else len(DATA) - 1
            end = min(end, len(DATA) - 1)
            self._send(DATA[start:end + 1], 206,
                       {"Content-Range": f"bytes {start}-{end}/{len(DATA)}"})
        else:
            self._send(DATA)

class NoRangeHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", str(len(DATA)))
        self.end_headers()
        self.wfile.write(DATA)

def wait_status(store, did, want, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = store.get(did)
        if r["status"] == want:
            return r
        if r["status"] == "error":
            raise AssertionError(f"error: {r['error']}")
        time.sleep(0.2)
    raise AssertionError(f"timeout menunggu {want}, status={store.get(did)['status']}")

def make_manager(tmp):
    settings = Settings(os.path.join(tmp, "settings.json"))
    settings.set("download_dir", tmp)
    settings.set("smart_sort", False)
    settings.set("max_concurrent", 3)
    store = Store(os.path.join(tmp, "db.sqlite3"))
    return DownloadManager(store, settings), store

def main():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), RangeHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    url = f"http://127.0.0.1:{port}/big.bin"

    with tempfile.TemporaryDirectory() as tmp:
        mgr, store = make_manager(tmp)
        # 1) multi-segmen sampai selesai + hash cocok
        did = mgr.add(url, save_dir=tmp, filename="big.bin", segments=8)
        r = wait_status(store, did, "completed")
        path = os.path.join(tmp, "big.bin")
        h = hashlib.sha256(open(path, "rb").read()).hexdigest()
        assert h == DIGEST, "hash hasil multi-segmen tidak cocok"
        leftovers = [f for f in os.listdir(tmp) if ".seg" in f]
        assert not leftovers, f"sisa berkas segmen: {leftovers}"
        print("OK 1: multi-segmen selesai, hash cocok, segmen dibersihkan")

        # 2) pause di tengah lalu resume (dibatasi 512 KB/dtk agar sempat dijeda)
        did2 = mgr.add(url, save_dir=tmp, filename="big2.bin", segments=4,
                       speed_limit=512 * 1024)
        time.sleep(1.0)
        mgr.pause(did2)
        r2 = wait_status(store, did2, "paused")
        assert 0 <= r2["downloaded"] <= len(DATA)
        segs = [f for f in os.listdir(tmp) if f.startswith("big2.bin") and ".seg" in f]
        assert segs, "berkas segmen pause tidak ditemukan (resume tidak mungkin)"
        mgr.start(did2)
        wait_status(store, did2, "completed")
        h2 = hashlib.sha256(open(os.path.join(tmp, "big2.bin"), "rb").read()).hexdigest()
        assert h2 == DIGEST, "hash setelah resume tidak cocok"
        print("OK 2: pause menyimpan segmen, resume menyelesaikan dengan hash cocok")
        mgr.shutdown()

    # 3) server tanpa Range -> aliran tunggal
    srv2 = ThreadingHTTPServer(("127.0.0.1", 0), NoRangeHandler)
    threading.Thread(target=srv2.serve_forever, daemon=True).start()
    url2 = f"http://127.0.0.1:{srv2.server_address[1]}/plain.bin"
    with tempfile.TemporaryDirectory() as tmp:
        mgr, store = make_manager(tmp)
        did = mgr.add(url2, save_dir=tmp, filename="plain.bin", segments=8)
        wait_status(store, did, "completed")
        h = hashlib.sha256(open(os.path.join(tmp, "plain.bin"), "rb").read()).hexdigest()
        assert h == DIGEST
        print("OK 3: server tanpa Range tetap selesai (aliran tunggal)")
        mgr.shutdown()

    srv.shutdown(); srv2.shutdown()
    print("SEMUA TES LULUS")

if __name__ == "__main__":
    main()
