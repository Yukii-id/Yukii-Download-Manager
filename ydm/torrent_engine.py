"""Wrapper BitTorrent opsional berbasis libtorrent.

Jika libtorrent belum terpasang, modul tetap bisa diimpor dan TorrentJob akan
memberi status error yang jelas. Pasang dengan: pip install libtorrent
"""
import os, threading, time

try:
    import libtorrent as lt
    AVAILABLE = True
    VERSION = getattr(lt, "version", "?")
except Exception:
    lt = None
    AVAILABLE = False
    VERSION = None

_session = None
_session_lock = threading.Lock()

def get_session():
    global _session
    if not AVAILABLE:
        return None
    with _session_lock:
        if _session is None:
            _session = lt.session({"listen_interfaces": "0.0.0.0:6881"})
        return _session

def parse_magnet_name(magnet):
    from urllib.parse import urlparse, parse_qs, unquote
    try:
        qs = parse_qs(urlparse(magnet).query)
        dn = qs.get("dn", [None])[0]
        if dn:
            return unquote(dn)
    except Exception:
        pass
    return "torrent"

class TorrentJob:
    """Satu unduhan torrent. on_event(kind, id, ...) sama seperti DownloadJob."""
    def __init__(self, record, on_event=None):
        self.rec = record
        self.id = record["id"]
        self.on_event = on_event or (lambda *a, **k: None)
        self.stop_event = threading.Event()
        self.thread = None
        self.handle = None
        self.speed = 0.0
        self.segments_state = []
        from collections import deque
        self.logs = deque(maxlen=300)

    def log(self, msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        self.logs.append(line)
        self.on_event("log", self.id, line)

    def pause(self):
        self.stop_event.set()
        try:
            if self.handle:
                self.handle.pause()
        except Exception:
            pass

    def set_speed_limit(self, bps):
        try:
            if self.handle:
                self.handle.set_download_limit(int(bps) if bps else -1)
        except Exception:
            pass

    def start(self):
        self.thread = threading.Thread(target=self._run, name=f"ydm-bt-{self.id}", daemon=True)
        self.thread.start()

    def _run(self):
        if not AVAILABLE:
            self.on_event("status", self.id, "error", 0,
                          "libtorrent belum terpasang. Jalankan: pip install libtorrent")
            return
        ses = get_session()
        src = self.rec["url"]  # magnet: atau path file .torrent
        try:
            os.makedirs(self.rec["save_dir"], exist_ok=True)
            if src.lower().startswith("magnet:"):
                params = lt.parse_magnet_uri(src)
                params.save_path = self.rec["save_dir"]
                self.handle = ses.add_torrent(params)
                name = parse_magnet_name(src)
            else:
                info = lt.torrent_info(src)
                params = lt.add_torrent_params()
                params.ti = info
                params.save_path = self.rec["save_dir"]
                self.handle = ses.add_torrent(params)
                name = info.name()
            self.on_event("meta", self.id, -1, name)
            self.on_event("status", self.id, "downloading")
            self.log(f"Torrent dimulai: {name}")
            while not self.stop_event.is_set():
                st = self.handle.status()
                total = st.total_wanted
                done = st.total_wanted_done
                self.speed = st.download_rate
                if total > 0:
                    self.on_event("meta", self.id, total, name)
                self.on_event("progress", self.id, done, self.speed, [])
                if st.is_seeding or (total > 0 and done >= total and st.progress >= 1.0):
                    self.on_event("status", self.id, "completed", done)
                    self.log("Torrent selesai (seeding dijeda otomatis oleh YDM).")
                    try:
                        self.handle.pause()
                    except Exception:
                        pass
                    return
                time.sleep(1)
            self.on_event("status", self.id, "paused", self.handle.status().total_wanted_done if self.handle else 0)
        except Exception as e:
            self.on_event("status", self.id, "error", 0, str(e))
            self.log(f"Error torrent: {e}")
